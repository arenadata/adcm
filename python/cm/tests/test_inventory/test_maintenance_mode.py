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
    Action,
    Component,
    MaintenanceMode,
)
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestMaintenanceMode(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")

        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )

        self.action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        self.action_on_provider = Action.objects.get(name="action_on_provider", prototype=self.provider.prototype)
        self.action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)

    def test_host_in_maintenance_mode_cluster(self):
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        expected_topology = {
            "CLUSTER.maintenance_mode": [self.host_1.fqdn],
        }
        expected_data = {
            ("CLUSTER.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
        }

        self.assert_inventory(
            obj=self.cluster_1,
            action=self.action_on_cluster,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

    def test_host_in_maintenance_mode_service_one_component(self):
        service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster_1).first()
        component = Component.objects.get(prototype__name="component_1", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component)])

        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        expected_topology_base = {
            "CLUSTER.maintenance_mode": [self.host_1.fqdn],
            f"{service.name}.maintenance_mode": [self.host_1.fqdn],
            f"{service.name}.{component.name}.maintenance_mode": [self.host_1.fqdn],
        }
        expected_data_base = {
            ("CLUSTER.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component.name}.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": service.pk,
                    "service_maintenance_mode": "true",
                    "component_id": component.pk,
                    "component_maintenance_mode": "true",
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component = Action.objects.get(name="action_on_component", prototype=component.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component, action_on_component, expected_topology_base, expected_data_base),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )

    def test_service_in_maintenance_mode_service_one_component(self):
        service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster_1).first()
        component = Component.objects.get(prototype__name="component_1", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component)])

        service.maintenance_mode = MaintenanceMode.ON
        service.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn],
            f"{service.name}": [self.host_1.fqdn],
            f"{service.name}.{component.name}": [self.host_1.fqdn],
        }
        expected_data_base = {
            ("CLUSTER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": service.pk,
                    "service_maintenance_mode": "true",
                    "component_id": component.pk,
                    "component_maintenance_mode": "true",
                },
            ),
        }

        expected_topology_for_provider = {
            "PROVIDER": [self.host_1.fqdn],
        }
        expected_data_for_provider = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component = Action.objects.get(name="action_on_component", prototype=component.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component, action_on_component, expected_topology_base, expected_data_base),
            (self.provider, self.action_on_provider, expected_topology_for_provider, expected_data_for_provider),
            (self.host_1, self.action_on_host_1, expected_topology_for_host, expected_data_for_host),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )

    def test_component_in_maintenance_mode_service_one_component(self):
        service = self.add_services_to_cluster(service_names=["service_one_component"], cluster=self.cluster_1).first()
        component = Component.objects.get(prototype__name="component_1", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component)])

        component.maintenance_mode = MaintenanceMode.ON
        component.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn],
            f"{service.name}": [self.host_1.fqdn],
            f"{service.name}.{component.name}": [self.host_1.fqdn],
        }
        expected_data_base = {
            ("CLUSTER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": service.pk,
                    "service_maintenance_mode": "true",
                    "component_id": component.pk,
                    "component_maintenance_mode": "true",
                },
            ),
        }

        expected_topology_for_provider = {
            "PROVIDER": [self.host_1.fqdn],
        }
        expected_data_for_provider = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component = Action.objects.get(name="action_on_component", prototype=component.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component, action_on_component, expected_topology_base, expected_data_base),
            (self.provider, self.action_on_provider, expected_topology_for_provider, expected_data_for_provider),
            (self.host_1, self.action_on_host_1, expected_topology_for_host, expected_data_for_host),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_data=expected_data, expected_topology=expected_topology
                )

    def test_host_in_maintenance_mode_service_two_components(self):
        host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )
        service = self.add_services_to_cluster(service_names=["service_two_components"], cluster=self.cluster_1).first()
        component_1 = Component.objects.get(prototype__name="component_1", service=service)
        component_2 = Component.objects.get(prototype__name="component_2", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component_1), (host_2, component_2)])

        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [host_2.fqdn],
            "CLUSTER.maintenance_mode": [self.host_1.fqdn],
            f"{service.name}": [host_2.fqdn],
            f"{service.name}.{component_2.name}": [host_2.fqdn],
            f"{service.name}.maintenance_mode": [self.host_1.fqdn],
            f"{service.name}.{component_1.name}.maintenance_mode": [self.host_1.fqdn],
        }
        expected_data_base = {
            ("CLUSTER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("CLUSTER.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (service.name, "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (f"{service.name}.{component_2.name}", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (f"{service.name}.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component_1.name}.maintenance_mode", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": service.pk,
                    "component_1_id": component_1.pk,
                    "component_1_maintenance_mode": "true",
                    "component_2_id": component_2.pk,
                },
            ),
        }

        expected_topology_for_provider = {
            "PROVIDER": [self.host_1.fqdn, host_2.fqdn],
        }

        expected_data_for_provider = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("PROVIDER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_2 = {
            "HOST": [host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("HOST", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": host_2.prototype.pk,
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=component_2.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=host_2.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component_1, action_on_component_1, expected_topology_base, expected_data_base),
            (component_2, action_on_component_2, expected_topology_base, expected_data_base),
            (self.provider, self.action_on_provider, expected_topology_for_provider, expected_data_for_provider),
            (self.host_1, self.action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                )

    def test_service_in_maintenance_mode_service_two_components(self):
        host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )
        service = self.add_services_to_cluster(service_names=["service_two_components"], cluster=self.cluster_1).first()
        component_1 = Component.objects.get(prototype__name="component_1", service=service)
        component_2 = Component.objects.get(prototype__name="component_2", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component_1), (host_2, component_2)])

        service.maintenance_mode = MaintenanceMode.ON
        service.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn, host_2.fqdn],
            f"{service.name}": [self.host_1.fqdn, host_2.fqdn],
            f"{service.name}.{component_1.name}": [self.host_1.fqdn],
            f"{service.name}.{component_2.name}": [host_2.fqdn],
        }
        expected_data_base = {
            ("CLUSTER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("CLUSTER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (service.name, "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (service.name, "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (f"{service.name}.{component_1.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component_2.name}", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": service.pk,
                    "service_maintenance_mode": "true",
                    "component_1_id": component_1.pk,
                    "component_1_maintenance_mode": "true",
                    "component_2_id": component_2.pk,
                    "component_2_maintenance_mode": "true",
                },
            ),
        }

        expected_topology_for_provider = {
            "PROVIDER": [self.host_1.fqdn, host_2.fqdn],
        }

        expected_data_for_provider = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("PROVIDER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_2 = {
            "HOST": [host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("HOST", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=component_2.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=host_2.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component_1, action_on_component_1, expected_topology_base, expected_data_base),
            (component_2, action_on_component_2, expected_topology_base, expected_data_base),
            (self.provider, self.action_on_provider, expected_topology_for_provider, expected_data_for_provider),
            (self.host_1, self.action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                )

    def test_component_in_maintenance_mode_service_two_components(self):
        host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )
        service = self.add_services_to_cluster(service_names=["service_two_components"], cluster=self.cluster_1).first()
        component_1 = Component.objects.get(prototype__name="component_1", service=service)
        component_2 = Component.objects.get(prototype__name="component_2", service=service)

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component_1), (host_2, component_2)])

        component_1.maintenance_mode = MaintenanceMode.ON
        component_1.save(update_fields=["_maintenance_mode"])

        expected_topology_base = {
            "CLUSTER": [self.host_1.fqdn, host_2.fqdn],
            f"{service.name}": [self.host_1.fqdn, host_2.fqdn],
            f"{service.name}.{component_1.name}": [self.host_1.fqdn],
            f"{service.name}.{component_2.name}": [host_2.fqdn],
        }
        expected_data_base = {
            ("CLUSTER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("CLUSTER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (service.name, "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (service.name, "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            (f"{service.name}.{component_1.name}", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            (f"{service.name}.{component_2.name}", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": service.pk,
                    "component_1_id": component_1.pk,
                    "component_1_maintenance_mode": "true",
                    "component_2_id": component_2.pk,
                },
            ),
        }

        expected_topology_for_provider = {
            "PROVIDER": [self.host_1.fqdn, host_2.fqdn],
        }

        expected_data_for_provider = {
            ("PROVIDER", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("PROVIDER", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("HOST", "hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_topology_for_host_2 = {
            "HOST": [host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("HOST", "hosts", host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": host_2.prototype.pk,
                },
            ),
        }

        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=component_2.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=host_2.prototype)

        for obj, action, expected_topology, expected_data in [
            (self.cluster_1, self.action_on_cluster, expected_topology_base, expected_data_base),
            (service, action_on_service, expected_topology_base, expected_data_base),
            (component_1, action_on_component_1, expected_topology_base, expected_data_base),
            (component_2, action_on_component_2, expected_topology_base, expected_data_base),
            (self.provider, self.action_on_provider, expected_topology_for_provider, expected_data_for_provider),
            (self.host_1, self.action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ]:
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                )
