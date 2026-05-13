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

from typing import Iterable

from core.cluster._types import ClusterTopology
from core.types import (
    ComponentID,
    MaintenanceModeOfObjects,
    MaintenanceModeState,
    MMReason,
    ObjectMM,
)


def calculate_maintenance_mode_for_cluster_objects(
    topology: ClusterTopology, own_maintenance_mode: MaintenanceModeOfObjects
) -> MaintenanceModeOfObjects:
    cluster_objects_mm = MaintenanceModeOfObjects(
        services={},
        components={},
        hosts={
            host_id: own_maintenance_mode.hosts.get(host_id, ObjectMM(MaintenanceModeState.OFF))
            for host_id in topology.hosts
        },
    )

    for service_id, service in topology.services.items():
        service_own_mm = own_maintenance_mode.services.get(service_id, ObjectMM(MaintenanceModeState.OFF))
        service_components_calculated_mm: dict[ComponentID, ObjectMM] = {}

        for component_id, component in service.components.items():
            component_own_mm = own_maintenance_mode.components.get(component_id, ObjectMM(MaintenanceModeState.OFF))
            service_components_calculated_mm[component_id] = _calculate_maintenance_mode_for_component(
                own_mm=component_own_mm,
                service_own_mm=service_own_mm,
                component_hosts_own_mm=(
                    own_maintenance_mode.hosts.get(host_id, ObjectMM(MaintenanceModeState.OFF))
                    for host_id in component.hosts
                ),
            )

        cluster_objects_mm.services[service_id] = _calculate_maintenance_mode_for_service(
            own_mm=service_own_mm,
            service_components_calculated_mm=service_components_calculated_mm.values(),
            service_hosts_own_mm=(
                own_maintenance_mode.hosts.get(host_id, ObjectMM(MaintenanceModeState.OFF))
                for host_id in service.host_ids
            ),
        )
        cluster_objects_mm.components.update(service_components_calculated_mm)

    return cluster_objects_mm


def _calculate_maintenance_mode_for_service(
    own_mm: ObjectMM,
    service_components_calculated_mm: Iterable[ObjectMM],
    service_hosts_own_mm: Iterable[ObjectMM],
) -> ObjectMM:
    if own_mm.state == MaintenanceModeState.ON:
        return own_mm

    # service has components and all components' maintenance mode is ON
    if {mm.state for mm in service_components_calculated_mm} == {MaintenanceModeState.ON}:
        return ObjectMM(MaintenanceModeState.ON, MMReason.ALL_COMPONENTS_IN_MM)

    # service has hosts and all hosts' maintenance mode is set to ON
    if {mm.state for mm in service_hosts_own_mm} == {MaintenanceModeState.ON}:
        return ObjectMM(MaintenanceModeState.ON, MMReason.ALL_HOSTS_IN_MM)

    return own_mm


def _calculate_maintenance_mode_for_component(
    own_mm: ObjectMM,
    service_own_mm: ObjectMM,
    component_hosts_own_mm: Iterable[ObjectMM],
) -> ObjectMM:
    if own_mm.state == MaintenanceModeState.ON:
        return own_mm

    if service_own_mm.state == MaintenanceModeState.ON:
        return ObjectMM(MaintenanceModeState.ON, MMReason.SERVICE_IN_MM)

    if {mm.state for mm in component_hosts_own_mm} == {MaintenanceModeState.ON}:
        return ObjectMM(MaintenanceModeState.ON, MMReason.ALL_HOSTS_IN_MM)

    return own_mm
