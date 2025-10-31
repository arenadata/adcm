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
from typing import Any, TypeAlias

from core.types import ConfigID, CoreObjectDescriptor

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

PARAMETER_NAME_SEPARATOR = "/"
PARAMETER_NAME_ROOT_PREFIX = "/"
"""
Prefix to put before first level name
"""

PARAMETER_FILE_NAME_SEPARATOR = "."


@dataclass(slots=True)
class ConfigOwnerObjectInfo:
    state: str


@dataclass(slots=True)
class ConfigOwner:
    descriptor: CoreObjectDescriptor
    info: ConfigOwnerObjectInfo


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
            raise ValueError(message)


ConfigValues: TypeAlias = dict[ParameterLevelName, Any]
ConfigFlatValues: TypeAlias = dict[ParameterFullName, Any]
ConfigAttrs: TypeAlias = dict[ParameterFullName, Attributes]

Defaults: TypeAlias = dict[ParameterFullName, Any]


@dataclass(slots=True)
class Configuration:
    values: ConfigValues = field(default_factory=dict)
    attributes: ConfigAttrs = field(default_factory=dict)


@dataclass(slots=True)
class ConfigurationWithID(Configuration):
    # keep that way while it's direct dataclass descendant of `Configuration`
    # for inheritance simplicity
    id: ConfigID = 0


@dataclass(slots=True)
class FlatConfiguration:
    values: ConfigFlatValues = field(default_factory=dict)
    attributes: ConfigAttrs = field(default_factory=dict)
