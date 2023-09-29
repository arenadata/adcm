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

from typing import Callable
from unittest.mock import patch

from api_v2.tests.base import BaseAPITestCase
from cm.models import (
    Action,
    ADCMEntityStatus,
    ClusterObject,
    MaintenanceMode,
    ObjectType,
    Prototype,
)
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_409_CONFLICT,
)


class TestServiceAPI(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.service_2 = self.add_service_to_cluster(service_name="service_2", cluster=self.cluster_1)
        self.action = Action.objects.filter(prototype=self.service_2.prototype).first()

    def get_service_status_mock(self) -> Callable:
        def inner(service: ClusterObject) -> int:
            if service.pk == self.service_2.pk:
                return 0

            return 32

        return inner

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_adcm_4544_list_service_name_ordering_success(self):
        service_3 = self.add_service_to_cluster(service_name="service_3_manual_add", cluster=self.cluster_1)
        service_list = [self.service_1.display_name, self.service_2.display_name, service_3.display_name]
        response: Response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"ordering": "displayName"},
        )

        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            service_list,
        )

        response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"ordering": "-displayName"},
        )

        self.assertListEqual(
            [service["displayName"] for service in response.json()["results"]],
            service_list[::-1],
        )

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.service_2.pk)

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

    def test_delete_failed(self):
        self.service_2.state = "non_created"
        self.service_2.save(update_fields=["state"])

        response: Response = self.client.delete(
            path=reverse(
                viewname="v2:service-detail", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk}
            ),
        )

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertTrue(ClusterObject.objects.filter(pk=self.service_2.pk).exists())

    def test_create_success(self):
        initial_service_count = ClusterObject.objects.count()
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")

        response: Response = self.client.post(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"prototype_id": manual_add_service_proto.pk}],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(ClusterObject.objects.count(), initial_service_count + 1)

    def test_filter_by_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"name": "service_1"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_status_success(self):
        with patch("api_v2.service.filters.get_service_status", new_callable=self.get_service_status_mock):
            response: Response = self.client.get(
                path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
                data={"status": ADCMEntityStatus.UP},
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], self.service_2.pk)

    def test_limit_offset_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:service-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"limit": 1, "offset": 1},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_change_mm(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-maintenance-mode",
                kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.service_2.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_action_list_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:service-action-list",
                kwargs={"cluster_pk": self.cluster_1.pk, "service_pk": self.service_2.pk},
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 2)

    def test_action_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                viewname="v2:service-action-detail",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_2.pk,
                    "pk": self.action.pk,
                },
            ),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(response.json())

    def test_action_run_success(self):
        response: Response = self.client.post(
            path=reverse(
                viewname="v2:service-action-run",
                kwargs={
                    "cluster_pk": self.cluster_1.pk,
                    "service_pk": self.service_2.pk,
                    "pk": self.action.pk,
                },
            ),
            data={"host_component_map": [], "config": {}, "attr": {}, "is_verbose": False},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
