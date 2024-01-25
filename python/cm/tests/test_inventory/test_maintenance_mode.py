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
from typing import Mapping

from adcm.settings import ADCM_TURN_ON_MM_ACTION_NAME
from api_v2.service.utils import bulk_add_services_to_cluster

from cm.models import (
    Action,
    Cluster,
    ClusterObject,
    ConfigLog,
    Host,
    MaintenanceMode,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.tests.test_inventory.base import BaseInventoryTestCase


class TestMaintenanceMode(BaseInventoryTestCase):
    def setUp(self) -> None:
        bundles_dir = Path(__file__).parent.parent / "bundles"
        self.templates_dir = Path(__file__).parent.parent / "files/response_templates"

        self.provider_bundle = self.add_bundle(source_dir=bundles_dir / "provider")
        cluster_bundle = self.add_bundle(source_dir=bundles_dir / "cluster_1")

        self.cluster_1 = self.add_cluster(bundle=cluster_bundle, name="cluster_1")
        self.provider = self.add_provider(bundle=self.provider_bundle, name="provider")

        self.host_1 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_1", cluster=self.cluster_1
        )
        self.host_2 = None
        self.service_two_components = None
        self.component_1 = None
        self.component_2 = None

    def get_provider_mm_config(self, obj: Host):
        path, ids = self.get_action_on_host_expected_template_data_part(host=obj)[("HOST", "vars", "provider")]

        return self.render_json_template(path, dict(ids))

    def get_host_mm_config(self, obj: Host):
        path, ids = self.templates_dir / "one_host.json.j2", {"host_fqnd": obj.fqdn, "adcm_hostid": obj.id}

        return self.render_json_template(path, ids)[""]

    def get_cluster_mm_config(self, obj: Cluster):
        path, ids = self.templates_dir / "cluster.json.j2", {"id": obj.id}

        return self.render_json_template(path, ids)

    def get_service_mm_config(self, obj: ClusterObject, component: ServiceComponent):
        mm_state = {MaintenanceMode.ON: "true", MaintenanceMode.OFF: "false"}
        path, ids = (
            self.templates_dir / "service_one_component.json.j2",
            {
                "service_id": obj.id,
                "service_mm": mm_state[obj.maintenance_mode],
                "component_id": component.pk,
                "component_mm": mm_state[component.maintenance_mode],
            },
        )

        return self.render_json_template(path, ids)

    def check_hosts_topology(self, data: Mapping[str, dict], expected: Mapping[str, list[str]]) -> None:
        errors = set(data.keys()).symmetric_difference(set(expected.keys()))
        self.assertSetEqual(errors, set())

    def _get_2_hosts_topology(self, host_mm_on: Host, host_mm_off: Host):
        return {
            "CLUSTER": {"hosts": {}, "vars": self.get_cluster_mm_config(self.cluster_1)},
            f"{self.service_two_components.name}": {
                "hosts": {host_mm_off.fqdn: self.get_host_mm_config(host_mm_off)},
            },
            f"{self.service_two_components.name}.{self.component_1.name}": {
                "hosts": {host_mm_off.fqdn: self.get_host_mm_config(host_mm_off)},
            },
            f"{self.service_two_components.name}.{self.component_2.name}": {
                "hosts": {host_mm_off.fqdn: self.get_host_mm_config(host_mm_off)},
            },
            f"{self.service_two_components.name}.{self.component_1.name}.maintenance_mode": {
                "hosts": {host_mm_on.fqdn: self.get_host_mm_config(host_mm_on)},
                "vars": {
                    "cluster": self.get_cluster_mm_config(self.cluster_1),
                    "services": {
                        "service_one_component": self.get_service_mm_config(
                            self.service_two_components, self.component_1
                        )
                    },
                },
            },
            f"{self.service_two_components.name}.{self.component_2.name}.maintenance_mode": {
                "hosts": {host_mm_on.fqdn: self.get_host_mm_config(host_mm_on)},
                "vars": {
                    "cluster": self.get_cluster_mm_config(self.cluster_1),
                    "services": {
                        "service_one_component": self.get_service_mm_config(
                            self.service_two_components, self.component_1
                        )
                    },
                },
            },
            f"{self.service_two_components.name}.maintenance_mode": {
                "hosts": {host_mm_on.fqdn: self.get_host_mm_config(host_mm_on)},
                "vars": {
                    "cluster": self.get_cluster_mm_config(self.cluster_1),
                    "services": {
                        "service_one_component": self.get_service_mm_config(
                            self.service_two_components, self.component_1
                        )
                    },
                },
            },
            "HOST": {"hosts": {}, "vars": self.get_provider_mm_config(host_mm_on)},
        }

    def test_1_component_1_host(self):
        service_one_component: ClusterObject = bulk_add_services_to_cluster(
            cluster=self.cluster_1,
            prototypes=Prototype.objects.filter(
                type=ObjectType.SERVICE, name="service_one_component", bundle=self.cluster_1.prototype.bundle
            ),
        ).get()
        component_1 = ServiceComponent.objects.get(service=service_one_component, prototype__name="component_1")

        self.add_hostcomponent_map(
            cluster=self.cluster_1,
            hc_map=[
                {"service_id": service_one_component.pk, "component_id": component_1.pk, "host_id": self.host_1.pk}
            ],
        )

        action_on_service_mm_on = Action.objects.create(
            name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=service_one_component.prototype
        )
        action_on_component_mm_on = Action.objects.create(
            name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=component_1.prototype
        )
        action_on_host_on = Action.objects.create(name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=self.host_1.prototype)

        host_names = [self.host_1.fqdn]
        expected_topology = {
            "CLUSTER": host_names,
            f"{service_one_component.name}.{component_1.name}": host_names,
            service_one_component.name: host_names,
        }

        expected_topology_host_mm = {
            "CLUSTER": {"hosts": {}, "vars": self.get_cluster_mm_config(self.cluster_1)},
            f"{service_one_component.name}.{component_1.name}.maintenance_mode": {
                "hosts": self.get_provider_mm_config(self.host_1),
                "vars": {
                    "cluster": self.get_cluster_mm_config(self.cluster_1),
                    "services": {
                        "service_one_component": self.get_service_mm_config(service_one_component, component_1)
                    },
                },
            },
            f"{service_one_component.name}.maintenance_mode": {
                "hosts": self.get_provider_mm_config(self.host_1),
                "vars": {
                    "cluster": self.get_cluster_mm_config(self.cluster_1),
                    "services": {
                        "service_one_component": self.get_service_mm_config(service_one_component, component_1)
                    },
                },
            },
            "HOST": {"hosts": {}, "vars": self.get_provider_mm_config(self.host_1)},
        }

        expected_data = {
            ("service_one_component.component_1", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                    "password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                },
            ),
            ("service_one_component", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                    "password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                },
            ),
        }

        expected_data_host_mm = {
            ("service_one_component.component_1.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                    "password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                },
            ),
            ("service_one_component.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                    "password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                },
            ),
        }

        for obj, action, topology, data in (
            (
                service_one_component,
                action_on_service_mm_on,
                expected_topology,
                {
                    **expected_data,
                    **{
                        ("CLUSTER", "vars", "services"): (
                            self.templates_dir / "service_one_component.json.j2",
                            {
                                "service_id": service_one_component.pk,
                                "service_password": ConfigLog.objects.get(
                                    pk=service_one_component.config.current
                                ).config["password"],
                                "service_mm": "true",
                                "component_id": component_1.pk,
                                "component_password": ConfigLog.objects.get(pk=component_1.config.current).config[
                                    "password"
                                ],
                                "component_mm": "true",
                            },
                        )
                    },
                },
            ),
            (
                component_1,
                action_on_component_mm_on,
                expected_topology,
                {
                    **expected_data,
                    **{
                        ("CLUSTER", "vars", "services"): (
                            self.templates_dir / "service_one_component.json.j2",
                            {
                                "service_id": service_one_component.pk,
                                "service_password": ConfigLog.objects.get(
                                    pk=service_one_component.config.current
                                ).config["password"],
                                "service_mm": "true",
                                "component_id": component_1.pk,
                                "component_password": ConfigLog.objects.get(pk=component_1.config.current).config[
                                    "password"
                                ],
                                "component_mm": "true",
                            },
                        )
                    },
                },
            ),
            (
                self.host_1,
                action_on_host_on,
                expected_topology_host_mm,
                expected_data_host_mm,
            ),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                obj.maintenance_mode = MaintenanceMode.ON
                obj.save()
                self.assert_inventory(obj, action, topology, data)
                obj.maintenance_mode = MaintenanceMode.OFF
                obj.save()

    def test_2_components_2_hosts(self):
        self.host_2 = self.add_host(
            bundle=self.provider_bundle, provider=self.provider, fqdn="host_2", cluster=self.cluster_1
        )

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

        action_on_service_mm_on = Action.objects.create(
            name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=self.service_two_components.prototype
        )
        action_on_component_1_mm_on = Action.objects.create(
            name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=self.component_1.prototype
        )
        action_on_component_2_mm_on = Action.objects.create(
            name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=self.component_2.prototype
        )
        action_on_host_on = Action.objects.create(name=ADCM_TURN_ON_MM_ACTION_NAME, prototype=self.host_1.prototype)

        host_names = [self.host_1.fqdn, self.host_2.fqdn]
        expected_hosts_topology = {
            "CLUSTER": host_names,
            f"{self.service_two_components.name}.{self.component_1.name}": host_names,
            f"{self.service_two_components.name}.{self.component_2.name}": host_names,
            self.service_two_components.name: host_names,
        }

        expected_topology_host_1_mm = self._get_2_hosts_topology(self.host_1, self.host_2)

        expected_topology_host_2_mm = self._get_2_hosts_topology(self.host_2, self.host_1)

        expected_data = {
            ("service_two_components.component_1", "hosts"): (
                self.templates_dir / "two_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_1_password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                    "host_2_id": self.host_2.pk,
                    "host_2_password": ConfigLog.objects.get(pk=self.host_2.config.current).config["password"],
                },
            ),
            ("service_two_components", "hosts"): (
                self.templates_dir / "two_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_1_password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                    "host_2_id": self.host_2.pk,
                    "host_2_password": ConfigLog.objects.get(pk=self.host_2.config.current).config["password"],
                },
            ),
            ("service_two_components.component_2", "hosts"): (
                self.templates_dir / "two_hosts.json.j2",
                {
                    "host_1_id": self.host_1.pk,
                    "host_1_password": ConfigLog.objects.get(pk=self.host_1.config.current).config["password"],
                    "host_2_id": self.host_2.pk,
                    "host_2_password": ConfigLog.objects.get(pk=self.host_2.config.current).config["password"],
                },
            ),
        }

        expected_data_host_1_mm = {
            ("service_two_components.component_1.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                },
            ),
            ("service_two_components.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_1.fqdn,
                    "adcm_hostid": self.host_1.pk,
                },
            ),
        }

        expected_data_host_2_mm = {
            ("service_two_components.component_1.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_2.fqdn,
                    "adcm_hostid": self.host_2.pk,
                },
            ),
            ("service_two_components.maintenance_mode", "hosts"): (
                self.templates_dir / "one_host.json.j2",
                {
                    "host_fqdn": self.host_2.fqdn,
                    "adcm_hostid": self.host_2.pk,
                },
            ),
        }

        for obj, action, topology, data in (
            (self.service_two_components, action_on_service_mm_on, expected_hosts_topology, expected_data),
            (self.component_1, action_on_component_1_mm_on, expected_hosts_topology, expected_data),
            (self.component_2, action_on_component_2_mm_on, expected_hosts_topology, expected_data),
            (
                self.host_1,
                action_on_host_on,
                expected_topology_host_1_mm,
                expected_data_host_1_mm,
            ),
            (
                self.host_2,
                action_on_host_on,
                expected_topology_host_2_mm,
                expected_data_host_2_mm,
            ),
        ):
            with self.subTest(msg=f"Object: {obj.prototype.type} #{obj.pk} {obj.name}, action: {action.name}"):
                obj.maintenance_mode = MaintenanceMode.ON
                obj.save()
                self.assert_inventory(obj, action, topology, data)
                obj.maintenance_mode = MaintenanceMode.OFF
                obj.save()
