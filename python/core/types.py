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

from dataclasses import dataclass
from enum import Enum
from typing import Literal, NamedTuple, TypeAlias

ObjectID: TypeAlias = int
ClusterID: TypeAlias = ObjectID
ServiceID: TypeAlias = ObjectID
ComponentID: TypeAlias = ObjectID
HostID: TypeAlias = ObjectID
HostProviderID: TypeAlias = ObjectID

BundleID: TypeAlias = int
PrototypeID: TypeAlias = int
ActionID: TypeAlias = int
TaskID: TypeAlias = int

ConfigID: TypeAlias = int
ConcernID: TypeAlias = int

HostName: TypeAlias = str
ServiceName: TypeAlias = str
ComponentName: TypeAlias = str

MappingDict: TypeAlias = dict[Literal["host_id", "component_id", "service_id"], HostID | ComponentID | ServiceID]


class ADCMCoreError(Exception):
    ...


class ADCMMessageError(ADCMCoreError):
    def __init__(self, message: str):
        super().__init__()

        self.message = message


class ADCMCoreType(Enum):
    ADCM = "adcm"
    CLUSTER = "cluster"
    SERVICE = "service"
    COMPONENT = "component"
    HOSTPROVIDER = "hostprovider"
    HOST = "host"


class ADCMHostGroupType(Enum):
    CONFIG = "config-group"
    ACTION = "action-group"


class ExtraActionTargetType(Enum):
    ACTION_HOST_GROUP = "action-host-group"


class ShortObjectInfo(NamedTuple):
    id: ObjectID
    name: str


class ADCMDescriptor(NamedTuple):
    id: int


class PrototypeDescriptor(NamedTuple):
    id: PrototypeID
    type: ADCMCoreType


@dataclass(slots=True, frozen=True)
class GeneralEntityDescriptor:
    id: ObjectID
    type: str


@dataclass(slots=True, frozen=True)
class HostGroupDescriptor(GeneralEntityDescriptor):
    type: ADCMHostGroupType


@dataclass(slots=True, frozen=True)
class ActionTargetDescriptor(GeneralEntityDescriptor):
    type: ADCMCoreType | ExtraActionTargetType

    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


# inheritance from `ActionTargetDescriptor` is for convenience purposes,
# because `CoreObjectDescriptor` is just a bit stricter than `ActionTargetDescriptor`
@dataclass(slots=True, frozen=True)
class CoreObjectDescriptor(ActionTargetDescriptor):
    type: ADCMCoreType


@dataclass(slots=True, frozen=True)
class NamedActionObject(ActionTargetDescriptor):
    name: str


class NamedCoreObjectWithPrototype(NamedTuple):
    id: ObjectID
    prototype_id: PrototypeID
    type: ADCMCoreType
    name: str


class ServiceNameKey(NamedTuple):
    service: ServiceName

    def __str__(self) -> str:
        return f'service "{self.service}"'


class ComponentNameKey(NamedTuple):
    service: ServiceName
    component: ComponentName

    def __str__(self) -> str:
        return f'component "{self.component}" of service "{self.service}"'
