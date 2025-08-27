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

from core.bundle_alt.schema import ActionProcessStage, _WizardNames
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
    last_completed_step: ActionProcessStepID | None = None


class StepUpdateDTO(BaseModel):
    step_spec: Any = None
    state: ProcessStepState | None = None


class ActionProcess(BaseModel):
    id: ActionProcessID
    object_id: ObjectID
    object_type: ADCMCoreType
    flow_spec: list[ActionProcessStage] = Field(..., min_length=1)
    sync_key: UUID


class Step(_WizardNames):
    id: ActionProcessStepID
    process_id: ActionProcessID
    display_name: str
    step_spec: Any = None
    type: Literal[StepType.CONFIGURATION, StepType.OPERATION]
    state: ProcessStepState

    model_config = ConfigDict(extra="allow")

    @property
    def is_render_required(self) -> bool:
        return self.step_spec is None
