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
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, Field

from core.config._names import ensure_full_name
from core.config._types import ParameterFullName, ParameterLevelName


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
class Identifier:
    name: ParameterLevelName
    full: ParameterFullName


@dataclass(slots=True)
class ExtraProperties:
    display_name: str = ""
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
    edit_rule: WritableRule | ReadOnlyRule = field(default_factory=lambda: WritableRule(writable="any"))
    is_desyncable: bool = False
    is_active_by_default: bool = False


class ParameterGroup(BaseModel):
    identifier: Identifier
    extra: ExtraProperties = Field(default_factory=ExtraProperties)
    activation: Activation | None = None

    @property
    def is_activatable(self) -> bool:
        return self.activation is not None


class _SimpleParameterBase(BaseModel):
    identifier: Identifier
    edit_rule: WritableRule | ReadOnlyRule = Field(default_factory=lambda: WritableRule(writable="any"))
    extra: ExtraProperties = Field(default_factory=ExtraProperties)
    is_required: bool = True
    is_desyncable: bool = False


class StringParameter(_SimpleParameterBase):
    supports_multiline: bool = False
    as_file: bool = False
    pattern: str | None = None
    is_secret: bool = False
    type: Literal[ParameterType.STRING] = ParameterType.STRING


class NumberParameter(_SimpleParameterBase):
    is_float: bool
    min: float | int | None = None
    max: float | int | None = None
    type: Literal[ParameterType.NUMBER] = ParameterType.NUMBER


class BooleanParameter(_SimpleParameterBase):
    type: Literal[ParameterType.BOOLEAN] = ParameterType.BOOLEAN


class MapParameter(_SimpleParameterBase):
    is_secret: bool = False
    type: Literal[ParameterType.MAP] = ParameterType.MAP


class ListParameter(_SimpleParameterBase):
    type: Literal[ParameterType.LIST] = ParameterType.LIST


class JSONParameter(_SimpleParameterBase):
    type: Literal[ParameterType.JSON] = ParameterType.JSON


class OptionParameter(_SimpleParameterBase):
    options: dict[str, Any]
    type: Literal[ParameterType.OPTION] = ParameterType.OPTION


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
