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

from api_v2.tests.cluster.base import ClusterBaseTestCase
from cm.models import ClusterObject, Host, ObjectType, Prototype, ServiceComponent
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON


class TestMapping(ClusterBaseTestCase):
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
