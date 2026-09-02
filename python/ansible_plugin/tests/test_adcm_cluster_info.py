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

from cm.models import Component
from tests.suites import ADCMPluginExecutorSuite

from ansible_plugin.errors import PluginValidationError
from ansible_plugin.executors.cluster_info import ADCMClusterInfoPluginExecutor


class TestClusterInfoPluginExecutor(ADCMPluginExecutorSuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.service_1, *_ = cls.uc.add_services_to_cluster(["service_1"], cluster=cls.cluster)
        cls.component_1 = Component.objects.filter(service=cls.service_1, prototype__name="component_1").first()

        cls.uc.add_host_to_cluster(cls.cluster, cls.host_1)
        cls.uc.add_host_to_cluster(cls.cluster, cls.host_2)
        cls.uc.set_hostcomponent(cluster=cls.cluster, entries=[(cls.host_1, cls.component_1)])

        cls.observer_cluster = cls.uc.add_cluster(bundle=cls.cluster_bundle, name="Observer Cluster")

    def execute(self, arguments: str):
        task = self.prepare_task(owner=self.observer_cluster, name="dummy")
        job, *_ = self.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMClusterInfoPluginExecutor,
            call_arguments=arguments,
            call_context=job,
        )
        return executor.execute()

    def test_resolve_by_name_success(self) -> None:
        result = self.execute(f"name: {self.cluster.name}")

        self.assertIsNone(result.error)
        self.assertFalse(result.changed)
        self.assertTrue(result.value["found"])
        self.assertEqual(
            result.value["cluster"],
            {
                "id": self.cluster.id,
                "name": self.cluster.name,
                "uuid": str(self.cluster.uuid),
                "state": self.cluster.state,
            },
        )
        self.assertEqual(result.value["hosts"], sorted([self.host_1.fqdn, self.host_2.fqdn]))
        self.assertEqual(result.value["mapping"], {"service_1.component_1": [self.host_1.fqdn]})
        self.assertEqual(result.value["services"], ["service_1"])

    def test_resolve_by_uuid_success(self) -> None:
        result = self.execute(f"uuid: {self.cluster.uuid}")

        self.assertIsNone(result.error)
        self.assertTrue(result.value["found"])
        self.assertEqual(result.value["cluster"]["id"], self.cluster.id)

    def test_uuid_is_preferred_over_name_success(self) -> None:
        result = self.execute(
            f"""
            uuid: {self.cluster.uuid}
            name: {self.observer_cluster.name}
            """
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.value["cluster"]["id"], self.cluster.id)

    def test_empty_uuid_falls_back_to_name_success(self) -> None:
        result = self.execute(
            f"""
            uuid: ""
            name: {self.cluster.name}
            """
        )

        self.assertIsNone(result.error)
        self.assertEqual(result.value["cluster"]["id"], self.cluster.id)

    def test_unknown_cluster_reported_not_found_success(self) -> None:
        result = self.execute("name: no-such-cluster")

        self.assertIsNone(result.error)
        self.assertFalse(result.changed)
        self.assertEqual(result.value, {"found": False, "cluster": {}, "hosts": [], "mapping": {}, "services": []})

    def test_no_arguments_fail(self) -> None:
        result = self.execute("{}")

        self.assertIsInstance(result.error, PluginValidationError)
        self.assertIn("either `uuid` or `name`", result.error.message)

    def test_invalid_uuid_fail(self) -> None:
        result = self.execute("uuid: not-a-uuid")

        self.assertIsInstance(result.error, PluginValidationError)
