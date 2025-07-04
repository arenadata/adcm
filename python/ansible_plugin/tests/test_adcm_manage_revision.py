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

from cm.converters import orm_object_to_core_descriptor
from cm.models import ADCMEntity, ConfigRevision
from cm.services.config import retrieve_primary_configs
from cm.services.hierarchy import retrieve_object_hierarchy
from cm.services.job.run.repo import JobRepoImpl

from ansible_plugin.executors.manage_revision import ADCMManageRevisionPluginExecutor
from ansible_plugin.tests.base import BaseTestEffectsOfADCMAnsiblePlugins


class TestADCMManageRevisionPluginExecutor(BaseTestEffectsOfADCMAnsiblePlugins):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.service_1 = self.add_services_to_cluster(["service_1"], cluster=self.cluster).first()
        self.component_1 = self.service_1.components.get(prototype__name="component_1")

        self.add_host_to_cluster(cluster=self.cluster, host=self.host_1)
        self.set_hostcomponent(cluster=self.cluster, entries=((self.host_1, self.component_1),))

    def get_related_configs(self, object_: ADCMEntity):
        hierarchy = retrieve_object_hierarchy(object_=orm_object_to_core_descriptor(object_))
        return retrieve_primary_configs(objects=hierarchy)

    @patch.object(ADCMManageRevisionPluginExecutor, attribute="_get_related_configs")
    def test_set_revisions_success(self, mock_get_related_configs):
        mock_get_related_configs.return_value = self.get_related_configs(self.cluster)
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        self.assertEqual(ConfigRevision.objects.count(), 0)

        for expected_changed in (True, False):
            with self.subTest(f"{expected_changed=}"):
                executor = self.prepare_executor(
                    executor_type=ADCMManageRevisionPluginExecutor,
                    call_arguments="""
                        operation: set_primary_revision
                        objects:
                          - type: cluster
                          - type: component
                            service_name: "service_1"
                            component_name: "component_1"
                    """,
                    call_context=job,
                )

                result = executor.execute()
                self.assertIsNone(result.error)
                self.assertEqual(result.changed, expected_changed)

                expected_revisions = {self.cluster.config.current, self.component_1.config.current}
                actual_revisions = set(ConfigRevision.objects.values_list("configlog_id", flat=True))
                self.assertSetEqual(actual_revisions, expected_revisions)

    @patch.object(ADCMManageRevisionPluginExecutor, attribute="_get_related_configs")
    def test_get_diff_success(self, mock_get_related_configs):
        current_config_ids = {
            self.cluster.config.current,
            self.service_1.config.current,
            self.component_1.config.current,
        }
        ConfigRevision.objects.bulk_create([ConfigRevision(configlog_id=id_) for id_ in current_config_ids])

        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        self.change_configuration(
            target=self.cluster,
            config_diff={
                "integer_field": -1,
                "map_field": {"integer_key": "-2", "string_key": "map_string_value"},
                "group": {
                    "group_integer_field": -11,
                    "group_map_field": {"integer_key": "-22", "string_key": "group_map_string_value"},
                },
                "activatable_group": {
                    "activatable_group_integer_field": -111,
                    "activatable_group_map_field": {
                        "integer_key": "-222",
                        "string_key": "activatable_group_map_string_value",
                    },
                },
            },
            meta_diff={"/activatable_group": {"isActive": False}},
        )
        self.change_configuration(
            target=self.service_1, config_diff={}, meta_diff={"/activatable_group": {"isActive": False}}
        )
        self.change_configuration(
            target=self.component_1, config_diff={"activatable_group": {"activatable_group_string_field": "new_string"}}
        )
        expected_diff = {
            "CLUSTER": {
                "diff": {
                    "group": {
                        "group_integer_field": {"value": [11, -11]},
                        "group_map_field": {
                            "value": [
                                {"integer_key": "22", "string_key": "group_map_string_value"},
                                {"integer_key": "-22", "string_key": "group_map_string_value"},
                            ]
                        },
                    },
                    "activatable_group": {
                        "activatable_group_integer_field": {"value": [111, -111]},
                        "activatable_group_map_field": {
                            "value": [
                                {"integer_key": "222", "string_key": "activatable_group_map_string_value"},
                                {"integer_key": "-222", "string_key": "activatable_group_map_string_value"},
                            ]
                        },
                    },
                    "integer_field": {"value": [1, -1]},
                    "map_field": {
                        "value": [
                            {"integer_key": "2", "string_key": "map_string_value"},
                            {"integer_key": "-2", "string_key": "map_string_value"},
                        ]
                    },
                },
                "attr_diff": {"activatable_group": {"active": {"value": [True, False]}}},
            },
            "services": {
                "service_1": {"diff": {}, "attr_diff": {"activatable_group": {"active": {"value": [True, False]}}}}
            },
            "components": {
                "service_1.component_1": {
                    "diff": {
                        "activatable_group": {
                            "activatable_group_string_field": {
                                "value": ["activatable_group_string_value", "new_string"]
                            }
                        }
                    },
                    "attr_diff": {},
                }
            },
        }

        mock_get_related_configs.return_value = self.get_related_configs(self.cluster)

        executor = self.prepare_executor(
            executor_type=ADCMManageRevisionPluginExecutor,
            call_arguments="""
                operation: get_primary_diff
                objects:
                    - type: cluster
                    - type: service
                      service_name: "service_1"
                    - type: component
                      service_name: "service_1"
                      component_name: "component_1"
                    - type: component
                      service_name: "service_1"
                      component_name: "component_2"
            """,
            call_context=job,
        )

        result = executor.execute()
        self.assertIsNone(result.error)
        self.assertDictEqual(result.value, expected_diff)

    def test_arguments_validation(self):
        task = self.prepare_task(owner=self.cluster, name="dummy")
        job, *_ = JobRepoImpl.get_task_jobs(task.id)

        executor = self.prepare_executor(
            executor_type=ADCMManageRevisionPluginExecutor,
            call_arguments="""
                operation: get_primary_diff
                objects:
                    - type: provider
                    - type: service
                      service_name: "service_1"
            """,
            call_context=job,
        )
        result = executor.execute()
        self.assertIsNotNone(result.error)
        self.assertIn("Target objects must belong to", result.error.message)
