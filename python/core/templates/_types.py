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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, field_serializer, field_validator


class RenderEngineType(str, Enum):
    PYTHON = "python"
    JINJA2 = "jinja2"


# Basic Public Interface


class TemplateRenderer(ABC):
    @abstractmethod
    def can_be_rendered(self) -> bool:
        ...

    @abstractmethod
    def render(self, context: dict) -> Any:
        ...


# Renderer Arguments


class TemplateFile(BaseModel):
    path: Path

    # validators/serializers needed to read string path from bundle definition and dump data in json-compatible format
    @field_validator("path", mode="before")
    @classmethod
    def string_path_to_path_cls(cls, value: Any) -> Any:
        if isinstance(value, str):
            return Path(value)

        return value

    @field_serializer("path", when_used="always")
    def path_to_string(self, path: Path) -> str:
        return str(path)


class TemplateFileWithEntrypoint(TemplateFile):
    entrypoint: str


# Renderer Environments


@dataclass(slots=True)
class RendererEnv:
    discovery_root: Path


# Template engines


class PythonEngine(BaseModel):
    type: Literal[RenderEngineType.PYTHON]


class Jinja2Engine(BaseModel):
    type: Literal[RenderEngineType.JINJA2]


# Templates


class _TemplateBaseModel(BaseModel, ABC):
    pass


class PythonTemplate(_TemplateBaseModel):
    engine: PythonEngine
    file: TemplateFileWithEntrypoint


class Jinja2Template(_TemplateBaseModel):
    engine: Jinja2Engine
    file: TemplateFile


# Template Generics


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
Template = Annotated[
    Annotated[Jinja2Template, Tag("jinja2")] | Annotated[PythonTemplate, Tag("python")],
    Field(
        discriminator=Discriminator(
            engine_type_discriminator, custom_error_type="invalid_template", custom_error_message=_discriminator_err_msg
        )
    ),
]


class _OneOfTemplates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template: Template


def parse_template(raw: dict) -> Template:
    serialized = _OneOfTemplates.model_validate({"template": raw})
    return serialized.template
