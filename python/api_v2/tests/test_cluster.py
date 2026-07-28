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

from cm.models import (
    Action,
    ActionHostGroup,
    ADCMEntityStatus,
    AnsibleConfig,
    Cluster,
    Component,
    ConfigHostGroup,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    Service,
    TaskLog,
)
from cm.tests.utils import gen_component, gen_host, gen_prototype, gen_service, generate_hierarchy
from core.status import FullStatusMap
from core.types import TaskID
from django.contrib.contenttypes.models import ContentType
from guardian.models import GroupObjectPermission
from rbac.models import User
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.dependencies import get_status_scenarios_manager
from tests.suites import ADCMDjangoAPISuite


class TestCluster(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.cluster_action = Action.objects.get(prototype=cls.cluster_1.prototype, name="action")

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def test_list_success(self):
        manager = get_status_scenarios_manager()
        manager.reset()
        response = (self.client.v2 / "clusters").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertSetEqual({cl["prototype"]["edition"] for cl in response.json()["results"]}, {"community"})
        manager.expect_not_called("get_raw_status")
        manager.expect_called("retrieve_status_map")

    def test_adcm_4539_ordering_success(self):
        self.uc.add_cluster(bundle=self.bundle_1, name="cluster_3", description="cluster_3")
        self.uc.add_cluster(bundle=self.bundle_2, name="cluster_4", description="cluster_3")

        response = (self.client.v2 / "clusters").get(query={"ordering": "name"})
        self.assertListEqual(
            [cluster["name"] for cluster in response.json()["results"]],
            ["cluster_1", "cluster_2", "cluster_3", "cluster_4"],
        )

        response = (self.client.v2 / "clusters").get(query={"ordering": "-name"})
        self.assertListEqual(
            [cluster["name"] for cluster in response.json()["results"]],
            ["cluster_4", "cluster_3", "cluster_2", "cluster_1"],
        )

    def test_retrieve_success(self):
        manager = get_status_scenarios_manager()
        response = (self.client.v2 / "clusters" / self.cluster_1.id).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1.pk)
        self.assertEqual(response.json()["prototype"]["edition"], "community")

        manager.expect_called_once("get_raw_status")
        manager.expect_not_called("retrieve_status_map")

    def test_filter_simple_types_success(self):
        filters = {
            "id": (self.cluster_1.id, 0),
            "name": (self.cluster_1.name, "wrong"),
            "prototypeName": (self.cluster_1.prototype.name, "wrong"),
            "prototypeDisplayName": (self.cluster_1.prototype.display_name, "wrong"),
        }

        for filter_name, (correct_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "clusters").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)

                response = (self.client.v2 / "clusters").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status_up_success(self):
        status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {"services": {}, "status": 0, "hosts": {}},
                str(self.cluster_2.pk): {"services": {}, "status": 16, "hosts": {}},
            }
        )
        with patch("api_v2.filters.retrieve_status_map", return_value=status_map):
            response = (self.client.v2 / "clusters").get(query={"status": ADCMEntityStatus.UP})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status_down_success(self):
        status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {"services": {}, "status": 0, "hosts": {}},
                str(self.cluster_2.pk): {"services": {}, "status": 16, "hosts": {}},
            }
        )
        with patch("api_v2.filters.retrieve_status_map", return_value=status_map):
            response = (self.client.v2 / "clusters").get(query={"status": ADCMEntityStatus.DOWN})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_create_success(self):
        response = (self.client.v2 / "clusters").post(
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": "new_test_cluster-1",
                "description": "Test cluster description",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())

    def test_create_unsupported_contract_version_fail(self):
        self.uc.set_unsupported_contract_version(prototype=self.cluster_1.prototype)

        response = (self.client.v2 / "clusters").post(
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": "unsupported_contract_version_cluster",
            }
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"], "Unsupported bundle's prototype usage")

    def test_create_without_required_field_fail(self):
        response = (self.client.v2 / "clusters").post(data={})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": "prototype_id - This field is required.;name - This field is required.;",
                "level": "error",
            },
        )

    def test_create_without_not_required_field_success(self):
        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "new_test_cluster"}
        )

        cluster = Cluster.objects.get(name="new_test_cluster")
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(cluster.description, "")

    def test_adcm_5371_create_start_digits_success(self):
        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "1new_test_cluster"}
        )

        cluster = Cluster.objects.get(name="1new_test_cluster")
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(cluster.description, "")

    def test_adcm_5371_create_dot_fail(self):
        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "new_test_cluster."}
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_adcm_5371_create_space_prohibited_end_start_fail(self):
        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": " new_test_cluster "}
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_adcm_5371_create_min_name_2_chars_success(self):
        response = (self.client.v2 / "clusters").post(data={"prototype_id": self.cluster_1.prototype.pk, "name": "a"})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        response = (self.client.v2 / "clusters").post(data={"prototype_id": self.cluster_1.prototype.pk, "name": "aa"})

        self.assertIsNotNone(Cluster.objects.filter(name="aa").first())
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_adcm_5371_create_max_name_150_chars_success(self):
        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "a" * 151}
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        response = (self.client.v2 / "clusters").post(
            data={"prototype_id": self.cluster_1.prototype.pk, "name": "a" * 150}
        )

        self.assertIsNotNone(Cluster.objects.filter(name="a" * 150).first())
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_create_same_name_fail(self):
        response = (self.client.v2 / "clusters").post(
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": self.cluster_1.name,
                "description": "Test cluster description",
            },
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_create_non_existent_prototype_fail(self):
        response = (self.client.v2 / "clusters").post(
            data={
                "prototypeId": self.get_non_existent_pk(Prototype),
                "name": "cool name",
                "description": "Test cluster description",
            },
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_update_failed(self):
        wrong_cluster_name = "__new_test_cluster_name"
        correct_cluster_name = "new_test_cluster_name"

        response = self.client.v2[self.cluster_1].patch(data={"name": wrong_cluster_name})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

        self.cluster_1.state = "not_created"
        self.cluster_1.save(update_fields=["state"])

        response = self.client.v2[self.cluster_1].patch(data={"name": correct_cluster_name})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_update_locking_concern_fail(self):
        cluster_ep = self.client.v2[self.cluster_1]
        response = (cluster_ep / "actions" / self.cluster_action / "run").post(
            data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = cluster_ep.patch(data={"name": "new_name"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "CLUSTER_CONFLICT",
                "desc": "Name change is available only if no locking concern exists",
                "level": "error",
            },
        )

    def test_update_success(self):
        new_test_cluster_name = "new_test_cluster_name"
        response = self.client.v2[self.cluster_1].patch(data={"name": new_test_cluster_name})

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.cluster_1.refresh_from_db()

        self.assertEqual(self.cluster_1.name, new_test_cluster_name)

    def test_delete_success(self):
        response = self.client.v2[self.cluster_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(pk=self.cluster_1.pk).exists())

    def test_adcm_6146_delete_generic_relations_on_cluster_deletion(self):
        response = self.client.v2[self.cluster_1, "config-groups"].post(data={"name": "Cluster CHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        chg_id = response.json()["id"]
        self.assertTrue(ConfigHostGroup.objects.filter(pk=chg_id).exists())

        response = self.client.v2[self.cluster_1, "action-host-groups"].post(data={"name": "Cluster AHG"})
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        ahg_id = response.json()["id"]
        self.assertTrue(ActionHostGroup.objects.filter(pk=ahg_id).exists())

        ansible_config_id = AnsibleConfig.objects.get(
            object_id=self.cluster_1.pk, object_type=ContentType.objects.get_for_model(self.cluster_1)
        ).pk

        response = self.client.v2[self.cluster_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(pk=self.cluster_1.pk).exists())

        self.assertFalse(ConfigHostGroup.objects.filter(pk=chg_id).exists())
        self.assertFalse(ActionHostGroup.objects.filter(pk=ahg_id).exists())
        self.assertFalse(AnsibleConfig.objects.filter(pk=ansible_config_id).exists())

    def test_service_prototypes_success(self):
        response = (self.client.v2[self.cluster_1] / "service-prototypes").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "adcm_5756",
                "adcm_7586",
                "adcm_7807",
                "adcm_8014_8016",
                "service_1",
                "service_1_clone",
                "service_2",
                "service_3_manual_add",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
                "service_6_delete_with_action",
                "service_with_miss_config_service",
            ],
        )

    def test_service_candidates_success(self):
        self.uc.add_services_to_cluster(names=["service_3_manual_add"], cluster=self.cluster_1)

        response = (self.client.v2[self.cluster_1] / "service-candidates").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "adcm_5756",
                "adcm_7586",
                "adcm_7807",
                "adcm_8014_8016",
                "service_1",
                "service_1_clone",
                "service_2",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
                "service_6_delete_with_action",
                "service_with_miss_config_service",
            ],
        )

    def test_depends_on_in_service_candidates(self) -> None:
        self.maxDiff = None

        bundle = self.uc.upload_bundle(self.test_bundles_dir / "complex_dependencies")
        cluster = self.uc.add_cluster(bundle=bundle, name="With Deps")
        service_proto = Prototype.objects.get(name="first_service", type="service")
        component_proto = Prototype.objects.get(name="first_component", type="component", parent=service_proto)

        candidates = self.client.v2[cluster, "service-candidates"].get().json()
        depend_on = {entry["name"]: entry["dependOn"] for entry in candidates}

        self.assertDictEqual(
            depend_on,
            {
                "first_service": None,
                "second_service": [
                    {
                        "servicePrototype": {
                            "id": service_proto.id,
                            "name": "first_service",
                            "displayName": "first_service",
                            "version": "1.5",
                            "license": {"status": "absent", "text": None},
                            "componentPrototypes": [
                                {
                                    "id": component_proto.id,
                                    "name": "first_component",
                                    "displayName": "first_component",
                                    "version": "1.5",
                                }
                            ],
                        }
                    }
                ],
            },
        )

    def test_service_create_success(self):
        service_prototype = Prototype.objects.filter(type="service").first()
        response = (self.client.v2[self.cluster_1] / "services").post(data=[{"prototype_id": service_prototype.pk}])
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()[0]["name"], service_prototype.name)
        self.assertEqual(Service.objects.get(cluster_id=self.cluster_1.pk).name, "service_1")

    def test_retrieve_ansible_config_success(self):
        expected_response = {"adcmMeta": {}, "config": {"defaults": {"forks": 5}}}

        response = self.client.v2[self.cluster_1, "ansible-config"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json(), expected_response)

    def test_retrieve_ansible_config_as_cluster_administrator_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="Cluster Administrator"):
            expected_response = {"adcmMeta": {}, "config": {"defaults": {"forks": 5}}}

            response = self.client.v2[self.cluster_1, "ansible-config"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json(), expected_response)

    def test_retrieve_ansible_config_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[self.cluster_1], role_name="View cluster configurations"):
            response = self.client.v2[self.cluster_1, "ansible-config"].get()

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_retrieve_ansible_config_parent_not_found_denied(self):
        self.client.login(**self.test_user_credentials)
        response = self.client.v2[self.cluster_1, "ansible-config"].get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_ansible_config_schema_success(self):
        response = self.client.v2[self.cluster_1, "ansible-config-schema"].get()

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ansible configuration",
            "description": "",
            "readOnly": False,
            "adcmMeta": {
                "isAdvanced": False,
                "isInvisible": False,
                "activation": None,
                "synchronization": None,
                "NoneValue": None,
                "isSecret": False,
                "stringExtra": None,
                "enumExtra": None,
            },
            "type": "object",
            "properties": {
                "defaults": {
                    "title": "defaults",
                    "type": "object",
                    "description": "",
                    "default": {},
                    "readOnly": False,
                    "adcmMeta": {
                        "isAdvanced": False,
                        "isInvisible": False,
                        "activation": None,
                        "synchronization": None,
                        "NoneValue": None,
                        "isSecret": False,
                        "stringExtra": None,
                        "enumExtra": None,
                    },
                    "additionalProperties": False,
                    "properties": {
                        "forks": {
                            "title": "forks",
                            "type": "integer",
                            "description": "",
                            "default": 5,
                            "readOnly": False,
                            "adcmMeta": {
                                "isAdvanced": False,
                                "isInvisible": False,
                                "activation": None,
                                "synchronization": None,
                                "NoneValue": None,
                                "isSecret": False,
                                "stringExtra": None,
                                "enumExtra": None,
                            },
                            "minimum": 1,
                        }
                    },
                    "required": ["forks"],
                }
            },
            "additionalProperties": False,
            "required": ["defaults"],
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertDictEqual(schema, response.json())

    def test_retrieve_ansible_config_fail(self):
        response = (self.client.v2 / "clusters" / str(self.get_non_existent_pk(model=Cluster)) / "ansible-config").get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_update_ansible_config_success(self):
        response = self.client.v2[self.cluster_1, "ansible-config"].post(data={"config": {"defaults": {"forks": 13}}})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        ansible_config = AnsibleConfig.objects.get(
            object_id=self.cluster_1.pk,
            object_type=ContentType.objects.get_for_model(model=self.cluster_1),
        )
        self.assertDictEqual(ansible_config.value, {"defaults": {"forks": "13"}})

    def test_update_ansible_config_as_cluster_administrator_success(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = self.client.v2[self.cluster_1, "ansible-config"].post(
                data={"config": {"defaults": {"forks": 13}}}
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)

            ansible_config = AnsibleConfig.objects.get(
                object_id=self.cluster_1.pk,
                object_type=ContentType.objects.get_for_model(model=self.cluster_1),
            )
            self.assertDictEqual(ansible_config.value, {"defaults": {"forks": "13"}})

    def test_update_ansible_config_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="ADCM User"):
            response = self.client.v2[self.cluster_1, "ansible-config"].post(
                data={"config": {"defaults": {"forks": 13}}}
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_update_ansible_config_fail(self):
        ansible_config = AnsibleConfig.objects.get(
            object_id=self.cluster_1.pk,
            object_type=ContentType.objects.get_for_model(model=self.cluster_1),
        )

        for value in (
            {"defaults": {"forks": 0}},
            {"defaults": {"forks": "13"}},
            {"defaults": {"forks": "13.0"}},
            {"defaults": {"forks": 13, "stdout_callback": "not_yaml"}},
            {"defaults": {"not_forks": "not_13"}},
            {"defaults": {}},
            {"not_defaults": {}},
        ):
            with self.subTest(value=value):
                response = self.client.v2[self.cluster_1, "ansible-config"].post(data={"config": value})

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                ansible_config.refresh_from_db()
                self.assertDictEqual(ansible_config.value, {"defaults": {"forks": "5"}})


class TestClusterActions(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.cluster_action = Action.objects.get(prototype=cls.cluster_1.prototype, name="action")
        cls.cluster_action_with_config = Action.objects.get(prototype=cls.cluster_1.prototype, name="with_config")
        cls.cluster_action_with_hc = Action.objects.get(prototype=cls.cluster_1.prototype, name="with_hc")

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = cls.uc.create_user(**cls.test_user_credentials)

    def test_list_cluster_actions_success(self):
        response = (self.client.v2[self.cluster_1] / "actions").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 3)

    def test_adcm_5271_adcm_user_has_no_action_perms(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="ADCM User"):
            response = (self.client.v2[self.cluster_1] / "actions").get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(len(response.json()), 0)

    def test_list_cluster_actions_no_actions_cluster_success(self):
        response = (self.client.v2[self.cluster_2] / "actions").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(response.json(), [])

    def test_list_cluster_actions_wrong_cluster_fail(self):
        response = (self.client.v2 / "clusters" / self.get_non_existent_pk(model=Cluster) / "actions").get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_retrieve_cluster_action_success(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action).get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def assert_task_status_is(self, task_id: TaskID, status: str):
        task_status = TaskLog.objects.values_list("status", flat=True).get(id=task_id)
        self.assertEqual(task_status, status)

    def test_run_cluster_action_success(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action / "run").post(
            data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched(response.json()["id"]).id
        self.assert_task_status_is(task_id, "created")

        self.task_runner.run_task(task_id)
        self.assert_task_status_is(task_id, "success")

    def test_run_action_with_config_success(self):
        config = {
            "simple": "kuku",
            "grouped": {"simple": 5, "second": 4.3},
            "after": ["something"],
            "activatable_group": {"text": "text"},
        }
        adcm_meta = {"/activatable_group": {"isActive": True}}

        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
            data={"configuration": {"config": config, "adcmMeta": adcm_meta}}
        )

        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        task_id = self.task_runner.expect_task_launched(response.json()["id"]).id
        task = TaskLog.objects.get(id=task_id)
        self.assertEqual(task.config, config)
        self.assertEqual(task.attr, {})

    def test_run_action_with_config_wrong_configuration_fail(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
            data={"configuration": []}
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BAD_REQUEST",
                "desc": "non_field_errors - Invalid data. Expected a dictionary, but got list.;",
                "level": "error",
            },
        )
        self.task_runner.expect_task_not_launched()

    def test_run_action_with_config_required_adcm_meta_fail(self):
        config = {"simple": "kuku", "grouped": {"simple": 5, "second": 4.3}, "after": ["something"]}

        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
            data={"configuration": {"config": config}},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "adcm_meta - This field is required.;", "level": "error"}
        )
        self.task_runner.expect_task_not_launched()

    def test_run_action_with_config_required_config_fail(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
            data={"configuration": {"adcmMeta": {}}},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "config - This field is required.;", "level": "error"}
        )
        self.task_runner.expect_task_not_launched()

    def test_retrieve_action_with_hc_success(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_hc).get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        hc_map = response.json()["hostComponentMapRules"]
        self.assertEqual(len(hc_map), 2)
        add, remove = sorted(hc_map, key=lambda rec: rec["action"])
        self.assertDictEqual(add, {"action": "add", "component": "component_1", "service": "service_1"})
        self.assertDictEqual(remove, {"action": "remove", "component": "component_2", "service": "service_1"})

    def test_adcm_6684_no_perms_remove_flag_success(self):
        cluster_custom_flag_path = self.test_bundles_dir / "cluster_custom_flag"
        cluster_custom_flag_bundle = self.add_bundle(source_dir=cluster_custom_flag_path)

        cluster_1 = self.uc.add_cluster(
            bundle=cluster_custom_flag_bundle, name="cluster_custom_flag_1", description="cluster_1"
        )

        action = Action.objects.get(name="flag_up_cluster", prototype=cluster_1.prototype)
        response = self.client.v2[cluster_1, "actions", action, "run"].post()
        self.assertEqual(response.status_code, HTTP_200_OK)

        concerns = cluster_1.concerns.all()
        self.assertEqual(len(cluster_1.concerns.all()), 1)
        self.assertEqual(concerns.first().cause, "job")

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="ADCM User"):
            response = self.client.v2[concerns.first()].delete()

        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)


