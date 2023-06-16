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
from cm.models import Action, MaintenanceMode, ServiceComponent
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT


class TestComponentAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.component_1 = ServiceComponent.objects.get(
            prototype__name="component_1", service=self.service_1, cluster=self.cluster_1
        )
        self.component_2_to_delete = ServiceComponent.objects.get(
            prototype__name="component_2", service=self.service_1, cluster=self.cluster_1
        )
        self.action_1 = Action.objects.get(name="action_1_comp_1")

    def test_list(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:component-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_1.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:component-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.component_1.pk)

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(
                "v2:component-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(ServiceComponent.objects.filter(pk=self.component_1.pk).exists())

    def test_action_list_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:component-action-list",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:component-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.action_1.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                "v2:component-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "component_pk": self.component_1.pk,
                    "pk": self.action_1.pk,
                },
            ),
            data={"host_component_map": {}, "config": {}, "attr": {}, "is_verbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_change_mm(self):
        response: Response = self.client.post(
            path=reverse(
                "v2:component-maintenance-mode",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_1.pk,
                    "pk": self.component_1.pk,
                },
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
