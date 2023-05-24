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
from cm.models import Host, MaintenanceMode, ObjectType, Prototype
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON


class TestHost(ClusterBaseTestCase):
    def test_list_success(self):
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
        host = Host.objects.create(
            fqdn="test-host-new",
            prototype=Prototype.objects.create(bundle=self.bundle, type=ObjectType.HOST),
        )

        response: Response = self.client.post(
            path=reverse(viewname="v2:host-list", kwargs={"cluster_pk": self.cluster_1.pk}),
            data=[{"host_id": host.pk}],
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_maintenance_mode(self):
        self.host.cluster = self.cluster_1
        self.host.save(update_fields=["cluster"])

        self.cluster_1.prototype.allow_maintenance_mode = True
        self.cluster_1.prototype.save(update_fields=["allow_maintenance_mode"])

        response: Response = self.client.post(
            path=reverse(
                viewname="v2:host-maintenance-mode", kwargs={"cluster_pk": self.cluster_1.pk, "pk": self.host.pk}
            ),
            data={"maintenance_mode": MaintenanceMode.ON},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
