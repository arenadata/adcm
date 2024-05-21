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

from pathlib import Path

from adcm.tests.base import BaseTestCase, BusinessLogicMixin, TaskTestMixin
from rest_framework.status import HTTP_422_UNPROCESSABLE_ENTITY

from cm.errors import AdcmEx
from cm.models import ConfigLog, JobLog, MaintenanceMode, ServiceComponent, TaskLog
from cm.services.job.jinja_scripts import get_env
from cm.tests.test_inventory.base import ansible_decrypt, decrypt_secrets


class TestJinjaScriptsEnvironment(BusinessLogicMixin, TaskTestMixin, BaseTestCase):
    maxDiff = None

    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent / "bundles"

        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")
        provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")

        cluster = self.add_cluster(bundle=cluster_bundle, name="test_cluster")
        self.cluster_task_id = self.prepare_task(owner=cluster, name="action_on_cluster").id

        service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=cluster).get()
        self.service_task_id = self.prepare_task(owner=service, name="action_on_service").id

        component = service.servicecomponent_set.get(prototype__name="component_1")
        self.component_task_id = self.prepare_task(owner=component, name="action_on_component").id

        provider = self.add_provider(bundle=provider_bundle, name="test_hostprovider")
        host = self.add_host(provider=provider, fqdn="test_host", cluster=cluster)
        self.set_hostcomponent(cluster=cluster, entries=((host, component),))

        self.component_host_task_id = self.prepare_task(owner=component, host=host, name="host_action_on_component").id

        common_config = ConfigLog.objects.get(pk=cluster.config.current).config
        common_config["password"] = ansible_decrypt(common_config["password"])

        self.expected_env_part = {
            "cluster": {
                "before_upgrade": {"state": None, "config": None},
                "edition": cluster.edition,
                "config": common_config,
                "id": cluster.pk,
                "multi_state": cluster.multi_state,
                "name": cluster.name,
                "state": cluster.state,
                "version": cluster.prototype.version,
                "imports": None,
            },
            "services": {
                service.prototype.name: {
                    "before_upgrade": {"state": None, "config": None},
                    "config": common_config,
                    "id": service.pk,
                    "multi_state": service.multi_state,
                    "state": service.state,
                    "display_name": service.display_name,
                    "maintenance_mode": service.maintenance_mode == MaintenanceMode.ON,
                    "version": service.prototype.version,
                    component.prototype.name: {
                        "before_upgrade": {"state": None, "config": None},
                        "component_id": component.pk,
                        "config": common_config,
                        "display_name": component.display_name,
                        "maintenance_mode": component.maintenance_mode.value == MaintenanceMode.ON,
                        "multi_state": component.multi_state,
                        "state": component.state,
                    },
                }
            },
            "groups": {
                "CLUSTER": [host.fqdn],
                "service_one_component": [host.fqdn],
                "service_one_component.component_1": [host.fqdn],
            },
            "task": {"config": None, "verbose": False},
        }

    def test_env_for_cluster(self):
        env = decrypt_secrets(source=get_env(task=TaskLog.objects.get(pk=self.cluster_task_id)))
        expected_env = {**self.expected_env_part, "action": {"name": "action_on_cluster", "owner_group": "CLUSTER"}}
        self.assertDictEqual(env, expected_env)

    def test_env_for_service(self):
        env = decrypt_secrets(source=get_env(task=TaskLog.objects.get(pk=self.service_task_id)))
        expected_env = {
            **self.expected_env_part,
            "action": {"name": "action_on_service", "owner_group": "service_one_component"},
        }
        self.assertDictEqual(env, expected_env)

    def test_env_for_component(self):
        env = decrypt_secrets(source=get_env(task=TaskLog.objects.get(pk=self.component_task_id)))
        expected_env = {
            **self.expected_env_part,
            "action": {"name": "action_on_component", "owner_group": "service_one_component.component_1"},
        }
        self.assertDictEqual(env, expected_env)

    def test_env_for_host(self):
        env = decrypt_secrets(source=get_env(task=TaskLog.objects.get(pk=self.component_host_task_id)))
        expected_env = {
            **self.expected_env_part,
            "action": {"name": "host_action_on_component", "owner_group": "service_one_component.component_1"},
        }
        self.assertDictEqual(env, expected_env)


class TestJinjaScriptsJobs(BusinessLogicMixin, TaskTestMixin, BaseTestCase):
    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent / "bundles"
        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")
        provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="test_cluster")
        service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster).get()
        self.component = ServiceComponent.objects.get(service=service)

        provider = self.add_provider(bundle=provider_bundle, name="test_hostprovider")
        self.host = self.add_host(provider=provider, fqdn="test_host", cluster=self.cluster)

    def test_jobs_generation(self):
        task_id = self.prepare_task(owner=self.cluster, name="jinja_scripts_action").id

        self.assertListEqual(
            list(JobLog.objects.filter(task_id=task_id).values_list("name", flat=True).order_by("id")),
            ["job1", "job2", "job3", "job4"],
        )
        self.assertEqual(
            dict(JobLog.objects.filter(task_id=task_id).values_list("name", "script")),
            {
                "job1": "playbook.yaml",
                "job2": "jinja/playbook.yaml",
                "job3": "inner/playbook.yaml",
                "job4": "jinja/inner/playbook.yaml",
            },
        )

        self.set_hostcomponent(cluster=self.cluster, entries=((self.host, self.component),))
        task_id = self.prepare_task(owner=self.cluster, name="jinja_scripts_action").id

        self.assertSetEqual(
            set(JobLog.objects.filter(task_id=task_id).values_list("name", flat=True)),
            {"job_if_component_1_group_exists", "job3", "job4"},
        )

    def test_unprocessable_template(self):
        initial_jobs_count = JobLog.objects.count()

        with self.assertRaises(expected_exception=AdcmEx) as err:
            self.prepare_task(owner=self.cluster, name="unprocessable_jinja_scripts_action")

        self.assertEqual(err.exception.code, "UNPROCESSABLE_ENTITY")
        self.assertEqual(err.exception.level, "error")
        self.assertEqual(err.exception.msg, "Can't render jinja template")
        self.assertEqual(err.exception.status_code, HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(JobLog.objects.count(), initial_jobs_count)
