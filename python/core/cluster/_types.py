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

# Topology

from dataclasses import dataclass
from itertools import chain
from typing import Iterable, TypeAlias

from core.types import (
    ClusterID,
    ComponentID,
    ComponentName,
    ComponentNameKey,
    HostID,
    ServiceID,
    ServiceName,
    ShortObjectInfo,
)

NamedMapping: TypeAlias = dict[ServiceName, dict[ComponentName, set[HostID]]]


@dataclass(slots=True)
class ComponentTopology:
    info: ShortObjectInfo
    hosts: dict[HostID, ShortObjectInfo]


@dataclass(slots=True)
class ServiceTopology:
    info: ShortObjectInfo
    components: dict[ComponentID, ComponentTopology]

    @property
    def host_ids(self) -> Iterable[HostID]:
        return chain.from_iterable(component.hosts for component in self.components.values())


@dataclass(slots=True)
class ClusterTopology:
    cluster_id: ClusterID
    services: dict[ServiceID, ServiceTopology]
    hosts: dict[HostID, ShortObjectInfo]

    @property
    def component_ids(self) -> Iterable[ComponentID]:
        return chain.from_iterable(service.components for service in self.services.values())

    @property
    def unmapped_hosts(self) -> set[HostID]:
        mapped_hosts = chain.from_iterable(
            component_topology.hosts
            for component_topology in chain.from_iterable(
                service.components.values() for service in self.services.values()
            )
        )

        return set(self.hosts).difference(mapped_hosts)

    @property
    def component_full_name_id_mapping(self) -> dict[ComponentNameKey, ComponentID]:
        return {
            ComponentNameKey(service=service.info.name, component=component.info.name): component.info.id
            for service in self.services.values()
            for component in service.components.values()
        }

    @property
    def component_host_id_map(self) -> dict[ComponentID, set[HostID]]:
        return {
            component_id: set(component.hosts)
            for service in self.services.values()
            for component_id, component in service.components.items()
        }

    def get_component(self, component_id: ComponentID) -> ComponentTopology:
        for service in self.services.values():
            if component := service.components.get(component_id):
                return component
        else:
            raise KeyError(f"No component with id {component_id}")
