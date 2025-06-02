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

from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, NamedTuple, TypeAlias, TypeVar

ObjectID: TypeAlias = int
ClusterID: TypeAlias = ObjectID
ServiceID: TypeAlias = ObjectID
ComponentID: TypeAlias = ObjectID
HostID: TypeAlias = ObjectID
ProviderID: TypeAlias = ObjectID

BundleID: TypeAlias = int
PrototypeID: TypeAlias = int
ActionID: TypeAlias = int
TaskID: TypeAlias = int
PID: TypeAlias = int

ConfigID: TypeAlias = int
ConcernID: TypeAlias = int

ProviderName: TypeAlias = str
HostName: TypeAlias = str
ClusterName: TypeAlias = str
ServiceName: TypeAlias = str
ComponentName: TypeAlias = str

MappingDict: TypeAlias = dict[Literal["host_id", "component_id", "service_id"], HostID | ComponentID | ServiceID]

T = TypeVar("T")


class ADCMCoreError(Exception):
    ...


class ADCMMessageError(ADCMCoreError):
    def __init__(self, message: str):
        super().__init__(message)

        self.message = message


class ADCMLocalizedError(ADCMCoreError):
    def __init__(self, message: str):
        super().__init__(message)

        self.error = message
        self.locations = deque()

    @property
    def message(self) -> str:
        if not self.locations:
            return self.error

        # reversing locations, because they are added bottom->up the stack
        location = "\n-> ".join(reversed(self.locations))

        return f"Error at:\n{location}\n{self.error}"

    def localize(self, location: str) -> None:
        self.locations.append(location)


class ADCMCoreType(Enum):
    ADCM = "adcm"
    CLUSTER = "cluster"
    SERVICE = "service"
    COMPONENT = "component"
    PROVIDER = "provider"
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
class _Descriptor(Generic[T]):
    id: ObjectID
    type: T


@dataclass(slots=True, frozen=True)
class GeneralEntityDescriptor(_Descriptor[str]):
    ...


@dataclass(slots=True, frozen=True)
class HostGroupDescriptor(_Descriptor[ADCMHostGroupType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


@dataclass(slots=True, frozen=True)
class ActionTargetDescriptor(_Descriptor[ADCMCoreType | ExtraActionTargetType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


# inheritance from `ActionTargetDescriptor` is for convenience purposes,
# because `CoreObjectDescriptor` is just a bit stricter than `ActionTargetDescriptor`
@dataclass(slots=True, frozen=True)
class CoreObjectDescriptor(_Descriptor[ADCMCoreType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


class HostGroupOfObject:
    group: HostGroupDescriptor
    owner: CoreObjectDescriptor


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


class Concern(NamedTuple):
    id: ObjectID
    type: str
    cause: str
