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


class TestHostAction(BaseInventoryTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.provider_bundle = self.uc.upload_bundle(self.bundles_dir / "provider")
        cluster_bundle = self.uc.upload_bundle(self.bundles_dir / "cluster_1")

        self.cluster = self.uc.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.uc.add_provider(bundle=self.provider_bundle, name="provider")
        self.host_1 = self.uc.add_host(provider=self.provider, fqdn="host_1", cluster=self.cluster)
        self.host_2 = self.uc.add_host(provider=self.provider, fqdn="host_2", cluster=self.cluster)

        self.service: Service = self.uc.add_services_to_cluster(cluster=self.cluster, names=["service_one_component"])[
            0
        ]

        self.component = Component.objects.get(service=self.service, prototype__name="component_1")

        self.uc.set_hostcomponent(
            cluster=self.cluster, entries=[(self.host_1, self.component), (self.host_2, self.component)]
        )

        self.cluster_host_action = Action.objects.get(name="host_action_on_cluster", prototype=self.cluster.prototype)
        self.service_host_action = Action.objects.get(name="host_action_on_service", prototype=self.service.prototype)
        self.component_host_action = Action.objects.get(
            name="host_action_on_component", prototype=self.component.prototype
        )

        self.cluster_host_group = self.add_config_host_group(parent=self.cluster, hosts=[self.host_1])
        self.uc.change_config(
            owner=self.cluster_host_group,
            values_diff={"integer": 101},
            meta_diff={"/integer": {"isSynchronized": False}},
        )
        self.service_host_group = self.add_config_host_group(parent=self.service, hosts=[self.host_1])
        self.uc.change_config(
            owner=self.service_host_group,
            values_diff={"integer": 102},
            meta_diff={"/integer": {"isSynchronized": False}},
        )
        self.component_host_group = self.add_config_host_group(parent=self.component, hosts=[self.host_1])
        self.uc.change_config(
            owner=self.component_host_group,
            values_diff={"integer": 103},
            meta_diff={"/integer": {"isSynchronized": False}},
        )

    def test_host_action(self):
        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        group_key = f"chg_{self.cluster_host_group.pk}_{self.service_host_group.pk}_{self.component_host_group.pk}"
        expected_topology = {
            "CLUSTER": host_names,
            self.service.name: host_names,
            f"{self.service.name}.{self.component.name}": host_names,
            "target": [self.host_1.fqdn],
            group_key: [self.host_1.fqdn],
        }

        expected_data = {
            ("hosts", f"{self.host_1.fqdn}"): (
                self.templates_dir / "host_with_vars_service_one_component.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "uuid": self.host_1.uuid,
                },
            ),
            ("hosts", f"{self.host_2.fqdn}"): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "uuid": self.host_2.uuid,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "cluster.json.j2",
                {
                    "id": self.cluster.pk,
                    "uuid": self.cluster.uuid,
                },
            ),
            ("vars", "services"): (
                self.templates_dir / "service_one_component.json.j2",
                {
                    "service_id": self.service.pk,
                    "service_uuid": self.service.uuid,
                    "component_id": self.component.pk,
                    "component_uuid": self.component.uuid,
                },
            ),
            ("children", group_key, "vars"): (
                self.templates_dir / "host_group_host_action_with_chg.json.j2",
                {
                    "cluster_config_integer": 101,
                    "cluster_id": self.cluster.pk,
                    "cluster_uuid": self.cluster.uuid,
                    "service_id": self.service.pk,
                    "service_uuid": self.service.uuid,
                    "service_config_integer": 102,
                    "component_id": self.component.pk,
                    "component_uuid": self.component.uuid,
                    "component_config_integer": 103,
                },
            ),
        }

        for action in [self.cluster_host_action, self.service_host_action, self.component_host_action]:
            with self.subTest(
                msg=f"Object: {self.host_1.prototype.type} #{self.host_1.pk} {self.host_1.name}, action: {action.name}"
            ):
                self.assert_inventory(
                    obj=self.host_1, action=action, expected_topology=expected_topology, expected_data=expected_data
                )
