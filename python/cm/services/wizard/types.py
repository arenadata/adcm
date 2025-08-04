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
from typing import Any, Literal

from core.bundle_alt.schema import WizardStage, _WizardNames
from core.types import ActionProcessID, ActionProcessStepID, ADCMCoreType, ObjectID
from pydantic import BaseModel, ConfigDict, Field


class ProcessState(str, Enum):
    CREATED = "created"
    BROKEN = "broken"
    REVOKED = "revoked"
    FINISHED = "finished"


class ProcessOperationType(str, Enum):
    SUBMIT = "submit"
    COMPLETE = "complete"


@dataclass(slots=True)
class ProcessToChangeDTO:
    id: ActionProcessID
    sync_key: str


class StepUpdateDTO(BaseModel):
    step_spec: Any = None


class StepType(str, Enum):
    CONFIGURATION = "configuration"
    OPERATION = "operation"


class ActionProcess(BaseModel):
    id: ActionProcessID
    obejct_id: ObjectID
    object_type: ADCMCoreType
    flow_spec: list[WizardStage] = Field(..., min_length=1)


class Step(_WizardNames):
    id: ActionProcessStepID
    process_id: ActionProcessID
    display_name: str
    step_spec: Any = None
    type: Literal[StepType.CONFIGURATION, StepType.OPERATION]

    model_config = ConfigDict(extra="allow")

    @property
    def is_render_required(self) -> bool:
        return self.step_spec is None
