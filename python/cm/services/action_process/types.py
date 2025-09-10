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

from enum import Enum
from typing import Any, Literal
from uuid import UUID

from core.bundle_alt.schema import ActionProcessStage
from core.job.types import StepType
from core.types import ActionProcessID, ActionProcessStepID, ADCMCoreType, ObjectID
from pydantic import BaseModel, ConfigDict, Field


class ProcessState(str, Enum):
    CREATED = "created"
    BROKEN = "broken"
    COMPLETED = "completed"


class ProcessStepState(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    BROKEN = "broken"


class ProcessUpdateDTO(BaseModel):
    sync_key: UUID | None = None
    current_step: ActionProcessID | None = None
    last_completed_step: ActionProcessStepID | None = None
    flow_spec: list[ActionProcessStage] | None = None


class StepUpdateDTO(BaseModel):
    step_spec: Any = None
    state: ProcessStepState | None = None


class ActionProcess(BaseModel):
    id: ActionProcessID
    sync_key: UUID
    object_id: ObjectID
    object_type: ADCMCoreType
    flow_spec: list[ActionProcessStage] = Field(..., min_length=1)
    current_step_id: ActionProcessStepID | None = None
    last_completed_step_id: ActionProcessStepID | None = None


class Step(BaseModel):
    id: ActionProcessStepID
    process_id: ActionProcessID
    name: str
    display_name: str
    step_spec: Any = None
    type: Literal[StepType.CONFIGURATION, StepType.OPERATION]
    state: ProcessStepState

    model_config = ConfigDict(extra="allow", use_enum_values=True)

    @property
    def is_render_required(self) -> bool:
        return self.step_spec is None


class DBPrototypeConfig(BaseModel):
    type: str
    name: str
    subname: str
    display_name: str
    description: str
    default: Any
    required: bool
    limits: dict
    ui_options: dict
    group_customization: bool
    ansible_options: dict


class SerializedPrototypeConfigs(BaseModel):
    configs: list[DBPrototypeConfig] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")
