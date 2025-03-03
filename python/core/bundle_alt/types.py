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

from dataclasses import dataclass, field
from functools import partial
from typing import Any, Literal, NamedTuple, Protocol, TypeAlias

from core.job.types import JobSpec


class WithName(Protocol):
    name: str


class GeneralObjectDescription(Protocol):
    type: str
    name: str
    version: str


# EXTERNAL SECTION START

ParameterKey: TypeAlias = tuple[str, ...]


# copied from cm.services.config.spec for ADCM-6355
# should be removed later
@dataclass(slots=True)
class ConfigParamPlainSpec:
    # Identification
    key: ParameterKey
    type: str

    # Description
    display_name: str = ""
    description: str = ""

    # Properties
    required: bool = True
    group_customization: bool = False
    limits: dict = field(default_factory=dict)
    ui_options: dict = field(default_factory=dict)

    # the problem is that here default is anything at all
    # yet after save-load to/from db it's str / None
    # => should be unified for both cases
    #    (IMO defaults should be stored separately)
    default: Any = None  # str

    @property
    def name(self) -> str:
        return self.key[-1]


@dataclass(slots=True)
class ConfigDefinition:
    parameters: dict[ParameterKey, ConfigParamPlainSpec]
    # values that were directly set as defaults by bundle developer
    default_values: dict[ParameterKey, Any]
    # detected from options like group customization
    # and active fields of groups
    default_attrs: dict[ParameterKey, Any]


# EXTERNAL SECTION END

# this action stuff may be reused in future repos for Action/Task/Script


@dataclass(slots=True)
class OnCompletion:
    set_state: str | None = None
    set_multi_state: list = field(default_factory=list)
    unset_multi_state: list = field(default_factory=list)


@dataclass(slots=True)
class ActionAvailability:
    states: Literal["any"] | list[str]
    multi_states: Literal["any"] | list[str]


@dataclass(slots=True)
class ActionDefinition:
    # Identification
    type: Literal["task", "job"]
    name: str

    # Details
    display_name: str = ""
    description: str = ""
    ui_options: dict = field(default_factory=dict)

    # Specifics
    is_host_action: bool = False
    venv: Literal["default", "2.9"] = "default"

    # Allowed operations
    allow_to_terminate: bool = False
    allow_for_action_host_group: bool = False
    allow_in_maintenance_mode: bool = False

    # Availability
    available_at: ActionAvailability = field(default_factory=lambda: ActionAvailability(states=[], multi_states="any"))
    unavailable_at: ActionAvailability = field(default_factory=lambda: ActionAvailability(states=[], multi_states=[]))

    # Task settings
    scripts: list[JobSpec] = field(default_factory=list)
    scripts_jinja: str | None = None

    config: ConfigDefinition | None = None
    config_jinja: str | None = None

    hostcomponentmap: list = field(default_factory=list)

    # Task completion
    on_success: OnCompletion = field(default_factory=OnCompletion)
    on_fail: OnCompletion = field(default_factory=OnCompletion)

    # Misc
    partial_execution: bool = False

    def __post_init__(self):
        if self.scripts and self.scripts_jinja:
            raise ValueError("Either `scripts` or `jinja_scripts` should be set, not both at once")

        if self.config and self.config_jinja:
            raise ValueError("Either `config` or `jinja_config` should be set, not both at once")


class VersionBound(NamedTuple):
    value: str
    is_strict: bool


@dataclass(slots=True)
class UpgradeRestrictions:
    min_version: VersionBound = VersionBound(value="0", is_strict=False)
    max_version: VersionBound = VersionBound(value="0", is_strict=False)
    from_editions: list[str] = field(default_factory=partial(list, ("community",)))


@dataclass(slots=True)
class UpgradeDefinition:
    # Description
    name: str
    display_name: str = ""
    description: str = ""

    # Details
    # should be set, defaults are tricky
    restrictions: UpgradeRestrictions = field(default_factory=UpgradeRestrictions)
    # improve typing here, it should be similar/the same as with action
    # ;; also how is it calculated??
    state_available: str | list = field(default_factory=list)
    state_on_success: str = ""

    # Related objects
    action: ActionDefinition | None = None


class License(NamedTuple):
    status: Literal["absent", "accepted", "unaccepted"] = "absent"
    path: str = ""
    # looks like hash is not required for anything than storing in db?
    # hash: str = ""


@dataclass(slots=True)
class Definition(GeneralObjectDescription):
    # Essentials
    type: str
    # how version is defined in component since it's non-nullable char field in db?
    version: str
    name: str

    # Details
    display_name: str = ""
    description: str = ""
    edition: str = "community"
    license: License = field(default_factory=partial(License))
    monitoring: Literal["active", "passive"] = "active"
    allow_maintenance_mode: bool = False
    config_group_customization: bool = False
    flag_autogeneration: dict = field(default_factory=partial(dict, adcm_outdated_config=False))

    # Dependencies
    required: bool = False
    requires: list[dict] = field(default_factory=list)
    bound_to: dict = field(default_factory=dict)
    constraint: list = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    imports: list[dict] = field(default_factory=list)

    # Related Objects
    config: ConfigDefinition | None = None
    actions: list[ActionDefinition] = field(default_factory=list)
    upgrades: list[UpgradeDefinition] = field(default_factory=list)

    # Misc
    path: str = "."
    adcm_min_version: str = ""
    venv: Literal["default", "2.9"] = "default"
    shared: bool = False


BundleDefinitionKey: TypeAlias = tuple[str] | tuple[Literal["service"], str] | tuple[Literal["component"], str, str]
DefinitionsMap: TypeAlias = dict[BundleDefinitionKey, Definition]
