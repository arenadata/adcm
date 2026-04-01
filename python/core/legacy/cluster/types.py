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

from collections import UserDict
from dataclasses import dataclass, field
from itertools import chain
from typing import Generic, Iterable, NamedTuple, TypeAlias, TypeVar

from core.types import (
    ClusterID,
    ComponentID,
    ComponentName,
    ComponentNameKey,
    HostID,
    HostName,
    ServiceID,
    ServiceName,
    ShortObjectInfo,
)


class HostClusterPair(NamedTuple):
    host_id: HostID
    cluster_id: ClusterID | None


@dataclass(slots=True, frozen=True)
class HostAddInfo:
    id: HostID
    name: HostName
    original_id: HostID | None
    cluster_id: ClusterID | None

    @property
    def fqdn(self) -> str:
        # added for convenience in some APIs / serializers
        return self.name


class HostComponentEntry(NamedTuple):
    host_id: HostID
    component_id: ComponentID


# Topology

NamedMapping: TypeAlias = dict[ServiceName, dict[ComponentName, set[HostID]]]


class ComponentTopology(NamedTuple):
    info: ShortObjectInfo
    hosts: dict[HostID, ShortObjectInfo]


class ServiceTopology(NamedTuple):
    info: ShortObjectInfo
    components: dict[ComponentID, ComponentTopology]

    @property
    def host_ids(self) -> Iterable[HostID]:
        return chain.from_iterable(component.hosts for component in self.components.values())


class ClusterTopology(NamedTuple):
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


K = TypeVar("K")
V = TypeVar("V")


class NoEmptyValuesDict(UserDict[K, V], Generic[K, V]):
    def __setitem__(self, key: K, value: V) -> None:
        if not value:
            return
        super().__setitem__(key, value)


@dataclass(slots=True)
class MovedHosts:
    services: NoEmptyValuesDict[ServiceID, set[HostID]] = field(default_factory=NoEmptyValuesDict)
    components: NoEmptyValuesDict[ComponentID, set[HostID]] = field(default_factory=NoEmptyValuesDict)

    @property
    def all(self) -> set[HostID]:
        return set(chain.from_iterable(chain(self.services.values(), self.components.values())))


@dataclass(slots=True)
class TopologyHostDiff:
    mapped: MovedHosts = field(default_factory=MovedHosts)
    unmapped: MovedHosts = field(default_factory=MovedHosts)
