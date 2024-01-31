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

from cm.models import ClusterObject, ObjectType, Prototype, ServiceComponent, Upgrade
from cm.services.job.inventory import get_inventory_data
from cm.tests.test_inventory.base import BaseInventoryTestCase, decrypt_secrets
from cm.upgrade import bundle_switch, update_before_upgrade


class TestBeforeUpgrade(BaseInventoryTestCase):
    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files/response_templates"

        self.provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")

        self.test_bundles_dir = Path(__file__).parent / "bundles"

        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")

        self.cluster_upgrade_bundle = self.add_bundle(source_dir=Path(bundles_dir / "cluster_1_upgrade"))
        self.provider_upgrade_bundle = self.add_bundle(source_dir=Path(bundles_dir / "provider_upgrade"))

        self.host_1 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=None)
        self.host_2 = self.add_host(bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=None)
        self.service_two_components = None
        self.component_1 = None
        self.component_2 = None

        self.upgrade_for_provider = Upgrade.objects.get(
            bundle=self.provider_upgrade_bundle, name="upgrade_via_action_simple"
        )
        self.upgrade_for_cluster = Upgrade.objects.get(
            bundle=self.cluster_upgrade_bundle, name="upgrade_via_action_simple"
        )

    def test_provider_two_hosts(self):
        self.provider.before_upgrade["bundle_id"] = self.provider.prototype.bundle.pk
        update_before_upgrade(obj=self.provider)

        bundle_switch(obj=self.provider, upgrade=self.upgrade_for_provider)

        self.provider.state = "success"
        self.provider.save(update_fields=["state"])

        expected_topology_provider = {"PROVIDER": [self.host_1.fqdn, self.host_2.fqdn]}
        expected_topology_host_1 = {"HOST": [self.host_1.fqdn]}
        expected_topology_host_2 = {"HOST": [self.host_2.fqdn]}

        expected_data_provider = {
            ("PROVIDER", "hosts"): (
                self.templates_dir / "before_upgrade_2_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_2_id": self.host_2.pk,
                },
            ),
        }

        expected_data_host_1 = {
            ("HOST", "vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.host_1.provider.pk,
                    "host_prototype_id": Prototype.objects.filter(type="host", version="2.0").last().pk,
                },
            )
        }
        expected_data_host_2 = {
            ("HOST", "vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.host_2.provider.pk,
                    "host_prototype_id": Prototype.objects.filter(type="host", version="2.0").last().pk,
                },
            ),
        }

        for obj, topology, expected_data in (
            (self.provider, expected_topology_provider, expected_data_provider),
            (self.host_1, expected_topology_host_1, expected_data_host_1),
            (self.host_2, expected_topology_host_2, expected_data_host_2),
        ):
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {self.upgrade_for_provider.name}"
            ):
                self.assert_inventory(
                    obj=obj,
                    action=self.upgrade_for_provider.action,
                    expected_topology=topology,
                    expected_data=expected_data,
                )

    def test_provider_full_two_hosts(self):
        self.provider.before_upgrade["bundle_id"] = self.provider.prototype.bundle.pk
        update_before_upgrade(obj=self.provider)

        bundle_switch(obj=self.provider, upgrade=self.upgrade_for_provider)

        self.provider.state = "success"
        self.provider.save(update_fields=["state"])

        expected_topology_provider = {"PROVIDER": [self.host_1.fqdn, self.host_2.fqdn]}

        expected_data_provider = {
            ("all", "vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.host_2.provider.pk,
                    "host_prototype_id": Prototype.objects.filter(type="host", version="2.0").last().pk,
                },
            ),
        }

        actual_inventory = decrypt_secrets(
            source=get_inventory_data(obj=self.provider, action=self.upgrade_for_provider.action)
        )

        self.check_hosts_topology(data=actual_inventory["all"]["children"], expected=expected_topology_provider)
        self.check_data_by_template(data=actual_inventory, templates_data=expected_data_provider)

    def test_2_components_2_hosts(self):
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.service_two_components: ClusterObject = bulk_add_services_to_cluster(
            cluster=self.cluster_1,
            prototypes=Prototype.objects.filter(
                type=ObjectType.SERVICE, name="service_two_components", bundle=self.cluster_1.prototype.bundle
            ),
        ).get()
        self.component_1 = ServiceComponent.objects.get(
            service=self.service_two_components, prototype__name="component_1"
        )
        self.component_2 = ServiceComponent.objects.get(
            service=self.service_two_components, prototype__name="component_2"
        )

        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {
                    "service_id": self.service_two_components.pk,
                    "component_id": self.component_1.pk,
                    "host_id": self.host_1.pk,
                },
                {
                    "service_id": self.service_two_components.pk,
                    "component_id": self.component_1.pk,
                    "host_id": self.host_2.pk,
                },
                {
                    "service_id": self.service_two_components.pk,
                    "component_id": self.component_2.pk,
                    "host_id": self.host_1.pk,
                },
                {
                    "service_id": self.service_two_components.pk,
                    "component_id": self.component_2.pk,
                    "host_id": self.host_2.pk,
                },
            ],
        )

        self.cluster_1.before_upgrade["bundle_id"] = self.cluster_1.prototype.bundle.pk
        update_before_upgrade(obj=self.cluster_1)

        bundle_switch(obj=self.cluster_1, upgrade=self.upgrade_for_cluster)

        self.cluster_1.state = "success"
        self.cluster_1.save(update_fields=["state"])

        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{self.service_two_components.name}.{self.component_1.name}": host_names,
            f"{self.service_two_components.name}.{self.component_2.name}": host_names,
            self.service_two_components.name: host_names,
        }

        expected_data = {
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "before_upgrade_cluster.json.j2",
                {"object_name": self.cluster_1.name, "id": self.cluster_1.id},
            ),
            ("CLUSTER", "vars", "services"): (
                self.templates_dir / "before_upgrade_service_two_components.json.j2",
                {
                    "service_id": self.service_two_components.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.cluster_1,
            action=self.upgrade_for_cluster.action,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )
