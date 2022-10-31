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
from rest_framework.status import HTTP_204_NO_CONTENT, HTTP_409_CONFLICT

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
)


class TestService(BaseTestCase):
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

    def test_delete(self):
        self.service.state = "updated"
        self.service.save(update_fields=["state"])
        url = reverse(
            "service-details", kwargs={"cluster_id": self.cluster.pk, "service_id": self.service.pk}
        )

        response: Response = self.client.delete(path=url, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "SERVICE_DELETE_ERROR")

        self.service.state = "created"
        self.service.save(update_fields=["state"])

        response: Response = self.client.delete(path=url, content_type=APPLICATION_JSON)

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_maintenance_mode_by_hosts(self):
        host_1 = Host.objects.create(
            fqdn="test_host_1",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
            maintenance_mode=MaintenanceMode.ON,
        )
        host_2 = Host.objects.create(
            fqdn="test_host_2",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
            maintenance_mode=MaintenanceMode.ON,
        )
        component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster,
            service=self.service,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host_1,
            service=self.service,
            component=component,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host_2,
            service=self.service,
            component=component,
        )

        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)

        host_2.maintenance_mode = MaintenanceMode.OFF
        host_2.save(update_fields=["maintenance_mode"])

        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)

    def test_maintenance_mode_by_components(self):
        component_1 = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component_1",
            ),
            cluster=self.cluster,
            service=self.service,
            _maintenance_mode=MaintenanceMode.ON,
        )
        component_2 = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component_2",
            ),
            cluster=self.cluster,
            service=self.service,
            _maintenance_mode=MaintenanceMode.ON,
        )
        host = Host.objects.create(
            fqdn="test_host",
            prototype=Prototype.objects.create(bundle=self.bundle, type="host"),
            maintenance_mode=MaintenanceMode.OFF,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host,
            service=self.service,
            component=component_1,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host,
            service=self.service,
            component=component_2,
        )

        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.ON)

        self.client.post(
            path=reverse("component-maintenance-mode", kwargs={"component_id": component_2.pk}),
            data={"maintenance_mode": MaintenanceMode.OFF},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(self.service.maintenance_mode, MaintenanceMode.OFF)
