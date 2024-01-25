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

from unittest import TestCase

from core.cluster.operations import (
    calculate_maintenance_mode_for_cluster_objects,
    calculate_maintenance_mode_for_component,
    calculate_maintenance_mode_for_service,
)
from core.cluster.types import (
    ClusterTopology,
    ComponentTopology,
    MaintenanceModeOfObjects,
    ServiceTopology,
)
from core.cluster.types import ObjectMaintenanceModeState as MM  # noqa: N814
from core.types import ShortObjectInfo


class TestMaintenanceMode(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

    @staticmethod
    def prepare_component_topology(component_id: int, name: str, *hosts: ShortObjectInfo):
        return ComponentTopology(info=ShortObjectInfo(component_id, name), hosts={h.id: h for h in hosts})

    def test_calculate_maintenance_mode_for_cluster_objects(self) -> None:
        hosts = {i: ShortObjectInfo(i, f"host-{i}") for i in range(8)}

        maintenance_mode_info = MaintenanceModeOfObjects(
            services={10: MM.OFF, 20: MM.ON, 30: MM.CHANGING, 40: MM.CHANGING, 50: MM.OFF, 60: MM.OFF, 70: MM.ON},
            components={
                100: MM.OFF,
                101: MM.OFF,
                102: MM.ON,
                103: MM.CHANGING,
                200: MM.OFF,
                300: MM.ON,
                400: MM.OFF,
                401: MM.OFF,
                402: MM.ON,
                500: MM.OFF,
            },
            hosts={
                hosts[0].id: MM.OFF,
                hosts[1].id: MM.OFF,
                hosts[2].id: MM.ON,
                hosts[3].id: MM.ON,
                hosts[4].id: MM.CHANGING,
                hosts[5].id: MM.CHANGING,
                hosts[6].id: MM.OFF,
                hosts[7].id: MM.ON,
            },
        )

        result = calculate_maintenance_mode_for_cluster_objects(
            topology=ClusterTopology(
                cluster_id=400,
                services={
                    10: ServiceTopology(
                        info=ShortObjectInfo(10, "components & hosts => OFF"),
                        components={
                            100: self.prepare_component_topology(100, "hosts => OFF", hosts[0], hosts[1]),
                            101: self.prepare_component_topology(101, "hosts => ON [from hosts]", hosts[3]),
                            102: self.prepare_component_topology(102, "hosts => ON [own]", hosts[4]),
                            103: self.prepare_component_topology(103, "hosts => CHANGING [own]", hosts[0]),
                        },
                    ),
                    20: ServiceTopology(
                        info=ShortObjectInfo(20, "components & hosts => ON [own]"),
                        components={
                            200: self.prepare_component_topology(
                                200, "hosts => ON [service]", hosts[0], hosts[1], hosts[4]
                            )
                        },
                    ),
                    30: ServiceTopology(
                        info=ShortObjectInfo(30, "components & hosts => ON [components]"),
                        components={300: self.prepare_component_topology(300, "hosts => ON [own]", hosts[0])},
                    ),
                    40: ServiceTopology(
                        info=ShortObjectInfo(40, "components => CHANGING"),
                        components={
                            400: self.prepare_component_topology(400, "hosts => OFF", hosts[0]),
                            401: self.prepare_component_topology(401, " => OFF"),
                            402: self.prepare_component_topology(402, " => ON [own]"),
                        },
                    ),
                    50: ServiceTopology(
                        info=ShortObjectInfo(50, "components & hosts => ON [hosts]"),
                        components={500: self.prepare_component_topology(500, "hosts => ON [hosts]", hosts[2])},
                    ),
                    60: ServiceTopology(info=ShortObjectInfo(60, "=> OFF"), components={}),
                    70: ServiceTopology(info=ShortObjectInfo(70, "=> ON"), components={}),
                },
                hosts=hosts,
            ),
            own_maintenance_mode=maintenance_mode_info,
        )
        self.assertEqual(
            {"hosts": result.hosts, "services": result.services, "components": result.components},
            {
                "hosts": maintenance_mode_info.hosts,
                "services": {10: MM.OFF, 20: MM.ON, 30: MM.ON, 40: MM.CHANGING, 50: MM.ON, 60: MM.OFF, 70: MM.ON},
                "components": {
                    100: MM.OFF,
                    101: MM.ON,
                    102: MM.ON,
                    103: MM.CHANGING,
                    200: MM.ON,
                    300: MM.ON,
                    400: MM.OFF,
                    401: MM.OFF,
                    402: MM.ON,
                    500: MM.ON,
                },
            },
        )

    def test_calculate_maintenance_mode_for_service(self) -> None:
        for (own_mm, service_components_own_mm, service_hosts_mm), expected_result in [
            # own
            ((MM.OFF, (), ()), MM.OFF),
            ((MM.ON, (), ()), MM.ON),
            ((MM.CHANGING, (), ()), MM.CHANGING),
            ((MM.ON, (MM.OFF,), (MM.OFF,)), MM.ON),
            ((MM.CHANGING, (MM.OFF,), (MM.OFF,)), MM.CHANGING),
            # components-related
            ((MM.OFF, (MM.OFF, MM.CHANGING, MM.ON), ()), MM.OFF),
            ((MM.OFF, (MM.ON, MM.ON), ()), MM.ON),
            ((MM.OFF, (MM.OFF, MM.OFF), ()), MM.OFF),
            ((MM.OFF, (MM.OFF, MM.ON), ()), MM.OFF),
            # hosts-related
            ((MM.OFF, (), (MM.OFF, MM.CHANGING, MM.ON)), MM.OFF),
            ((MM.OFF, (), (MM.ON, MM.ON)), MM.ON),
            ((MM.CHANGING, (), (MM.OFF, MM.OFF)), MM.CHANGING),
            ((MM.OFF, (), (MM.OFF, MM.ON)), MM.OFF),
        ]:
            with self.subTest(f"{own_mm=} | {service_components_own_mm=} | {service_hosts_mm=} = {expected_result}"):
                self.assertEqual(
                    calculate_maintenance_mode_for_service(
                        own_mm=own_mm,
                        service_components_own_mm=service_components_own_mm,
                        service_hosts_mm=service_hosts_mm,
                    ),
                    expected_result,
                )

    def test_calculate_maintenance_mode_for_component(self) -> None:
        for (own_mm, service_mm, component_hosts_mm), expected_result in [
            # own
            ((MM.OFF, MM.OFF, ()), MM.OFF),
            ((MM.ON, MM.OFF, ()), MM.ON),
            ((MM.ON, MM.OFF, (MM.ON, MM.OFF)), MM.ON),
            ((MM.OFF, MM.CHANGING, (MM.OFF, MM.OFF)), MM.OFF),
            ((MM.CHANGING, MM.OFF, (MM.OFF, MM.OFF)), MM.CHANGING),
            # host-related
            ((MM.OFF, MM.OFF, (MM.ON,)), MM.ON),
            ((MM.CHANGING, MM.OFF, (MM.ON, MM.ON)), MM.ON),
            ((MM.OFF, MM.OFF, (MM.OFF, MM.ON)), MM.OFF),
            ((MM.OFF, MM.OFF, (MM.OFF, MM.OFF)), MM.OFF),
            ((MM.OFF, MM.OFF, (MM.OFF, MM.CHANGING, MM.ON)), MM.OFF),
            ((MM.CHANGING, MM.OFF, (MM.ON, MM.CHANGING, MM.OFF)), MM.CHANGING),
            # service-related
            ((MM.OFF, MM.ON, ()), MM.ON),
            ((MM.ON, MM.ON, ()), MM.ON),
            ((MM.CHANGING, MM.ON, ()), MM.ON),
            ((MM.OFF, MM.ON, (MM.OFF, MM.OFF)), MM.ON),
        ]:
            with self.subTest(f"{own_mm=} | {service_mm=} | {component_hosts_mm=} = {expected_result}"):
                self.assertEqual(
                    calculate_maintenance_mode_for_component(
                        own_mm=own_mm, service_mm=service_mm, component_hosts_mm=component_hosts_mm
                    ),
                    expected_result,
                )
