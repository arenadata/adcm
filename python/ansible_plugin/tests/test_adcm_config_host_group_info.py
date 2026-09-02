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

from cm.models import Component, ConfigHostGroup
from django.contrib.contenttypes.models import ContentType
from tests.suites import ADCMPluginExecutorSuite

from ansible_plugin.errors import PluginRuntimeError
from ansible_plugin.executors.config_host_group_info import ADCMConfigHostGroupInfoPluginExecutor


class TestConfigHostGroupInfoPluginExecutor(ADCMPluginExecutorSuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.service_1, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster)
        cls.component_1 = Component.objects.filter(service=cls.service_1, prototype__name="component_1").first()

        cls.uc.add_host_to_cluster(cls.cluster, cls.host_1)
        cls.uc.set_hostcomponent(cluster=cls.cluster, entries=[(cls.host_1, cls.component_1)])

    def execute(self, arguments: dict | str):
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = self.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMConfigHostGroupInfoPluginExecutor,
            call_arguments=arguments,
            call_context=job,
        )
        return executor.execute()

    def create_group(self, name: str, with_host: bool = False) -> ConfigHostGroup:
        group = ConfigHostGroup.objects.create(
            object_id=self.service_1.pk,
            object_type=ContentType.objects.get_for_model(model=self.service_1),
            name=name,
            description="made for the test",
        )
        if with_host:
            group.hosts.add(self.host_1)

        return group

    def test_lists_groups_success(self) -> None:
        self.create_group("beta")
        self.create_group("alpha", with_host=True)

        result = self.execute({"type": "service", "service_name": "service_1"})

        self.assertIsNone(result.error)
        self.assertFalse(result.changed)
        self.assertEqual(result.value["names"], ["alpha", "beta"])
        self.assertEqual([group["name"] for group in result.value["groups"]], ["alpha", "beta"])
        self.assertEqual(result.value["groups"][0]["hosts"], [self.host_1.fqdn])
        self.assertNotIn("exists", result.value)

    def test_named_group_success(self) -> None:
        self.create_group("per-cluster", with_host=True)

        result = self.execute({"type": "service", "service_name": "service_1", "name": "per-cluster"})

        self.assertIsNone(result.error)
        self.assertTrue(result.value["exists"])
        self.assertEqual(result.value["hosts"], [self.host_1.fqdn])

    def test_missing_named_group_success(self) -> None:
        result = self.execute({"type": "service", "service_name": "service_1", "name": "never-created"})

        self.assertIsNone(result.error)
        self.assertFalse(result.value["exists"])
        self.assertEqual(result.value["hosts"], [])
        self.assertEqual(result.value["names"], [])

    def test_no_groups_success(self) -> None:
        result = self.execute({"type": "cluster"})

        self.assertIsNone(result.error)
        self.assertEqual(result.value, {"groups": [], "names": []})

    def test_host_target_fail(self) -> None:
        result = self.execute({"type": "host", "host_id": self.host_1.pk})

        self.assertIsInstance(result.error, PluginRuntimeError)
        self.assertIn("can't belong to a host", result.error.message)
