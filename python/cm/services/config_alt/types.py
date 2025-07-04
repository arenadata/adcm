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
from enum import Enum
from typing import Any, Iterable, Literal, TypeAlias, TypeVar

from core.types import ConfigID, CoreObjectDescriptor, HostGroupOfObject, ObjectID
from typing_extensions import Self

# !===== Basic Types =====!

ParameterFullName: TypeAlias = str
"""
"Flat" name for nested fields, each level will start with `/`.
Elements at "root" of configuration will be named like `"/param"`, `"/group"`,
and elements inside groups `"/groupname/param"`.
"""

ParameterLevelName: TypeAlias = str
"""
Parameter technical name, unique inside one config hierarchy level (root or group).
Doesn't contain `/`, just name from bundle.
"""

ROOT_PREFIX = "/"
"""
Prefix to put before first level name
"""


def ensure_full_name(name: str) -> ParameterFullName:
    if not name.startswith(ROOT_PREFIX):
        return f"{ROOT_PREFIX}{name}"

    return name


def full_name_to_level_names(full: ParameterFullName) -> tuple[ParameterLevelName, ...]:
    return tuple(filter(bool, full.split("/")))


def level_names_to_full_name(levels: Iterable[ParameterLevelName]) -> ParameterFullName:
    return ensure_full_name("/".join(levels))


def level_names_to_full_name_safe(levels: Iterable[ParameterLevelName | None]) -> ParameterFullName:
    non_empty_strings: Iterable[ParameterLevelName] = (level for level in levels if level)
    return level_names_to_full_name(non_empty_strings)


def full_name_to_file_name(full: ParameterFullName) -> str:
    """
    Convert full name of parameter to "own name" of file (indifferent to object)
    """

    levels = full_name_to_level_names(full)
    if len(levels) == 1:
        # backward compatibility
        # first-leveled parameters' names ended with "."
        return f"{levels[0]}."

    return ".".join(levels)


class ParameterType(str, Enum):
    # Basic Types

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"

    LIST = "list"
    MAP = "map"
    JSON = "json"

    # Custom Types

    OPTION = "option"
    VARIANT = "variant"

    STRUCTURE = "structure"


@dataclass(slots=True)
class ConfigOwnerObjectInfo:
    state: str


@dataclass(slots=True)
class ConfigOwner:
    descriptor: CoreObjectDescriptor
    info: ConfigOwnerObjectInfo


@dataclass(slots=True)
class ConfigGroupOwner:
    descriptor: HostGroupOfObject
    info: ConfigOwnerObjectInfo


# !===== Configuration =====!


@dataclass(slots=True)
class Attributes:
    is_active: bool | None = None
    is_synced: bool | None = None

    @property
    def activation(self) -> bool:
        return self.is_active is not None

    @property
    def synchronization(self) -> bool:
        return self.is_synced is not None

    def __post_init__(self) -> None:
        if not (self.activation or self.synchronization):
            message = "Attributes should have either activation or synchronization info"
            raise RuntimeError(message)


ParameterValue = TypeVar("ParameterValue")


@dataclass(slots=True)
class Configuration:
    values: dict[ParameterLevelName, Any]
    attributes: dict[ParameterFullName, Attributes]
    description: str = ""


# Repo related


@dataclass(slots=True)
class RepoConfigIdentifier:
    config_id: ConfigID
    """
    Identifier of this config record
    """

    config_object_link: ObjectID
    """
    Identifier of object that links object itself and records.
    Is vulnerable to DB schema changes.
    """


@dataclass(slots=True)
class MainConfiguration:
    identifier: RepoConfigIdentifier
    owner: CoreObjectDescriptor
    config: Configuration


@dataclass(slots=True)
class HostGroupConfiguration(MainConfiguration):
    group_id: ObjectID


# !===== Specification =====!


@dataclass(slots=True)
class Identifier:
    name: ParameterLevelName
    full: ParameterFullName


@dataclass(slots=True)
class ExtraProperties:
    display_name: str
    description: str = ""
    ui_options: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WritableRule:
    writable: Literal["any"] | list[str]


@dataclass(slots=True)
class ReadOnlyRule:
    read_only: Literal["any"] | list[str]


@dataclass(slots=True)
class Activation:
    edit_rule: WritableRule | ReadOnlyRule
    is_desyncable: bool
    is_active_by_default: bool


@dataclass(slots=True)
class ParameterGroup:
    identifier: Identifier
    extra: ExtraProperties
    activation: Activation | None

    @property
    def is_activatable(self) -> bool:
        return self.activation is not None


@dataclass(slots=True)
class _SimpleParameterBase:
    identifier: Identifier
    edit_rule: WritableRule | ReadOnlyRule
    extra: ExtraProperties
    is_required: bool
    is_desyncable: bool
    is_secret: bool


