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

from operator import itemgetter

from cm.models import Action, Cluster, Component, Host, MaintenanceMode
from cm.services.host.duplicates import create_duplicate
from core.types import HostID
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase, RunTaskMock


class TestDuplicateHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")

    def get_ids(self, collection: list[dict]) -> set[int]:
        return set(map(itemgetter("id"), collection))

    def get_action_names_from_response(self, actions: list[dict]) -> list[str]:
        return list(map(itemgetter("name"), actions))

    def create_duplicate(self, origin: Host, name: str = "duplicate", cluster: Cluster | None = None) -> Host:
        duplicate_id = create_duplicate(host_id=origin.pk, name=name, cluster_id=getattr(cluster, "id", None))
        return Host.objects.get(id=duplicate_id)

    def assert_cluster_host_candidates(self, cluster: Cluster, expected_ids: set[int]):
        host_candidates = self.client.v2[cluster, "host-candidates"].get().json()

        self.assertEqual(len(host_candidates), len(expected_ids))
        self.assertTrue(all("bindings" not in entry for entry in host_candidates))
        self.assertSetEqual(self.get_ids(host_candidates), expected_ids)

    def assert_host_name_in_db(self, host_id: HostID, expected_name: str):
        host_name = Host.objects.filter(id=host_id).values_list("fqdn", flat=True).first()
        self.assertEqual(host_name, expected_name)

    def test_allow_user_set_duplicate_name_no_cluster(self):
        name = "very-own-name"
        data = {"name": name}
        expected_data = data | {"cluster": None, "description": f"Copied from {self.host_1.fqdn}"}
        response = self.client.v2[self.host_1, "duplicates"].post(data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        actual_data = response.json()
        duplicate_id = actual_data["id"]
        self.assertNotEqual(duplicate_id, self.host_1.id)
        self.assertDictContainsSubset(expected_data, actual_data)
        self.assert_host_name_in_db(host_id=duplicate_id, expected_name=name)

    def test_allow_user_set_duplicate_name_with_cluster(self):
        name = self.host_1.fqdn
        data = {"name": name, "clusterId": self.cluster_1.id}
        expected_data = {
            "cluster": {"id": self.cluster_1.id, "name": self.cluster_1.name},
            "description": f"Copied from {self.host_1.fqdn}",
        }
        response = self.client.v2[self.host_1, "duplicates"].post(data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictContainsSubset(expected_data, response.json())

    def test_add_duplicate_to_cluster_after_creation(self):
        duplicate_1_id = create_duplicate(host_id=self.host_1.id, name="awesome")
        duplicate_2_id = create_duplicate(host_id=self.host_1.id, name="another-host")

        expected_duplicates = [
            {
                "id": duplicate_1_id,
                "name": "awesome",
                "cluster": {"id": self.cluster_1.id, "name": self.cluster_1.name},
                "isMaintenanceModeAvailable": True,
                "maintenanceMode": "off",
                "concerns": [],
            },
            {
                "id": duplicate_2_id,
                "name": "another-host",
                "cluster": None,
                "isMaintenanceModeAvailable": False,
                "maintenanceMode": "off",
                "concerns": [],
            },
        ]

        response = self.client.v2[self.cluster_1, "hosts"].post(data=[{"hostId": duplicate_1_id}])
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_list = (self.client.v2 / "hosts").get().json()["results"]
        host_1_record = next(host for host in host_list if host["id"] == self.host_1.id)
        duplicates = host_1_record["duplicates"]
        self.assertEqual(duplicates, expected_duplicates)

    def test_adcm_6944_duplicate_when_mm_is_on(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        name = "another"
        data = {"name": name}
        expected_data = {
            "cluster": None,
            "description": f"Copied from {self.host_1.fqdn}",
            "isMaintenanceModeAvailable": False,
            "maintenanceMode": "off",
        }
        response = self.client.v2[self.host_1, "duplicates"].post(data=data)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertDictContainsSubset(expected_data, response.json())

    def test_adcm_6943_new_host_with_name_of_duplicate_pass(self):
        create_duplicate(host_id=self.host_1.id, name="awesome")
        create_duplicate(host_id=self.host_1.id, name="awesome-2")
        with self.subTest("New host"):
            response = (self.client.v2 / "hosts").post(data={"hostproviderId": self.provider.pk, "name": "awesome"})

            self.assertEqual(response.status_code, HTTP_201_CREATED)

        with self.subTest("Renaming already existent"):
            response = self.client.v2[self.host_1].patch(data={"name": "awesome-2"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.host_1.refresh_from_db()
            self.assertEqual(self.host_1.fqdn, "awesome-2")

    def test_adcm_6980_host_wtih_duplicates_cant_be_deleted(self):
        duplicate_1_id = create_duplicate(host_id=self.host_1.id, name="duplicate-1", cluster_id=self.cluster_1.id)
        duplicate_2_id = create_duplicate(host_id=self.host_1.id, name="duplicate-2")

        service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).first()
        component_1 = Component.objects.get(service=service, prototype__name="component_1")

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (Host.objects.get(id=duplicate_1_id), component_1),
            ],
        )

        response = self.client.v2[self.host_1].delete()

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "HOST_CONFLICT")
        self.assertEqual(
            response.data["desc"],
            "It is forbidden to delete a host if at least one duplicate is associated with the cluster.",
        )

        self.assertEqual(Host.objects.filter(id__in=[self.host_1.id, duplicate_1_id, duplicate_2_id]).count(), 3)

    def test_adcm_6968_host_duplicates_validators(self):
        with self.subTest("clusterId is incorrect"):
            data = {"name": "duplicate", "clusterId": 0}
            response = self.client.v2[self.host_1, "duplicates"].post(data=data)

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
            self.assertIn("cluster doesn't exist", response.json()["desc"])

        with self.subTest("host name has length < 2"):
            data = {"name": "a"}
            response = self.client.v2[self.host_1, "duplicates"].post(data=data)

            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            self.assertIn("Min length is 2", response.json()["desc"])
        with self.subTest("host name has length > 253"):
            data = {"name": "a" * 256}
            response = self.client.v2[self.host_1, "duplicates"].post(data=data)

            self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
            self.assertIn("Ensure this field has no more than 253 characters.", response.json()["desc"])

    def test_adcm_6961_duplicate_host_cant_be_added_without_permissions(self):
        test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        test_user = self.create_user(**test_user_credentials)
        self.client.login(**test_user_credentials)

        with self.subTest("No permission granted - denied"):
            with self.grant_permissions(to=test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[self.host_1, "duplicates"].post(
                    data={"name": "another-host", "cluster_id": self.cluster_1.pk}
                )

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
                self.assertEqual(response.json()["desc"], "You do not have permission to perform this action.")

        with self.subTest("No permission granted (non-existend pk) - denied"):
            with self.grant_permissions(to=test_user, on=self.cluster_1, role_name="View cluster configurations"):
                response = self.client.v2[self.host_1, "duplicates"].post(
                    data={"name": "another-host", "cluster_id": 999}
                )

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)
                self.assertEqual(response.json()["desc"], "You do not have permission to perform this action.")

        with self.subTest("Permissions Create host only - denied"):
            with self.grant_permissions(to=test_user, on=self.provider, role_name="Create host"):
                response = self.client.v2[self.host_1, "duplicates"].post(
                    data={"name": "another-host", "cluster_id": self.cluster_1.pk}
                )

                self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
                self.assertEqual(response.json()["code"], "CLUSTER_NOT_FOUND")

        with self.subTest("Permission Create host and View cluster configurations granted - success"):
            with self.grant_permissions(to=test_user, on=self.cluster_1, role_name="View cluster configurations"):
                with self.grant_permissions(to=test_user, on=self.provider, role_name="Create host"):
                    response = self.client.v2[self.host_1, "duplicates"].post(
                        data={"name": "another-host", "cluster_id": self.cluster_1.pk}
                    )

                    self.assertEqual(response.status_code, HTTP_201_CREATED)
                    self.assertTrue(Host.objects.filter(fqdn="another-host").exists())

    def test_forbid_action_launch_of_host_own_actions_on_duplicates(self):
        duplicate = self.create_duplicate(origin=self.host_1, cluster=self.cluster_1)
        self.add_services_to_cluster(["service_1"], cluster=self.cluster_1)
        component = Component.objects.get(prototype__name="component_1")
        self.set_hostcomponent(self.cluster_1, [(duplicate, component)])

        action_from_component = Action.objects.get(prototype=component.prototype, name="component_on_host")
        action_from_host = Action.objects.get(prototype=duplicate.prototype, name="host_action")

        with self.subTest("host action list is correct"):
            response = self.client.v2[duplicate, "actions"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertNotIn(action_from_host.name, self.get_action_names_from_response(response.json()))

        with self.subTest("own host action can not be launched"):
            response = self.client.v2[duplicate, "actions", action_from_host, "run"].post()

            self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.subTest("action from cluster objects can be launched"):
            with RunTaskMock():
                response = self.client.v2[duplicate, "actions", action_from_component, "run"].post()

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_forbid_config_change(self):
        duplicate = self.create_duplicate(origin=self.host_1)

        response = self.client.v2[duplicate, "configs"].post(data={"config": {"not": "exist"}, "adcmMeta": {}})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn("host duplicate", response.json()["desc"])

    def test_host_list_queries_amount(self):
        expected_queries_amount = 10

        # When there aren't any duplicates, there will be 1 less query (for concerns prefetch),
        # yet amount of queries won't increase when more instances/duplicates arrive
        create_duplicate(host_id=self.host_1.pk, name="jjjj")

        with self.assertNumQueries(expected_queries_amount):
            response = (self.client.v2 / "hosts").get()

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.add_host(provider=self.provider, fqdn="something")
        another_host = self.add_host(provider=self.provider, fqdn="something-else")
        create_duplicate(host_id=another_host.pk, name="wow")

        with self.assertNumQueries(expected_queries_amount):
            response = (self.client.v2 / "hosts").get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_duplicate_add_to_wrong_cluster_fail(self):
        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=self.cluster_1)
        duplicate = self.create_duplicate(origin=self.host_1, name=host_2.fqdn)

        response = self.client.v2[self.cluster_1, "hosts"].post(data=[{"hostId": duplicate.pk}])

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, msg=response.json())
        self.assertIn("same name", response.json()["desc"])

    def test_create_duplicate_and_add_to_cluster_with_same_duplicate_added_fail(self):
        self.create_duplicate(origin=self.host_1, name=self.host_1.fqdn, cluster=self.cluster_1)

        response = self.client.v2[self.host_1, "duplicates"].post(
            data={"name": self.host_1.fqdn, "clusterId": self.cluster_1.id}
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT, msg=response.json())
        self.assertEqual("Host with the same origin is already added to cluster", response.json()["desc"])
