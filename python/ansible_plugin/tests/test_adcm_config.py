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

from cm.adcm_config.ansible import ansible_decrypt
from cm.models import ADCMEntity, ConcernItem, ConfigLog, ServiceComponent
from cm.services.config import ConfigAttrPair
from cm.services.job.run.repo import JobRepoImpl
from core.job.types import Task

from ansible_plugin.base import CallResult
from ansible_plugin.errors import PluginTargetError
from ansible_plugin.executors.config import ADCMConfigPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins

EXECUTOR_MODULE = "ansible_plugin.executors.config"


class TestEffectsOfADCMAnsiblePlugins(BaseTestEffectsOfADCMAnsiblePlugins):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_bundle = self.add_bundle(self.bundles_dir / "cluster_complex_config")
        self.cluster = self.add_cluster(bundle=self.cluster_bundle, name="Cluster With Config")

        ConcernItem.objects.all().delete()

        self.service_1, self.service_2 = self.add_services_to_cluster(
            ["service_1", "service_2"], cluster=self.cluster
        ).order_by("prototype__name")
        self.component_1, self.component_2 = (
            ServiceComponent.objects.filter(service=self.service_1).order_by("prototype__name").all()
        )

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster, host=self.host_2)

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=((self.host_1, self.component_1), (self.host_1, self.component_2), (self.host_2, self.component_1)),
        )

    def get_config_attr(self, object_: ADCMEntity) -> ConfigAttrPair:
        object_.refresh_from_db(fields=["config"])
        return ConfigAttrPair(**ConfigLog.objects.values("config", "attr").get(id=object_.config.current))

    def execute_plugin(self, task: Task, call_arguments: str | dict) -> CallResult:
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMConfigPluginExecutor,
            call_arguments=call_arguments,
            call_context=job,
        )

        return executor.execute()

    def test_simple_change_one_value_success(self) -> None:
        changed_value = "awesomenewstring"
        in_group_value = "inside of group"

        result = self.execute_plugin(
            task=self.prepare_task(owner=self.cluster, name="dummy"),
            call_arguments=f"""
                type: cluster
                key: plain_s
                value: {changed_value}
            """,
        )

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, {"value": changed_value})

        after = self.get_config_attr(self.cluster)
        self.assertEqual(after.config["plain_s"], changed_value)
        self.assertEqual(after.config["g1"]["plain_s"], in_group_value)

    def test_multi_change_with_activation_success(self) -> None:
        values_to_change = {
            "plain_i": 4,
            "g1/records": ["hello", "14953"],
            "g1/group_b": True,
            "ag1/kv_pairs": {"good": "in-every", "per": "son"},
        }
        expected_config = self.get_config_attr(self.cluster).config
        expected_config["plain_i"] = values_to_change["plain_i"]
        expected_config["g1"]["records"] = values_to_change["g1/records"]
        expected_config["g1"]["group_b"] = values_to_change["g1/group_b"]
        expected_config["ag1"]["kv_pairs"] = values_to_change["ag1/kv_pairs"]

        result = self.execute_plugin(
            task=self.prepare_task(owner=self.cluster, name="dummy"),
            call_arguments={
                "type": "cluster",
                "parameters": [
                    *[{"key": key, "value": value} for key, value in values_to_change.items()],
                    {"key": "ag1", "active": True},
                ],
            },
        )

        self.assertIsNone(result.error, result.error)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, {"value": values_to_change})

        after = self.get_config_attr(self.cluster)
        self.assertTrue(after.attr["ag1"], {"active": True})
        self.assertEqual(after.config, expected_config)

    def test_no_change_call_on_provider_success(self) -> None:
        expected_config = self.get_config_attr(self.provider).config
        same_values = {"ip": expected_config["ip"], "inside/simple_secret": None}
        config_before = self.provider.config.current

        result = self.execute_plugin(
            task=self.prepare_task(owner=self.provider, name="dummy"),
            call_arguments={
                "type": "provider",
                "parameters": [*[{"key": key, "value": value} for key, value in same_values.items()]],
            },
        )

        self.assertIsNone(result.error, result.error)
        self.assertFalse(result.changed)
        self.assertEqual(result.value, {"value": same_values})

        after = self.get_config_attr(self.provider)
        self.assertEqual(after.config, expected_config)

        self.assertEqual(self.provider.config.current, config_before)

    def test_change_secret_field_success(self) -> None:
        new_secretfile = "multiline awesome\ncontent"

        result = self.execute_plugin(
            task=self.prepare_task(owner=self.provider, name="dummy"),
            call_arguments={"type": "provider", "key": "inside/complex_secret", "value": new_secretfile},
        )

        self.assertIsNone(result.error, result.error)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, {"value": new_secretfile})

        config = self.get_config_attr(self.provider).config
        self.assertEqual(ansible_decrypt(config["inside"]["complex_secret"]), new_secretfile)

    def test_change_only_active_success(self) -> None:
        object_ = self.service_1

        result = self.execute_plugin(
            task=self.prepare_task(owner=object_, name="dummy"),
            call_arguments="""
                type: service
                key: ag1
                active: true
            """,
        )

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, {"value": {}})

        after = self.get_config_attr(object_)
        self.assertTrue(after.attr["ag1"]["active"])

    def test_change_de_activate_multiple_groups_success(self) -> None:
        object_ = self.component_1

        result = self.execute_plugin(
            task=self.prepare_task(owner=object_, name="dummy"),
            call_arguments={
                "type": "component",
                "parameters": [{"key": "ag1", "active": True}, {"key": "ag2", "active": False}],
            },
        )

        self.assertIsNone(result.error)
        self.assertTrue(result.changed)
        self.assertEqual(result.value, {"value": {}})

        after = self.get_config_attr(object_)
        self.assertTrue(after.attr["ag1"]["active"])
        self.assertFalse(after.attr["ag2"]["active"])

    def test_no_change_multiple_activatable_groups_success(self) -> None:
        object_ = self.component_1

        result = self.execute_plugin(
            task=self.prepare_task(owner=object_, name="dummy"),
            call_arguments={
                "type": "component",
                "parameters": [{"key": "ag1", "active": False}, {"key": "ag2", "active": True}],
            },
        )

        self.assertIsNone(result.error)
        self.assertFalse(result.changed)
        self.assertEqual(result.value, {"value": {}})

        after = self.get_config_attr(object_)
        self.assertFalse(after.attr["ag1"]["active"])
        self.assertTrue(after.attr["ag2"]["active"])

    def test_change_one_host_from_another_fail(self) -> None:
        result = self.execute_plugin(
            task=self.prepare_task(owner=self.host_1, name="dummy"),
            call_arguments={"type": "host", "host_id": self.host_2.id, "key": "something", "value": "troll"},
        )

        self.assertIsInstance(result.error, PluginTargetError)
        self.assertEqual(result.error.message, "Wrong context. One host can't be changed from another's context.")
