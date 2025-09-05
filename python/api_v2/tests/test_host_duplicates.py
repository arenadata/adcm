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

from cm.models import Cluster, Component, Host, MaintenanceMode
from cm.services.host.duplicates import create_duplicate
from core.types import HostID
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_409_CONFLICT

from api_v2.tests.base import BaseAPITestCase


class TestDuplicateHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host_1 = self.add_host(provider=self.provider, fqdn="host-1")

    def get_ids(self, collection: list[dict]) -> set[int]:
        return set(map(itemgetter("id"), collection))

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

    def test_host_candidates_include_originals_and_duplicates(self):
        get_id = itemgetter("id")

        host_2 = self.add_host(provider=self.provider, fqdn="host-2", cluster=self.cluster_1)
        host_1_d1_id = create_duplicate(host_id=self.host_1.id, name="awesome")
        host_1_d2_id = create_duplicate(host_id=self.host_1.id, name=self.host_1.fqdn)
        # for now it is allowed to map duplicate to cluster alongside the original
        create_duplicate(host_id=host_2.id, name="host-2-duplicate", cluster_id=self.cluster_1.id)
        host_2_d2_id = create_duplicate(host_id=host_2.id, name="host-2-duplicate")

        expected_candidates = [
            {"id": self.host_1.id, "name": self.host_1.fqdn},
            {"id": host_1_d1_id, "name": "awesome"},
            {"id": host_1_d2_id, "name": self.host_1.fqdn},
            {"id": host_2_d2_id, "name": "host-2-duplicate"},
        ]

        response = self.client.v2[self.cluster_1, "host-candidates"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        candidates = response.json()
        self.assertEqual(sorted(candidates, key=get_id), sorted(expected_candidates, key=get_id))

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

        response = (self.client.v2 / "hosts").post(data={"hostproviderId": self.provider.pk, "name": "awesome"})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

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
