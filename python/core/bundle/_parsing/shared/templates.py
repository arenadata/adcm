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

from abc import ABC
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Discriminator, Field, Tag

from core import templates
from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.shared.validation import template_script_is_correct_path


@dataclass(slots=True)
class PythonEngine:
    type: Literal[templates.RenderEngineType.PYTHON]


@dataclass(slots=True)
class Jinja2Engine:
    type: Literal[templates.RenderEngineType.JINJA2]


@dataclass(slots=True)
class TemplateFile:
    path: str


@dataclass(slots=True)
class TemplateFileWithEntrypoint(TemplateFile):
    entrypoint: str


class _TemplateBaseModel(BundleModel, ABC):
    model_config = ConfigDict(extra="forbid")


class PythonTemplate(_TemplateBaseModel):
    engine: PythonEngine
    file: TemplateFileWithEntrypoint

    def to_core_template(self, resolve_path: Callable[[str], Path]) -> templates.PythonTemplate:
        engine = templates.PythonEngine(type=templates.RenderEngineType.PYTHON)
        path = resolve_path(self.file.path)
        file_ = templates.TemplateFileWithEntrypoint(path=path, entrypoint=self.file.entrypoint)
        return templates.PythonTemplate(engine=engine, file=file_)


class Jinja2Template(_TemplateBaseModel):
    engine: Jinja2Engine
    file: TemplateFile

    def to_core_template(self, resolve_path: Callable[[str], Path]) -> templates.Jinja2Template:
        engine = templates.Jinja2Engine(type=templates.RenderEngineType.JINJA2)
        path = resolve_path(self.file.path)
        file_ = templates.TemplateFile(path=path)
        return templates.Jinja2Template(engine=engine, file=file_)


def engine_type_discriminator(value):
    if isinstance(value, dict):
        try:
            return value.get("engine", {}).get("type")
        except AttributeError:
            return None

    try:
        return value.engine.type
    except AttributeError:
        return None


_discriminator_err_msg = f'Expected {" | ".join(cls.__name__ for cls in _TemplateBaseModel.__subclasses__())} template'
_TemplateDiscriminator = Discriminator(
    engine_type_discriminator, custom_error_type="invalid_template", custom_error_message=_discriminator_err_msg
)

Template = Annotated[
    Annotated[Jinja2Template, Tag("jinja2")] | Annotated[PythonTemplate, Tag("python")],
    Field(discriminator=_TemplateDiscriminator),
]
# Template Examples

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
