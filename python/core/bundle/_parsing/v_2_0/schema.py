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
from functools import partial
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    model_validator,
)

from core.bundle._parsing.shared.templates import Template
from core.bundle._parsing.shared.validation import (
    min_less_than_max,
    patch_masking,
    template_script_is_correct_path,
    validate_name,
)

Version: TypeAlias = int | float | str
Venv: TypeAlias = Annotated[
    Literal["default", "2.8", "2.9", "2.16"] | None,
    Field(default=None),
    # fixme cast is too broad, but required since round trip load
    BeforeValidator(lambda x: str(x) if x is not None else x),
]
Monitoring: TypeAlias = Annotated[Literal["active", "passive"] | None, Field(default=None)]

Name: TypeAlias = Annotated[str, AfterValidator(validate_name)]

WizardTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="wizard_template"))
]
ScriptsTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="scripts_template"))
]
ConfigTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="config_template"))
]
HCTemplate = Annotated[Template, AfterValidator(partial(template_script_is_correct_path, field_name="hc_template"))]


# States


@dataclass(slots=True)
class StatesSchema:
    available: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    on_success: Annotated[str | None, Field(default=None)]
    on_fail: Annotated[str | None, Field(default=None)]


@dataclass(slots=True)
class AvailabilitySchema:
    available: Literal["any"] | list[str]


@dataclass(slots=True)
class UnAvailabilitySchema:
    unavailable: Literal["any"] | list[str]


@dataclass(slots=True)
class MaskingSchema:
    state: Annotated[AvailabilitySchema | UnAvailabilitySchema | None, Field(default=None)]
    multi_state: Annotated[AvailabilitySchema | UnAvailabilitySchema | None, Field(default=None)]


Masking = Annotated[MaskingSchema | None, Field(default=None), BeforeValidator(patch_masking)]


@dataclass(slots=True)
class VersionsSchema:
    min: Annotated[Version | None, Field(default=None)]
    max: Annotated[Version | None, Field(default=None)]
    min_strict: Annotated[Version | None, Field(default=None)]
    max_strict: Annotated[Version | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_min_max_stricts(self):
        if self.min is not None and self.min_strict is not None:
            raise ValueError("min and min_strict can not be used simultaneously in versions")

        if self.max is not None and self.max_strict is not None:
            raise ValueError("max and max_strict can not be used simultaneously in versions")

        return self


@dataclass(slots=True)
class FlagAutogenerationSchema:
    enable_outdated_config: bool


@dataclass(slots=True)
class ServiceRequiresSchema:
    service: str
    component: Annotated[str | None, Field(default=None)]


@dataclass(slots=True)
class ComponentRequiresSchema:
    service: Annotated[str | None, Field(default=None)]
    component: Annotated[str | None, Field(default=None)]


@dataclass(slots=True)
class BoundSchema:
    service: str
    component: str


@dataclass(slots=True)
class ImportSchema:
    versions: Annotated[VersionsSchema | None, Field(default=None), AfterValidator(min_less_than_max)]
    required: Annotated[bool | None, Field(default=None)]
    multibind: Annotated[bool | None, Field(default=None)]
    default: Annotated[list[str] | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_default_and_required(self):
        if self.required and self.default:
            raise ValueError("Import can't have default and be required in the same time")

        return self


License = Annotated[str | None, Field(default=None)]

Export = Annotated[str | list[str] | None, Field(default=None)]
Imports = Annotated[dict[str, ImportSchema] | None, Field(alias="import", default=None)]

FlagAutogeneration = Annotated[FlagAutogenerationSchema | None, Field(default=None)]
