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

from core.job.dto import TaskPayloadDTO
from core.job.runners import ADCMSettings, AnsibleSettings, ExternalSettings, IntegrationsSettings
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings

from cm.adcm_config.ansible import ansible_decrypt
from cm.converters import model_name_to_core_type
from cm.models import Action, Component
from cm.services.job.action import ActionRunPayload, prepare_task_for_action, run_action
from cm.services.job.run._target_factories import prepare_ansible_job_config
from cm.services.job.run.repo import JobRepoImpl
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.test_inventory.base import BaseInventoryTestCase, decrypt_secrets


class TestConfigAndImportsInInventory(BaseInventoryTestCase):
    CONFIG_WITH_NONES = {
        "boolean": True,
        "secrettext": "awe\nsopme\n\ttext\n",
        "list": ["1", "5", "baset"],
        "variant_inline": "f",
        "plain_group": {"file": "contente\t\n\n\n\tbest\n\t   ", "map": {"k": "v", "key": "val"}, "simple": None},
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
        self.host_1 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-1")
        self.host_2 = self.add_host(bundle=self.provider.prototype.bundle, provider=self.provider, fqdn="host-2")
        self.host_3 = self.add_host(provider=self.provider, fqdn="host-3")

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service = self.add_services_to_cluster(service_names=["all_params"], cluster=self.cluster).first()
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
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
        )

    def test_action_config(self) -> None:
        for object_, config, type_name in (
            (self.cluster, None, "cluster"),
            (self.service, self.FULL_CONFIG, "service"),
            (self.component, self.CONFIG_WITH_NONES, "component"),
            (self.provider, self.FULL_CONFIG, "provider"),
            (self.host_1, self.CONFIG_WITH_NONES, "host"),
        ):
            # prepare_task_for_action is now checking sanity of config, so we have to pass the correct one
            action_name = "with_config" if type_name != "cluster" else "dummy"
            active = type_name in ("service", "provider")
            config_diff = {} if type_name != "provider" else {"variant_builtin": "host-3"}

            action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()
            obj_ = CoreObjectDescriptor(
                id=object_.pk, type=model_name_to_core_type(model_name=object_.__class__.__name__.lower())
            )
            task = prepare_task_for_action(
                target=obj_,
                orm_owner=object_,
                action=action.pk,
                payload=TaskPayloadDTO(
                    conf=(deepcopy(config) or {}) | config_diff, attr={"activatable_group": {"active": active}}
                ),
            )
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Own Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}.json.j2",
                    context={**self.context, "job_id": job.id, "task_id": task.id},
                )
                job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)

                self.assertDictEqual(decrypt_secrets(job_config), expected_data)

        for object_, config, type_name in (
            (self.cluster, self.FULL_CONFIG, "cluster"),
            (self.service, self.CONFIG_WITH_NONES, "service"),
            (self.component, None, "component"),
        ):
            # prepare_task_for_action is now checking sanity of config, so we have to pass the correct one
            action_name = "with_config_on_host" if type_name != "component" else "without_config_on_host"
            active = type_name == "cluster"

            action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()
            target = CoreObjectDescriptor(id=self.host_1.pk, type=ADCMCoreType.HOST)

            task = prepare_task_for_action(
                target=target,
                orm_owner=object_,
                action=action.pk,
                payload=TaskPayloadDTO(
                    verbose=True, conf=deepcopy(config), attr={"activatable_group": {"active": active}}
                ),
            )
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Host Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}_on_host.json.j2",
                    context={**self.context, "job_id": job.id, "task_id": task.id},
                )
                job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)

                self.assertDictEqual(decrypt_secrets(job_config), expected_data)

    def test_adcm_5305_action_config_with_secrets_bug(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `prepare_ansible_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.filter(prototype=self.service.prototype, name="name_and_pass").first()
        with RunTaskMock() as run_task:
            run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"rolename": "test_user", "rolepass": raw_value}),
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
        action = Action.objects.filter(prototype=self.service.prototype, name="with_jinja").first()
        with RunTaskMock() as run_task:
            run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"rolename": "test_user", "rolepass": raw_value}),
            )

        task = run_task.target_task

        self.assertIn("__ansible_vault", task.config["rolepass"])
        self.assertEqual(ansible_decrypt(task.config["rolepass"]["__ansible_vault"]), raw_value)

        job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)
        job_config = prepare_ansible_job_config(
            task=JobRepoImpl.get_task(task.id), job=job, configuration=self.configuration
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
        action = Action.objects.filter(prototype=self.service.prototype, name="with_jinja").first()
        with RunTaskMock() as run_task:
            run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"reqsec": deepcopy(raw_value), "secretval": None}),
            )

        task = run_task.target_task

        self.assertIn("__ansible_vault", task.config["reqsec"]["key"])
        self.assertIn("__ansible_vault", task.config["reqsec"]["another"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["key"]["__ansible_vault"]), raw_value["key"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["another"]["__ansible_vault"]), raw_value["another"])
        self.assertEqual(task.config["secretval"], None)

        job, *_ = JobRepoImpl.get_task_jobs(task_id=task.id)
        job_config = prepare_ansible_job_config(
            task=JobRepoImpl.get_task(task.id), job=job, configuration=self.configuration
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
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
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
                            task=JobRepoImpl.get_task(task.id), job=job, configuration=self.configuration
                        )

                        self.assertDictEqual(job_config, expected_data)
