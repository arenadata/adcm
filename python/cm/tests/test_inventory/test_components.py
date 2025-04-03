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


from cm.models import Action, Component, Service
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestInventoryComponents(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )

    def test_1_component_1_host(self):
        service: Service = self.add_services_to_cluster(
            service_names=["service_one_component"], cluster=self.cluster_1
        ).first()
        component = Component.objects.get(service=service, prototype__name="component_1")

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component)])

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component = Action.objects.get(name="action_on_component", prototype=component.prototype)
        action_on_host = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)

        host_names = [self.host_1.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{service.name}.{component.name}": host_names,
            service.name: host_names,
        }

        expected_data = {
            ("hosts", self.host_1.fqdn): (
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
                    "component_id": component.pk,
                },
            ),
        }

        expected_topology_for_host = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host = {
            ("hosts", self.host_1.fqdn): (
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

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (service, action_on_service, expected_topology, expected_data),
            (component, action_on_component, expected_topology, expected_data),
            (self.host_1, action_on_host, expected_topology_for_host, expected_data_for_host),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_2_components_2_hosts_mapped_all_to_all(self):
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

        service: Service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).first()
        component_1 = Component.objects.get(service=service, prototype__name="component_1")
        component_2 = Component.objects.get(service=service, prototype__name="component_2")

        component_2.set_multi_state("kat")
        self.host_2.set_multi_state("bac")
        self.host_2.set_multi_state("osscc")

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, component_1),
                (self.host_2, component_1),
                (self.host_1, component_2),
                (self.host_2, component_2),
            ],
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=component_2.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=self.host_2.prototype)

        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{service.name}.{component_1.name}": host_names,
            f"{service.name}.{component_2.name}": host_names,
            service.name: host_names,
        }

        expected_data = {
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
                    "multi_state": '["bac", "osscc"]',
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
                    "component_2_id": component_2.pk,
                    "component_2_multi_state": '["kat"]',
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }
        expected_data_for_host_1 = {
            ("hosts", self.host_1.fqdn): (
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
            "HOST": [self.host_2.fqdn],
        }
        expected_data_for_host_2 = {
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "multi_state": '["bac", "osscc"]',
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_2.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (service, action_on_service, expected_topology, expected_data),
            (component_1, action_on_component_1, expected_topology, expected_data),
            (component_2, action_on_component_2, expected_topology, expected_data),
            (self.host_1, action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (self.host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_2_components_2_hosts_mapped_in_pairs(self):
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

        service: Service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).first()
        component_1 = Component.objects.get(service=service, prototype__name="component_1")
        component_2 = Component.objects.get(service=service, prototype__name="component_2")

        self.set_hostcomponent(cluster=self.cluster_1, entries=[(self.host_1, component_1), (self.host_2, component_2)])

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=component_2.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=self.host_2.prototype)

        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{service.name}.{component_1.name}": [self.host_1.fqdn],
            f"{service.name}.{component_2.name}": [self.host_2.fqdn],
            service.name: host_names,
        }

        expected_data = {
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
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": service.pk,
                    "component_1_id": component_1.pk,
                    "component_2_id": component_2.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("hosts", self.host_1.fqdn): (
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
            "HOST": [self.host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_2.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (service, action_on_service, expected_topology, expected_data),
            (component_1, action_on_component_1, expected_topology, expected_data),
            (component_2, action_on_component_2, expected_topology, expected_data),
            (self.host_1, action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (self.host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_2_services_2_components_each_on_1_host(self):
        service: Service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).first()

        component_1_s1 = Component.objects.get(service=service, prototype__name="component_1")
        component_2_s1 = Component.objects.get(service=service, prototype__name="component_2")

        another_service: Service = self.add_services_to_cluster(
            service_names=["another_service_two_components"], cluster=self.cluster_1
        ).first()

        component_1_s2 = Component.objects.get(service=another_service, prototype__name="component_1")
        component_2_s2 = Component.objects.get(service=another_service, prototype__name="component_2")

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, component_1_s1),
                (self.host_1, component_2_s1),
                (self.host_1, component_1_s2),
                (self.host_1, component_2_s2),
            ],
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service_1 = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_service_2 = Action.objects.get(name="action_on_service", prototype=another_service.prototype)
        action_on_component_1_s1 = Action.objects.get(name="action_on_component_1", prototype=component_1_s1.prototype)
        action_on_component_2_s1 = Action.objects.get(name="action_on_component_2", prototype=component_2_s1.prototype)
        action_on_component_1_s2 = Action.objects.get(name="action_on_component_1", prototype=component_1_s2.prototype)
        action_on_component_2_s2 = Action.objects.get(name="action_on_component_1", prototype=component_1_s2.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)

        host_names = [self.host_1.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{service.name}.{component_1_s1.name}": host_names,
            f"{service.name}.{component_2_s1.name}": host_names,
            f"{another_service.name}.{component_1_s2.name}": host_names,
            f"{another_service.name}.{component_2_s2.name}": host_names,
            service.name: host_names,
            another_service.name: host_names,
        }

        expected_data = {
            ("hosts", self.host_1.fqdn): (
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
                self.templates_dir / "two_services_two_components_each.json.j2",
                {
                    "service_1_id": service.pk,
                    "component_1_s1_id": component_1_s1.pk,
                    "component_2_s1_id": component_2_s1.pk,
                    "service_2_id": another_service.pk,
                    "component_1_s2_id": component_1_s2.pk,
                    "component_2_s2_id": component_2_s2.pk,
                },
            ),
        }

        expected_topology_for_host = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host = {
            ("hosts", self.host_1.fqdn): (
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

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (service, action_on_service_1, expected_topology, expected_data),
            (another_service, action_on_service_2, expected_topology, expected_data),
            (component_1_s1, action_on_component_1_s1, expected_topology, expected_data),
            (component_2_s1, action_on_component_2_s1, expected_topology, expected_data),
            (component_1_s2, action_on_component_1_s2, expected_topology, expected_data),
            (component_2_s2, action_on_component_2_s2, expected_topology, expected_data),
            (self.host_1, action_on_host_1, expected_topology_for_host, expected_data_for_host),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_2_services_2_components_each_2_hosts_cross_mapping(self):
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )
        service: Service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).get()
        component_1_s1 = Component.objects.get(service=service, prototype__name="component_1")
        component_2_s1 = Component.objects.get(service=service, prototype__name="component_2")

        another_service: Service = self.add_services_to_cluster(
            service_names=["another_service_two_components"], cluster=self.cluster_1
        ).first()

        component_1_s2 = Component.objects.get(service=another_service, prototype__name="component_1")
        component_2_s2 = Component.objects.get(service=another_service, prototype__name="component_2")

        self.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, component_1_s1),
                (self.host_2, component_2_s1),
                (self.host_1, component_1_s2),
                (self.host_2, component_2_s2),
            ],
        )

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service_1 = Action.objects.get(name="action_on_service", prototype=service.prototype)
        action_on_service_2 = Action.objects.get(name="action_on_service", prototype=another_service.prototype)
        action_on_component_1_s1 = Action.objects.get(name="action_on_component_1", prototype=component_1_s1.prototype)
        action_on_component_2_s1 = Action.objects.get(name="action_on_component_2", prototype=component_2_s1.prototype)
        action_on_component_1_s2 = Action.objects.get(name="action_on_component_1", prototype=component_1_s2.prototype)
        action_on_component_2_s2 = Action.objects.get(name="action_on_component_1", prototype=component_1_s2.prototype)
        action_on_host_1 = Action.objects.get(name="action_on_host", prototype=self.host_1.prototype)
        action_on_host_2 = Action.objects.get(name="action_on_host", prototype=self.host_2.prototype)

        expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            f"{service.name}.{component_1_s1.name}": [self.host_1.fqdn],
            f"{service.name}.{component_2_s1.name}": [self.host_2.fqdn],
            f"{another_service.name}.{component_1_s2.name}": [self.host_1.fqdn],
            f"{another_service.name}.{component_2_s2.name}": [self.host_2.fqdn],
            service.name: [self.host_1.fqdn, self.host_2.fqdn],
            another_service.name: [self.host_1.fqdn, self.host_2.fqdn],
        }

        expected_data = {
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
                    "id": self.cluster_1.pk,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "two_services_two_components_each.json.j2",
                {
                    "service_1_id": service.pk,
                    "component_1_s1_id": component_1_s1.pk,
                    "component_2_s1_id": component_2_s1.pk,
                    "service_2_id": another_service.pk,
                    "component_1_s2_id": component_1_s2.pk,
                    "component_2_s2_id": component_2_s2.pk,
                },
            ),
        }

        expected_topology_for_host_1 = {
            "HOST": [self.host_1.fqdn],
        }

        expected_data_for_host_1 = {
            ("hosts", self.host_1.fqdn): (
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
            "HOST": [self.host_2.fqdn],
        }

        expected_data_for_host_2 = {
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_2.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (service, action_on_service_1, expected_topology, expected_data),
            (another_service, action_on_service_2, expected_topology, expected_data),
            (component_1_s1, action_on_component_1_s1, expected_topology, expected_data),
            (component_2_s1, action_on_component_2_s1, expected_topology, expected_data),
            (component_1_s2, action_on_component_1_s2, expected_topology, expected_data),
            (component_2_s2, action_on_component_2_s2, expected_topology, expected_data),
            (self.host_1, action_on_host_1, expected_topology_for_host_1, expected_data_for_host_1),
            (self.host_2, action_on_host_2, expected_topology_for_host_2, expected_data_for_host_2),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)
