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
from typing import Any, Literal

from pydantic import BaseModel, field_serializer


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


@dataclass(slots=True)
class TemplateFile:
    path: Path

    @field_serializer("path", when_used="always")
    def path_to_string(self, path: Path) -> str:
        return str(path)


@dataclass(slots=True)
class TemplateFileWithEntrypoint(TemplateFile):
    entrypoint: str


# Renderer Environments


@dataclass(slots=True)
class RendererEnv:
    discovery_root: Path


# Template engines


@dataclass(slots=True)
class PythonEngine:
    type: Literal[RenderEngineType.PYTHON]


@dataclass(slots=True)
class Jinja2Engine:
    type: Literal[RenderEngineType.JINJA2]


# Templates


class PythonTemplate(BaseModel):
    engine: PythonEngine
    file: TemplateFileWithEntrypoint


class Jinja2Template(BaseModel):
    engine: Jinja2Engine
    file: TemplateFile


# Template Generics


Template = Jinja2Template | PythonTemplate


def parse_template(raw: dict) -> Template:
    try:
        type_ = RenderEngineType(raw["engine"]["type"])
    except KeyError as e:
        message = f"Failed to detect template engine: {raw}"
        raise ValueError(message) from e
    except ValueError as e:
        message = f"Unknown engine type: {raw}"
        raise ValueError(message) from e

    match type_:
        case RenderEngineType.JINJA2:
            model_ = Jinja2Template
        case RenderEngineType.PYTHON:
            model_ = PythonTemplate

    return model_.model_validate(raw)
