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
    ComponentMMReason,
    MaintenanceModeOfObjects,
    MaintenanceModeOfObjectsWithReason,
    MMReason,
    ObjectMaintenanceModeState,
    ServiceMMReason,
)


# COPIED from core.legacy.cluster.operations.calculate_maintenance_mode_for_cluster_objects
def calculate_maintenance_mode_for_cluster_objects(
    topology: ClusterTopology, own_maintenance_mode: MaintenanceModeOfObjects
) -> MaintenanceModeOfObjectsWithReason:
    cluster_objects_mm = MaintenanceModeOfObjectsWithReason(
        services={},
        components={},
        hosts={
            host_id: (own_maintenance_mode.hosts.get(host_id, ObjectMaintenanceModeState.OFF), MMReason.SELF)
            for host_id in topology.hosts
        },
    )

    for service_id, service in topology.services.items():
        service_own_mm = own_maintenance_mode.services.get(service_id, ObjectMaintenanceModeState.OFF)
        cluster_objects_mm.services[service_id] = _calculate_maintenance_mode_for_service(
            own_mm=service_own_mm,
            service_components_own_mm=(
                own_maintenance_mode.components.get(component_id, ObjectMaintenanceModeState.OFF)
                for component_id in service.components
            ),
            service_hosts_mm=(
                own_maintenance_mode.hosts.get(host_id, ObjectMaintenanceModeState.OFF) for host_id in service.host_ids
            ),
        )

        for component_id, component in service.components.items():
            component_own_mm = own_maintenance_mode.components.get(component_id, ObjectMaintenanceModeState.OFF)
            cluster_objects_mm.components[component_id] = _calculate_maintenance_mode_for_component(
                own_mm=component_own_mm,
                service_mm=service_own_mm,
                component_hosts_mm=(
                    own_maintenance_mode.hosts.get(host_id, ObjectMaintenanceModeState.OFF)
                    for host_id in component.hosts
                ),
            )

    return cluster_objects_mm


def _calculate_maintenance_mode_for_service(
    own_mm: ObjectMaintenanceModeState,
    service_components_own_mm: Iterable[ObjectMaintenanceModeState],
    service_hosts_mm: Iterable[ObjectMaintenanceModeState],
) -> tuple[ObjectMaintenanceModeState, ServiceMMReason]:
    # service has components and all components' maintenance mode is set to ON
    if set(service_components_own_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON, MMReason.ALL_COMPONENTS_IN_MM

    # service has hosts and all hosts' maintenance mode is set to ON
    if set(service_hosts_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON, MMReason.ALL_HOSTS_IN_MM

    return own_mm, MMReason.SELF


def _calculate_maintenance_mode_for_component(
    own_mm: ObjectMaintenanceModeState,
    service_mm: ObjectMaintenanceModeState,
    component_hosts_mm: Iterable[ObjectMaintenanceModeState],
) -> tuple[ObjectMaintenanceModeState, ComponentMMReason]:
    if service_mm == ObjectMaintenanceModeState.ON:
        return ObjectMaintenanceModeState.ON, MMReason.SERVICE_IN_MM

    if set(component_hosts_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON, MMReason.ALL_HOSTS_IN_MM

    return own_mm, MMReason.SELF


# END COPY
