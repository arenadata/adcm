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

from cm.api import add_service_to_cluster
from cm.models import (
    ADCMEntityStatus,
    ClusterObject,
    MaintenanceMode,
    ObjectType,
    Prototype,
)
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestServiceAPI(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle_file = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files" / "test_services_bundle.tar"
        _, self.cluster, _ = self.upload_bundle_create_cluster_config_log(bundle_path=bundle_file)

        for service_proto in Prototype.objects.filter(type=ObjectType.SERVICE, name__in={"service_1", "service_2"}):
            self.last_created_service = add_service_to_cluster(cluster=self.cluster, proto=service_proto)

    def get_service_status_mock(self) -> Callable:
        def inner(service: ClusterObject) -> int:
            if service.pk == self.last_created_service.pk:
                return 0

            return 32

        return inner

    def test_list_success(self):
        response: Response = self.client.get(
            path=reverse("v2:clusterobject-list", kwargs={"cluster_pk": self.cluster.pk}), content_type=APPLICATION_JSON
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(
                "v2:clusterobject-detail", kwargs={"cluster_pk": self.cluster.pk, "pk": self.last_created_service.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.last_created_service.pk)

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(
                "v2:clusterobject-detail", kwargs={"cluster_pk": self.cluster.pk, "pk": self.last_created_service.pk}
            ),
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(ClusterObject.objects.filter(pk=self.last_created_service.pk).exists())

    def test_create_success(self):
        manual_add_service_proto = Prototype.objects.get(type=ObjectType.SERVICE, name="service_3_manual_add")
        response: Response = self.client.post(
            path=reverse("v2:clusterobject-list", kwargs={"cluster_pk": self.cluster.pk}),
            data={"prototype": manual_add_service_proto.pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_filter_by_name_success(self):
        response: Response = self.client.get(
            path=reverse("v2:clusterobject-list", kwargs={"cluster_pk": self.cluster.pk}),
            data={"name": "service_1"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_status_success(self):
        with patch("api_v2.service.filters.get_service_status", new_callable=self.get_service_status_mock):
            response: Response = self.client.get(
                path=reverse("v2:clusterobject-list", kwargs={"cluster_pk": self.cluster.pk}),
                data={"status": ADCMEntityStatus.UP},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["id"], self.last_created_service.pk)

    def test_limit_offset_success(self):
        response: Response = self.client.get(
            path=reverse("v2:clusterobject-list", kwargs={"cluster_pk": self.cluster.pk}),
            data={"limit": 1, "offset": 1},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 1)

    def test_change_mm(self):
        response: Response = self.client.post(
            path=reverse(
                "v2:clusterobject-maintenance-mode",
                kwargs={"cluster_pk": self.cluster.pk, "pk": self.last_created_service.pk},
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
