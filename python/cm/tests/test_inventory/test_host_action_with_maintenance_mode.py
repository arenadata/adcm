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


from api_v2.service.utils import bulk_add_services_to_cluster

from cm.models import Action, Component, MaintenanceMode, ObjectType, Prototype, Service
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestHostActionWithMaintenanceMode(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_1")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster
        )
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster
        )

        self.service: Service = bulk_add_services_to_cluster(
            cluster=self.cluster,
            prototypes=Prototype.objects.filter(
                type=ObjectType.SERVICE, name="service_one_component", bundle=self.cluster.prototype.bundle
            ),
        ).first()

        self.component = Component.objects.get(service=self.service, prototype__name="component_1")

        self.set_hostcomponent(
            cluster=self.cluster,
            entries=[
                (self.host_1, self.component),
                (self.host_2, self.component),
            ],
        )

        self.cluster_action = Action.objects.get(name="host_action_on_cluster", prototype=self.cluster.prototype)
        self.service_action = Action.objects.get(name="host_action_on_service", prototype=self.service.prototype)
        self.component_action = Action.objects.get(name="host_action_on_component", prototype=self.component.prototype)

    def test_host_in_maintenance_mode_host_action(self):
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_2.fqdn],
            "CLUSTER.maintenance_mode": [self.host_1.fqdn],
            self.service.name: [self.host_2.fqdn],
            f"{self.service.name}.{self.component.name}": [self.host_2.fqdn],
            f"{self.service.name}.maintenance_mode": [self.host_1.fqdn],
            f"{self.service.name}.{self.component.name}.maintenance_mode": [self.host_1.fqdn],
            "target": [self.host_1.fqdn],
        }

        expected_data_base = {
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "component_id": self.component.pk,
                },
            ),
        }

        expected_topology_for_host_2 = {
            **expected_topology_base,
            "target": [self.host_2.fqdn],
        }

        expected_data_for_host_2 = {
            **expected_data_base,
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
        }

        expected_data_for_host_2.pop(("hosts", self.host_1.fqdn), None)

        for obj, action, expected_topology, expected_data in [
            (self.host_1, self.cluster_action, expected_topology_base, expected_data_base),
            (self.host_1, self.service_action, expected_topology_base, expected_data_base),
            (self.host_1, self.component_action, expected_topology_base, expected_data_base),
            (self.host_2, self.cluster_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.service_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.component_action, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_topology=expected_topology, expected_data=expected_data
                )

    def test_service_in_maintenance_mode_host_action(self):
        self.service.maintenance_mode = MaintenanceMode.ON
        self.service.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component.name}": [self.host_1.fqdn, self.host_2.fqdn],
            "target": [self.host_1.fqdn],
        }

        expected_data_base = {
            ("hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "service_maintenance_mode": "true",
                    "component_id": self.component.pk,
                    "component_maintenance_mode": "true",
                },
            ),
        }

        expected_topology_for_host_2 = {
            **expected_topology_base,
            "target": [self.host_2.fqdn],
        }

        expected_data_for_host_2 = {
            **expected_data_base,
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
        }

        expected_data_for_host_2.pop(("hosts", self.host_1.fqdn))

        for obj, action, expected_topology, expected_data in [
            (self.host_1, self.cluster_action, expected_topology_base, expected_data_base),
            (self.host_1, self.service_action, expected_topology_base, expected_data_base),
            (self.host_1, self.component_action, expected_topology_base, expected_data_base),
            (self.host_2, self.cluster_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.service_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.component_action, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )

    def test_component_in_maintenance_mode_host_action(self):
        self.component.maintenance_mode = MaintenanceMode.ON
        self.component.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component.name}": [self.host_1.fqdn, self.host_2.fqdn],
            "target": [self.host_1.fqdn],
        }

        expected_data_base = {
            ("hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "service_maintenance_mode": "true",
                    "component_id": self.component.pk,
                    "component_maintenance_mode": "true",
                },
            ),
        }

        expected_topology_for_host_2 = {
            **expected_topology_base,
            "target": [self.host_2.fqdn],
        }

        expected_data_for_host_2 = {
            **expected_data_base,
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
        }

        expected_data_for_host_2.pop(("hosts", self.host_1.fqdn))

        for obj, action, expected_topology, expected_data in [
            (self.host_1, self.cluster_action, expected_topology_base, expected_data_base),
            (self.host_1, self.service_action, expected_topology_base, expected_data_base),
            (self.host_1, self.component_action, expected_topology_base, expected_data_base),
            (self.host_2, self.cluster_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.service_action, expected_topology_for_host_2, expected_data_for_host_2),
            (self.host_2, self.component_action, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )
