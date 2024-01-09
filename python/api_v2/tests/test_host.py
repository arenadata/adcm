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

from api_v2.tests.base import BaseAPITestCase
from cm.models import Action, Host, HostComponent, HostProvider, ServiceComponent
from django.urls import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


class TestHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(
            bundle=self.provider_bundle, description="description", provider=self.provider, fqdn="test_host"
        )

    def test_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:host-list"),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
        )
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
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new-test-host",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        response = self.client.get(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 2}),
        )

        data = {
            "id": 2,
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
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={"hostprovider_id": self.get_non_existent_pk(model=HostProvider), "name": "woohoo"},
        )

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_create_with_cluster_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={"hostprovider_id": self.provider.pk, "name": "new-test-host", "cluster_id": self.cluster_1.pk},
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_2 = Host.objects.get(fqdn="new-test-host")
        self.assertEqual(host_2.cluster, self.cluster_1)

    def test_fqdn_validation_create_failed(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "hostproviderId": self.provider.pk,
                "name": "new_test_host",
            },
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "Wrong FQDN. Errors: `__`")

    def test_update_name_success(self):
        new_test_host_fqdn = "new-fqdn"
        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"name": new_test_host_fqdn},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.fqdn, new_test_host_fqdn)

    def test_update_name_fail(self):
        new_host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="new_host")

        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"name": new_host.name},
        )
        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "HOST_CONFLICT", "desc": "Host with the same name already exists.", "level": "error"},
        )

    def test_update_name_state_not_create_fail(self):
        self.host.state = "running"
        self.host.save(update_fields=["state"])

        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"name": "new-fqdn"},
        )
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

        response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"name": "new-fqdn"},
        )
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
        response = self.client.delete(path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.assertFalse(Host.objects.filter(pk=self.host.pk).exists())

    def test_maintenance_mode(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-maintenance-mode", kwargs={"pk": self.host.pk}),
            data={"maintenanceMode": "on"},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "MAINTENANCE_MODE_NOT_AVAILABLE")

        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.post(
            path=reverse(viewname="v2:host-maintenance-mode", kwargs={"pk": self.host.pk}),
            data={"maintenanceMode": "on"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "on")


class TestClusterHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")

    def test_list_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.get(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.get(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host.pk)

    def test_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.host.pk},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

    def test_create_belonging_to_another_cluster_fail(self):
        self.add_host_to_cluster(cluster=self.cluster_2, host=self.host)

        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.host.pk},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "FOREIGN_HOST", "desc": "Host already linked to another cluster.", "level": "error"},
        )

    def test_create_already_added_fail(self) -> None:
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)

        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.host.pk},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {"code": "HOST_CONFLICT", "desc": "The host is already associated with this cluster.", "level": "error"},
        )

    def test_create_not_found_fail(self):
        response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hostId": self.get_non_existent_pk(model=Host)},
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertDictEqual(
            response.json(),
            {"code": "BAD_REQUEST", "desc": 'host_id - Invalid pk "2" - object does not exist.;', "level": "error"},
        )

    def test_maintenance_mode(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk},
            ),
            data={"maintenanceMode": "on"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data["maintenance_mode"], "on")


class TestHostActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.action = Action.objects.get(name="host_action", prototype=self.host.prototype)

        self.service_1 = self.add_services_to_cluster(service_names=["service_1"], cluster=self.cluster_1).get()
        self.component_1 = ServiceComponent.objects.get(prototype__name="component_1", service=self.service_1)

    def test_host_cluster_list_success(self):
        response = self.client.get(
            path=reverse(
                "v2:host-cluster-action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_cluster_retrieve_success(self):
        response = self.client.get(
            path=reverse(
                "v2:host-cluster-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host.pk,
                    "pk": self.action.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_cluster_run_success(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse(
                    "v2:host-cluster-action-run",
                    kwargs={
                        "cluster_pk": self.cluster_1.pk,
                        "host_pk": self.host.pk,
                        "pk": self.action.pk,
                    },
                ),
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_host_list_success(self):
        response = self.client.get(
            path=reverse("v2:host-action-list", kwargs={"host_pk": self.host.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_host_retrieve_success(self):
        response = self.client.get(
            path=reverse("v2:host-action-detail", kwargs={"host_pk": self.host.pk, "pk": self.action.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_run_success(self):
        with patch("cm.job.run_task", return_value=None):
            response = self.client.post(
                path=reverse("v2:host-action-run", kwargs={"host_pk": self.host.pk, "pk": self.action.pk}),
                data={"hostComponentMap": [], "config": {}, "adcmMeta": {}, "isVerbose": False},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_host_mapped_list_success(self) -> None:
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        response = self.client.get(
            path=reverse(
                "v2:host-action-list",
                kwargs={"host_pk": self.host.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 4)

    def test_host_mapped_retrieve_success(self) -> None:
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        action = Action.objects.filter(prototype=self.service_1.prototype, host_action=True).first()
        response = self.client.get(
            path=reverse(
                "v2:host-action-detail",
                kwargs={"host_pk": self.host.pk, "pk": action.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_filter_is_host_own_action_true_success(self):
        HostComponent.objects.create(
            cluster=self.cluster_1, service=self.service_1, component=self.component_1, host=self.host
        )
        host_action = Action.objects.filter(name="host_action", prototype=self.host.prototype).first()

        response = self.client.get(
            path=reverse(viewname="v2:host-action-list", kwargs={"host_pk": self.host.pk}),
            data={"isHostOwnAction": True},
        )

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

        response = self.client.get(
            path=reverse(viewname="v2:host-action-list", kwargs={"host_pk": self.host.pk}),
            data={"isHostOwnAction": False},
        )

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

        response = self.client.get(
            path=reverse(viewname="v2:host-action-list", kwargs={"host_pk": self.host.pk}),
            data={"isHostOwnAction": False, "prototypeId": self.component_1.prototype.pk},
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
        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "host_id": self.host_1.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_1.pk,
                },
                {
                    "host_id": self.host_1.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_2.pk,
                },
                {
                    "host_id": self.host_2.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_1.pk,
                },
                {
                    "host_id": self.host_2.pk,
                    "service_id": self.service_1.pk,
                    "component_id": self.component_2.pk,
                },
            ],
        )

    def test_components_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:host-cluster-component-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host_1.pk},
            )
        )
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
        response = self.client.get(
            path=reverse(
                viewname="v2:host-cluster-component-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host_1.pk},
            ),
            data={"ordering": "-displayName"},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)
        self.assertListEqual(
            [component["name"] for component in response.json()["results"]], ["component_2", "component_1"]
        )
