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

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from core.bundle_alt.schema import ActionProcessStage
from core.job.types import StepType
from core.types import ActionProcessID, ActionProcessStepID, ADCMCoreType, ObjectID, TaskID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import TypedDict
import core

from cm.services.action_process.schema_validation import HostComponentMapDelta


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


class _ConfigAttr(TypedDict):
    config: dict
    attr: dict


class MappingInputDTO(BaseModel):
    delta: HostComponentMapDelta
    cumulative_delta: HostComponentMapDelta | None = None


class StepInputDTO(BaseModel):
    configuration: core.config.Configuration | None = None
    job_id: TaskID | None = None
    mapping: MappingInputDTO | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def validate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            config_specified = "configuration" in data and data.get("configuration") is not None
            task_specified = "job_id" in data and data.get("job_id") is not None
            mapping_specified = "mapping" in data and data.get("mapping") is not None

            specified_fields = [config_specified, task_specified, mapping_specified]
            num_specified = sum(specified_fields)

            if num_specified != 1:
                raise ValueError('Exactly one of ("configuration", "job_id", "mapping") must be specified.')

        return data


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
    type: StepType
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
