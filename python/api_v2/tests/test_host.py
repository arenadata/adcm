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

from cm.models import Action, Host, HostComponent, HostProvider, ServiceComponent
from cm.tests.mocks.task_runner import RunTaskMock
from core.types import ADCMCoreType
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(
            bundle=self.provider_bundle, description="description", provider=self.provider, fqdn="test_host"
        )

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
            "name": "test_host",
            "description": "description",
            "state": "created",
            "status": 32,
            "hostprovider": {"id": 1, "name": "provider", "display_name": "provider"},
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
        response = (self.client.v2 / "hosts").post(data={"hostproviderId": self.provider.pk, "name": "new-test-host"})

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_pk = response.json()["id"]
        response = (self.client.v2 / "hosts" / str(host_pk)).get()

        data = {
            "id": host_pk,
            "name": "new-test-host",
            "state": "created",
            "status": 32,
            "hostprovider": {"id": 1, "name": "provider", "display_name": "provider"},
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
            data={"hostprovider_id": self.get_non_existent_pk(model=HostProvider), "name": "woohoo"}
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
        new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new_host")

        response = self.client.v2[self.host].patch(data={"name": new_host.name})
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "HOST_CONFLICT", "desc": "Host with the same name already exists.", "level": "error"},
        )

    def test_update_name_locking_concern_fail(self):
        with RunTaskMock():
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

        with RunTaskMock():
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

    def test_filter_is_host_in_cluster_success(self):
        host2 = self.add_host(
            bundle=self.provider_bundle,
            description="description",
            provider=self.provider,
            fqdn="test_host_2",
            cluster=self.cluster_1,
        )

        response = (self.client.v2 / "hosts").get(query={"isInCluster": True})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], host2.pk)
        self.assertEqual(response.json()["results"][0]["cluster"]["name"], self.cluster_1.name)

    def test_filter_is_host_not_in_cluster_success(self):
        host2 = self.add_host(
            bundle=self.provider_bundle, description="description", provider=self.provider, fqdn="test_host_2"
        )
        self.add_host_to_cluster(self.cluster_1, host=host2)

        response = (self.client.v2 / "hosts").get(query={"isInCluster": False})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.host.pk)
        self.assertEqual(response.json()["results"][0]["cluster"], None)

    def test_hostprovider_filter(self):
        second_provider = self.add_provider(bundle=self.provider_bundle, name="second_provider", description="provider")
        host2 = self.add_host(
            bundle=self.provider_bundle, description="description", provider=second_provider, fqdn="test_host_2"
        )

        response = (self.client.v2 / "hosts").get(query={"hostproviderName": second_provider.name})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], host2.pk)

    def test_ordering_by_default_success(self):
        self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_5")
        self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")

        response = (self.client.v2 / "hosts").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertListEqual(
            ["test_host", "test_host_2", "test_host_5"],
            [host["name"] for host in response.json()["results"]],
        )

    def test_ordering_by_id_desc_success(self):
        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_6")
        host_3 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_3")

        response = (self.client.v2 / "hosts").get(query={"ordering": "-id"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertListEqual(
            [host_3.pk, host_2.pk, self.host.pk],
            [host["id"] for host in response.json()["results"]],
        )


class TestClusterHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="second-host")
        self.control_free_host = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="not-bound-host"
        )
        self.control_host_same_cluster = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="bound-to-same-host", cluster=self.cluster_1
        )
        self.control_host_another_cluster = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="bound-to-another-host", cluster=self.cluster_2
        )

    def check_control_hosts(self) -> None:
        self.control_free_host.refresh_from_db()
        self.assertIsNone(self.control_free_host.cluster)

        self.control_host_same_cluster.refresh_from_db()
        self.assertEqual(self.control_host_same_cluster.cluster, self.cluster_1)

        self.control_host_another_cluster.refresh_from_db()
        self.assertEqual(self.control_host_another_cluster.cluster, self.cluster_2)

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

    def test_maintenance_mode(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.v2[self.cluster_1, "hosts", self.host, "maintenance-mode"].post(
            data={"maintenanceMode": "on"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "on")

    def test_ordering_by_default_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        response = self.client.v2[self.cluster_1, "hosts"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertListEqual(
            ["bound-to-same-host", "second-host", "test_host"],
            [host["name"] for host in response.json()["results"]],
        )

    def test_ordering_by_id_desc_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        response = self.client.v2[self.cluster_1, "hosts"].get(query={"ordering": "-id"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 3)
        self.assertListEqual(
            [self.control_host_same_cluster.pk, self.host_2.pk, self.host.pk],
            [host["id"] for host in response.json()["results"]],
        )


class TestHostActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.action = Action.objects.get(name="host_action", prototype=self.host.prototype)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(prototype__name="component_1", service=self.service_1)

    def test_host_cluster_list_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_cluster_retrieve_success(self):
        response = self.client.v2[self.cluster_1, "hosts", self.host, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_cluster_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.cluster_1, "hosts", self.host, "actions", self.action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")
        self.assertEqual(run_task.target_task.task_object, self.host)
        self.assertEqual(run_task.target_task.owner_id, self.host.pk)
        self.assertEqual(run_task.target_task.owner_type, ADCMCoreType.HOST.value)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")

    def test_host_list_success(self):
        response = self.client.v2[self.host, "actions"].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_retrieve_success(self):
        response = self.client.v2[self.host, "actions", self.action].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_run_success(self):
        with RunTaskMock() as run_task:
            response = self.client.v2[self.host, "actions", self.action, "run"].post(
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False}
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], run_task.target_task.id)
        self.assertEqual(run_task.target_task.status, "created")
        self.assertEqual(run_task.target_task.task_object, self.host)
        self.assertEqual(run_task.target_task.owner_id, self.host.pk)
        self.assertEqual(run_task.target_task.owner_type, ADCMCoreType.HOST.value)

        run_task.runner.run(run_task.target_task.id)
        run_task.target_task.refresh_from_db()
        self.assertEqual(run_task.target_task.status, "success")

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


class TestClusterHostComponent(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host1")
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host2")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)
        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )
        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, self.component_1),
                (self.host_1, self.component_2),
                (self.host_2, self.component_1),
                (self.host_2, self.component_2),
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
