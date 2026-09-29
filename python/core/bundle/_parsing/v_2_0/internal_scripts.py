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
#
# Names are the addresses of these scripts, and a bundle substitutes most of them from the
# action configuration at render time. A key that does not exist renders to an empty string
# rather than failing, so an empty name is refused here: without that, a typo in
# `{{ task.config.cluster_name }}` would quietly mean "the current cluster".
#
# Both scripts address ADCM objects with one vocabulary: `object` names the owner of a host
# group the same way `config_apply` names the object whose configuration it writes, and a
# `source` entry names the hosts to act on. Every rejection a combination of keys implies is
# expressed by the variant not declaring the key, so an unknown key is refused at parse time.


@dataclass(slots=True, frozen=True)
class TypeBasedObjectRule:
    type: Literal["cluster", "provider"]


@dataclass(slots=True, frozen=True)
class ServiceObjectRule:
    type: Literal["service"]
    service_name: NonEmptyName


@dataclass(slots=True, frozen=True)
class ComponentObjectRule:
    type: Literal["component"]
    service_name: NonEmptyName
    component_name: NonEmptyName


ObjectRule = Annotated[
    TypeBasedObjectRule | ServiceObjectRule | ComponentObjectRule,
    Field(discriminator="type"),
]


# `source` entries. A cluster-relative entry may name a foreign cluster; `host` and the group
# types may not, because a group only ever holds hosts of its owner's cluster and a host is
# named within the cluster the entry is resolved against.


@dataclass(slots=True, frozen=True)
class ClusterHostSourceRule:
    type: Literal["cluster"]
    cluster_name: OptionalName = None


@dataclass(slots=True, frozen=True)
class ServiceHostSourceRule:
    type: Literal["service"]
    service_name: NonEmptyName
    cluster_name: OptionalName = None


@dataclass(slots=True, frozen=True)
class ComponentHostSourceRule:
    type: Literal["component"]
    service_name: NonEmptyName
    component_name: NonEmptyName
    cluster_name: OptionalName = None


@dataclass(slots=True, frozen=True)
class NamedHostSourceRule:
    type: Literal["host"]
    host_name: NonEmptyName


@dataclass(slots=True, frozen=True)
class ConfigHostGroupSourceRule:
    type: Literal["config_host_group"]
    name: NonEmptyName
    object: ObjectRule


@dataclass(slots=True, frozen=True)
class ActionHostGroupSourceRule:
    type: Literal["action_host_group"]
    name: NonEmptyName
    object: ObjectRule


HostSourceRule = Annotated[
    ClusterHostSourceRule
    | ServiceHostSourceRule
    | ComponentHostSourceRule
    | NamedHostSourceRule
    | ConfigHostGroupSourceRule
    | ActionHostGroupSourceRule,
    Field(discriminator="type"),
]


def ensure_unique_source_entries(source: list[HostSourceRule]) -> list[HostSourceRule]:
    seen = set()
    for entry in source:
        if entry in seen:
            message = f"Duplicate `source` entry: {entry}"
            raise ValueError(message)
        seen.add(entry)

    return source


@dataclass(slots=True, frozen=True)
class TargetClusterRule:
    cluster_name: NonEmptyName


@dataclass(slots=True, frozen=True)
class HostGroupReference:
    name: NonEmptyName
    type: Literal["config_host_group", "action_host_group"]
    # owner of the group; the task owner when not given
    object: Annotated[ObjectRule | None, Field(default=None)]


@dataclass(slots=True)
class HostManageSchema:
    operation: Literal["add_duplicates", "remove_duplicates", "add_to_groups"]
    source: Annotated[list[HostSourceRule], Field(min_length=1), AfterValidator(ensure_unique_source_entries)]
    # `add_duplicates` only: where the duplicates are created; the current cluster when not given
    target: Annotated[list[TargetClusterRule] | None, Field(default=None)]
    # `add_duplicates` only: written to the task's mapping delta, not committed - `hc_apply` commits
    mapping_rules: Annotated[list[HcApplyRule] | None, Field(default=None)]
    # membership only: every group must already exist
    groups: Annotated[list[HostGroupReference] | None, Field(default=None)]


def ensure_host_manage_operation_fields(params: HostManageSchema) -> HostManageSchema:
    for field_name in ("target", "mapping_rules"):
        if getattr(params, field_name) is not None and params.operation != "add_duplicates":
            message = f"`{field_name}` is only allowed for `operation: add_duplicates`"
            raise ValueError(message)

    if params.groups is not None and params.operation == "remove_duplicates":
        message = "`groups` is not allowed for `operation: remove_duplicates`"
        raise ValueError(message)

    if params.operation == "add_to_groups" and not params.groups:
        message = "`operation: add_to_groups` requires a non-empty `groups`"
        raise ValueError(message)

    return params


HostManageParams = Annotated[HostManageSchema, AfterValidator(ensure_host_manage_operation_fields)]


@dataclass(slots=True, frozen=True)
class HostGroupItem:
    name: NonEmptyName
    type: Literal["config_host_group", "action_host_group"]
    object: ObjectRule
    description: Annotated[str | None, Field(default=None)]
    # three states: absent leaves membership alone, a list replaces it, an empty list empties it
    hosts: Annotated[list[NonEmptyName] | None, Field(default=None)]
    # configuration host groups only
    parameters: Annotated[list[ConfigApplyParameterItem] | None, Field(default=None)]


@dataclass(slots=True)
class HostGroupManageSchema:
    operation: Literal["add", "remove"]
    groups: Annotated[list[HostGroupItem], Field(min_length=1)]


def ensure_host_group_manage_entries(params: HostGroupManageSchema) -> HostGroupManageSchema:
    seen = set()

    for group in params.groups:
        address = (group.type, group.name, group.object)
        if address in seen:
            message = f'Duplicate {group.type} "{group.name}" of the same object in `groups`'
            raise ValueError(message)
        seen.add(address)

        if params.operation == "remove":
            for field_name in ("description", "hosts", "parameters"):
                if getattr(group, field_name) is not None:
                    message = f"`{field_name}` is not allowed for `operation: remove`"
                    raise ValueError(message)

        if group.type == "action_host_group":
            if group.parameters is not None:
                message = "`parameters` is only allowed for a `config_host_group`"
                raise ValueError(message)

            if group.object.type == "provider":
                message = "An `action_host_group` can't be owned by a provider"
                raise ValueError(message)

    return params


HostGroupManageParams = Annotated[HostGroupManageSchema, AfterValidator(ensure_host_group_manage_entries)]
