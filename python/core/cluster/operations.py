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

from collections import defaultdict
from typing import Any, Collection, Generator, Iterable, Protocol

from core.cluster.rules import (
    check_all_hosts_exist,
    check_hosts_can_be_added_to_cluster,
)
from core.cluster.types import (
    ClusterTopology,
    ComponentTopology,
    HostClusterPair,
    HostComponentEntry,
    MaintenanceModeOfObjects,
    ObjectMaintenanceModeState,
    ServiceTopology,
)
from core.types import ClusterID, ComponentID, HostID, MappingDict, ShortObjectInfo

# !===== Cluster Topology =====!


class ClusterTopologyDBProtocol(Protocol):
    def get_clusters_hosts(self, cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, Iterable[ShortObjectInfo]]:
        """Get hosts that belongs to given clusters"""

    def get_clusters_services_with_components(
        self, cluster_ids: Iterable[ClusterID]
    ) -> dict[ClusterID, Iterable[tuple[ShortObjectInfo, Collection[ShortObjectInfo]]]]:
        """
        Retrieve pairs of clusters' services and its components.
        If service has no components, should return empty collection.
        """

    def get_host_component_entries(
        self, cluster_ids: Iterable[ClusterID]
    ) -> dict[ClusterID, Iterable[HostComponentEntry]]:
        """Retrieve host-components entries of clusters"""


def build_clusters_topology(
    cluster_ids: Iterable[ClusterID],
    db: ClusterTopologyDBProtocol,
    input_mapping: dict[ClusterID, list[MappingDict]] | None = None,
) -> Generator[ClusterTopology, None, None]:
    input_mapping = {} if input_mapping is None else input_mapping

    hosts_in_clusters = {
        cluster_id: {host.id: host for host in hosts}
        for cluster_id, hosts in db.get_clusters_hosts(cluster_ids=cluster_ids).items()
    }
    services_in_clusters = db.get_clusters_services_with_components(cluster_ids=cluster_ids)

    # either existing mapping or input mapping is used to collect `hosts_on_components`
    hosts_on_components: dict[ClusterID, dict[ComponentID, set[HostID]]] = {
        cluster_id: defaultdict(set) for cluster_id in cluster_ids
    }
    if hosts_in_clusters and services_in_clusters and not input_mapping:
        for cluster_id, entries in db.get_host_component_entries(cluster_ids=cluster_ids).items():
            for entry in entries:
                hosts_on_components[cluster_id][entry.component_id].add(entry.host_id)

    for cluster_id, input_mapping_list in input_mapping.items():
        for input_mapping_entry in input_mapping_list:
            hosts_on_components[cluster_id][input_mapping_entry["component_id"]].add(input_mapping_entry["host_id"])

    return (
        ClusterTopology(
            cluster_id=cluster_id,
            hosts=hosts_in_clusters.get(cluster_id, {}),
            services={
                service.id: ServiceTopology(
                    info=service,
                    components={
                        component.id: ComponentTopology(
                            info=component,
                            hosts={
                                host_id: hosts_in_clusters[cluster_id][host_id]
                                for host_id in hosts_on_components[cluster_id][component.id]
                            },
                        )
                        for component in components
                    },
                )
                for service, components in services_in_clusters.get(cluster_id, ())
            },
        )
        for cluster_id in cluster_ids
    )


def calculate_maintenance_mode_for_cluster_objects(
    topology: ClusterTopology, own_maintenance_mode: MaintenanceModeOfObjects
) -> MaintenanceModeOfObjects:
    cluster_objects_mm = MaintenanceModeOfObjects(
        services={},
        components={},
        hosts={
            host_id: own_maintenance_mode.hosts.get(host_id, ObjectMaintenanceModeState.OFF)
            for host_id in topology.hosts
        },
    )

    for service_id, service in topology.services.items():
        service_own_mm = own_maintenance_mode.services.get(service_id, ObjectMaintenanceModeState.OFF)
        cluster_objects_mm.services[service_id] = calculate_maintenance_mode_for_service(
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
            cluster_objects_mm.components[component_id] = calculate_maintenance_mode_for_component(
                own_mm=component_own_mm,
                service_mm=service_own_mm,
                component_hosts_mm=(
                    own_maintenance_mode.hosts.get(host_id, ObjectMaintenanceModeState.OFF)
                    for host_id in component.hosts
                ),
            )

    return cluster_objects_mm


def calculate_maintenance_mode_for_service(
    own_mm: ObjectMaintenanceModeState,
    service_components_own_mm: Iterable[ObjectMaintenanceModeState],
    service_hosts_mm: Iterable[ObjectMaintenanceModeState],
) -> ObjectMaintenanceModeState:
    # service has components and all components' maintenance mode is set to ON
    if set(service_components_own_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON

    # service has hosts and all hosts' maintenance mode is set to ON
    if set(service_hosts_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON

    return own_mm


def calculate_maintenance_mode_for_component(
    own_mm: ObjectMaintenanceModeState,
    service_mm: ObjectMaintenanceModeState,
    component_hosts_mm: Iterable[ObjectMaintenanceModeState],
) -> ObjectMaintenanceModeState:
    if service_mm == ObjectMaintenanceModeState.ON:
        return ObjectMaintenanceModeState.ON

    if set(component_hosts_mm) == {ObjectMaintenanceModeState.ON}:
        return ObjectMaintenanceModeState.ON

    return own_mm


# !===== Hosts In Cluster =====!


class HostClusterDBProtocol(Protocol):
    def get_host_cluster_pairs_for_hosts(self, hosts: Iterable[HostID]) -> Iterable[HostClusterPair]:
        """Extract pairs of ids host-component for given hosts"""

    def set_cluster_id_for_hosts(self, cluster_id: ClusterID, hosts: Iterable[HostID]) -> Any:
        """Set `cluster_id` to all given hosts"""


def add_hosts_to_cluster(cluster_id: int, hosts: Collection[int], db: HostClusterDBProtocol) -> Collection[int]:
    existing_hosts: tuple[HostClusterPair, ...] = tuple(db.get_host_cluster_pairs_for_hosts(hosts))

    check_all_hosts_exist(host_candidates=hosts, existing_hosts=existing_hosts)
    check_hosts_can_be_added_to_cluster(cluster_id=cluster_id, hosts=existing_hosts)

    db.set_cluster_id_for_hosts(cluster_id, hosts)

    return hosts
