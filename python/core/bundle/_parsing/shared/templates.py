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
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import ConfigDict, Discriminator, Field, Tag

from core.bundle._parsing.shared.model import BundleModel
from core.templates import RenderEngineType


@dataclass(slots=True)
class PythonEngine:
    type: Literal[RenderEngineType.PYTHON]


@dataclass(slots=True)
class Jinja2Engine:
    type: Literal[RenderEngineType.JINJA2]


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


class Jinja2Template(_TemplateBaseModel):
    engine: Jinja2Engine
    file: TemplateFile


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
