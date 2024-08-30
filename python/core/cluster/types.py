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

from enum import Enum
from itertools import chain
from typing import Generator, NamedTuple

from typing_extensions import Self

from core.types import ClusterID, ComponentID, HostID, ServiceID, ShortObjectInfo


class HostClusterPair(NamedTuple):
    host_id: HostID
    cluster_id: ClusterID | None


class HostComponentEntry(NamedTuple):
    host_id: HostID
    component_id: ComponentID


class ComponentTopology(NamedTuple):
    info: ShortObjectInfo
    hosts: dict[HostID, ShortObjectInfo]


class ServiceTopology(NamedTuple):
    info: ShortObjectInfo
    components: dict[ComponentID, ComponentTopology]

    @property
    def host_ids(self) -> Generator[HostID, None, None]:
        return chain.from_iterable(component.hosts for component in self.components.values())


class MovedHosts(NamedTuple):
    services: dict[ServiceID, set[HostID]]
    components: dict[ComponentID, set[HostID]]


class ClusterTopology(NamedTuple):
    cluster_id: ClusterID
    services: dict[ServiceID, ServiceTopology]
    hosts: dict[HostID, ShortObjectInfo]

    @property
    def component_ids(self) -> Generator[ComponentID, None, None]:
        return chain.from_iterable(service.components for service in self.services.values())

    def __sub__(self, previous: Self) -> MovedHosts:
        """Returns unmapped hosts that were in the previous and removed from self"""
        services_diff, components_diff = {}, {}
        for service_id, service_topology in previous.services.items():
            new_service_topology = self.services.get(service_id)
            if not new_service_topology:
                if host_diff := set(service_topology.host_ids):
                    services_diff[service_id] = host_diff
                continue

            host_diff = set(new_service_topology.host_ids) - set(service_topology.host_ids)
            if host_diff:
                services_diff[service_id] = host_diff

            for component_id, component_topology in service_topology.components.items():
                new_component_topology = new_service_topology.components.get(component_id)
                if not new_component_topology:
                    if host_diff := set(service_topology.host_ids):
                        components_diff[service_id] = host_diff
                    continue

                host_diff = set(new_component_topology.hosts) - set(component_topology.hosts)
                if host_diff:
                    components_diff[component_id] = host_diff

        return MovedHosts(services=services_diff, components=components_diff)


class ObjectMaintenanceModeState(Enum):
    ON = "on"
    OFF = "off"
    CHANGING = "changing"


class MaintenanceModeOfObjects(NamedTuple):
    services: dict[ServiceID, ObjectMaintenanceModeState]
    components: dict[ComponentID, ObjectMaintenanceModeState]
    hosts: dict[HostID, ObjectMaintenanceModeState]
