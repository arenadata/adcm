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

from adcm.tests.base import BusinessLogicMixin
from cm.models import (
    Action,
    ADCMEntityStatus,
    AnsibleConfig,
    Cluster,
    ClusterObject,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.status.client import FullStatusMap
from cm.tests.mocks.task_runner import RunTaskMock
from cm.tests.utils import gen_component, gen_host, gen_prototype, gen_service, generate_hierarchy
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

from api_v2.config.utils import convert_adcm_meta_to_attr
from api_v2.tests.base import BaseAPITestCase


class TestCluster(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

    def test_list_success(self):
        with patch("cm.services.status.client.api_request") as patched_request:
            response = (self.client.v2 / "clusters").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

        patched_request.assert_called_once()

    def test_adcm_4539_ordering_success(self):
        cluster_3 = self.add_cluster(bundle=self.bundle_1, name="cluster_3", description="cluster_3")
        cluster_4 = self.add_cluster(bundle=self.bundle_2, name="cluster_4", description="cluster_3")
        cluster_list = [self.cluster_1.name, self.cluster_2.name, cluster_3.name, cluster_4.name]
        response = (self.client.v2 / "clusters").get(query={"ordering": "name"})

        self.assertListEqual([cluster["name"] for cluster in response.json()["results"]], cluster_list)

        response = (self.client.v2 / "clusters").get(query={"ordering": "-name"})

        self.assertListEqual([cluster["name"] for cluster in response.json()["results"]], cluster_list[::-1])

    def test_retrieve_success(self):
        with patch("api_v2.views.retrieve_status_map") as patched_retrieve, patch(
            "api_v2.views.get_raw_status"
        ) as patched_raw:
            response = (self.client.v2 / "clusters" / self.cluster_1.id).get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1.pk)

        patched_raw.assert_called_once()
        patched_retrieve.assert_not_called()

    def test_filter_by_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"name": self.cluster_1.name})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_wrong_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"name": "wrong"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status_up_success(self):
        status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {"services": {}, "status": 0, "hosts": {}},
                str(self.cluster_2.pk): {"services": {}, "status": 16, "hosts": {}},
            }
        )
        with patch("api_v2.cluster.filters.retrieve_status_map", return_value=status_map):
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
        with patch("api_v2.cluster.filters.retrieve_status_map", return_value=status_map):
            response = (self.client.v2 / "clusters").get(query={"status": ADCMEntityStatus.DOWN})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_filter_by_prototype_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"prototypeName": self.cluster_1.prototype.name})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"prototypeName": "wrong"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_prototype_display_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"prototypeDisplayName": self.cluster_1.prototype.name})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_display_name_success(self):
        response = (self.client.v2 / "clusters").get(query={"prototypeDisplayName": "wrong"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_success(self):
        response = (self.client.v2 / "clusters").post(
            data={
                "prototype_id": self.cluster_1.prototype.pk,
                "name": "new_test_cluster",
                "description": "Test cluster description",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_crete_without_required_field_fail(self):
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
        with RunTaskMock():
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

    def test_service_prototypes_success(self):
        response = (self.client.v2[self.cluster_1] / "service-prototypes").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "adcm_5756",
                "service_1",
                "service_1_clone",
                "service_2",
                "service_3_manual_add",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
                "service_6_delete_with_action",
                "service_with_bound_to",
            ],
        )

    def test_service_candidates_success(self):
        self.add_services_to_cluster(service_names=["service_3_manual_add"], cluster=self.cluster_1)

        response = (self.client.v2[self.cluster_1] / "service-candidates").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [prototype["displayName"] for prototype in response.json()],
            [
                "adcm_5756",
                "service_1",
                "service_1_clone",
                "service_2",
                "service_4_save_config_without_required_field",
                "service_5_variant_type_without_values",
                "service_6_delete_with_action",
                "service_with_bound_to",
            ],
        )

    def test_service_create_success(self):
        service_prototype = Prototype.objects.filter(type="service").first()
        response = (self.client.v2[self.cluster_1] / "services").post(data=[{"prototype_id": service_prototype.pk}])
        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(response.json()[0]["name"], service_prototype.name)
        self.assertEqual(ClusterObject.objects.get(cluster_id=self.cluster_1.pk).name, "service_1")

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


class TestClusterActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.cluster_action = Action.objects.get(prototype=self.cluster_1.prototype, name="action")
        self.cluster_action_with_config = Action.objects.get(prototype=self.cluster_1.prototype, name="with_config")
        self.cluster_action_with_hc = Action.objects.get(prototype=self.cluster_1.prototype, name="with_hc")

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

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

    def test_run_cluster_action_success(self):
        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action / "run").post(
                data={"configuration": None, "isVerbose": True, "hostComponentMap": []}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")

    def test_run_action_with_config_success(self):
        config = {
            "simple": "kuku",
            "grouped": {"simple": 5, "second": 4.3},
            "after": ["something"],
            "activatable_group": {"text": "text"},
        }
        adcm_meta = {"/activatable_group": {"isActive": True}}

        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
                data={"configuration": {"config": config, "adcmMeta": adcm_meta}}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.config, config)
        self.assertEqual(run_task.target_task.attr, convert_adcm_meta_to_attr(adcm_meta))

    def test_run_action_with_config_wrong_configuration_fail(self):
        with RunTaskMock() as run_task:
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
        self.assertIsNone(run_task.target_task)

    def test_run_action_with_config_required_adcm_meta_fail(self):
        config = {"simple": "kuku", "grouped": {"simple": 5, "second": 4.3}, "after": ["something"]}

        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
                data={"configuration": {"config": config}},
            )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "adcm_meta - This field is required.;", "level": "error"}
        )
        self.assertIsNone(run_task.target_task)

    def test_run_action_with_config_required_config_fail(self):
        with RunTaskMock() as run_task:
            response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_config / "run").post(
                data={"configuration": {"adcmMeta": {}}},
            )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(), {"code": "BAD_REQUEST", "desc": "config - This field is required.;", "level": "error"}
        )
        self.assertIsNone(run_task.target_task)

    def test_retrieve_action_with_hc_success(self):
        response = (self.client.v2[self.cluster_1] / "actions" / self.cluster_action_with_hc).get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        hc_map = response.json()["hostComponentMapRules"]
        self.assertEqual(len(hc_map), 2)
        add, remove = sorted(hc_map, key=lambda rec: rec["action"])
        self.assertDictEqual(add, {"action": "add", "component": "component_1", "service": "service_1"})
        self.assertDictEqual(remove, {"action": "remove", "component": "component_2", "service": "service_1"})


