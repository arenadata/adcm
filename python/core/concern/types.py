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
from typing import Callable, NamedTuple, TypeAlias

from core.types import ComponentName, ServiceName


class ComponentNameKey(NamedTuple):
    service: ServiceName
    component: ComponentName

    def __str__(self) -> str:
        return f'component "{self.component}" of service "{self.service}"'


ComponentRestrictionOwner: TypeAlias = ComponentNameKey


class ServiceRestrictionOwner(NamedTuple):
    name: ServiceName

    def __str__(self) -> str:
        return f'service "{self.name}"'


class MappingRestrictionType(Enum):
    CONSTRAINT = "constraint"
    REQUIRES = "requires"
    BOUND_TO = "bound_to"


class MappingRestrictionViolation(NamedTuple):
    restriction: MappingRestrictionType
    component: ComponentNameKey
    message: str


class MissingServiceRequiresViolation(NamedTuple):
    required_service: ServiceName
    dependant_object: ServiceRestrictionOwner | ComponentRestrictionOwner


HostsAmount: TypeAlias = int


# Constraints - Requirements On Mapped Hosts Amount


SupportedConstraintFormat: TypeAlias = tuple[str] | tuple[HostsAmount | str, HostsAmount | str]


class Constraint(NamedTuple):
    internal: SupportedConstraintFormat
    checks: tuple[Callable[[HostsAmount, HostsAmount], bool], ...]


# Bundle Restrictions

# Services that should be added to cluster
ServiceDependencies: TypeAlias = dict[ServiceRestrictionOwner | ComponentRestrictionOwner, set[ServiceName]]


@dataclass(slots=True)
class MappingRestrictions:
    constraints: dict[ComponentRestrictionOwner, Constraint]
    # Components that should be mapped at least on one host
    required: dict[ServiceRestrictionOwner | ComponentRestrictionOwner, deque[ComponentNameKey]]
    # Should be mapped on the same hosts
    binds: dict[ComponentRestrictionOwner, ComponentNameKey]


@dataclass(slots=True, frozen=True)
class BundleRestrictions:
    service_requires: ServiceDependencies
    mapping: MappingRestrictions
