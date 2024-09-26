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

from cm.models import Action, Component, MaintenanceMode
from cm.tests.test_inventory.base import BaseInventoryTestCase, MappingEntry


class TestInventoryHcAclMaintenanceModeGroupConfig(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_1")

        self.cluster = self.add_cluster(bundle=cluster_bundle, name="cluster")
        self.provider = self.add_provider(bundle=provider_bundle, name="provider")

        self.host_1 = self.add_host(bundle=provider_bundle, provider=self.provider, fqdn="host1", cluster=self.cluster)
        self.host_2 = self.add_host(bundle=provider_bundle, provider=self.provider, fqdn="host2", cluster=self.cluster)
        self.host_3 = self.add_host(bundle=provider_bundle, provider=self.provider, fqdn="host3", cluster=self.cluster)
        self.host_4 = self.add_host(bundle=provider_bundle, provider=self.provider, fqdn="host4", cluster=self.cluster)

        self.service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster
        ).get()

        self.component_1 = Component.objects.get(prototype__name="component_1", service=self.service)
        self.component_2 = Component.objects.get(prototype__name="component_2", service=self.service)

        self.set_hostcomponent(
            cluster=self.cluster, entries=[(self.host_1, self.component_1), (self.host_2, self.component_2)]
        )

        self.cluster_group = self.add_group_config(parent=self.cluster, hosts=[self.host_1, self.host_2])
        self.service_group = self.add_group_config(parent=self.service, hosts=[self.host_1, self.host_2])
        self.component_1_group = self.add_group_config(parent=self.component_1, hosts=[self.host_1])

        self.change_configuration(
            target=self.cluster_group, config_diff={"integer": 101}, meta_diff={"/integer": {"isSynchronized": False}}
        )
        self.change_configuration(
            target=self.service_group, config_diff={"integer": 102}, meta_diff={"/integer": {"isSynchronized": False}}
        )
        self.change_configuration(
            target=self.component_1_group,
            config_diff={"integer": 103},
            meta_diff={"/integer": {"isSynchronized": False}},
        )

        self.hc_acl_action_cluster = Action.objects.get(
            name="hc_acl_action_on_cluster", prototype=self.cluster.prototype
        )
        self.hc_acl_action_service = Action.objects.get(
            name="hc_acl_action_on_service", prototype=self.service.prototype
        )
        self.hc_acl_action_component_1 = Action.objects.get(
            name="hc_acl_action_on_component_1", prototype=self.component_1.prototype
        )
        self.hc_acl_action_component_2 = Action.objects.get(
            name="hc_acl_action_on_component_2", prototype=self.component_2.prototype
        )

    def test_hc_acl_maintenance_mode_group_config(self):
        self.host_1.maintenance_mode = MaintenanceMode.ON
        self.host_1.save(update_fields=["maintenance_mode"])

        action_hc_map: list[MappingEntry] = [
            {"service_id": self.service.pk, "component_id": self.component_1.pk, "host_id": self.host_3.pk},
            {"service_id": self.service.pk, "component_id": self.component_2.pk, "host_id": self.host_4.pk},
        ]
        delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster, new_mapping=action_hc_map)

        self.set_hostcomponent(
            cluster=self.cluster, entries=[(self.host_3, self.component_1), (self.host_4, self.component_2)]
        )

        expected_topology = {
            "CLUSTER": [self.host_2.fqdn, self.host_3.fqdn, self.host_4.fqdn],
            "CLUSTER.maintenance_mode": [self.host_1.fqdn],
            f"{self.service.name}": [self.host_3.fqdn, self.host_4.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_3.fqdn],
            f"{self.service.name}.{self.component_2.name}": [self.host_4.fqdn],
            f"{self.service.name}.{self.component_1.name}.add": [self.host_3.fqdn],
            f"{self.service.name}.{self.component_2.name}.add": [self.host_4.fqdn],
            f"{self.service.name}.{self.component_1.name}.remove.maintenance_mode": [self.host_1.fqdn],
            f"{self.service.name}.{self.component_2.name}.remove": [self.host_2.fqdn],
        }

        expected_data = {
            ("CLUSTER", "hosts", f"{self.host_2.fqdn}"): (
                self.templates_dir / "host_with_vars_service_two_components.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "cluster_id": self.cluster.pk,
                    "cluster_config_integer": 101,
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
            ("CLUSTER", "hosts", f"{self.host_3.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {"adcm_hostid": self.host_3.pk},
            ),
            ("CLUSTER", "hosts", f"{self.host_4.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {"adcm_hostid": self.host_4.pk},
            ),
            ("CLUSTER.maintenance_mode", "hosts", f"{self.host_1.fqdn}"): (
                self.templates_dir / "host_with_vars_service_two_components.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "cluster_id": self.cluster.pk,
                    "cluster_config_integer": 101,
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
            (f"{self.service.name}.{self.component_1.name}", "hosts", f"{self.host_3.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_3.pk,
                },
            ),
            (f"{self.service.name}", "hosts", f"{self.host_3.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_3.pk,
                },
            ),
            (f"{self.service.name}", "hosts", f"{self.host_4.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_4.pk,
                },
            ),
            (f"{self.service.name}.{self.component_2.name}", "hosts", f"{self.host_4.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_4.pk,
                },
            ),
            (f"{self.service.name}.{self.component_1.name}.add", "hosts", f"{self.host_3.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_3.pk,
                },
            ),
            (f"{self.service.name}.{self.component_2.name}.add", "hosts", f"{self.host_4.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_4.pk,
                },
            ),
            (f"{self.service.name}.{self.component_1.name}.remove.maintenance_mode", "hosts", f"{self.host_1.fqdn}"): (
                self.templates_dir / "host_with_vars_service_two_components.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "cluster_id": self.cluster.pk,
                    "cluster_config_integer": 101,
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
            (f"{self.service.name}.{self.component_2.name}.remove", "hosts", f"{self.host_2.fqdn}"): (
                self.templates_dir / "host_with_vars_service_two_components.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "cluster_id": self.cluster.pk,
                    "cluster_config_integer": 101,
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                    "name": self.cluster.name,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.cluster, self.hc_acl_action_cluster, expected_topology, expected_data),
            (self.service, self.hc_acl_action_service, expected_topology, expected_data),
            (self.component_1, self.hc_acl_action_component_1, expected_topology, expected_data),
            (self.component_2, self.hc_acl_action_component_2, expected_topology, expected_data),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj, action=action, expected_topology=topology, expected_data=data, delta=delta
                )