@dataclass(slots=True)
class StringParameter(_SimpleParameterBase):
    supports_multiline: bool
    as_file: bool
    pattern: str | None = None
    type: Literal[ParameterType.STRING] = ParameterType.STRING


@dataclass(slots=True)
class NumberParameter(_SimpleParameterBase):
    is_float: bool
    min: float | int | None = None
    max: float | int | None = None
    type: Literal[ParameterType.NUMBER] = ParameterType.NUMBER


@dataclass(slots=True)
class BooleanParameter(_SimpleParameterBase):
    type: Literal[ParameterType.BOOLEAN] = ParameterType.BOOLEAN


@dataclass(slots=True)
class MapParameter(_SimpleParameterBase):
    type: Literal[ParameterType.MAP] = ParameterType.MAP


@dataclass(slots=True)
class ListParameter(_SimpleParameterBase):
    type: Literal[ParameterType.LIST] = ParameterType.LIST


@dataclass(slots=True)
class JSONParameter(_SimpleParameterBase):
    type: Literal[ParameterType.JSON] = ParameterType.JSON


@dataclass(slots=True)
class OptionParameter(_SimpleParameterBase):
    options: dict[str, Any]
    type: Literal[ParameterType.OPTION] = ParameterType.OPTION


@dataclass(slots=True)
class VariantParameter(_SimpleParameterBase):
    source: Literal["config", "inline", "builtin"]
    is_strict: bool
    payload: dict[str, Any]
    type: Literal[ParameterType.VARIANT] = ParameterType.VARIANT

    def __post_init__(self) -> None:
        # validate source-payload pair and normalize fields if required
        if self.source == "config":
            param_name = self.payload.get("name")
            if not param_name:
                message = 'Variant of type "config" must have "name" specificed'
                raise ValueError(message)

            self.payload["name"] = ensure_full_name(param_name)


@dataclass(slots=True)
class StructureParameter(_SimpleParameterBase):
    yspec: dict
    type: Literal[ParameterType.STRUCTURE] = ParameterType.STRUCTURE


SimpleParameter: TypeAlias = (
    StringParameter
    | NumberParameter
    | BooleanParameter
    | MapParameter
    | ListParameter
    | JSONParameter
    | OptionParameter
    | VariantParameter
    | StructureParameter
)


@dataclass(slots=True)
class SpecAttributes:
    """
    "Special" properties of parameters that's worth storing separately
    and may affect certain scenarios.
    """

    activatable_groups: set[ParameterFullName] = field(default_factory=set)
    """
    Names of parameter groups that can be (de)activated
    """

    desyncable_parameters: set[ParameterFullName] = field(default_factory=set)
    """
    Names of parameters (including groups) that can be desynced from main configuration
    when working with configuration host groups
    """


@dataclass(slots=True)
class SpecDependencies:
    """
    Configuration may be self-sufficient and may have internal and external dependencies.

    Internal dependencies are ones between values of config itself.
    Their consistency doesn't require anything but "current" configuraiton.
    Major example: `variant` parameter with `config` source.

    External dependencies are ones relating on state of objects in ADCM.
    Their consistency requires additional context retrieval of which may be costly.
    Major example: `variant` parameter with `builtin` source.
    """

    internal: dict[ParameterFullName, set[ParameterFullName]] = field(default_factory=dict)
    """
    Keys are parameters on which others depends.
    Values are dependant parameters.

    Example:
        Variant parameter `/aqua` has list typed parameter `/liquid` as it's `config` source.
        Their dependency in `internal` will look like `{"/liquid": {"/aqua"}}`.

        The reason for that is that when dependant (`/aqua`) parameter is changed,
        their dependency (`/liquid`) can be easily detected from dependant specification.
        On the contrary, `/liquid` specification won't contain information about dependant parameters,
        so in case when `/liquid` is changed we will be able
        to ensure that `/aqua`'s value is consistent with `/liquid`.
    """

    external: set[ParameterFullName] = field(default_factory=set)


@dataclass(slots=True)
class SpecHierarchyLevel:
    fields: list[ParameterLevelName] = field(default_factory=list)
    child_groups: dict[ParameterLevelName, Self] = field(default_factory=dict)


@dataclass(slots=True)
class FullSpec:
    """
    Configuration Specification in ADCM-oriented format (as opposed to "raw bundle DSL format").

    Original format can be restored from this one thou (except defaults).

    Note that "defaults" information isn't part of Specification.
    Reasons for that:
        - in most cases defaults aren't required
        - they can be great in size => no reason to take them everywhere the spec goes
    """

    hierarchy: SpecHierarchyLevel = field(default_factory=SpecHierarchyLevel)
    groups: dict[ParameterFullName, ParameterGroup] = field(default_factory=dict)
    parameters: dict[ParameterFullName, SimpleParameter] = field(default_factory=dict)
    attributes: SpecAttributes = field(default_factory=SpecAttributes)
    dependencies: SpecDependencies = field(default_factory=SpecDependencies)
