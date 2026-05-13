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


from core.cluster import ClusterService
from core.scenarios.config import ConfigScenarios
from core.types import ADCMCoreType, CoreObjectDescriptor
from django.conf import settings
from rbac.scenarios import RBACScenarios
import core

from cm.legacy.bundle_switch_revert import bundle_switch
from cm.legacy.services.job.context import get_inventory_data
from cm.legacy.upgrade import update_before_upgrade
from cm.models import Action, Component, Service, Upgrade
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestBeforeUpgrade(BaseInventoryTestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()

        cls.provider_bundle = cls.uc.upload_bundle(src=cls.bundles_dir / "provider")

        cluster_bundle = cls.uc.upload_bundle(src=cls.bundles_dir / "cluster_1")
        cls.cluster_1 = cls.uc.add_cluster(bundle=cluster_bundle, name="cluster_1")
        cls.provider = cls.uc.add_provider(bundle=cls.provider_bundle, name="provider")

        cls.cluster_upgrade_bundle = cls.uc.upload_bundle(src=cls.bundles_dir / "cluster_1_upgrade")
        cls.provider_upgrade_bundle = cls.uc.upload_bundle(src=cls.bundles_dir / "provider_upgrade")

        cls.host_1 = cls.uc.add_host(provider=cls.provider, fqdn="host_1", cluster=None)
        cls.host_2 = cls.uc.add_host(provider=cls.provider, fqdn="host_2", cluster=None)

        cls.upgrade_for_provider = Upgrade.objects.get(
            bundle=cls.provider_upgrade_bundle, name="upgrade_via_action_simple"
        )
        cls.upgrade_for_cluster = Upgrade.objects.get(
            bundle=cls.cluster_upgrade_bundle, name="upgrade_via_action_simple"
        )

    def bundle_switch(self, obj, upgrade):
        from use_cases.legacy.upgrade import build_switch_revert_callbacks

        with self.container() as container:
            config_service = container.get(core.config.ConfigService)
            config_scenarios = container.get(ConfigScenarios)
            callbacks = build_switch_revert_callbacks(
                config_service=config_service,
                rbac_scenarios=RBACScenarios(),
                cluster_service=self.uc.container.get(ClusterService),
            )
            bundle_switch(
                obj=obj,
                upgrade=upgrade,
                callbacks=callbacks,
                config_service=config_service,
                config_scenarios=config_scenarios,
            )

    def update_before_upgrade(self, obj):
        with self.container() as container:
            update_before_upgrade(obj=obj, config_service=container.get(core.config.ConfigService))

    def test_provider_two_hosts(self):
        self.provider.before_upgrade["bundle_id"] = self.provider.prototype.bundle.pk
        self.update_before_upgrade(obj=self.provider)

        self.bundle_switch(obj=self.provider, upgrade=self.upgrade_for_provider)

        self.provider.state = "success"
        self.provider.save()

        self.host_1.refresh_from_db()
        self.host_2.refresh_from_db()
        self.provider.refresh_from_db()
        self.provider.prototype.refresh_from_db()

        provider_action = Action.objects.get(name="provider_action", prototype=self.provider.prototype)
        host_1_action = Action.objects.get(name="host_action", prototype=self.host_1.prototype)
        host_2_action = Action.objects.get(name="host_action", prototype=self.host_2.prototype)

        expected_topology_provider = {"PROVIDER": [self.host_1.fqdn, self.host_2.fqdn]}
        expected_topology_host_1 = {"HOST": [self.host_1.fqdn]}
        expected_topology_host_2 = {"HOST": [self.host_2.fqdn]}

        expected_data_provider = {
            ("hosts",): (
                self.templates_dir / "before_upgrade_2_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_1_uuid": self.host_1.uuid,
                    "host_2_id": self.host_2.pk,
                    "host_2_uuid": self.host_2.uuid,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }

        expected_data_host_1 = {
            ("hosts", self.host_1.fqdn): (
                self.templates_dir / "before_upgrade_1_host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "uuid": self.host_1.uuid,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.host_1.provider.pk,
                    "host_prototype_id": self.host_1.prototype.pk,
                },
            ),
        }
        expected_data_host_2 = {
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "before_upgrade_1_host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "uuid": self.host_2.uuid,
                },
            ),
            ("vars", "provider"): (
                self.templates_dir / "before_upgrade_provider.json.j2",
                {
                    "id": self.host_2.provider.pk,
                    "host_prototype_id": self.host_2.prototype.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.provider, self.upgrade_for_provider.action, expected_topology_provider, expected_data_provider),
            (self.provider, provider_action, expected_topology_provider, expected_data_provider),
            (self.host_1, host_1_action, expected_topology_host_1, expected_data_host_1),
            (self.host_2, host_2_action, expected_topology_host_2, expected_data_host_2),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                self.assert_inventory(
                    obj=obj,
                    action=action,
                    expected_topology=topology,
                    expected_data=data,
                )

    def test_2_components_2_hosts(self):
        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.service_two_components: Service = self.uc.add_services_to_cluster(
            ["service_two_components"], cluster=self.cluster_1
        )[0]

        self.component_1 = Component.objects.get(service=self.service_two_components, prototype__name="component_1")
        self.component_2 = Component.objects.get(service=self.service_two_components, prototype__name="component_2")

        self.uc.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, self.component_1),
                (self.host_2, self.component_1),
                (self.host_1, self.component_2),
                (self.host_2, self.component_2),
            ],
        )

        self.cluster_1.before_upgrade["bundle_id"] = self.cluster_1.prototype.bundle.pk
        self.update_before_upgrade(obj=self.cluster_1)

        self.bundle_switch(obj=self.cluster_1, upgrade=self.upgrade_for_cluster)

        self.cluster_1.state = "success"
        self.cluster_1.save()

        self.service_two_components.refresh_from_db()
        self.component_1.refresh_from_db()
        self.component_2.refresh_from_db()

        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            self.service_two_components.name: host_names,
            f"{self.service_two_components.name}.{self.component_1.name}": host_names,
            f"{self.service_two_components.name}.{self.component_2.name}": host_names,
        }

        expected_data = {
            ("hosts", self.host_1.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_1.pk,
                    "uuid": self.host_1.uuid,
                },
            ),
            ("hosts", self.host_2.fqdn): (
                self.templates_dir / "host.json.j2",
                {
                    "adcm_hostid": self.host_2.pk,
                    "uuid": self.host_2.uuid,
                },
            ),
            ("vars", "cluster"): (
                self.templates_dir / "before_upgrade_cluster.json.j2",
                {"object_name": self.cluster_1.name, "id": self.cluster_1.id, "uuid": self.cluster_1.uuid},
            ),
            ("vars", "services"): (
                self.templates_dir / "before_upgrade_service_two_components.json.j2",
                {
                    "service_id": self.service_two_components.pk,
                    "service_uuid": self.service_two_components.uuid,
                    "component_1_id": self.component_1.pk,
                    "component_1_uuid": self.component_1.uuid,
                    "component_2_id": self.component_2.pk,
                    "component_2_uuid": self.component_2.uuid,
                },
            ),
        }

        action_on_cluster = Action.objects.get(name="action_on_cluster", prototype=self.cluster_1.prototype)
        action_on_service = Action.objects.get(
            name="action_on_service", prototype=self.service_two_components.prototype
        )
        action_on_component_1 = Action.objects.get(name="action_on_component_1", prototype=self.component_1.prototype)
        action_on_component_2 = Action.objects.get(name="action_on_component_2", prototype=self.component_2.prototype)

        for obj, action, topology, data in [
            (self.cluster_1, self.upgrade_for_cluster.action, expected_topology, expected_data),
            (self.cluster_1, action_on_cluster, expected_topology, expected_data),
            (self.service_two_components, action_on_service, expected_topology, expected_data),
            (self.component_1, action_on_component_1, expected_topology, expected_data),
            (self.component_2, action_on_component_2, expected_topology, expected_data),
        ]:
            self.assert_inventory(obj=obj, action=action, expected_topology=topology, expected_data=data)

    def test_config_host_group_effect_on_before_upgrade(self) -> None:
        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.service_two_components: Service = self.uc.add_services_to_cluster(
            cluster=self.cluster_1, names=["service_two_components"]
        )[0]
        self.component_1 = Component.objects.get(service=self.service_two_components, prototype__name="component_1")
        self.component_2 = Component.objects.get(service=self.service_two_components, prototype__name="component_2")

        self.uc.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, self.component_1),
                (self.host_1, self.component_2),
                (self.host_2, self.component_1),
                (self.host_2, self.component_2),
            ],
        )

        cluster_group = self.add_config_host_group(parent=self.cluster_1, hosts=[self.host_1, self.host_2])
        service_group = self.add_config_host_group(parent=self.service_two_components, hosts=[self.host_2])
        component_1_group = self.add_config_host_group(parent=self.component_1, hosts=[self.host_1])

        changed_integer = 40
        changed_string = "woohoo"
        changed_list = ["1", "2"]

        self.change_configuration(
            target=cluster_group,
            config_diff={"integer": changed_integer},
            meta_diff={"/integer": {"isSynchronized": False}},
        )
        self.change_configuration(
            target=service_group,
            config_diff={"string": changed_string},
            meta_diff={"/string": {"isSynchronized": False}},
        )
        self.change_configuration(
            target=component_1_group, config_diff={"list": changed_list}, meta_diff={"/list": {"isSynchronized": False}}
        )

        self.cluster_1.before_upgrade["bundle_id"] = self.cluster_1.prototype.bundle.pk
        self.update_before_upgrade(obj=self.cluster_1)

        self.bundle_switch(obj=self.cluster_1, upgrade=self.upgrade_for_cluster)

        self.cluster_1.refresh_from_db()
        self.service_two_components.refresh_from_db()
        self.component_1.refresh_from_db()
        self.component_2.refresh_from_db()
        cluster_group.object.refresh_from_db()
        service_group.object.refresh_from_db()
        component_1_group.object.refresh_from_db()

        cluster_file = self.templates_dir / "config_host_group_before_upgrade" / "cluster_section.json.j2"
        services_file = self.templates_dir / "config_host_group_before_upgrade" / "services_section.json.j2"

        expected_hosts_cluster = (
            cluster_file,
            {"config_integer": changed_integer, "before_upgrade_integer": changed_integer, "cluster": self.cluster_1},
        )
        expected_host_1_services = (
            # list is pre-defined in template, so just True is ok
            services_file,
            {
                "config_list": True,
                "before_upgrade_list": True,
                "service": self.service_two_components,
                "component_1": self.component_1,
                "component_2": self.component_2,
            },
        )
        expected_host_2_services = (
            services_file,
            {
                "config_string": changed_string,
                "before_upgrade_string": changed_string,
                "service": self.service_two_components,
                "component_1": self.component_1,
                "component_2": self.component_2,
            },
        )
        host_names = [self.host_1.fqdn, self.host_2.fqdn]

        expected_topology = {
            "CLUSTER": host_names,
            "service_two_components": host_names,
            "service_two_components.component_1": host_names,
            "service_two_components.component_2": host_names,
        }

        expected_data = {
            ("vars", "cluster"): (cluster_file, {"cluster": self.cluster_1}),
            ("vars", "services"): (
                services_file,
                {
                    "service": self.service_two_components,
                    "component_1": self.component_1,
                    "component_2": self.component_2,
                },
            ),
            ("hosts", "host_1", "cluster"): expected_hosts_cluster,
            ("hosts", "host_1", "services"): expected_host_1_services,
            ("hosts", "host_2", "services"): expected_host_2_services,
        }

        self.assert_inventory(
            obj=self.cluster_1,
            action=self.upgrade_for_cluster.action,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

        new_string = "another-string"
        component_1_group.delete()
        self.change_configuration(
            target=service_group,
            config_diff={"string": new_string},
            meta_diff={"/string": {"isSynchronized": False}},
        )

        expected_hosts_cluster = (
            cluster_file,
            {"config_integer": changed_integer, "before_upgrade_integer": changed_integer, "cluster": self.cluster_1},
        )
        expected_host_1_services = (
            # group is removed, data is retrieved from "regular" config
            services_file,
            {
                "config_list": False,
                "before_upgrade_list": False,
                "service": self.service_two_components,
                "component_1": self.component_1,
                "component_2": self.component_2,
            },
        )
        expected_host_2_services = (
            services_file,
            {
                "config_string": new_string,
                "before_upgrade_string": changed_string,
                "service": self.service_two_components,
                "component_1": self.component_1,
                "component_2": self.component_2,
            },
        )
        expected_data = {
            ("vars", "cluster"): (cluster_file, {"cluster": self.cluster_1}),
            ("vars", "services"): (
                services_file,
                {
                    "service": self.service_two_components,
                    "component_1": self.component_1,
                    "component_2": self.component_2,
                },
            ),
            ("hosts", "host_1", "cluster"): expected_hosts_cluster,
            ("hosts", "host_1", "services"): expected_host_1_services,
            ("hosts", "host_2", "services"): expected_host_2_services,
        }

        self.assert_inventory(
            obj=self.cluster_1,
            action=self.upgrade_for_cluster.action,
            expected_topology=expected_topology,
            expected_data=expected_data,
        )

    def test_adcm_5367_bug(self) -> None:
        another_1, *_ = self.uc.add_services_to_cluster(
            names=["another_service_two_components"], cluster=self.cluster_1
        )
        service, *_ = self.uc.add_services_to_cluster(
            names=["another_service_two_components_2"], cluster=self.cluster_1
        )
        problem_component = Component.objects.get(service=service, prototype__name="component_1")
        another_2, *_ = self.uc.add_services_to_cluster(
            names=["another_service_two_components_3"], cluster=self.cluster_1
        )

        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_1)
        self.uc.add_host_to_cluster(cluster=self.cluster_1, host=self.host_2)

        self.uc.set_hostcomponent(
            cluster=self.cluster_1,
            entries=[
                (self.host_1, problem_component),
                (self.host_2, problem_component),
                (self.host_1, Component.objects.filter(service=another_1).first()),
                (self.host_2, Component.objects.filter(service=another_2).first()),
            ],
        )

        component_group = self.add_config_host_group(parent=problem_component, hosts=[self.host_1])

        self.change_configuration(
            target=component_group,
            config_diff={"plain": "someother\ntext", "bunch": {"secte": "itsasecret"}},
            meta_diff={
                "/plain": {"isSynchronized": False},
                "/secte": {"isSynchronized": False},
                "/bunch/secte": {"isSynchronized": False},
            },
        )

        self.cluster_1.before_upgrade["bundle_id"] = self.cluster_1.prototype.bundle.pk
        self.update_before_upgrade(obj=self.cluster_1)

        self.bundle_switch(obj=self.cluster_1, upgrade=self.upgrade_for_cluster)

        problem_component.refresh_from_db()
        action = Action.objects.get(name="action_on_component_1", prototype=problem_component.prototype)

        inventory = get_inventory_data(
            target=CoreObjectDescriptor(id=problem_component.id, type=ADCMCoreType.COMPONENT),
            is_host_action=action.host_action,
            cluster_service=self.uc.container.get(ClusterService),
        )
        services = inventory["all"]["vars"]["services"]

        component_prefix = f"{settings.FILE_DIR}/component.{problem_component.id}"

        node = services[service.name]["component_1"]["before_upgrade"]["config"]
        self.assertEqual(node["plain"], f"{component_prefix}.plain.")
        self.assertEqual(node["secte"], f"{component_prefix}.secte.")
        self.assertEqual(node["bunch"]["plain"], f"{component_prefix}.bunch.plain")
        self.assertEqual(node["bunch"]["secte"], f"{component_prefix}.bunch.secte")

        group_prefix = f"{settings.FILE_DIR}/component.{problem_component.id}.group.{component_group.id}"

        hosts_node = inventory["all"]["hosts"]
        node = hosts_node["host_1"]["services"][service.name][problem_component.name]["before_upgrade"]["config"]
        self.assertEqual(node["plain"], f"{group_prefix}.plain.")
        self.assertEqual(node["secte"], f"{group_prefix}.secte.")
        self.assertEqual(node["bunch"]["plain"], f"{group_prefix}.bunch.plain")
        self.assertEqual(node["bunch"]["secte"], f"{group_prefix}.bunch.secte")

        self.assertNotIn("services", hosts_node["host_2"])
