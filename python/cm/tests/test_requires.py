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

from adcm.tests.base import BaseTestCase
from core.cluster.types import HostComponentEntry

from cm.api import add_service_to_cluster
from cm.errors import AdcmEx
from cm.issue import update_hierarchy_issues
from cm.models import (
    Bundle,
    Cluster,
    Component,
    ConcernCause,
    Host,
    Prototype,
    Service,
)
from cm.services.mapping import set_host_component_mapping


class TestComponent(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.bundle = Bundle.objects.create()
        self.cluster = Cluster.objects.create(
            prototype=Prototype.objects.create(bundle=self.bundle, type="cluster"),
            name="test_cluster",
        )
        self.service_proto_1 = Prototype.objects.create(
            bundle=self.bundle,
            name="service_1",
            type="service",
        )
        self.service_proto_2 = Prototype.objects.create(
            bundle=self.bundle,
            name="service_2",
            type="service",
            requires=[{"service": "service_1", "component": "component_1_1"}, {"service": "service_3"}],
        )
        self.service_proto_3 = Prototype.objects.create(
            bundle=self.bundle,
            name="service_3",
            type="service",
        )
        self.component_1_1_proto = Prototype.objects.create(
            bundle=self.bundle,
            type="component",
            parent=self.service_proto_1,
            name="component_1_1",
            requires=[{"service": "service_1", "component": "component_1_1"}, {"service": "service_2"}],
        )
        self.component_2_1_proto = Prototype.objects.create(
            bundle=self.bundle,
            type="component",
            parent=self.service_proto_2,
            name="component_2_1",
            requires=[{"service": "service_1", "component": "component_1_1"}, {"service": "service_2"}],
        )

    def test_requires_hc(self):
        service_1 = add_service_to_cluster(cluster=self.cluster, proto=self.service_proto_1)
        component_1 = Component.objects.get(prototype=self.component_1_1_proto, service=service_1)
        host = Host.objects.create(
            prototype=Prototype.objects.create(type="host", bundle=self.bundle), cluster=self.cluster
        )

        with self.assertRaisesRegex(
            AdcmEx, 'Services required for component "component_1_1" of service "service_1" are missing: service_2'
        ):
            set_host_component_mapping(
                cluster_id=self.cluster.id,
                bundle_id=self.cluster.bundle_id,
                new_mapping=(HostComponentEntry(host_id=host.id, component_id=component_1.id),),
            )

    def test_service_requires_issue(self):
        service_2 = Service.objects.create(prototype=self.service_proto_2, cluster=self.cluster)
        update_hierarchy_issues(obj=self.cluster)
        concerns = service_2.concerns.all()
        self.assertEqual(len(concerns), 1)
        self.assertEqual(concerns.first().cause, ConcernCause.REQUIREMENT)
        self.assertIn(
            "${source} has an issue with requirement. Need to be installed: ${target}",
            concerns.first().reason.values(),
        )
