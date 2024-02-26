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
from unittest.mock import patch

from django.conf import settings
from django.utils import timezone

from cm.adcm_config.ansible import ansible_decrypt
from cm.job import ActionRunPayload, run_action
from cm.models import Action, JobLog, ServiceComponent, TaskLog
from cm.services.job.config import get_job_config
from cm.services.job.utils import JobScope, get_selector
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
            selector = get_selector(obj=object_, action=action)
            task = TaskLog.objects.create(
                task_object=object_,
                action=action,
                config=config,
                start_date=timezone.now(),
                finish_date=timezone.now(),
                selector=selector,
            )
            job = JobLog.objects.create(
                task=task, action=action, start_date=timezone.now(), finish_date=timezone.now(), selector=selector
            )

            with self.subTest(f"Own Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}.json.j2",
                    context={**self.context, "job_id": job.pk},
                )
                job_config = get_job_config(job_scope=JobScope(job_id=job.pk, object=object_))

                self.assertDictEqual(job_config, expected_data)

        for object_, config, type_name in (
            (self.cluster, self.FULL_CONFIG, "cluster"),
            (self.service, self.CONFIG_WITH_NONES, "service"),
            (self.component, None, "component"),
        ):
            action = Action.objects.filter(prototype=object_.prototype, name="with_config_on_host").first()
            selector = get_selector(obj=self.host_1, action=action)
            task = TaskLog.objects.create(
                task_object=self.host_1,
                action=action,
                config=config,
                start_date=timezone.now(),
                finish_date=timezone.now(),
                verbose=True,
                selector=selector,
            )
            job = JobLog.objects.create(
                task=task, action=action, start_date=timezone.now(), finish_date=timezone.now(), selector=selector
            )

            with self.subTest(f"Host Action for {object_.__class__.__name__}"):
                expected_data = self.render_json_template(
                    file=self.templates_dir / "action_configs" / f"{type_name}_on_host.json.j2",
                    context={**self.context, "job_id": job.pk},
                )
                job_config = get_job_config(job_scope=JobScope(job_id=job.pk, object=self.host_1))

                self.assertDictEqual(job_config, expected_data)

    def test_action_config_with_secrets_bug_adcm_5305(self):
        """
        Actually bug is about `run_action`, because it prepares `config` for task,
        but it was caught within `get_job_config` generation, so checked here
        """
        raw_value = "12345ddd"
        action = Action.objects.filter(prototype=self.service.prototype, name="name_and_pass").first()
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
