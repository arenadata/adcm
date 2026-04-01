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
import secrets

from cm.legacy.api import remove_host_from_cluster
from cm.legacy.services.cluster import perform_host_to_cluster_map
from cm.legacy.services.status import notify
from cm.legacy.services.status.client import FullStatusMap
from cm.models import Action, Cluster, Component, Host, HostComponent, Provider, TaskLog
from core.types import ADCMCoreType, HostID, HostName
from infra.services import get_config_service
from rbac.scenarios import RBACScenarios
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.deprecated import BusinessLogicMixin
from tests.suites import ADCMDjangoAPISuite
from use_cases.transition.host.duplicate import create_duplicate


class TestHost(ADCMDjangoAPISuite, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(provider=self.provider, fqdn="test-host")

        self.host_action = Action.objects.get(name="host_action", prototype=self.host.prototype)
        self.cluster_action = Action.objects.filter(prototype=self.cluster_1.prototype, host_action=True).first()

    def test_list_success(self):
        response = (self.client.v2 / "hosts").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response = self.client.v2[self.host].get()
        data = {
            "id": self.host.pk,
            "name": "test-host",
            "description": "",
            "state": "created",
            "status": 32,
            "hostprovider": {"id": self.provider.id, "name": "provider", "display_name": "provider"},
            "concerns": [],
            "is_maintenance_mode_available": False,
            "maintenance_mode": "off",
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], data["id"])
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["description"], data["description"])
        self.assertEqual(response.data["state"], data["state"])
        self.assertDictEqual(response.data["hostprovider"], data["hostprovider"])
        self.assertEqual(response.data["concerns"], data["concerns"])
        self.assertEqual(response.data["is_maintenance_mode_available"], data["is_maintenance_mode_available"])
        self.assertEqual(response.data["maintenance_mode"], data["maintenance_mode"])

    def test_create_without_cluster_success(self):
        name = "new-test-host-1"
        response = (self.client.v2 / "hosts").post(data={"hostproviderId": self.provider.pk, "name": name})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_pk = response.json()["id"]
        response = (self.client.v2 / "hosts" / str(host_pk)).get()

        data = {
            "id": host_pk,
            "name": name,
            "state": "created",
            "status": 32,
            "hostprovider": {"id": self.provider.id, "name": "provider", "display_name": "provider"},
            "concerns": [],
            "is_maintenance_mode_available": False,
            "maintenance_mode": "off",
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["id"], data["id"])
        self.assertEqual(response.data["name"], data["name"])
        self.assertEqual(response.data["state"], data["state"])
        self.assertDictEqual(response.data["hostprovider"], data["hostprovider"])
        self.assertEqual(response.data["concerns"], data["concerns"])
        self.assertEqual(response.data["is_maintenance_mode_available"], data["is_maintenance_mode_available"])
        self.assertEqual(response.data["maintenance_mode"], data["maintenance_mode"])

    def test_create_failed_wrong_provider(self):
        response = (self.client.v2 / "hosts").post(
            data={"hostprovider_id": self.get_non_existent_pk(model=Provider), "name": "woohoo"}
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_with_cluster_success(self):
        response = (self.client.v2 / "hosts").post(
            data={"hostprovider_id": self.provider.pk, "name": "new-test-host", "cluster_id": self.cluster_1.pk}
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_2 = Host.objects.get(fqdn="new-test-host")
        self.assertEqual(host_2.cluster, self.cluster_1)

    def test_fqdn_validation_create_failed(self):
        response = (self.client.v2 / "hosts").post(
            data={
                "hostproviderId": self.provider.pk,
                "name": "new_test_host",
            }
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "Wrong FQDN. Errors: `__`")

    def test_update_name_success(self):
        new_test_host_fqdn = "new-fqdn"
        response = self.client.v2[self.host].patch(data={"name": new_test_host_fqdn})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.fqdn, new_test_host_fqdn)

    def test_update_name_fail(self):
        new_host = self.add_host(provider=self.provider, fqdn="new_host")

        response = self.client.v2[self.host].patch(data={"name": new_host.name})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "HOST_CONFLICT", "desc": "Host with the same name already exists.", "level": "error"},
        )

    def test_update_name_locking_concern_fail(self):
        response = self.client.v2[self.host, "actions", self.host_action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.v2[self.host].patch(
            data={"name": "new-name"},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_CONFLICT",
                "desc": "Name change is available only if no locking concern exists",
                "level": "error",
            },
        )

    def test_update_name_locking_concern_from_cluster_fail(self):
        self.add_host_to_cluster(self.cluster_1, self.host)

        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions", self.cluster_action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.v2[self.host].patch(data={"name": "new-name"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_CONFLICT",
                "desc": "Name change is available only if no locking concern exists",
                "level": "error",
            },
        )

    def test_update_name_state_not_create_fail(self):
        self.host.state = "running"
        self.host.save(update_fields=["state"])

        response = self.client.v2[self.host].patch(data={"name": "new-fqdn"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_UPDATE_ERROR",
                "desc": "FQDN can't be changed if cluster bound or not CREATED state",
                "level": "error",
            },
        )

    def test_update_name_bound_to_cluster_fail(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)

        response = self.client.v2[self.host].patch(data={"name": "new-fqdn"})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_UPDATE_ERROR",
                "desc": "FQDN can't be changed if cluster bound or not CREATED state",
                "level": "error",
            },
        )

    def test_delete_success(self):
        response = self.client.v2[self.host].delete()
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.assertFalse(Host.objects.filter(pk=self.host.pk).exists())

    def test_maintenance_mode(self):
        response = self.client.v2[self.host, "maintenance-mode"].post(data={"maintenanceMode": "on"})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "MAINTENANCE_MODE_NOT_AVAILABLE")

        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.v2[self.host, "maintenance-mode"].post(data={"maintenanceMode": "on"})
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "on")

    def test_filtering_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.add_host(provider=self.provider, fqdn="host-2")
        self.add_host(provider=self.provider, fqdn="host-3", cluster=self.cluster_1)

        filters = {
            "name": (self.host.name, self.host.name[1:-3].upper(), "wrong", 1),
            "hostproviderName": (self.host.provider.name, None, "wrong", 3),
            "clusterName": (self.host.cluster.name, None, "wrong", 2),
            "isInCluster": (True, False, "wrong", 2),
        }

        for filter_name, (correct_value, partial_value, wrong_value, count) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "hosts").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], count)

                response = (self.client.v2 / "hosts").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                wrong_value = 0 if filter_name != "isInCluster" else 3
                self.assertEqual(response.json()["count"], wrong_value)

                if partial_value:
                    response = (self.client.v2 / "hosts").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], count)

    def test_ordering_success(self):
        provider_2 = self.add_provider(bundle=self.provider_bundle, name="another provider", description="provider")
        test_host_5 = self.add_host(provider=self.provider, fqdn="test_host_5", cluster=self.cluster_1)
        test_host_2 = self.add_host(provider=self.provider, fqdn="test_host_2", cluster=self.cluster_2)

        test_host_7 = self.add_host(provider=provider_2, fqdn="test_host_7", cluster=self.cluster_2)
        test_host_6 = self.add_host(provider=provider_2, fqdn="test_host_6", cluster=self.cluster_1)
        self.add_host(provider=self.provider, fqdn="a_first_host")
        Host.objects.filter(id__in=[test_host_5.id, test_host_6.id]).update(state="running")
        Host.objects.filter(id__in=[test_host_2.id, test_host_7.id]).update(state="active")

        with self.subTest("Ascending order by default (by fqdn"):
            response = (self.client.v2 / "hosts").get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["a_first_host", "test-host", "test_host_2", "test_host_5", "test_host_6", "test_host_7"],
                [host["name"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by provider name"):
            response = (self.client.v2 / "hosts").get(query={"ordering": "-hostproviderName"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["provider", "provider", "provider", "provider", "another provider", "another provider"],
                [host["hostprovider"]["name"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by id"):
            response = (self.client.v2 / "hosts").get(query={"ordering": "-id"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["a_first_host", "test_host_6", "test_host_7", "test_host_2", "test_host_5", "test-host"],
                [host["name"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by cluster name"):
            response = (self.client.v2 / "hosts").get(query={"ordering": "-clusterName"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                [None, None, "cluster_2", "cluster_2", "cluster_1", "cluster_1"],
                [host["cluster"]["name"] if host["cluster"] else None for host in response.json()["results"]],
            )

        with self.subTest("Ascending order by state"):
            response = (self.client.v2 / "hosts").get(query={"ordering": "state"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["active", "active", "created", "created", "running", "running"],
                [host["state"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by state, ascending by name and provider name"):
            response = (self.client.v2 / "hosts").get(query={"ordering": "state,-id,hostproviderName"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["test_host_7", "test_host_2", "a_first_host", "test-host", "test_host_6", "test_host_5"],
                [host["name"] for host in response.json()["results"]],
            )


class TestClusterHost(ADCMDjangoAPISuite, BusinessLogicMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.host = cls.uc.add_host(provider=cls.provider, fqdn="test-host")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="second-host")
        cls.control_free_host = cls.uc.add_host(provider=cls.provider, fqdn="not-bound-host")
        cls.control_host_same_cluster = cls.uc.add_host(
            provider=cls.provider, fqdn="bound-to-same-host", cluster=cls.cluster_1
        )
        cls.control_host_another_cluster = cls.uc.add_host(
            provider=cls.provider, fqdn="bound-to-another-host", cluster=cls.cluster_2
        )

    def check_control_hosts(self) -> None:
        self.control_free_host.refresh_from_db()
        self.assertIsNone(self.control_free_host.cluster)

        self.control_host_same_cluster.refresh_from_db()
        self.assertEqual(self.control_host_same_cluster.cluster, self.cluster_1)

        self.control_host_another_cluster.refresh_from_db()
        self.assertEqual(self.control_host_another_cluster.cluster, self.cluster_2)

    def get_host_candidates(self, cluster: Cluster) -> list[tuple[HostID, HostName]]:
        response = self.client.v2[cluster, "host-candidates"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        entries = response.json()
        return [(entry["id"], entry["name"]) for entry in entries]

    def assert_hosts_in_candidates(self, *hosts: Host, candidates: list[tuple[HostID, HostName]]):
        expected = {(h.id, h.fqdn) for h in hosts}
        self.assertTrue(
            expected.issubset(candidates),
            msg=f"Not found entries: {', '.join(map(str, expected.difference( candidates)))}",
        )

    def assert_hosts_not_in_candidates(self, *hosts: Host, candidates: list[tuple[HostID, HostName]]):
        expected = {(h.id, h.fqdn) for h in hosts}
        self.assertFalse(
            expected.intersection(candidates),
            msg=f"Not expected entries: {', '.join(map(str, expected.difference( candidates)))}",
        )

    def test_list_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.v2[self.cluster_1, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.v2[self.cluster_1, "hosts", self.host].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host.pk)

    def test_create_success(self):
        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": self.host.pk})

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

        self.check_control_hosts()

    def test_create_belonging_to_another_cluster_fail(self):
        self.add_host_to_cluster(cluster=self.cluster_2, host=self.host)

        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": self.host.pk})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "FOREIGN_HOST",
                "desc": "At least one host is already linked to another cluster.",
                "level": "error",
            },
        )

        self.check_control_hosts()

    def test_create_already_added_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)

        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": self.host.pk})

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_CONFLICT",
                "desc": "At least one host is already associated with this cluster.",
                "level": "error",
            },
        )

        self.check_control_hosts()

    def test_create_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": self.get_non_existent_pk(model=Host)})

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "BAD_REQUEST", "desc": "At least one host does not exist.", "level": "error"},
        )

        self.check_control_hosts()

    def test_add_many_success(self):
        response = self.client.v2[self.cluster_1, "hosts"].post(
            data=[{"hostId": self.host.pk}, {"hostId": self.host_2.pk}]
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()

        self.assertEqual(len(data), 2)

        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

        self.host_2.refresh_from_db()
        self.assertEqual(self.host_2.cluster, self.cluster_1)

        self.check_control_hosts()

    def test_add_many_when_one_belongs_to_another_cluster_fail(self):
        self.add_host_to_cluster(cluster=self.cluster_2, host=self.host)

        response = self.client.v2[self.cluster_1, "hosts"].post(
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host.pk}]
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "FOREIGN_HOST",
                "desc": "At least one host is already linked to another cluster.",
                "level": "error",
            },
        )

        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_2)

        self.host_2.refresh_from_db()
        self.assertIsNone(self.host_2.cluster)

        self.check_control_hosts()

    def test_add_many_when_one_is_already_added_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)

        response = self.client.v2[self.cluster_1, "hosts"].post(
            data=[{"hostId": self.host_2.pk}, {"hostId": self.host.pk}]
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "HOST_CONFLICT",
                "desc": "At least one host is already associated with this cluster.",
                "level": "error",
            },
        )

        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

        self.host_2.refresh_from_db()
        self.assertIsNone(self.host_2.cluster)

        self.check_control_hosts()

    def test_add_many_when_one_is_not_found_fail(self):
        response = self.client.v2[self.cluster_1, "hosts"].post(
            data=[
                {"hostId": self.host_2.pk},
                {"hostId": self.host.pk},
                {"hostId": self.get_non_existent_pk(model=Host)},
            ],
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "BAD_REQUEST", "desc": "At least one host does not exist.", "level": "error"},
        )

        self.host.refresh_from_db()
        self.assertIsNone(self.host.cluster)

        self.host_2.refresh_from_db()
        self.assertIsNone(self.host_2.cluster)

        self.check_control_hosts()

    def test_adcm_7228_add_originals_with_duplicates_fail(self):
        h1_dup = Host.objects.get(
            id=create_duplicate(
                host_id=self.host.id,
                name=f"{self.host.fqdn}-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )
        h2_dup = Host.objects.get(
            id=create_duplicate(
                host_id=self.host_2.id,
                name=f"{self.host_2.fqdn}-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )
        hosts_to_add = (self.host, h1_dup, self.host_2, h2_dup)

        data = [{"hostId": host.id} for host in hosts_to_add]
        response = self.client.v2[self.cluster_1, "hosts"].post(data=data)

        hosts_repr = ", ".join(sorted(f"<Host #{host.id} {host.fqdn}>" for host in hosts_to_add))
        expected_response = {
            "code": "HOST_CONFLICT",
            "level": "error",
            "desc": f"Only one copy of a host can be added to the cluster. Errors: {hosts_repr}",
        }
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(response.json(), expected_response)

        self.check_control_hosts()

    def test_adcm_7228_add_original_and_copy_of_host_fail(self):
        h1_dup = Host.objects.get(
            id=create_duplicate(
                host_id=self.host.id,
                name=f"{self.host.fqdn}-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )
        h2_dup = Host.objects.get(
            id=create_duplicate(
                host_id=self.host_2.id,
                name=f"{self.host_2.fqdn}-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )

        # cluster with original host; add the duplicate
        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": self.host.pk})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[self.cluster_1, "hosts"].post(data={"hostId": h1_dup.id})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        expected_response = {
            "code": "HOST_CONFLICT",
            "level": "error",
            "desc": f"Only one copy of a host can be added to the cluster. Errors: <Host #{h1_dup.id} {h1_dup.fqdn}>",
        }
        self.assertDictEqual(response.json(), expected_response)

        # cluster with duplicate; add the original host
        response = self.client.v2[self.cluster_2, "hosts"].post(data={"hostId": h2_dup.id})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[self.cluster_2, "hosts"].post(data={"hostId": self.host_2.id})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        expected_response = {
            "code": "HOST_CONFLICT",
            "level": "error",
            "desc": "Only one copy of a host can be added to the cluster. "
            f"Errors: <Host #{self.host_2.id} {self.host_2.fqdn}>",
        }
        self.assertDictEqual(response.json(), expected_response)

        self.check_control_hosts()

    def test_adcm_7228_add_two_duplicates_fail(self):
        h1_dup = Host.objects.get(
            id=create_duplicate(
                host_id=self.host.id,
                name=f"{self.host.fqdn}-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )
        h1_dup_2 = Host.objects.get(
            id=create_duplicate(
                host_id=self.host.id,
                name=f"{self.host.fqdn}-dup-dup",
                config_service=get_config_service(),
                rbac_scenarios=RBACScenarios(),
            )
        )
        hosts_to_add = (h1_dup, h1_dup_2)

        # add two duplicates together
        response = self.client.v2[self.cluster_2, "hosts"].post(data=[{"hostId": host.id} for host in hosts_to_add])
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        hosts_repr = ", ".join(sorted(f"<Host #{host.id} {host.fqdn}>" for host in hosts_to_add))
        expected_response = {
            "code": "HOST_CONFLICT",
            "level": "error",
            "desc": f"Only one copy of a host can be added to the cluster. Errors: {hosts_repr}",
        }
        self.assertDictEqual(response.json(), expected_response)

        # add two duplicates one by one
        response = self.client.v2[self.cluster_2, "hosts"].post(data={"hostId": h1_dup.id})
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response = self.client.v2[self.cluster_2, "hosts"].post(data={"hostId": h1_dup_2.id})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        expected_response = {
            "code": "HOST_CONFLICT",
            "level": "error",
            "desc": "Only one copy of a host can be added to the cluster. "
            f"Errors: <Host #{h1_dup_2.id} {h1_dup_2.fqdn}>",
        }
        self.assertDictEqual(response.json(), expected_response)

        self.check_control_hosts()

    def test_maintenance_mode(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.v2[self.cluster_1, "hosts", self.host, "maintenance-mode"].post(
            data={"maintenanceMode": "on"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "on")

    def test_ordering_success(self):
        provider_2 = self.add_provider(bundle=self.provider_bundle, name="another provider", description="provider")
        self.add_host_to_cluster(self.cluster_1, self.host)
        test_host_5 = self.add_host(provider=self.provider, fqdn="test_host_5", cluster=self.cluster_1)
        self.add_host(provider=self.provider, fqdn="test_host_2", cluster=self.cluster_1)

        test_host_7 = self.add_host(provider=provider_2, fqdn="test_host_7", cluster=self.cluster_1)
        test_host_6 = self.add_host(provider=provider_2, fqdn="test_host_6", cluster=self.cluster_1)

        Host.objects.filter(id__in=[test_host_5.id, test_host_7.id]).update(state="running")
        Host.objects.filter(id__in=[self.host.id, test_host_6.id]).update(state="active")

        with self.subTest("Ascending order by default (by name)"):
            response = self.client.v2[self.cluster_1, "hosts"].get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["bound-to-same-host", "test-host", "test_host_2", "test_host_5", "test_host_6", "test_host_7"],
                [host["name"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by id"):
            response = self.client.v2[self.cluster_1, "hosts"].get(query={"ordering": "-id"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["test_host_6", "test_host_7", "test_host_2", "test_host_5", "bound-to-same-host", "test-host"],
                [host["name"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by provider name"):
            response = self.client.v2[self.cluster_1, "hosts"].get(query={"ordering": "hostproviderName"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["another provider", "another provider", "provider", "provider", "provider", "provider"],
                [host["hostprovider"]["name"] for host in response.json()["results"]],
            )

        with self.subTest("Ascending order by state"):
            response = self.client.v2[self.cluster_1, "hosts"].get(query={"ordering": "state"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["active", "active", "created", "created", "running", "running"],
                [host["state"] for host in response.json()["results"]],
            )

        with self.subTest("Descending order by state, ascending by name and provider name"):
            response = self.client.v2[self.cluster_1, "hosts"].get(query={"ordering": "state,-id,hostproviderName"})

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 6)
            self.assertListEqual(
                ["test_host_6", "test-host", "test_host_2", "bound-to-same-host", "test_host_7", "test_host_5"],
                [host["name"] for host in response.json()["results"]],
            )

    def test_filtering_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.add_host(provider=self.provider, fqdn="host-2")
        self.add_host(provider=self.provider, fqdn="host-3", cluster=self.cluster_1)

        filters = {
            "name": (self.host.name, self.host.name[1:-3].upper(), "wrong", 1),
            "hostproviderName": (self.host.provider.name, None, "wrong", 3),
        }

        for filter_name, (correct_value, partial_value, wrong_value, count) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = self.client.v2[self.cluster_1, "hosts"].get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], count)

                response = self.client.v2[self.cluster_1, "hosts"].get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = self.client.v2[self.cluster_1, "hosts"].get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], count)

    def test_adcm_5687_filtering_by_component_id(self):
        service = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        component_1 = service.components.get(prototype__name="component_1")
        component_2 = service.components.get(prototype__name="component_2")

        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=((self.host, component_1), (self.host_2, component_2)),
        )

        for query, expected_ids in (
            ({"componentId": component_1.pk}, {self.host.pk}),
            ({"componentId": component_2.pk}, {self.host_2.pk}),
            (None, {self.host.pk, self.host_2.pk, self.control_host_same_cluster.pk}),
            ({"componentId": self.get_non_existent_pk(model=Component)}, set()),
        ):
            with self.subTest(query=query, expected_ids=expected_ids):
                response = self.client.v2[self.cluster_1, "hosts"].get(query=query)
                self.assertEqual(response.status_code, HTTP_200_OK)

                host_ids = {host["id"] for host in response.json()["results"]}
                self.assertSetEqual(host_ids, expected_ids)

    def test_host_candidates_filtering_success(self):
        host_1 = self.host
        host_2 = self.host_2
        host_duplicate_1 = Host.objects.get(
            id=create_duplicate(
                host_id=host_1.pk, name="duplicate", config_service=get_config_service(), rbac_scenarios=RBACScenarios()
            )
        )
        host_duplicate_named_as_host_2 = Host.objects.get(
            id=create_duplicate(
                host_id=host_1.pk, name=host_2.name, config_service=get_config_service(), rbac_scenarios=RBACScenarios()
            )
        )

        candidates = self.get_host_candidates(self.cluster_1)
        self.assert_hosts_in_candidates(
            host_1, host_duplicate_1, host_2, host_duplicate_named_as_host_2, candidates=candidates
        )

        with self.subTest("exclude by name and origin"):
            perform_host_to_cluster_map(
                cluster_id=self.cluster_1.pk,
                hosts=[host_duplicate_named_as_host_2.pk],
                status_service=notify,
                rbac_scenarios=RBACScenarios(),
            )

            candidates = self.get_host_candidates(self.cluster_1)
            self.assert_hosts_not_in_candidates(
                host_2, host_1, host_duplicate_1, host_duplicate_named_as_host_2, candidates=candidates
            )

        host_duplicate_named_as_host_2.refresh_from_db()
        remove_host_from_cluster(host=host_duplicate_named_as_host_2, rbac_scenarios=RBACScenarios())

        with self.subTest("exclude by original host add"):
            perform_host_to_cluster_map(
                cluster_id=self.cluster_2.pk, hosts=[host_1.pk], status_service=notify, rbac_scenarios=RBACScenarios()
            )

            candidates = self.get_host_candidates(self.cluster_2)
            self.assert_hosts_in_candidates(host_2, candidates=candidates)
            self.assert_hosts_not_in_candidates(
                host_1, host_duplicate_1, host_duplicate_named_as_host_2, candidates=candidates
            )

        with self.subTest("verify ordering"):
            candidates = self.get_host_candidates(self.cluster_1)
            self.assertListEqual(
                candidates,
                sorted(candidates, key=lambda h: h[1]),
            )

    def test_host_candidates_not_allowed_without_cluster_admin_permissions(self):
        credentials = {"username": "aaaa", "password": secrets.token_hex(8)}
        user = self.create_user(user_data=credentials)

        self.client.login(**credentials)
        ep = self.client.v2[self.cluster_1, "host-candidates"]

        response = ep.get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

        with self.grant_permissions(to=user, on=self.cluster_1, role_name="Cluster Administrator"):
            response = ep.get()

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertGreater(len(response.json()), 0)


class TestHostActions(ADCMDjangoAPISuite, BusinessLogicMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.host = cls.uc.add_host(provider=cls.provider, fqdn="test-host", cluster=cls.cluster_1)
        cls.action = Action.objects.get(name="host_action", prototype=cls.host.prototype)

        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)[0]
        cls.component_1 = Component.objects.get(prototype__name="component_1", service=cls.service_1)

    def test_host_cluster_list_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_cluster_retrieve_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_cluster_run_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions", self.action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched(response.json()["id"]).id
        task = TaskLog.objects.get(id=task_id)
        self.assertEqual(task.status, "created")
        self.assertEqual(task.task_object, self.host)
        self.assertEqual(task.owner_id, self.host.pk)
        self.assertEqual(task.owner_type, ADCMCoreType.HOST.value)

        self.task_runner.run_task(task_id)
        task.refresh_from_db()
        self.assertEqual(task.status, "success")

    def test_host_list_success(self):
        response = self.client.v2[self.host, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_retrieve_success(self):
        response = self.client.v2[self.host, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_run_success(self):
        response = self.client.v2[self.host, "actions", self.action, "run"].post(
            data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        task_id = self.task_runner.expect_task_launched(response.json()["id"]).id
        task = TaskLog.objects.get(id=task_id)
        self.assertEqual(task.status, "created")
        self.assertEqual(task.task_object, self.host)
        self.assertEqual(task.owner_id, self.host.pk)
        self.assertEqual(task.owner_type, ADCMCoreType.HOST.value)

        self.task_runner.run_task(task_id)
        task.refresh_from_db()
        self.assertEqual(task.status, "success")

    def test_host_mapped_list_success(self) -> None:
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        response = self.client.v2[self.host, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 4)

    def test_host_mapped_retrieve_success(self) -> None:
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        action = Action.objects.filter(prototype=self.service_1.prototype, host_action=True).first()
        response = self.client.v2[self.host, "actions", action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_filter_is_host_own_action_true_success(self):
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        host_action = Action.objects.filter(name="host_action", prototype=self.host.prototype).first()

        response = self.client.v2[self.host, "actions"].get(query={"isHostOwnAction": True})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            response.json(),
            [
                {
                    "displayName": "host_action",
                    "id": host_action.pk,
                    "name": "host_action",
                    "startImpossibleReason": None,
                }
            ],
        )

    def test_filter_is_host_own_action_false_success(self):
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        cluster_on_host = Action.objects.filter(name="cluster_on_host", prototype=self.cluster_1.prototype).first()
        service_on_host = Action.objects.filter(name="service_on_host", prototype=self.service_1.prototype).first()
        component_on_host = Action.objects.filter(
            name="component_on_host", prototype=self.component_1.prototype
        ).first()

        response = self.client.v2[self.host, "actions"].get(query={"isHostOwnAction": False})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            response.json(),
            [
                {
                    "id": cluster_on_host.pk,
                    "name": "cluster_on_host",
                    "displayName": "cluster_on_host",
                    "startImpossibleReason": None,
                },
                {
                    "id": service_on_host.pk,
                    "name": "service_on_host",
                    "displayName": "service_on_host",
                    "startImpossibleReason": None,
                },
                {
                    "id": component_on_host.pk,
                    "name": "component_on_host",
                    "displayName": "component_on_host",
                    "startImpossibleReason": None,
                },
            ],
        )

    def test_filter_is_host_own_action_false_component_success(self):
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        component_on_host = Action.objects.filter(
            name="component_on_host", prototype=self.component_1.prototype
        ).first()

        response = self.client.v2[self.host, "actions"].get(
            query={"isHostOwnAction": False, "prototypeId": self.component_1.prototype.pk}
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            response.json(),
            [
                {
                    "id": component_on_host.pk,
                    "name": "component_on_host",
                    "displayName": "component_on_host",
                    "startImpossibleReason": None,
                },
            ],
        )


class TestClusterHostComponent(ADCMDjangoAPISuite, BusinessLogicMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host1", cluster=cls.cluster_1)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host2", cluster=cls.cluster_1)
        cls.service_1 = cls.uc.add_services_to_cluster(names=["service_1"], cluster=cls.cluster_1)[0]
        cls.component_1 = Component.objects.get(service=cls.service_1, prototype__name="component_1")
        cls.component_2 = Component.objects.get(service=cls.service_1, prototype__name="component_2")
        cls.uc.set_hostcomponent(
            cluster=cls.cluster_1,
            entries=[
                (cls.host_1, cls.component_1),
                (cls.host_1, cls.component_2),
                (cls.host_2, cls.component_1),
                (cls.host_2, cls.component_2),
            ],
        )

    def test_components_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host_1, "components"].get()
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertSetEqual(
            set(response.json()["results"][0].keys()),
            {
                "id",
                "name",
                "displayName",
                "status",
                "concerns",
                "isMaintenanceModeAvailable",
                "maintenanceMode",
                "cluster",
                "service",
                "prototype",
            },
        )
        self.assertListEqual(
            [component["name"] for component in response.json()["results"]], ["component_1", "component_2"]
        )

    def test_ordering_by_display_name_reverse_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host_1, "components"].get(
            query={"ordering": "-displayName"}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertListEqual(
            [component["name"] for component in response.json()["results"]], ["component_2", "component_1"]
        )


class TestAdvancedFilters(ADCMDjangoAPISuite, BusinessLogicMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host-1")
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host-2")
        cls.host_3 = cls.uc.add_host(provider=cls.provider, fqdn="host-3")

        cls.status_map = FullStatusMap.model_validate(
            {
                "hosts": {
                    str(cls.host_1.pk): {"status": 0},
                    str(cls.host_2.pk): {"status": 16},
                    str(cls.host_3.pk): {"status": 16},
                }
            }
        )

    def test_filter_by_status__eq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "hosts").get(query={"status__eq": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "hosts").get(query={"status__eq": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ieq(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: Down"):
                response = (self.client.v2 / "hosts").get(query={"status__ieq": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__ieq": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status__ne(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "hosts").get(query={"status__ne": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "hosts").get(query={"status__ne": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 3)

    def test_filter_by_status__ine(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "hosts").get(query={"status__ine": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__ine": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 3)

    def test_filter_by_status__in(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "hosts").get(query={"status__in": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "hosts").get(query={"status__in": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: down,bar"):
                response = (self.client.v2 / "hosts").get(query={"status__in": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

    def test_filter_by_status__iin(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "hosts").get(query={"status__iin": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__iin": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

            with self.subTest("Filter value: Up,BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__iin": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

    def test_filter_by_status__exclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: up"):
                response = (self.client.v2 / "hosts").get(query={"status__exclude": "up"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)

            with self.subTest("Filter value: bar"):
                response = (self.client.v2 / "hosts").get(query={"status__exclude": "bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 3)

            with self.subTest("Filter value: down,bar"):
                response = (self.client.v2 / "hosts").get(query={"status__exclude": "down,bar"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

    def test_filter_by_status__iexclude(self):
        with patch("api_v2.filters.retrieve_status_map", return_value=self.status_map):
            with self.subTest("Filter value: DoWn"):
                response = (self.client.v2 / "hosts").get(query={"status__iexclude": "DoWn"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 1)
                self.assertEqual(response.json()["results"][0]["id"], self.host_1.pk)

            with self.subTest("Filter value: BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__iexclude": "BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 3)

            with self.subTest("Filter value: Up,BaR"):
                response = (self.client.v2 / "hosts").get(query={"status__iexclude": "Up,BaR"})

                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 2)
