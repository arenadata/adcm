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
from cm.models import HostComponent, ServiceComponent
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestMapping(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.host = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host")
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host)
        self.service_1 = self.add_service_to_cluster(service_name="service_1", cluster=self.cluster_1)
        self.component_1 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_1"
        )
        self.hostcomponent_map = self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[{"host_id": self.host.pk, "service_id": self.service_1.pk, "component_id": self.component_1.pk}],
        )

    def test_list_mapping_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_create_mapping_success(self):
        host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="test_host_2")
        self.add_host_to_cluster(cluster=self.cluster_1, host=host_2)
        component_2 = ServiceComponent.objects.get(
            cluster=self.cluster_1, service=self.service_1, prototype__name="component_2"
        )

        response: Response = self.client.post(
            path=reverse(viewname="v2:mapping-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data={"service": self.service_1.pk, "host": host_2.pk, "component": component_2.pk},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(HostComponent.objects.count(), 2)

    def test_mapping_hosts_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-hosts", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], self.host.pk)

    def test_mapping_components_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v2:mapping-components", kwargs={"cluster_pk": self.cluster_1.pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["id"], self.component_1.pk)
