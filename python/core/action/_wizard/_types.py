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
from enum import Enum
from typing import Any, Generic, Literal, TypeAlias, TypeVar

from core import config, templates
from core.action import JobSpec
from core.mapping import MappingOperation, MappingPair, MappingRule

ProcessID: TypeAlias = int

StageName: TypeAlias = str

StepID: TypeAlias = int
StepName: TypeAlias = str
StepFullName: TypeAlias = tuple[StageName, StepName]


class ProcessOperationType(str, Enum):
    # on step
    SUBMIT_STEP = "submit_step"
    RESET_STEP = "reset_step"
    # on process
    COMPLETE = "complete"


class StepType(str, Enum):
    CONFIGURATION = "configuration"
    MAPPING = "mapping"
    OPERATION = "operation"


class ProcessState(str, Enum):
    CREATED = "created"
    BROKEN = "broken"
    COMPLETED = "completed"


class StepState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    BROKEN = "broken"


ConfigStepSpec: TypeAlias = tuple[config.spec.FullSpec, config.Defaults]
ConfigStepData: TypeAlias = config.Configuration


OperationStepSpec: TypeAlias = list[JobSpec]

# use cases are unknown for now
OperationStepData: TypeAlias = Any

MappingStepSpec: TypeAlias = list[MappingRule]

Delta = dict[MappingOperation, list[MappingPair]]


@dataclass(slots=True)
class MappingStepData:
    delta: Delta
    cumulative: Delta


ST = TypeVar("ST", bound=StepType)
SpecT = TypeVar("SpecT", bound=ConfigStepSpec | list[JobSpec] | list[MappingRule] | None)


@dataclass(slots=True)
class _Step(Generic[ST, SpecT]):
    id: StepID
    full_name: StepFullName
    state: StepState

    type: ST
    spec: SpecT | None


StepT = TypeVar("StepT", bound=_Step)


@dataclass(slots=True)
class ConfigStep(_Step[Literal[StepType.CONFIGURATION], ConfigStepSpec]):
    ...


@dataclass(slots=True)
class OperationStep(_Step[Literal[StepType.OPERATION], OperationStepSpec]):
    ...


@dataclass(slots=True)
class MappingStep(_Step[Literal[StepType.MAPPING], MappingStepSpec]):
    ...


Step: TypeAlias = ConfigStep | OperationStep | MappingStep

ConfigStepWithData: TypeAlias = tuple[ConfigStep, ConfigStepData | None]
OperationStepWithData: TypeAlias = tuple[OperationStep, OperationStepData | None]
MappingStepWithData: TypeAlias = tuple[MappingStep, MappingStepData | None]

StepWithData: TypeAlias = ConfigStepWithData | OperationStepWithData | MappingStepWithData
StepWithTemplate: TypeAlias = tuple[Step, templates.Template]

# "Full" Objects


@dataclass(slots=True)
class OperationUIOptions:
    button_name: str


@dataclass(slots=True, kw_only=True)
class StepExtra:
    display_name: str
    description: str = ""


@dataclass(slots=True)
class OperationStepExtra(StepExtra):
    ui_options: OperationUIOptions


M = TypeVar("M", bound=StepExtra | OperationStepExtra)


@dataclass(slots=True)
class _StepDefinition(Generic[ST, M]):
    type: ST
    template: templates.Template
    name: str
    extra: M


@dataclass(slots=True)
class ConfigStepDefinition(_StepDefinition[StepType.CONFIGURATION, StepExtra]):
    ...


@dataclass(slots=True)
class OperationStepDefinition(_StepDefinition[StepType.OPERATION, OperationStepExtra]):
    ...


@dataclass(slots=True)
class MappingStepDefinition(_StepDefinition[StepType.MAPPING, StepExtra]):
    ...


StepDefinition: TypeAlias = ConfigStepDefinition | OperationStepDefinition | MappingStepDefinition


@dataclass(slots=True)
class StageExtra:
    display_name: str
    description: str = ""


@dataclass(slots=True)
class Stage:
    name: str
    extra: StageExtra
    steps: list[StepDefinition]
