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
from typing import Any, Callable, Literal, NamedTuple, TypeAlias, TypedDict

from typing_extensions import Self

from core.config.constants import SYSTEM_CONFIG_CREATOR
from core.types import ConfigHostGroupDesc, ConfigID, CoreObjectDescriptor, PrototypeID

EncryptFunc: TypeAlias = Callable[[str], str]
DecryptFunc: TypeAlias = Callable[[str], str]

ParameterFullName: TypeAlias = str
"""
"Flat" name for nested fields, each level will start with `/`.
Elements at "root" of configuration will be named like `"/param"`, `"/group"`,
and elements inside groups `"/groupname/param"`.
"""

FullDisplayName: TypeAlias = str
"""
"Flat" display name for nested fields.
Elements at "root" of configuration will be named like `"/Param"`, `"/Group Name"`,
and elements inside groups `"/Group Name/Param"`.
If `display_name` is not defined for a parameter or group, its technical name will be used
to build the full display name, for example: `"/Group Name/nested/Param"`.
"""

ParameterLevelName: TypeAlias = str
"""
Parameter technical name, unique inside one config hierarchy level (root or group).
Doesn't contain `/`, just name from bundle.
"""

PARAMETER_NAME_SEPARATOR = "/"
PARAMETER_NAME_ROOT_PREFIX = "/"
"""
Prefix to put before first level name
"""

PARAMETER_FILE_NAME_SEPARATOR = "."


@dataclass(slots=True)
class ConfigOwner:
    descriptor: CoreObjectDescriptor
    state: str


@dataclass(slots=True)
class HostGroupConfigOwner:
    descriptor: CoreObjectDescriptor
    state: str
    group: ConfigHostGroupDesc


@dataclass(slots=True)
class Attributes:
    # todo: inconvenient design
    #       always having to check both synchronization and is_synced
    #       (same for is_active);
    #       maybe make regular class with protected values
    #       and make reasonable defaults available via properties;
    #       on the other hand, it only makes sense for `synced`
    #       when `is_active` makes sense only for activatable groups
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
            raise ValueError(message)


ConfigParameterValue = Any

ConfigValues: TypeAlias = dict[ParameterLevelName, ConfigParameterValue]
"""
Config values in "nested" format,
e.g. `{"a": {"b": {"c": 4}}}` instead of `{"/a/b/c": 4}` (flat format)
"""

ConfigFlatValues: TypeAlias = dict[ParameterFullName, ConfigParameterValue]
ConfigAttrs: TypeAlias = dict[ParameterFullName, Attributes]
RevisionDiff: TypeAlias = dict[Literal["diff", "attr_diff"], dict]
ConfigDict: TypeAlias = dict


class RelatedConfigs(TypedDict):
    object_id: int
    object_type: str
    prototype_id: int
    primary_config_id: int


class ConfigCoreObjectWithPrototype(NamedTuple):
    object: CoreObjectDescriptor
    prototype_id: PrototypeID
    config_id: ConfigID


@dataclass(slots=True)
class Defaults:
    """
    Various defaults for object's configuration / specification if "flat" format:
    - `values` are parameters-only default values, may include `None`
    - `activation` has "active" status default for activatable groups
    - `selection` has default "branch" for selection, may be `None`

    Expectations and restrictions:
    - No specific order in keys
    - Presense of all parameters isn't guaranteed
    - Defaults are correct types:
      it is expected that constructor function will provide correct defaults (e.g. `True` for `bool`, not `"True"`);
      which means consumer shouldn't "guess" or parse present values any further.
    - Consider this type as "known defaults", not "ready to use" default configuration:
      keys are presented for all possible known defaults, which doesn't mean they may be correct config by itself.
    """

    values: dict[ParameterFullName, ConfigParameterValue] = field(default_factory=dict)
    activation: dict[ParameterFullName, bool] = field(default_factory=dict)
    selection: dict[ParameterFullName, str | None] = field(default_factory=dict)


@dataclass(slots=True)
class ConfigurationExtraInfo:
    description: str
    created_by: str


@dataclass(slots=True)
class Configuration:
    values: ConfigValues = field(default_factory=dict)
    attributes: ConfigAttrs = field(default_factory=dict)


@dataclass(slots=True)
class ConfigurationWithInfo(Configuration):
    # keep that way while it's direct dataclass descendant of `Configuration`
    # for inheritance simplicity
    id: ConfigID = 0
    extra_info: ConfigurationExtraInfo = ConfigurationExtraInfo(description="", created_by=SYSTEM_CONFIG_CREATOR)


@dataclass(slots=True)
class FlatConfiguration:
    values: ConfigFlatValues = field(default_factory=dict)
    attributes: ConfigAttrs = field(default_factory=dict)


class ChangeType(str, Enum):
    VALUE = "value"
    ACTIVATION = "activation"
    SELECTION = "selection"
    SYNCHRONIZATION = "synchronization"


@dataclass(slots=True)
class Change:
    parameter: ParameterFullName
    type: ChangeType
    # keep bool in here for "attrs", thou I doubt it'll require changing in near future
    old: ConfigParameterValue | bool | None
    new: ConfigParameterValue | bool | None


@dataclass(slots=True)
class ChangeRequest:
    type: Literal[ChangeType.VALUE, ChangeType.ACTIVATION, ChangeType.SELECTION]
    parameter: ParameterFullName
    value: Any

    @classmethod
    def for_value(cls, name: ParameterFullName, value: Any) -> Self:
        return cls(type=ChangeType.VALUE, parameter=name, value=value)

    @classmethod
    def for_activation_attribute(cls, name: ParameterFullName, value: bool) -> Self:
        return cls(type=ChangeType.ACTIVATION, parameter=name, value=value)

    @classmethod
    def for_group_selection(cls, name: ParameterFullName, value: str | None) -> Self:
        return cls(type=ChangeType.SELECTION, parameter=name, value=value)
