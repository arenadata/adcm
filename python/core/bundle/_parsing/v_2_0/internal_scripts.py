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
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, Field

from core.action.internal_scripts import HostGroupManageScriptParams, HostManageScriptParams
from core.bundle._parsing.shared.validation import ensure_unique_object

NonEmptyName = Annotated[str, Field(min_length=1)]
OptionalName = Annotated[str | None, Field(min_length=1, default=None)]

# HC Apply


@dataclass(slots=True)
class HcApplyRule:
    service: str
    component: str
    action: Literal["add", "remove"]


@dataclass(slots=True)
class HcApplySchema:
    rules: list[HcApplyRule]


HcApplyParams = Annotated[HcApplySchema | None, Field(default=None)]


# Config Apply
@dataclass(slots=True, frozen=True)
class TypeBasedConfigApplyRule:
    type: Literal["adcm", "provider", "host", "cluster"]


@dataclass(slots=True, frozen=True)
class ServiceConfigApplyRule:
    type: Literal["service"]
    service_name: str


@dataclass(slots=True, frozen=True)
class ComponentConfigApplyRule:
    type: Literal["component"]
    service_name: str
    component_name: str


@dataclass(slots=True, frozen=True)
class ConfigApplyParameterItem:
    key: str
    value: Any


@dataclass(slots=True, frozen=True)
class ConfigApplyObject:
    object: Annotated[
        TypeBasedConfigApplyRule | ServiceConfigApplyRule | ComponentConfigApplyRule,
        Field(discriminator="type"),
    ]
    parameters: list[ConfigApplyParameterItem]


@dataclass(slots=True)
class ConfigApplyParams:
    changes: Annotated[list[ConfigApplyObject], Field(min_length=1), AfterValidator(ensure_unique_object)]


# Service Manage


@dataclass(slots=True, frozen=True)
class ServiceManageMappingItem:
    component: str
    hosts: Annotated[list[str], Field(min_length=1)]


@dataclass(slots=True, frozen=True)
class ServiceManageServiceItem:
    name: str
    config_changes: Annotated[list[ConfigApplyParameterItem] | None, Field(default=None)]
    hc_changes: Annotated[list[ServiceManageMappingItem] | None, Field(default=None)]


def ensure_unique_service_names(services: list[ServiceManageServiceItem]) -> list[ServiceManageServiceItem]:
    seen = set()
    for service in services:
        if service.name in seen:
            message = f'Duplicate service "{service.name}" in `services`'
            raise ValueError(message)
        seen.add(service.name)

    return services


@dataclass(slots=True)
class ServiceManageParams:
    operation: Literal["add"]
    services: Annotated[
        list[ServiceManageServiceItem], Field(min_length=1), AfterValidator(ensure_unique_service_names)
    ]


# Host Manage / Host Group Manage

# The arguments of these scripts are defined in `core.action.internal_scripts` and
# validated both when a bundle is parsed and when the plan stored with a task is read
# back, so there is one set of models instead of a parsing and a runtime copy; the
# aliases keep the names the rest of the parsing package imports.

HostManageParams = HostManageScriptParams

HostGroupManageParams = HostGroupManageScriptParams
