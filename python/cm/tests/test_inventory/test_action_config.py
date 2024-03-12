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
from unittest.mock import patch

from core.job.dto import TaskPayloadDTO
from core.job.runners import ADCMSettings, AnsibleSettings, ExternalSettings, IntegrationsSettings
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings

from cm.adcm_config.ansible import ansible_decrypt
from cm.converters import model_name_to_core_type
from cm.models import Action, ServiceComponent
from cm.services.job.action import ActionRunPayload, run_action
from cm.job import ActionRunPayload, run_action
from cm.models import Action, JobLog, ServiceComponent, SubAction, TaskLog
from cm.services.job.config import get_job_config
from cm.services.job.prepare import prepare_task_for_action
from cm.services.job.run._target_factories import prepare_ansible_job_config
from cm.services.job.run.repo import JobRepoImpl
from cm.tests.test_inventory.base import BaseInventoryTestCase


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
        "activatable_group": None,
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
        "activatable_group": {"simple": "inactive", "list": ["one", "two"]},
    }

    def setUp(self) -> None:
        super().setUp()

        self.hostprovider = self.add_provider(
            bundle=self.add_bundle(self.bundles_dir / "provider_full_config"), name="Host Provider"
        )
        self.host_1 = self.add_host(
            bundle=self.hostprovider.prototype.bundle, provider=self.hostprovider, fqdn="host-1"
        )
        self.host_2 = self.add_host(
            bundle=self.hostprovider.prototype.bundle, provider=self.hostprovider, fqdn="host-2"
        )

        self.cluster = self.add_cluster(
            bundle=self.add_bundle(self.bundles_dir / "cluster_full_config"), name="Main Cluster"
        )
        self.service = self.add_services_to_cluster(service_names=["all_params"], cluster=self.cluster).first()
        self.component = ServiceComponent.objects.get(service=self.service)

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)
        self.set_hostcomponent(
            cluster=self.cluster, entries=((self.host_1, self.component), (self.host_2, self.component))
        )

        self.context = {
            "hostprovider_bundle": self.hostprovider.prototype.bundle,
            "cluster_bundle": self.cluster.prototype.bundle,
            "datadir": self.directories["DATA_DIR"],
            "stackdir": self.directories["STACK_DIR"],
            "token": settings.STATUS_SECRET_KEY,
            "component_type_id": self.component.prototype_id,
        }

        self.configuration = ExternalSettings(
            adcm=ADCMSettings(code_root_dir=settings.CODE_DIR, run_dir=settings.RUN_DIR, log_dir=settings.LOG_DIR),
            ansible=AnsibleSettings(ansible_secret_script=settings.CODE_DIR / "ansible_secret.py"),
            integrations=IntegrationsSettings(status_server_token=settings.STATUS_SECRET_KEY),
        )

    def test_action_config(self) -> None:
        # Thou action has a defined config
        # `prepare_job_config` itself doesn't check input config sanity,
        # but `None` is a valid config,
        # so I find it easier to check it in pairs here rather than use a separate action
        for object_, config, type_name in (
            (self.cluster, None, "cluster"),
            (self.service, self.FULL_CONFIG, "service"),
            (self.component, self.CONFIG_WITH_NONES, "component"),
            (self.hostprovider, self.FULL_CONFIG, "hostprovider"),
            (self.host_1, self.CONFIG_WITH_NONES, "host"),
        ):
            action = Action.objects.filter(prototype=object_.prototype, name="with_config").first()
            obj_ = CoreObjectDescriptor(
                id=object_.pk, type=model_name_to_core_type(model_name=object_.__class__.__name__.lower())
            )
            task = prepare_task_for_action(
                target=obj_,
                owner=obj_,
                action=action.pk,
                payload=TaskPayloadDTO(conf=config),
            )
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Own Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}.json.j2",
                    context={**self.context, "job_id": job.id},
                )
                job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)

                self.assertDictEqual(job_config, expected_data)

        for object_, config, type_name in (
            (self.cluster, self.FULL_CONFIG, "cluster"),
            (self.service, self.CONFIG_WITH_NONES, "service"),
            (self.component, None, "component"),
        ):
            action = Action.objects.filter(prototype=object_.prototype, name="with_config_on_host").first()
            target = CoreObjectDescriptor(id=self.host_1.pk, type=ADCMCoreType.HOST)

            task = prepare_task_for_action(
                target=target,
                owner=CoreObjectDescriptor(
                    id=object_.pk, type=model_name_to_core_type(object_.__class__.__name__.lower())
                ),
                action=action.pk,
                payload=TaskPayloadDTO(verbose=True, conf=config),
            )
            job, *_ = JobRepoImpl.get_task_jobs(task.id)

            with self.subTest(f"Host Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}_on_host.json.j2",
                    context={**self.context, "job_id": job.id},
                )
                job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)

                self.assertDictEqual(job_config, expected_data)

    def test_action_config_with_secrets_bug_adcm_5305(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `prepare_ansible_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.filter(prototype=self.service.prototype, name="name_and_pass").first()
        with patch("cm.services.job.action.run_task"):
            task = run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"rolename": "test_user", "rolepass": raw_value}),
            )

        self.assertIn("__ansible_vault", task.config["rolepass"])
        self.assertEqual(ansible_decrypt(task.config["rolepass"]["__ansible_vault"]), raw_value)

        task = JobRepoImpl.get_task(id=task.id)
        job, *_ = JobRepoImpl.get_task_jobs(task.id)
        job_config = prepare_ansible_job_config(task=task, job=job, configuration=self.configuration)
        self.assertIn("__ansible_vault", job_config["job"]["config"]["rolepass"])
        self.assertEqual(ansible_decrypt(job_config["job"]["config"]["rolepass"]["__ansible_vault"]), raw_value)

    def test_action_jinja_config_with_secrets_bug_adcm_5314(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `get_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.filter(prototype=self.service.prototype, name="with_jinja").first()
        with patch("cm.job.run_task"):
            task = run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"rolename": "test_user", "rolepass": raw_value}),
                hosts=[],
            )

        self.assertIn("__ansible_vault", task.config["rolepass"])
        self.assertEqual(ansible_decrypt(task.config["rolepass"]["__ansible_vault"]), raw_value)

        job = JobLog.objects.filter(task=task).first()
        job_config = get_job_config(job_scope=JobScope(job_id=job.pk, object=self.service))
        self.assertIn("__ansible_vault", job_config["job"]["config"]["rolepass"])
        self.assertEqual(ansible_decrypt(job_config["job"]["config"]["rolepass"]["__ansible_vault"]), raw_value)

    def test_action_jinja_config_with_secret_map_and_default_null_password_bug_adcm_5314(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `get_job_config` generation, so checked here
        """
        self.change_configuration(target=self.cluster, config_diff={"boolean": True})
        raw_value = {"key": "val", "another": "one"}
        action = Action.objects.filter(prototype=self.service.prototype, name="with_jinja").first()
        with patch("cm.job.run_task"):
            task = run_action(
                action=action,
                obj=self.service,
                payload=ActionRunPayload(conf={"reqsec": deepcopy(raw_value), "secretval": None}),
                hosts=[],
            )

        self.assertIn("__ansible_vault", task.config["reqsec"]["key"])
        self.assertIn("__ansible_vault", task.config["reqsec"]["another"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["key"]["__ansible_vault"]), raw_value["key"])
        self.assertEqual(ansible_decrypt(task.config["reqsec"]["another"]["__ansible_vault"]), raw_value["another"])
        self.assertEqual(task.config["secretval"], None)

        job = JobLog.objects.filter(task=task).first()
        job_config = get_job_config(job_scope=JobScope(job_id=job.pk, object=self.service))
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

    def test_scripts_in_action_config(self) -> None:
        for action_name in ("job_proto_relative", "job_bundle_relative", "task_mixed"):
            for object_, type_name in ((self.cluster, "cluster"), (self.service_1, "service")):
                action = Action.objects.filter(prototype=object_.prototype, name=action_name).first()
                selector = get_selector(obj=object_, action=action)
                task = TaskLog.objects.create(
                    task_object=object_,
                    action=action,
                    start_date=timezone.now(),
                    finish_date=timezone.now(),
                    selector=selector,
                )
                if action.name != "task_mixed":
                    jobs = [
                        JobLog.objects.create(
                            task=task,
                            action=action,
                            start_date=timezone.now(),
                            finish_date=timezone.now(),
                            selector=selector,
                        )
                    ]
                else:
                    jobs = [
                        JobLog.objects.create(
                            task=task,
                            action=action,
                            sub_action=sub_action,
                            start_date=timezone.now(),
                            finish_date=timezone.now(),
                            selector=selector,
                        )
                        for sub_action in SubAction.objects.filter(action=action)
                    ]

                for job in jobs:
                    prefix = f"{action_name}_{job.sub_action.name if job.sub_action else ''}".strip("_")
                    with self.subTest(
                        f"Action {action_name} for {object_.__class__.__name__} {object_.name} [{prefix}]"
                    ):
                        expected_data = self.render_json_template(
                            file=self.templates_dir / "action_configs" / f"{prefix}_{type_name}.json.j2",
                            context={**self.context, "job_id": job.pk},
                        )
                        job_config = get_job_config(job_scope=JobScope(job_id=job.pk, object=object_))

                        self.assertDictEqual(job_config, expected_data)
