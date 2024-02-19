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

from pathlib import Path

from api_v2.service.utils import bulk_add_services_to_cluster

from cm.models import Action, ClusterObject, ObjectType, Prototype, ServiceComponent
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestHostAction(BaseInventoryTestCase):
    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files/response_templates"

        self.provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster
        )
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster
        )

        self.service: ClusterObject = bulk_add_services_to_cluster(
            cluster=self.cluster,
            prototypes=Prototype.objects.filter(
                type=ObjectType.SERVICE, name="service_one_component", bundle=self.cluster.prototype.bundle
            ),
        ).get()

        self.component = ServiceComponent.objects.get(service=self.service, prototype__name="component_1")
        self.add_hostcomponent_map(
            cluster=self.cluster,
            hc_map=[
                {"service_id": self.service.pk, "component_id": self.component.pk, "host_id": self.host_1.pk},
                {"service_id": self.service.pk, "component_id": self.component.pk, "host_id": self.host_2.pk},
            ],
        )

        self.cluster_action = Action.objects.get(name="host_action_on_cluster", prototype=self.cluster.prototype)
        self.service_action = Action.objects.get(name="host_action_on_service", prototype=self.service.prototype)
        self.component_action = Action.objects.get(name="host_action_on_component", prototype=self.component.prototype)

    def test_host_action(self):
        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            self.service.name: host_names,
            f"{self.service.name}.{self.component.name}": host_names,
            "HOST": [self.host_1.fqdn],
            "target": [self.host_1.fqdn],
        }

        expected_data = {
            ("CLUSTER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("CLUSTER", "hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                },
            ),
            ("CLUSTER", "vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "component_id": self.component.pk,
                },
            ),
            (self.service.name, "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (self.service.name, "hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            (f"{self.service.name}.{self.component.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{self.service.name}.{self.component.name}", "hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("HOST", "vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
            ("target", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("target", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                },
            ),
            ("target", "vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "component_id": self.component.pk,
                },
            ),
        }

        for obj, action in [
            (self.host_1, self.cluster_action),
            (self.host_1, self.service_action),
            (self.host_1, self.component_action),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )