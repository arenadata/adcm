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
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import Bundle, Cluster, ClusterObject, Prototype, ServiceComponent


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        bundle = Bundle.objects.create()
        cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=bundle, type="cluster"),
            name="test_cluster",
        )
        service = ClusterObject.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="service",
                display_name="test_service",
            ),
            cluster=cluster,
        )
        self.component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=cluster,
            service=service,
        )

    def test_set_maintenance_mode_success(self):
        response: Response = self.client.patch(
            path=reverse("component-details", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": True},
            content_type=APPLICATION_JSON,
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertTrue(self.component.maintenance_mode)

        response: Response = self.client.patch(
            path=reverse("component-details", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": False},
            content_type=APPLICATION_JSON,
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertFalse(self.component.maintenance_mode)

    def test_set_maintenance_mode_fail(self):
        response: Response = self.client.patch(
            path=reverse("component-details", kwargs={"component_id": self.component.pk}),
            data={"maintenance_mode": "string"},
            content_type=APPLICATION_JSON,
        )

        self.component.refresh_from_db()

        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)
        self.assertFalse(self.component.maintenance_mode)
