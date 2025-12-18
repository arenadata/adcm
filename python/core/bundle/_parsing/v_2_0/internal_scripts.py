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

from pydantic import Field, model_validator

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
@dataclass(slots=True)
class TypeBasedConfigApplyRule:
    type: Literal["adcm", "provider", "host", "cluster"]


@dataclass(slots=True)
class ServiceConfigApplyRule:
    type: Literal["service"]
    service_name: str


@dataclass(slots=True)
class ComponentConfigApplyRule:
    type: Literal["component"]
    service_name: str
    component_name: str


@dataclass(slots=True)
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
    changes: Annotated[list[ConfigApplyObject], Field(min_length=1)]

    @model_validator(mode="after")
    def ensure_unique_changes(self):
        seen = set()
        for change in self.changes:
            if change in seen:
                raise ValueError("Duplicate change detected in 'changes'")
            seen.add(change)
        return self
