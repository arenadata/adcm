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
from django.urls import reverse

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        self.service = ClusterObject.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="service",
                display_name="test_service",
            ),
            cluster=self.cluster,
        )
        self.component = ServiceComponent.objects.create(
            prototype=Prototype.objects.create(
                bundle=self.bundle,
                type="component",
                display_name="test_component",
            ),
            cluster=self.cluster,
            service=self.service,
        )

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
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host_1,
            service=self.service,
            component=self.component,
        )
        HostComponent.objects.create(
            cluster=self.cluster,
            host=host_2,
            service=self.service,
            component=self.component,
        )

        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)

        host_2.maintenance_mode = MaintenanceMode.OFF
        host_2.save(update_fields=["maintenance_mode"])

        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.OFF)

    def test_maintenance_mode_by_service(self):
        self.client.post(
            path=reverse("service-maintenance-mode", kwargs={"service_id": self.service.pk}),
            data={"maintenance_mode": MaintenanceMode.ON},
            content_type=APPLICATION_JSON,
        )

        self.service.refresh_from_db()

        self.assertEqual(self.component.maintenance_mode, MaintenanceMode.ON)
