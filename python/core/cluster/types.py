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
from enum import Enum
from itertools import chain
from typing import Generator, NamedTuple

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


class ClusterTopology(NamedTuple):
    cluster_id: ClusterID
    services: dict[ServiceID, ServiceTopology]
    hosts: dict[HostID, ShortObjectInfo]

    @property
    def component_ids(self) -> Generator[ComponentID, None, None]:
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


class NoEmptyValuesDict(UserDict):
    def __setitem__(self, key, value):
        # if value is "empty" for one reason or another
        if not value:
            return

        super().__setitem__(key, value)


@dataclass(slots=True)
class MovedHosts:
    services: NoEmptyValuesDict[ServiceID, set[HostID]] = field(default_factory=NoEmptyValuesDict)
    components: NoEmptyValuesDict[ComponentID, set[HostID]] = field(default_factory=NoEmptyValuesDict)


@dataclass(slots=True)
class TopologyHostDiff:
    mapped: MovedHosts = field(default_factory=MovedHosts)
    unmapped: MovedHosts = field(default_factory=MovedHosts)


class ObjectMaintenanceModeState(Enum):
    ON = "on"
    OFF = "off"
    CHANGING = "changing"


class MaintenanceModeOfObjects(NamedTuple):
    services: dict[ServiceID, ObjectMaintenanceModeState]
    components: dict[ComponentID, ObjectMaintenanceModeState]
    hosts: dict[HostID, ObjectMaintenanceModeState]
