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
from cm.models import Action, MaintenanceMode
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestHost(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")

    def test_list_success(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:host-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.host.pk)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"host_id": self.host.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        self.host.refresh_from_db()
        self.assertEqual(self.host.cluster, self.cluster_1)

    def test_maintenance_mode(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk}
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

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:host-action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "host_pk": self.host.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:host-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host.pk,
                    "pk": self.action.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                "v2:host-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "host_pk": self.host.pk,
                    "pk": self.action.pk,
                },
            ),
            data={"host_component_map": {}, "config": {}, "attr": {}, "is_verbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
