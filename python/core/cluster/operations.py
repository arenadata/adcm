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
from copy import copy
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
    TopologyHostDiff,
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


def create_topology_with_new_mapping(
    topology: ClusterTopology, new_mapping: Iterable[HostComponentEntry]
) -> ClusterTopology:
    """
    If we assume that all objects from "new_mapping" are presented in topology,
    then we can create new topology based on that input without additional information.
    """
    mapping: dict[ComponentID, set[HostID]] = defaultdict(set)
    for entry in new_mapping:
        mapping[entry.component_id].add(entry.host_id)

    return ClusterTopology(
        cluster_id=topology.cluster_id,
        hosts=copy(topology.hosts),
        services={
            service_id: ServiceTopology(
                info=service.info,
                components={
                    component_id: ComponentTopology(
                        info=component.info,
                        hosts={host_id: topology.hosts[host_id] for host_id in mapping.get(component_id, ())},
                    )
                    for component_id, component in service.components.items()
                },
            )
            for service_id, service in topology.services.items()
        },
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


def find_hosts_difference(new_topology: ClusterTopology, old_topology: ClusterTopology) -> TopologyHostDiff:
    """
    Detect which hosts were mapped and unmapped between new and old topologies

    Note that results will contain newly added and removed services and components:
    - all hosts on newly added objects are considered mapped
    - all hosts on removed objects are considered unmapped
    """
    diff = TopologyHostDiff()

    dummy_info = ShortObjectInfo(id=-1, name="notexist")

    for service_id, new_service_topology in new_topology.services.items():
        old_service_topology = old_topology.services.get(service_id, ServiceTopology(info=dummy_info, components={}))

        old_service_hosts = set(old_service_topology.host_ids)
        new_service_hosts = set(new_service_topology.host_ids)

        diff.unmapped.services[service_id] = old_service_hosts - new_service_hosts
        diff.mapped.services[service_id] = new_service_hosts - old_service_hosts

        for component_id, new_component_topology in new_service_topology.components.items():
            old_component_topology = old_service_topology.components.get(
                component_id, ComponentTopology(info=dummy_info, hosts={})
            )

            old_component_hosts = set(old_component_topology.hosts)
            new_component_hosts = set(new_component_topology.hosts)

            diff.unmapped.components[component_id] = old_component_hosts - new_component_hosts
            diff.mapped.components[component_id] = new_component_hosts - old_component_hosts

        # it's possible that some components are gone now, for universality reasons we should handle that case
        for gone_component_id in set(old_service_topology.components).difference(new_service_topology.components):
            diff.unmapped.components[gone_component_id] = set(old_service_topology.components[gone_component_id].hosts)

    # Appearance of new services is well covered in previous loop (new/old components too),
    # but disappearance of old services isn't, so we handle it in here
    for gone_service_id in set(old_topology.services).difference(new_topology.services):
        gone_service_topology = old_topology.services[gone_service_id]
        diff.unmapped.services[gone_service_id] = set(gone_service_topology.host_ids)

        for gone_component_id, gone_component_topology in gone_service_topology.components.items():
            diff.unmapped.components[gone_component_id] = set(gone_component_topology.hosts)

    return diff


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
