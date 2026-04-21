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
from enum import Enum, auto
from typing import Generic, Literal, NamedTuple, NewType, TypeAlias, TypeVar

CurrentADCMVersion = NewType("CurrentADCMVersion", str)

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
JobID: TypeAlias = int
ActionProcessID: TypeAlias = int
ActionProcessStepID: TypeAlias = int
PID: TypeAlias = int

ActionHostGroupID: TypeAlias = int

ObjectConfigID: TypeAlias = int
ConfigID: TypeAlias = int
ConcernID: TypeAlias = int

LogStorageID: TypeAlias = int
IsCreated: TypeAlias = bool
GroupCheckLogID: TypeAlias = int
CheckLogID: TypeAlias = int

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


class ADCMCoreType(str, Enum):
    ADCM = "adcm"
    CLUSTER = "cluster"
    SERVICE = "service"
    COMPONENT = "component"
    PROVIDER = "provider"
    HOST = "host"


class RBACCoreType(Enum):
    USER = "user"
    GROUP = "group"
    ROLE = "role"
    POLICY = "policy"


class ADCMHostGroupType(Enum):
    CONFIG = "config-group"
    ACTION = "action-group"


class ExtraActionTargetType(str, Enum):
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
class Descriptor(Generic[T]):
    id: ObjectID
    type: T


@dataclass(slots=True, frozen=True)
class GeneralEntityDescriptor(Descriptor[str]):
    ...


@dataclass(slots=True, frozen=True)
class HostGroupDescriptor(Descriptor[ADCMHostGroupType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


@dataclass(slots=True, frozen=True)
class CoreObjectDescriptor(Descriptor[ADCMCoreType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"


@dataclass(slots=True, frozen=True)
class ActionTargetDescriptor(Descriptor[ADCMCoreType | ExtraActionTargetType]):
    def __str__(self) -> str:
        return f"{self.type.value} #{self.id}"

    @property
    def as_core_or_group_descriptor(self) -> CoreObjectDescriptor | HostGroupDescriptor:
        if isinstance(self.type, ADCMCoreType):
            return CoreObjectDescriptor(id=self.id, type=self.type)

        return HostGroupDescriptor(id=self.id, type=ADCMHostGroupType.ACTION)


ClusterDesc: TypeAlias = Descriptor[Literal[ADCMCoreType.CLUSTER]]
ServiceDesc: TypeAlias = Descriptor[Literal[ADCMCoreType.SERVICE]]
ComponentDesc: TypeAlias = Descriptor[Literal[ADCMCoreType.COMPONENT]]
ProviderDesc: TypeAlias = Descriptor[Literal[ADCMCoreType.PROVIDER]]
HostDesc: TypeAlias = Descriptor[Literal[ADCMCoreType.HOST]]
ConfigHostGroupDesc: TypeAlias = Descriptor[Literal[ADCMHostGroupType.CONFIG]]

ClusterObjectDesc: TypeAlias = ClusterDesc | ServiceDesc | ComponentDesc
ProviderObjectDesc: TypeAlias = ProviderDesc | HostDesc
MainObjectDesc: TypeAlias = ClusterObjectDesc | ProviderObjectDesc

ObjectOrGroup: TypeAlias = CoreObjectDescriptor | HostGroupDescriptor | ConfigHostGroupDesc
TaskDescriptor: TypeAlias = Descriptor[Literal["task"]]
ActionDescriptor: TypeAlias = Descriptor[Literal["action"]]


@dataclass(slots=True, frozen=True)
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

    @property
    def full_name(self) -> str:
        return f"{self.service}.{self.component}"


class Concern(NamedTuple):
    id: ObjectID
    type: str
    cause: str


class ObjectMaintenanceModeState(Enum):
    ON = "on"
    OFF = "off"
    CHANGING = "changing"


class MMReason(Enum):
    ALL_HOSTS_IN_MM = auto()
    SERVICE_IN_MM = auto()
    ALL_COMPONENTS_IN_MM = auto()
    SELF = auto()


class MaintenanceModeOfObjects(NamedTuple):
    services: dict[ServiceID, ObjectMaintenanceModeState]
    components: dict[ComponentID, ObjectMaintenanceModeState]
    hosts: dict[HostID, ObjectMaintenanceModeState]

    @property
    def objects_dict(self) -> dict[ServiceDesc | ComponentDesc | HostDesc, ObjectMaintenanceModeState]:
        iterables = set()
        for entities, core_type in (
            (self.services, ADCMCoreType.SERVICE),
            (self.components, ADCMCoreType.COMPONENT),
            (self.hosts, ADCMCoreType.HOST),
        ):
            iterables.update(((Descriptor(id=id_, type=core_type), mm) for id_, mm in entities.items()))

        return dict(iterables)


ServiceMMReason: TypeAlias = Literal[MMReason.ALL_COMPONENTS_IN_MM, MMReason.ALL_HOSTS_IN_MM, MMReason.SELF]
ComponentMMReason: TypeAlias = Literal[MMReason.SERVICE_IN_MM, MMReason.ALL_HOSTS_IN_MM, MMReason.SELF]
HostMMReason: TypeAlias = Literal[MMReason.SELF]


@dataclass(slots=True, frozen=True)
class MaintenanceModeOfObjectsWithReason:
    services: dict[ServiceID, tuple[ObjectMaintenanceModeState, ServiceMMReason]]
    components: dict[ComponentID, tuple[ObjectMaintenanceModeState, ComponentMMReason]]
    hosts: dict[HostID, tuple[ObjectMaintenanceModeState, HostMMReason]]

    @property
    def objects_dict(self) -> dict[ServiceDesc | ComponentDesc | HostDesc, ObjectMaintenanceModeState]:
        iterables = set()
        for entities, core_type in (
            (self.services, ADCMCoreType.SERVICE),
            (self.components, ADCMCoreType.COMPONENT),
            (self.hosts, ADCMCoreType.HOST),
        ):
            iterables.update(((Descriptor(id=id_, type=core_type), mm) for id_, (mm, _) in entities.items()))

        return dict(iterables)
