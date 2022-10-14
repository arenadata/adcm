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
from django.urls import reverse
from rest_framework import status

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Bundle, Cluster, ClusterObject, Prototype


class TestCluster(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.prototype = Prototype.objects.create(
            name="test_prototype_name", type="cluster", bundle=self.bundle
        )
        self.prototype_service = Prototype.objects.create(type="service", bundle=self.bundle)
        self.cluster = Cluster.objects.create(name="test_cluster_name", prototype=self.prototype)
        self.service = ClusterObject.objects.create(
            cluster=self.cluster, prototype=self.prototype_service
        )

    def test_service_deletion(self):
        self.service.state = "updated"
        self.service.save(update_fields=["state"])
        url = reverse(
            "service-details", kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk}
        )
        response = self.client.delete(path=url, content_type=APPLICATION_JSON)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "SERVICE_DELETE_ERROR")

        self.service.state = "created"
        self.service.save(update_fields=["state"])
        response = self.client.delete(path=url, content_type=APPLICATION_JSON)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
