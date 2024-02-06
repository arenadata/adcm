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


from cm.inventory import HcAclAction
from cm.models import Action, ClusterObject, ServiceComponent
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestInventoryHcAclActions(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.add_bundle(source_dir=self.bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=self.bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )
        self.service: ClusterObject = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).get()
        self.component_1 = ServiceComponent.objects.get(prototype__name="component_1", service=self.service)
        self.component_2 = ServiceComponent.objects.get(prototype__name="component_2", service=self.service)

        self.hc_acl_action_cluster = Action.objects.get(
            name="hc_acl_action_on_cluster", prototype=self.cluster_1.prototype
        )
        self.hc_acl_action_service = Action.objects.get(
            name="hc_acl_action_on_service", prototype=self.service.prototype
        )

        self.initial_hc_h1_c1 = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_1.pk,
                "host_id": self.host_1.pk,
            }
        ]
        self.expected_data = {
            ("CLUSTER", "hosts"): (
                self.templates_dir / "two_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_2_id": self.host_2.pk,
                },
            ),
            ("CLUSTER", "vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster_1.pk,
                },
            ),
            ("CLUSTER", "vars", "services"): (
                self.templates_dir / "service_two_components.json.j2",
                {
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }

    def test_expand(self):
        base_expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_1.fqdn],
        }

        action_hc_map_add_h2_c2 = [
            *self.initial_hc_h1_c1,
            {"host_id": self.host_2.pk, "component_id": self.component_2.pk, "service_id": self.service.pk},
        ]
        expected_topology_add_h2_c2 = {
            **base_expected_topology,
            **{f"{self.service.name}.{self.component_2.name}.{HcAclAction.ADD}": [self.host_2.fqdn]},
        }
        action_hc_map_add_h2_c1 = [
            *self.initial_hc_h1_c1,
            {"host_id": self.host_2.pk, "component_id": self.component_1.pk, "service_id": self.service.pk},
        ]
        expected_topology_add_h2_c1 = {
            **base_expected_topology,
            **{f"{self.service.name}.{self.component_1.name}.{HcAclAction.ADD}": [self.host_2.fqdn]},
        }

        for obj, action, action_hc_map, expected_topology in (
            (
                self.cluster_1,
                self.hc_acl_action_cluster,
                action_hc_map_add_h2_c2,
                expected_topology_add_h2_c2,
            ),
            (
                self.service,
                self.hc_acl_action_service,
                action_hc_map_add_h2_c2,
                expected_topology_add_h2_c2,
            ),
            (
                self.cluster_1,
                self.hc_acl_action_cluster,
                action_hc_map_add_h2_c1,
                expected_topology_add_h2_c1,
            ),
            (
                self.service,
                self.hc_acl_action_service,
                action_hc_map_add_h2_c1,
                expected_topology_add_h2_c1,
            ),
        ):
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {action_hc_map}"
            ):
                self.add_hostcomponent_map(cluster=self.cluster_1, hc_map=self.initial_hc_h1_c1)
                delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=action_hc_map)

                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=self.expected_data,
                    delta=delta,
                )

    def test_shrink(self):
        base_expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_1.fqdn],
        }

        initial_hc_h1_c1_h2_c2 = [
            *self.initial_hc_h1_c1,
            {"service_id": self.service.pk, "component_id": self.component_2.pk, "host_id": self.host_2.pk},
        ]
        expected_topology_remove_h2_c2 = {
            **base_expected_topology,
            **{
                self.service.name: [self.host_1.fqdn, self.host_2.fqdn],
                f"{self.service.name}.{self.component_2.name}": [self.host_2.fqdn],
                f"{self.service.name}.{self.component_2.name}.{HcAclAction.REMOVE}": [self.host_2.fqdn],
            },
        }

        initial_hc_h1_c1_h1_c2 = [
            *self.initial_hc_h1_c1,
            {"service_id": self.service.pk, "component_id": self.component_2.pk, "host_id": self.host_1.pk},
        ]
        expected_topology_remove_h1_c2 = {
            **base_expected_topology,
            **{
                self.service.name: [self.host_1.fqdn],
                f"{self.service.name}.{self.component_2.name}": [self.host_1.fqdn],
                f"{self.service.name}.{self.component_2.name}.{HcAclAction.REMOVE}": [self.host_1.fqdn],
            },
        }

        for obj, action, initial_hc_map, expected_topology in (
            (self.cluster_1, self.hc_acl_action_cluster, initial_hc_h1_c1_h2_c2, expected_topology_remove_h2_c2),
            (self.service, self.hc_acl_action_service, initial_hc_h1_c1_h2_c2, expected_topology_remove_h2_c2),
            (self.cluster_1, self.hc_acl_action_cluster, initial_hc_h1_c1_h1_c2, expected_topology_remove_h1_c2),
            (self.service, self.hc_acl_action_service, initial_hc_h1_c1_h1_c2, expected_topology_remove_h1_c2),
        ):
            action_hc_map = initial_hc_map[:-1]
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {action_hc_map}"
            ):
                self.add_hostcomponent_map(cluster=self.cluster_1, hc_map=initial_hc_map)
                delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=action_hc_map)

                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=self.expected_data,
                    delta=delta,
                )

    def test_expand_shrink_move(self):
        base_expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_1.fqdn],
        }

        action_hc_map_remove_h1_c1_add_h2_c2 = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_2.pk,
                "host_id": self.host_2.pk,
            }
        ]
        expected_topology_remove_h1_c1_add_h2_c2 = {
            **base_expected_topology,
            **{
                f"{self.service.name}.{self.component_1.name}.{HcAclAction.REMOVE}": [self.host_1.fqdn],
                f"{self.service.name}.{self.component_2.name}.{HcAclAction.ADD}": [self.host_2.fqdn],
            },
        }

        action_hc_map_remove_h1_c1_add_h1_c2 = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_2.pk,
                "host_id": self.host_1.pk,
            }
        ]
        expected_topology_remove_h1_c1_add_h1_c2 = {
            **base_expected_topology,
            **{
                f"{self.service.name}.{self.component_1.name}.{HcAclAction.REMOVE}": [self.host_1.fqdn],
                f"{self.service.name}.{self.component_2.name}.{HcAclAction.ADD}": [self.host_1.fqdn],
            },
        }

        action_hc_map_remove_h1_c1_add_h2_c1 = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_1.pk,
                "host_id": self.host_2.pk,
            }
        ]
        expected_topology_remove_h1_c1_add_h2_c1 = {
            **base_expected_topology,
            **{
                f"{self.service.name}.{self.component_1.name}.{HcAclAction.REMOVE}": [self.host_1.fqdn],
                f"{self.service.name}.{self.component_1.name}.{HcAclAction.ADD}": [self.host_2.fqdn],
            },
        }

        for obj, action, action_hc_map, expected_topology in (
            (
                self.cluster_1,
                self.hc_acl_action_cluster,
                action_hc_map_remove_h1_c1_add_h2_c2,
                expected_topology_remove_h1_c1_add_h2_c2,
            ),
            (
                self.service,
                self.hc_acl_action_service,
                action_hc_map_remove_h1_c1_add_h2_c2,
                expected_topology_remove_h1_c1_add_h2_c2,
            ),
            (
                self.cluster_1,
                self.hc_acl_action_cluster,
                action_hc_map_remove_h1_c1_add_h1_c2,
                expected_topology_remove_h1_c1_add_h1_c2,
            ),
            (
                self.service,
                self.hc_acl_action_service,
                action_hc_map_remove_h1_c1_add_h1_c2,
                expected_topology_remove_h1_c1_add_h1_c2,
            ),
            (
                self.cluster_1,
                self.hc_acl_action_cluster,
                action_hc_map_remove_h1_c1_add_h2_c1,
                expected_topology_remove_h1_c1_add_h2_c1,
            ),
            (
                self.service,
                self.hc_acl_action_service,
                action_hc_map_remove_h1_c1_add_h2_c1,
                expected_topology_remove_h1_c1_add_h2_c1,
            ),
        ):
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {action_hc_map}"
            ):
                self.add_hostcomponent_map(cluster=self.cluster_1, hc_map=self.initial_hc_h1_c1)
                delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=action_hc_map)

                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=self.expected_data,
                    delta=delta,
                )