class TestClusterMM(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_services_to_cluster(
            service_names=["service_3_manual_add"], cluster=self.cluster_1
        ).last()
        self.service_2 = self.add_services_to_cluster(service_names=["service"], cluster=self.cluster_2).last()
        self.component_1 = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle_1,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster_1,
            service=self.service_1,
        )
        self.component_2 = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle_2,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster_2,
            service=self.service_2,
        )
        self.host_1 = self.add_host(provider=self.provider, fqdn="test-host", cluster=self.cluster_1)
        self.host_2 = self.add_host(provider=self.provider, fqdn="test-host-2", cluster=self.cluster_2)

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = User.objects.create_user(**self.test_user_credentials)
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
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="servicecomponent").count(), 2)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="clusterobject").count(), 2)
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
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="servicecomponent").count(), 0)
            self.assertEqual(GroupObjectPermission.objects.filter(content_type__model="clusterobject").count(), 0)
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


class TestClusterStatuses(BaseAPITestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        hierarchy_1 = generate_hierarchy()
        self.cluster_1 = hierarchy_1["cluster"]
        self.service_11 = hierarchy_1["service"]
        self.component_111 = hierarchy_1["component"]
        component_112_prototype = gen_prototype(
            bundle=self.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_112"
        )
        self.component_112 = gen_component(service=self.service_11, prototype=component_112_prototype)
        service_12_prototype = gen_prototype(
            bundle=self.cluster_1.prototype.bundle, proto_type=ObjectType.SERVICE, name="service_12"
        )
        self.service_12 = gen_service(cluster=self.cluster_1, prototype=service_12_prototype)
        component_121_prototype = gen_prototype(
            bundle=self.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_121"
        )
        self.component_121 = gen_component(service=self.service_12, prototype=component_121_prototype)
        component_122_prototype = gen_prototype(
            bundle=self.cluster_1.prototype.bundle, proto_type=ObjectType.COMPONENT, name="component_122"
        )
        self.component_122 = gen_component(service=self.service_12, prototype=component_122_prototype)
        self.host_1 = hierarchy_1["host"]
        self.host_2 = gen_host(provider=hierarchy_1["provider"], cluster=self.cluster_1)
        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, self.component_111),
                (self.host_1, self.component_112),
                (self.host_1, self.component_121),
                (self.host_2, self.component_122),
                (self.host_2, self.component_112),
            ],
        )

        hierarchy_2 = generate_hierarchy()
        self.cluster_2 = hierarchy_2["cluster"]
        self.service_21 = hierarchy_2["service"]
        self.component_211 = hierarchy_2["component"]
        self.host_3 = hierarchy_2["host"]

        self.status_map = FullStatusMap(
            clusters={
                str(self.cluster_1.pk): {
                    "status": 0,
                    "hosts": {str(self.host_1.pk): {"status": 0}, str(self.host_2.pk): {"status": 16}},
                    "services": {
                        str(self.service_11.pk): {
                            "status": 4,
                            "components": {
                                str(self.component_111.pk): {"status": 16},
                                str(self.component_112.pk): {"status": 0},
                            },
                            "details": [
                                {"host": self.host_1.pk, "component": self.component_111.pk, "status": 0},
                                {"host": self.host_1.pk, "component": self.component_112.pk, "status": 16},
                                {"host": self.host_2.pk, "component": self.component_112.pk, "status": 0},
                            ],
                        },
                        str(self.service_12.pk): {
                            "status": 0,
                            "components": {
                                str(self.component_121.pk): {"status": 0},
                                str(self.component_122.pk): {"status": 2},
                            },
                            "details": [
                                {"host": self.host_1.pk, "component": self.component_121.pk, "status": 0},
                                {"host": self.host_2.pk, "component": self.component_122.pk, "status": 2},
                            ],
                        },
                    },
                },
                str(self.cluster_2.pk): {"status": 16, "hosts": {str(self.host_3.pk): {"status": 0}}, "services": {}},
            },
            hosts={
                str(self.host_1.pk): {"status": 0},
                str(self.host_2.pk): {"status": 16},
                str(self.host_3.pk): {"status": 0},
            },
        )

    @staticmethod
    def get_name_status_pairs(entries: list[dict]) -> set[tuple[int, str]]:
        return {(entry["name"], entry["status"]) for entry in entries}

    def test_services_statuses_success(self) -> None:
        with patch("api_v2.views.retrieve_status_map", return_value=self.status_map) as patched:
            response = (self.client.v2[self.cluster_1] / "statuses" / "services").get()

        patched.assert_called_once()

        self.assertEqual(response.status_code, HTTP_200_OK)
        services = response.json()["results"]
        self.assertEqual(len(services), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(services), {(self.service_11.name, "down"), (self.service_12.name, "up")}
        )
        service_1, service_2 = sorted(services, key=lambda i: i["id"])
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

    def test_hosts_statuses_success(self) -> None:
        with patch("api_v2.views.retrieve_status_map", return_value=self.status_map) as patched:
            response = (self.client.v2[self.cluster_1] / "statuses" / "hosts").get()

        patched.assert_called_once()

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["results"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(self.get_name_status_pairs(entries), {(self.host_1.name, "up"), (self.host_2.name, "down")})

    def test_components_of_service_statuses_success(self) -> None:
        with patch("api_v2.views.retrieve_status_map", return_value=self.status_map) as patched:
            response = (self.client.v2[self.service_11] / "statuses").get()

        patched.assert_called_once()

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["components"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.component_111.name, "down"), (self.component_112.name, "up")},
        )

    def test_hc_statuses_of_component_success(self) -> None:
        with patch("api_v2.views.retrieve_status_map", return_value=self.status_map) as patched:
            response = (self.client.v2[self.component_112] / "statuses").get()

        patched.assert_called_once()

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["hostComponents"]
        self.assertEqual(len(entries), 2)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.host_1.name, "down"), (self.host_2.name, "up")},
        )

    def test_hc_statuses_of_host_success(self) -> None:
        with patch("api_v2.views.retrieve_status_map", return_value=self.status_map) as patched:
            response = (self.client.v2[self.cluster_1] / "hosts" / self.host_1 / "statuses").get()

        patched.assert_called_once()

        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()["hostComponents"]
        self.assertEqual(len(entries), 3)
        self.assertSetEqual(
            self.get_name_status_pairs(entries),
            {(self.component_111.name, "up"), (self.component_112.name, "down"), (self.component_121.name, "up")},
        )
