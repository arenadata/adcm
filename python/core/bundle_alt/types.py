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
from pathlib import Path
from typing import Any, Literal, NamedTuple, Protocol, TypeAlias


class WithName(Protocol):
    name: str


class GeneralObjectDescription(Protocol):
    type: str
    name: str
    version: str | None


@dataclass(slots=True)
class Script:
    script_type: str
    script: str


@dataclass(slots=True)
class ActionDefinition(Script):
    type: str
    scripts: list[Script]
    hostcomponentmap: list
    jinja_scripts: str | None
    jinja_config: str | None


@dataclass(slots=True)
class UpgradeDefinition:
    name: str
    hostcomponentmap: list
    scripts: list[Script]


# alternative format for parameter key, should be moved to core.config
ParameterKey: TypeAlias = tuple[str, ...]


# copied from cm.services.config.spec for ADCM-6355
# should be removed later
class ConfigParamPlainSpec(NamedTuple):
    type: str
    key: ParameterKey
    display_name: str
    description: str

    # the problem is that here default is anything at all
    # yet after save-load to/from db it's str / None
    # => should be unified for both cases
    #    (IMO defaults should be stored separately)
    default: Any  # str
    limits: dict
    ui_options: dict
    required: bool

    group_customization: bool | None

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
    # todo implement: order and nested levels of config fields
    hierarchy = None


@dataclass(slots=True)
class Definition(GeneralObjectDescription):
    path: Path
    type: str
    name: str
    version: str | None
    requires: list[dict]
    bound_to: dict
    # make it a dict too
    actions: list[ActionDefinition]
    config: ConfigDefinition
    # specifics
    upgrades: list[UpgradeDefinition]
    export: list[str] | None
    import_: list[dict] | None
    constraint: list | None


BundleDefinitionKey: TypeAlias = tuple[str] | tuple[Literal["service"], str] | tuple[Literal["component"], str, str]
DefinitionsMap: TypeAlias = dict[BundleDefinitionKey, Definition]