class TestClusterMM(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_3_manual_add"], cluster=cls.cluster_1)[0]
        cls.service_2 = cls.uc.add_services_to_cluster(names=["service"], cluster=cls.cluster_2)[0]
        cls.component_1 = Component.objects.create(
            prototype=Prototype.objects.create(
                bundle=cls.bundle_1,
                type="component",
                display_name="test_component",
            ),
            cluster=cls.cluster_1,
            service=cls.service_1,
        )
        cls.component_2 = Component.objects.create(
            prototype=Prototype.objects.create(
                bundle=cls.bundle_2,
                type="component",
                display_name="test_component",
            ),
            cluster=cls.cluster_2,
            service=cls.service_2,
        )
        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="test-host", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="test-host-2", cluster=cls.cluster_2)

        cls.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        cls.test_user = User.objects.create_user(**cls.test_user_credentials)

    def setUp(self) -> None:
        super().setUp()

        self.client.login(**self.test_user_credentials)

        self.cluster_1_endpoints = [
            self.client.v2[self.component_1].path,
            self.client.v2[self.service_1].path,
            self.client.v2[self.cluster_1].path,
            (self.client.v2[self.cluster_1] / "hosts" / self.host_1).path,
        ]

        self.host_1_endpoint = self.client.v2[self.host_1].path
        self.cluster_1_and_host_mm_endpoints = [
            (ep / "maintenance-mode").path
            for ep in (
                self.client.v2[self.service_1],
                self.client.v2[self.component_1],
                self.client.v2[self.cluster_1] / "hosts" / self.host_1,
                self.client.v2[self.host_1],
            )
        ]

    def test_adcm_5051_change_mm_perm_success(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Manage cluster Maintenance mode"):
            for request in self.cluster_1_endpoints + [self.host_1_endpoint]:
                response = self.client.get(path=request)

                self.assertEqual(response.status_code, HTTP_200_OK)

            permissions_change_mm = GroupObjectPermission.objects.filter(
                permission__codename__contains="change_maintenance_mode"
            )
            permissions_view = GroupObjectPermission.objects.filter(permission__name__contains="view")
            self.assertEqual(permissions_change_mm.count(), 3)
            self.assertEqual(permissions_view.count(), 4)

            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="cluster").count(), 1)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="component").count(), 2)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="service").count(), 2)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="host").count(), 2)

    def test_adcm_5051_change_mm_perm_fail(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Manage cluster Maintenance mode"):
            for request in self.cluster_1_endpoints + [self.host_1_endpoint]:
                response = self.client.get(path=request)

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_5051_change_mm_perm_host_only_success(self):
        with self.grant_permissions(to=self.test_user, on=self.host_1, role_name="Manage Maintenance mode"):
            for request in self.cluster_1_endpoints:
                response = self.client.get(path=request)

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

            response = self.client.get(path=self.host_1_endpoint)
            self.assertEqual(response.status_code, HTTP_200_OK)

            permissions_change_mm = GroupObjectPermission.objects.filter(
                permission__codename__contains="change_maintenance_mode"
            )
            permissions_view = GroupObjectPermission.objects.filter(permission__name__contains="view")
            self.assertEqual(permissions_change_mm.count(), 1)
            self.assertEqual(permissions_view.count(), 1)

            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="cluster").count(), 0)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="component").count(), 0)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="service").count(), 0)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="host").count(), 2)

    def test_adcm_5051_change_mm_perm_host_only_fail(self):
        with self.grant_permissions(to=self.test_user, on=self.host_2, role_name="Manage Maintenance mode"):
            for request in self.cluster_1_endpoints:
                response = self.client.get(path=request)

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_adcm_5051_post_change_mm_perm_success(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_1, role_name="Manage cluster Maintenance mode"):
            for request in self.cluster_1_and_host_mm_endpoints:
                response = self.client.post(path=request, data={"maintenance_mode": "on"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["maintenanceMode"], "on")

                response = self.client.post(path=request, data={"maintenance_mode": "off"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["maintenanceMode"], "off")

    def test_adcm_5051_post_change_mm_perm_wrong_object_fail(self):
        with self.grant_permissions(to=self.test_user, on=self.cluster_2, role_name="Manage cluster Maintenance mode"):
            for request in self.cluster_1_and_host_mm_endpoints:
                response = self.client.post(path=request, data={"maintenance_mode": "on"})

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)


class TestClusterStatuses(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        hierarchy_1 = generate_hierarchy()
        cls.cluster_1 = hierarchy_1["cluster"]
        cls.service_11 = hierarchy_1["service"]
        cls.component_111 = hierarchy_1["component"]
        component_112_prototype = gen_prototype(
            bundle=cls.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_112"
        )
        cls.component_112 = gen_component(service=cls.service_11, prototype=component_112_prototype)
        service_12_prototype = gen_prototype(
            bundle=cls.cluster_1.prototype.bundle, proto_type=ObjectType.SERVICE, name="service_12"
        )
        cls.service_12 = gen_service(cluster=cls.cluster_1, prototype=service_12_prototype)
        component_121_prototype = gen_prototype(
            bundle=cls.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_121"
        )
        cls.component_121 = gen_component(service=cls.service_12, prototype=component_121_prototype)
        component_122_prototype = gen_prototype(
            bundle=cls.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_122"
        )
        cls.component_122 = gen_component(service=cls.service_12, prototype=component_122_prototype)
        cls.host_1 = hierarchy_1["host"]
        cls.host_2 = gen_host(provider=hierarchy_1["provider"], cluster=cls.cluster_1)
        cls.uc.set_hostcomponent(
            cluster=cls.cluster_1,
            entries=[
                (cls.host_1, cls.component_111),
                (cls.host_1, cls.component_112),
                (cls.host_1, cls.component_121),
                (cls.host_2, cls.component_122),
                (cls.host_2, cls.component_112),
            ],
        )

        hierarchy_2 = generate_hierarchy()
        cls.cluster_2 = hierarchy_2["cluster"]
        cls.service_21 = hierarchy_2["service"]
        cls.component_211 = hierarchy_2["component"]
        cls.host_3 = hierarchy_2["host"]

        cls.status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(cls.cluster_1.pk): {
                        "status": 0,
                        "hosts": {str(cls.host_1.pk): {"status": 0}, str(cls.host_2.pk): {"status": 16}},
                        "services": {
                            str(cls.service_11.pk): {
                                "status": 4,
                                "components": {
                                    str(cls.component_111.pk): {"status": 16},
                                    str(cls.component_112.pk): {"status": 0},
                                },
                                "details": [
                                    {"host": cls.host_1.pk, "component": cls.component_111.pk, "status": 0},
                                    {"host": cls.host_1.pk, "component": cls.component_112.pk, "status": 16},
                                    {"host": cls.host_2.pk, "component": cls.component_112.pk, "status": 0},
                                ],
                            },
                            str(cls.service_12.pk): {
                                "status": 0,
                                "components": {
                                    str(cls.component_121.pk): {"status": 0},
                                    str(cls.component_122.pk): {"status": 2},
                                },
                                "details": [
                                    {"host": cls.host_1.pk, "component": cls.component_121.pk, "status": 0},
                                    {"host": cls.host_2.pk, "component": cls.component_122.pk, "status": 2},
                                ],
                            },
                        },
                    },
                    str(cls.cluster_2.pk): {"status": 16, "hosts": {str(cls.host_3.pk): {"status": 0}}, "services": {}},
                },
                "hosts": {
                    str(cls.host_1.pk): {"status": 0},
                    str(cls.host_2.pk): {"status": 16},
                    str(cls.host_3.pk): {"status": 0},
                },
            }
        )

    @staticmethod
    def get_name_status_pairs(entries: list[dict]) -> set[tuple[int, str]]:
        return {(entry["name"], entry["status"]) for entry in entries}

    @staticmethod
    def _set_maintenance_mode(obj: Host | Service, value: MaintenanceMode) -> None:
        obj.maintenance_mode = value
        update_field = "_maintenance_mode" if isinstance(obj, Service) else "maintenance_mode"
        obj.save(update_fields=[update_field])

    def test_services_statuses_success(self) -> None:
        manager = get_status_scenarios_manager()
        manager.set_status_map(self.status_map)
        self._set_maintenance_mode(obj=self.service_12, value=MaintenanceMode.ON)
        response = (self.client.v2[self.cluster_1] / "statuses" / "services").get()

        manager.expect_called("retrieve_status_map")

        self.assertEqual(response.status_code, HTTP_200_OK)
        services = response.json()["results"]
        self.assertEqual(len(services), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(services), {(self.service_11.name, "down"), (self.service_12.name, "up")}
        )
        service_1, service_2 = sorted(services, key=lambda i: i["id"])
        self.assertEqual(service_1["maintenanceMode"], MaintenanceMode.OFF)
        self.assertEqual(service_2["maintenanceMode"], MaintenanceMode.ON)
        self.assertEqual(len(service_1["components"]), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(service_1["components"]),
            {(self.component_111.name, "down"), (self.component_112.name, "up")},
        )
        self.assertEqual(len(service_2["components"]), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(service_2["components"]),
            {(self.component_121.name, "up"), (self.component_122.name, "down")},
        )

    def test_filter_services_statuses_by_mm_success(self):
        # distribute hosts:
        #   service_11 - host_1
        #   service_12 - host_2
        # set host_2 MM to ON (indirect service_12 MM = ON)
        self.uc.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                *((self.host_1, component) for component in self.service_11.components.all()),
                *((self.host_2, component) for component in self.service_12.components.all()),
            ],
        )
        self._set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)

        response = (self.client.v2[self.cluster_1] / "statuses" / "services").get(query={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], self.service_12.pk)

        response = (self.client.v2[self.cluster_1] / "statuses" / "services").get(query={"maintenanceMode": "off"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], self.service_11.pk)

    def test_filter_services_statuses_by_name_success(self):
        # set prototypes' display_names
        for i, service in enumerate(self.cluster_1.services.all()):
            prototype = service.prototype
            prototype.display_name = f"Service {i} test"
            prototype.save(update_fields=["display_name"])

        response = (self.client.v2[self.cluster_1] / "statuses" / "services").get(query={"displayName": "SERVICE"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == self.cluster_1.services.count())

        response = (self.client.v2[self.cluster_1] / "statuses" / "services").get(query={"displayName": "SeRvIcE 0"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        target_service = self.cluster_1.services.get(prototype__display_name="Service 0 test")
        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], target_service.id)

    def test_hosts_statuses_success(self) -> None:
        manager = get_status_scenarios_manager()
        manager.set_status_map(self.status_map)
        self._set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)
        response = (self.client.v2[self.cluster_1] / "statuses" / "hosts").get()

        manager.expect_called("retrieve_status_map")

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["results"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(self.get_name_status_pairs(entries), {(self.host_1.name, "up"), (self.host_2.name, "down")})
        host_1, host_2 = sorted(entries, key=lambda i: i["id"])
        self.assertEqual(host_1["maintenanceMode"], MaintenanceMode.OFF)
        self.assertEqual(host_2["maintenanceMode"], MaintenanceMode.ON)

    def test_filter_hosts_statuses_by_mm_success(self):
        self._set_maintenance_mode(obj=self.host_2, value=MaintenanceMode.ON)

        response = (self.client.v2[self.cluster_1] / "statuses" / "hosts").get(query={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], self.host_2.id)

        response = (self.client.v2[self.cluster_1] / "statuses" / "hosts").get(query={"maintenanceMode": "off"})
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], self.host_1.id)

    def test_filter_hosts_statuses_by_name_success(self):
        response = (self.client.v2[self.cluster_1] / "statuses" / "hosts").get(
            query={"name": self.host_1.fqdn[:-2].upper()}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)

        response = response.json()
        self.assertTrue(response["count"] == len(response["results"]) == 1)
        self.assertEqual(response["results"][0]["id"], self.host_1.id)

    def test_components_of_service_statuses_success(self) -> None:
        manager = get_status_scenarios_manager()
        manager.set_status_map(self.status_map)
        response = (self.client.v2[self.service_11] / "statuses").get()

        manager.expect_called("retrieve_status_map")

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["components"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.component_111.name, "down"), (self.component_112.name, "up")},
        )

    def test_hc_statuses_of_component_success(self) -> None:
        manager = get_status_scenarios_manager()
        manager.set_status_map(self.status_map)
        response = (self.client.v2[self.component_112] / "statuses").get()

        manager.expect_called("retrieve_status_map")

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["hostComponents"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.host_1.name, "down"), (self.host_2.name, "up")},
        )

    def test_hc_statuses_of_host_success(self) -> None:
        manager = get_status_scenarios_manager()
        manager.set_status_map(self.status_map)
        response = (self.client.v2[self.cluster_1] / "hosts" / self.host_1 / "statuses").get()

        manager.expect_called("retrieve_status_map")

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["hostComponents"]
        self.assertEqual(len(entries), 3)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.component_111.name, "up"), (self.component_112.name, "down"), (self.component_121.name, "up")},
        )


