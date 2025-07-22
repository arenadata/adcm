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


@dataclass(slots=True)
class TemplateFileWithEntrypoint(TemplateFile):
    entrypoint: str


# Renderer Environments


@dataclass(slots=True)
class RendererEnv:
    discovery_root: Path


# Python Template


@dataclass(slots=True)
class PythonEngine:
    type: Literal[RenderEngineType.PYTHON] = RenderEngineType.PYTHON


@dataclass(slots=True)
class PythonTemplate:
    engine: PythonEngine
    file: TemplateFileWithEntrypoint


# Jinja2 Template


@dataclass(slots=True)
class Jinja2Engine:
    type: Literal[RenderEngineType.JINJA2] = RenderEngineType.JINJA2


@dataclass(slots=True)
class Jinja2Template:
    engine: Jinja2Engine
    file: TemplateFile
