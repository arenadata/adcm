# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from copy import deepcopy
from uuid import UUID

from core.legacy.job.dto import LaunchOptions, TaskPayloadDTO
from core.legacy.job.runners import (
    ADCMSettings,
    AnsibleSettings,
    ConsulSettings,
    ExternalSettings,
    IntegrationsSettings,
)
from core.types import CoreObjectDescriptor
from django.conf import settings
from use_cases.dto import ConfigurationDTO, RunActionDTO
import core

from cm.converters import model_name_to_core_type
from cm.legacy.adcm_config.ansible import ansible_decrypt
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.job.action import prepare_task_for_action
from cm.legacy.services.job.run._target_factories import prepare_ansible_job_config
from cm.legacy.services.job.run.repo import JobRepoImpl
from cm.legacy.utils import decrypt_secrets
from cm.models import Action, Component, ConcernItem
from cm.tests.dependencies import WithDishkaContainer
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.test_action_host_group import ScheduleTask
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestConfigAndImportsInInventory(WithDishkaContainer, BaseInventoryTestCase):
    CONFIG_WITH_NONES = {
        "boolean": True,
        "secrettext": "awe\nsopme\n\ttext\n",
        "list": ["1", "5", "baset"],
        "variant_inline": "f",
        "plain_group": {
            "file": "contente\t\n\n\n\tbest\n\t   ",
            "map": {"k": "v", "key": "val"},
            "simple": None,
            "listofstuff": None,
        },
        "integer": None,
        "float": None,
        "string": None,
        "password": None,
        "map": None,
        "secretmap": None,
        "json": None,
        "file": None,
        "secretfile": None,
        "variant_builtin": None,
        "activatable_group": {"simple": "inactive", "list": ["one", "two"]},
        "source_list": ["ok", "fail"],
        "text": None,
        "variant_config": None,
    }

    FULL_CONFIG = {
        **CONFIG_WITH_NONES,
        "integer": 4102,
        "float": 23.43,
        "string": "outside",
        "password": "unbreakable",
        "map": {"see": "yes", "no": "no"},
        "secretmap": {"see": "dont", "me": "you"},
        "json": '{"hey": ["yooo", 1]}',
        "file": "filecontent",
        "secretfile": "somesecrethere",
        "variant_builtin": "host-1",
        "plain_group": {**CONFIG_WITH_NONES["plain_group"], "simple": "ingroup"},
    }

    def setUp(self) -> None:
        super().setUp()

        self.provider = self.add_provider(
            bundle=self.add_bundle(self.bundles_dir / "provider_full_config"), name="Host Provider"
        )
        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(provider=self.provider, fqdn="host-2")
        self.host_3 = self.add_host(provider=self.provider, fqdn="host-3")

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service = self.add_services_to_cluster(service_names=["all_params"], cluster=self.cluster).get()
        self.component = Component.objects.get(service=self.service)

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

        self.context = {
            "hostprovider_bundle": self.provider.prototype.bundle,
            "cluster_bundle": self.cluster.prototype.bundle,
            "datadir": self.directories["DATA_DIR"],
            "stackdir": self.directories["STACK_DIR"],
            "filedir": self.directories["FILE_DIR"],
            "token": settings.STATUS_SECRET_KEY,
            "component_type_id": self.component.prototype_id,
            "service_type_id": self.service.prototype_id,
            "adcm_id": self.adcm_id,
            "cluster": self.cluster,
            "service": self.service,
            "component": self.component,
            "provider": self.provider,
            "host_1": self.host_1,
            "host_2": self.host_2,
            "host_3": self.host_3,
            "host_1_type_id": self.host_1.prototype_id,
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            consul=ConsulSettings(
                url=settings.CONSUL_URL, datacenter=settings.CONSUL_DATACENTER, cacert_file=settings.CONSUL_CACERT_FILE
            ),
        )

    def test_action_config(self) -> None:
        for object_, config, type_name in (
            (self.cluster, None, "cluster"),
            (self.service, self.FULL_CONFIG, "service"),
            (self.component, self.CONFIG_WITH_NONES, "component"),
            (self.provider, self.FULL_CONFIG, "provider"),
            (self.host_1, self.CONFIG_WITH_NONES, "host"),
        ):
            ConcernItem.objects.all().delete()

            # prepare_task_for_action is now checking sanity of config, so we have to pass the correct one
            action_name = "with_config" if type_name != "cluster" else "dummy"
            active = type_name in ("service", "provider")
            config_diff = {} if type_name != "provider" else {"variant_builtin": "host-3"}

            action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()

            with RunTaskMock() as run_task:
                configuration = None
                if config is not None:
                    configuration = ConfigurationDTO(
                        convert=lambda x, _: x,
                        input_config=core.config.Configuration(
                            values=(deepcopy(config) or {}) | config_diff,
                            attributes={"/activatable_group": core.config.Attributes(is_active=active)},
                        ),
                    )
                with self.container() as container:
                    container.get(ScheduleTask).do(
                        action_orm=action,
                        target=object_,
                        payload=RunActionDTO(configuration=configuration),
                    )

            task = JobRepoImpl.get_task(id=run_task.target_task.pk)
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Own Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}.json.j2",
                    context={**self.context, "job_id": job.id, "task_id": task.id},
                )
                topology = retrieve_cluster_topology(self.cluster.pk) if type_name != "provider" else None
                job_config = prepare_ansible_job_config(
                    task=task,
                    job=job,
                    configuration=self.configuration,
                    topology=topology,
                )

                self.assertTrue(isinstance(UUID(job_config["adcm"]["uuid"]), UUID))

                job_config = decrypt_secrets(job_config)
                job_config["adcm"]["uuid"] = "uuid_stub"

                self.assertDictEqual(job_config, expected_data)

        for object_, config, type_name in (
            (self.cluster, self.FULL_CONFIG, "cluster"),
            (self.service, self.CONFIG_WITH_NONES, "service"),
            (self.component, None, "component"),
        ):
            ConcernItem.objects.all().delete()
            # prepare_task_for_action is now checking sanity of config, so we have to pass the correct one
            action_name = "with_config_on_host" if type_name != "component" else "without_config_on_host"
            active = type_name == "cluster"

            action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()

            with RunTaskMock() as run_task:
                configuration = None
                if config is not None:
                    configuration = ConfigurationDTO(
                        convert=lambda x, _: x,
                        input_config=core.config.Configuration(
                            values=(deepcopy(config) or {}) | config_diff,
                            attributes={"/activatable_group": core.config.Attributes(is_active=active)},
                        ),
                    )
                with self.container() as container:
                    container.get(ScheduleTask).do(
                        action_orm=action,
                        target=self.host_1,
                        payload=RunActionDTO(configuration=configuration, launch=LaunchOptions(is_verbose=True)),
                    )

            task = JobRepoImpl.get_task(id=run_task.target_task.pk)
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Host Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}_on_host.json.j2",
                    context={**self.context, "job_id": job.id, "task_id": task.id},
                )
                job_config = prepare_ansible_job_config(
                    task=task,
                    job=job,
                    configuration=self.configuration,
                    topology=retrieve_cluster_topology(self.cluster.pk),
                )

                job_config = decrypt_secrets(job_config)
                job_config["adcm"]["uuid"] = "uuid_stub"

                self.assertDictEqual(job_config, expected_data)

    def test_adcm_5305_action_config_with_secrets_bug(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `prepare_ansible_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.get(prototype=self.service.prototype, name="name_and_pass")
        with RunTaskMock() as run_task:
            configuration = ConfigurationDTO(
                convert=lambda x, _: x,
                input_config=core.config.Configuration(values={"rolename": "test_user", "rolepass": raw_value}),
            )
            with self.container() as container:
                container.get(ScheduleTask).do(
                    action_orm=action,
                    target=self.service,
                    payload=RunActionDTO(configuration=configuration),
                )

        task = run_task.target_task
        self.assertIn("__ansible_vault", task.config["rolepass"])
        self.assertEqual(ansible_decrypt(task.config["rolepass"]["__ansible_vault"]), raw_value)

        task = JobRepoImpl.get_task(id=task.id)
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)
        self.assertIn("__ansible_vault", job_config["job"]["config"]["rolepass"])
        self.assertEqual(ansible_decrypt(job_config["job"]["config"]["rolepass"]["__ansible_vault"]), raw_value)

    def test_adcm_5314_action_jinja_config_with_secrets_bug(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `get_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.get(prototype=self.service.prototype, name="with_jinja")
        with RunTaskMock() as run_task:
            configuration = ConfigurationDTO(
                convert=lambda x, _: x,
                input_config=core.config.Configuration(values={"rolename": "test_user", "rolepass": raw_value}),
            )
            with self.container() as container:
                container.get(ScheduleTask).do(
                    action_orm=action,
                    target=self.service,
                    payload=RunActionDTO(configuration=configuration),
                )

        task = run_task.target_task

        self.assertIn("__ansible_vault", task.config["rolepass"])
        self.assertEqual(ansible_decrypt(task.config["rolepass"]["__ansible_vault"]), raw_value)

        job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)
        job_config = prepare_ansible_job_config(
            task=JobRepoImpl.get_task(task.id),
            job=job,
            configuration=self.configuration,
            topology=retrieve_cluster_topology(self.cluster.pk),
        )
        self.assertIn("__ansible_vault", job_config["job"]["config"]["rolepass"])
        self.assertEqual(ansible_decrypt(job_config["job"]["config"]["rolepass"]["__ansible_vault"]), raw_value)

    def test_adcm_5314_action_jinja_config_with_secret_map_and_default_null_password_bug(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `get_job_config` generation, so checked here
        """
        self.change_configuration(target=self.cluster, config_diff={"boolean": True})
        raw_value = {"key": "val", "another": "one"}
        action = Action.objects.get(prototype=self.service.prototype, name="with_jinja")
        with RunTaskMock() as run_task:
            configuration = ConfigurationDTO(
                convert=lambda x, _: x,
                input_config=core.config.Configuration(values={"reqsec": deepcopy(raw_value), "secretval": None}),
            )
            with self.container() as container:
                container.get(ScheduleTask).do(
                    action_orm=action,
                    target=self.service,
                    payload=RunActionDTO(configuration=configuration),
                )

        task = run_task.target_task

        self.assertIn("__ansible_vault", task.config["reqsec"]["key"])
        self.assertIn("__ansible_vault", task.config["reqsec"]["another"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["key"]["__ansible_vault"]), raw_value["key"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["another"]["__ansible_vault"]), raw_value["another"])
        self.assertEqual(task.config["secretval"], None)

        job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)
        job_config = prepare_ansible_job_config(
            task=JobRepoImpl.get_task(task.id),
            job=job,
            configuration=self.configuration,
            topology=retrieve_cluster_topology(self.cluster.pk),
        )
        self.assertIn("__ansible_vault", job_config["job"]["config"]["reqsec"]["key"])
        self.assertEqual(
            ansible_decrypt(job_config["job"]["config"]["reqsec"]["key"]["__ansible_vault"]), raw_value["key"]
        )
        self.assertEqual(job_config["job"]["config"]["secretval"], None)


class TestScriptPathsInActionConfig(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_various_path"), name="Main Cluster"
        )
        self.service_1 = self.add_services_to_cluster(service_names=["as_cluster"], cluster=self.cluster).first()

        self.context = {
            "cluster_bundle": self.cluster.prototype.bundle,
            "datadir": self.directories["DATA_DIR"],
            "stackdir": self.directories["STACK_DIR"],
            "token": settings.STATUS_SECRET_KEY,
            "adcm_id": self.adcm_id,
            "cluster": self.cluster,
            "service": self.service_1,
            "service_type_id": self.service_1.prototype.id,
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
            consul=ConsulSettings(
                url=settings.CONSUL_URL,
                datacenter=settings.CONSUL_DATACENTER,
                cacert_file=settings.CONSUL_CACERT_FILE,
            ),
        )

    def test_scripts_in_action_config(self) -> None:
        for action_name in ("job_proto_relative", "job_bundle_relative", "task_mixed"):
            for object_, type_name in ((self.cluster, "cluster"), (self.service_1, "service")):
                action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()
                target = CoreObjectDescriptor(
                    id=object_.pk, type=model_name_to_core_type(object_.__class__.__name__.lower())
                )
                task = prepare_task_for_action(
                    target=target,
                    orm_owner=object_,
                    orm_target=object_,
                    action=action.pk,
                    payload=TaskPayloadDTO(),
                )

                for job in JobRepoImpl.get_task_jobs(task_id=task.id):
                    prefix = f"{action_name}_{job.name if action_name == 'task_mixed' else ''}".strip("_")
                    with self.subTest(
                        f"Action {action_name} for {object_.__class__.__name__} {object_.name} [{prefix}]"
                    ):
                        expected_data = self.render_json_template(
                            file=self.templates_dir / "action_configs" / f"{prefix}_{type_name}.json.j2",
                            context={**self.context, "job_id": job.id},
                        )
                        job_config = prepare_ansible_job_config(
                            task=JobRepoImpl.get_task(task.id),
                            job=job,
                            configuration=self.configuration,
                            topology=retrieve_cluster_topology(self.cluster.pk),
                        )

                        self.assertTrue(isinstance(UUID(job_config["adcm"]["uuid"]), UUID))

                        job_config["adcm"]["uuid"] = "uuid_stub"

                        self.assertDictEqual(job_config, expected_data)
