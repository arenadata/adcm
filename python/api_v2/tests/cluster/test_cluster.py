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

from api_v2.tests.cluster.base import ClusterBaseTestCase
from cm.models import (
    Cluster,
    ClusterObject,
    ClusterStatus,
    Host,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT

from adcm.tests.base import APPLICATION_JSON


class TestCluster(ClusterBaseTestCase):
    def get_cluster_status_mock(self) -> Callable:
        def inner(cluster: Cluster) -> int:
            if cluster.pk == self.cluster_1.pk:
                return 0

            return 32

        return inner

    def test_list_success(self):
        response: Response = self.client.get(path=reverse(viewname="v2:cluster-list"))

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_retrieve_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.cluster_1.pk)

    def test_filter_by_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": self.cluster_1_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_wrong_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"name": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_filter_by_status_up_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response: Response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ClusterStatus.UP},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_status_down_success(self):
        with patch("api_v2.cluster.filters.get_cluster_status", new_callable=self.get_cluster_status_mock):
            response: Response = self.client.get(
                path=reverse(viewname="v2:cluster-list"),
                data={"status": ClusterStatus.DOWN},
            )

            self.assertEqual(response.status_code, HTTP_200_OK)
            self.assertEqual(response.json()["count"], 1)
            self.assertEqual(response.json()["results"][0]["id"], self.cluster_2.pk)

    def test_filter_by_prototype_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototype_name": self.cluster_1_prototype_name},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["id"], self.cluster_1.pk)

    def test_filter_by_wrong_prototype_name_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-list"),
            data={"prototype_name": "wrong"},
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 0)

    def test_create_success(self):
        response: Response = self.client.post(
            path=reverse(viewname="v2:cluster-list"),
            data={
                "prototype": self.cluster_1_prototype.pk,
                "name": "new_test_cluster",
                "description": "Test cluster description",
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_update_success(self):
        new_test_cluster_name = "new_test_cluster_name"
        response: Response = self.client.patch(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
            data={"name": new_test_cluster_name},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        self.cluster_1.refresh_from_db()

        self.assertEqual(self.cluster_1.name, new_test_cluster_name)

    def test_delete_success(self):
        response: Response = self.client.delete(
            path=reverse(viewname="v2:cluster-detail", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertFalse(Cluster.objects.filter(pk=self.cluster_1.pk).exists())

    def test_service_prototypes_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:cluster-service-prototypes", kwargs={"pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_list_mapping_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_create_mapping_success(self):
        service = ClusterObject.objects.create(
            cluster=self.cluster_1, prototype=Prototype.objects.create(bundle=self.bundle, type=ObjectType.SERVICE)
        )
        host = Host.objects.create(
            fqdn="test-host-new",
            prototype=Prototype.objects.create(bundle=self.bundle, type=ObjectType.HOST),
        )
        component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type=ObjectType.COMPONENT),
            cluster=self.cluster_1,
            service=self.service,
        )

        response: Response = self.client.post(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"service": service.pk, "host": host.pk, "component": component.pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_mapping_hosts_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-hosts", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    def test_mapping_components_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-components", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
