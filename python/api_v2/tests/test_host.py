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

from api_v2.tests.base import BaseAPITestCase
from cm.models import Action, Cluster, Host, MaintenanceMode
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)


class TestHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-list"),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
        )
        data = {
            "id": 1,
            "fqdn": "test_host",
            "state": "created",
            "status": 32,
            "provider": {"id": 1, "name": "provider"},
            "concerns": [],
            "is_maintenance_mode_available": False,
            "maintenance_mode": "OFF",
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host.pk)
        self.assertEqual(response.data, data)

    def test_create_without_cluster_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "provider": self.provider.pk,
                "fqdn": "new-test-host",
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": 2}),
        )

        data = {
            "id": 2,
            "fqdn": "new-test-host",
            "state": "created",
            "status": 32,
            "provider": {"id": 1, "name": "provider"},
            "concerns": [],
            "is_maintenance_mode_available": False,
            "maintenance_mode": "OFF",
        }
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.data, data)

    def test_create_with_cluster_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={"provider": self.provider.pk, "fqdn": "new-test-host", "cluster": self.cluster_1.pk},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        host_2 = Host.objects.get(fqdn="new-test-host")
        self.assertEqual(host_2.cluster, self.cluster_1)

    def test_fqdn_validation_create_failed(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list"),
            data={
                "provider": self.provider.pk,
                "fqdn": "new_test_host",
            },
        )

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["desc"], "Wrong FQDN. Errors: `__`")

    def test_update_success(self):
        new_test_host_fqdn = "new-fqdn"
        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"fqdn": new_test_host_fqdn},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.fqdn, new_test_host_fqdn)

        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"cluster": self.cluster_1.pk},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

    def test_update_fail(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}),
            data={"cluster": self.get_non_existent_pk(Cluster)},
        )
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_delete_success(self):
        response: Response = self.client.delete(path=reverse(viewname="v2:host-detail", kwargs={"pk": self.host.pk}))
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

        self.assertFalse(Host.objects.filter(pk=self.host.pk).exists())

    def test_maintenance_mode(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-maintenance-mode", kwargs={"pk": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "MAINTENANCE_MODE_NOT_AVAILABLE")

        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-maintenance-mode", kwargs={"pk": self.host.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
        )
        self.assertEqual(response.status_code, HTTP_200_OK)


class TestClusterHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")

    def test_list_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:host-cluster-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host.pk)

    def test_create_success(self):
        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_second")
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-cluster-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"hosts": [self.host.pk, host_2.pk]},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.host.refresh_from_db()
        host_2.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)
        self.assertEqual(host_2.cluster, self.cluster_1)

    def test_maintenance_mode(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-cluster-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)


class TestHostActions(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.action = Action.objects.get(name="host_action", prototype=self.host.prototype)

    def test_host_cluster_list_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:host-cluster-action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_host_cluster_retrieve_success(self):
        response: Response = self.client.get(
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
        response: Response = self.client.post(
            path=reverse(
                "v2:host-cluster-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host.pk,
                    "pk": self.action.pk,
                },
            ),
            data={"host_component_map": {}, "config": {}, "attr": {}, "is_verbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_host_list_success(self):
        response: Response = self.client.get(
            path=reverse("v2:host-action-list", kwargs={"host_pk": self.host.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_host_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse("v2:host-action-detail", kwargs={"host_pk": self.host.pk, "pk": self.action.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_host_run_success(self):
        response: Response = self.client.post(
            path=reverse("v2:host-action-run", kwargs={"host_pk": self.host.pk, "pk": self.action.pk}),
            data={"host_component_map": {}, "config": {}, "attr": {}, "is_verbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