class TestAdvancedFilters(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.status_map = FullStatusMap.model_validate(
            {
                "clusters": {
                    str(cls.cluster_1.pk): {"services": {}, "status": 0, "hosts": {}},
                    str(cls.cluster_2.pk): {"services": {}, "status": 16, "hosts": {}},
                }
            }
        )

    def test_filter_by_status__eq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "clusters").get(query={"status__eq": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "clusters").get(query={"status__eq": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ieq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: Down"):
                response = (self.client.v2 / "clusters").get(query={"status__ieq": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__ieq": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ne(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "clusters").get(query={"status__ne": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "clusters").get(query={"status__ne": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

    def test_filter_by_status__ine(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "clusters").get(query={"status__ine": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__ine": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

    def test_filter_by_status__in(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "clusters").get(query={"status__in": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "clusters").get(query={"status__in": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: down,bar"):
                response = (self.client.v2 / "clusters").get(query={"status__in": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_filter_by_status__iin(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "clusters").get(query={"status__iin": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__iin": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: Up,BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__iin": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status__exclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "clusters").get(query={"status__exclude": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "clusters").get(query={"status__exclude": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: down,bar"):
                response = (self.client.v2 / "clusters").get(query={"status__exclude": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status__iexclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "clusters").get(query={"status__iexclude": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__iexclude": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: Up,BaR"):
                response = (self.client.v2 / "clusters").get(query={"status__iexclude": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)
