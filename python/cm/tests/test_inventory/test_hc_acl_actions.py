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
from cm.services.job.types import HcAclAction
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
        self.service: Service = self.add_services_to_cluster(
            service_names=["service_two_components"], cluster=self.cluster_1
        ).get()
        self.component_1 = Component.objects.get(prototype__name="component_1", service=self.service)
        self.component_2 = Component.objects.get(prototype__name="component_2", service=self.service)

        self.hc_acl_action_cluster = Action.objects.get(
            name="hc_acl_action_on_cluster", prototype=self.cluster_1.prototype
        )
        self.hc_acl_action_service = Action.objects.get(
            name="hc_acl_action_on_service", prototype=self.service.prototype
        )

        self.hc_acl_action_component_1 = Action.objects.get(
            name="hc_acl_action_on_component_1", prototype=self.component_1.prototype
        )

        self.initial_hc = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_1.pk,
                "host_id": self.host_1.pk,
            }
        ]
        self.initial_hc_objects = ((self.host_1, self.component_1),)
        self.set_hostcomponent(cluster=self.cluster_1, entries=self.initial_hc_objects)

    def test_expand(self):
        expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_1.fqdn],
            f"{self.service.name}.{self.component_2.name}": [self.host_2.fqdn],
            f"{self.service.name}.{self.component_2.name}.{HcAclAction.ADD.value}": [self.host_2.fqdn],
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
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }

        hc_map_add = [
            *self.initial_hc,
            {"host_id": self.host_2.pk, "component_id": self.component_2.pk, "service_id": self.service.pk},
        ]

        delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=hc_map_add)
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[*self.initial_hc_objects, (self.host_2, self.component_2)]
        )

        for obj, action in [
            (self.cluster_1, self.hc_acl_action_cluster),
            (self.service, self.hc_acl_action_service),
            (self.component_1, self.hc_acl_action_component_1),
        ]:
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {hc_map_add}"
            ):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                    delta=delta,
                )

    def test_shrink(self):
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[*self.initial_hc_objects, (self.host_2, self.component_2)]
        )

        expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_1.fqdn],
            self.service.name: [self.host_1.fqdn],
            f"{self.service.name}.{self.component_2.name}.{HcAclAction.REMOVE.value}": [self.host_2.fqdn],
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
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }
        delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=self.initial_hc)
        self.set_hostcomponent(cluster=self.cluster_1, entries=self.initial_hc_objects)

        for obj, action in (
            (self.cluster_1, self.hc_acl_action_cluster),
            (self.service, self.hc_acl_action_service),
            (self.component_1, self.hc_acl_action_component_1),
        ):
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {self.initial_hc}"
            ):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                    delta=delta,
                )

    def test_move(self):
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[*self.initial_hc_objects, (self.host_2, self.component_2)]
        )

        expected_topology = {
            "CLUSTER": [self.host_1.fqdn, self.host_2.fqdn],
            self.service.name: [self.host_1.fqdn, self.host_2.fqdn],
            f"{self.service.name}.{self.component_1.name}": [self.host_2.fqdn],
            f"{self.service.name}.{self.component_2.name}": [self.host_1.fqdn],
            f"{self.service.name}.{self.component_1.name}.{HcAclAction.ADD.value}": [self.host_2.fqdn],
            f"{self.service.name}.{self.component_2.name}.{HcAclAction.ADD.value}": [self.host_1.fqdn],
            f"{self.service.name}.{self.component_1.name}.{HcAclAction.REMOVE.value}": [self.host_1.fqdn],
            f"{self.service.name}.{self.component_2.name}.{HcAclAction.REMOVE.value}": [self.host_2.fqdn],
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
                    "service_id": self.service.pk,
                    "component_1_id": self.component_1.pk,
                    "component_2_id": self.component_2.pk,
                },
            ),
        }

        hc_map_move = [
            {
                "service_id": self.service.pk,
                "component_id": self.component_1.pk,
                "host_id": self.host_2.pk,
            },
            {
                "service_id": self.service.pk,
                "component_id": self.component_2.pk,
                "host_id": self.host_1.pk,
            },
        ]

        delta = self.get_mapping_delta_for_hc_acl(cluster=self.cluster_1, new_mapping=hc_map_move)
        self.set_hostcomponent(
            cluster=self.cluster_1, entries=[(self.host_2, self.component_1), (self.host_1, self.component_2)]
        )

        for obj, action in [
            (self.cluster_1, self.hc_acl_action_cluster),
            (self.service, self.hc_acl_action_service),
            (self.component_1, self.hc_acl_action_component_1),
        ]:
            with self.subTest(
                msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, "
                f"action: {action.name}, action_hc_map: {hc_map_move}"
            ):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=expected_topology,
                    expected_data=expected_data,
                    delta=delta,
                )
