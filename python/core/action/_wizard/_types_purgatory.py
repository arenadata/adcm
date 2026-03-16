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

from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core import config, mapping
from core.action._types import JobSpec
from core.action._wizard._types import ConfigStepSpec, MappingStepSpec, OperationStepSpec, Stage, StepState, StepType
from core.types import (
    ActionProcessID,
    ActionProcessStepID,
    ADCMCoreType,
    ExtraActionTargetType,
    ObjectID,
    TaskID,
)

ProcessStepState = StepState


class ProcessUpdateDTO(BaseModel):
    sync_key: UUID | None = None
    current_step: ActionProcessID | None = None
    last_completed_step: ActionProcessStepID | None = None
    flow_spec: list[dict] | None = None


class StepUpdateDTO(BaseModel):
    step_spec: Any = None
    state: ProcessStepState | None = None


@dataclass(slots=True, frozen=True)
class HCMappingRule:
    host_id: int
    component_id: int


class HostComponentMapDelta(BaseModel):
    add: list[HCMappingRule] = Field(default_factory=list)
    remove: list[HCMappingRule] = Field(default_factory=list)


@dataclass(slots=True)
class HostComponentMapDeltaSets:
    """
    Convenience class to calculate cumulative delta
    """

    add: set[HCMappingRule] = field(default_factory=set)
    remove: set[HCMappingRule] = field(default_factory=set)

    def to_list_delta(self) -> HostComponentMapDelta:
        return HostComponentMapDelta(add=list(self.add), remove=list(self.remove))


class MappingInputDTO(BaseModel):
    delta: HostComponentMapDelta
    cumulative_delta: HostComponentMapDelta | None = None


class MappingStepInput(BaseModel):
    step_id: ActionProcessStepID
    mapping: MappingInputDTO


class StepInputDTO(BaseModel):
    configuration: config.Configuration | None = None
    job_id: TaskID | None = None
    mapping: MappingInputDTO | None = None
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def validate_input_exclusive_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            config_specified = "configuration" in data and data.get("configuration") is not None
            task_specified = "job_id" in data and data.get("job_id") is not None
            mapping_specified = "mapping" in data and data.get("mapping") is not None

            if sum([config_specified, task_specified, mapping_specified]) != 1:
                raise ValueError('Exactly one of ("configuration", "job_id", "mapping") must be specified.')

        return data


class ActionProcess(BaseModel):
    id: ActionProcessID
    sync_key: UUID
    target_id: ObjectID
    target_type: ADCMCoreType | ExtraActionTargetType
    owner_id: ObjectID
    owner_type: ADCMCoreType
    flow_spec: list[Stage] = Field(..., min_length=1)
    current_step_id: ActionProcessStepID | None = None
    last_completed_step_id: ActionProcessStepID | None = None


class Step(BaseModel):
    id: ActionProcessStepID
    process_id: ActionProcessID
    name: str
    stage: str
    display_name: str
    step_spec: list[dict] | None = None
    description: str = ""
    type: StepType
    state: ProcessStepState

    model_config = ConfigDict(extra="allow", use_enum_values=True)

    @property
    def is_render_required(self) -> bool:
        return self.step_spec is None

    @cached_property
    def spec(
        self,
    ) -> ConfigStepSpec | OperationStepSpec | MappingStepSpec | None:
        if self.step_spec is None:
            return None

        match self.type:
            case StepType.CONFIGURATION:
                raw_spec, raw_defaults = self.step_spec
                config_spec = config.spec.FullSpec.model_validate(raw_spec)
                config_defaults = config.Defaults(**raw_defaults)
                return config_spec, config_defaults

            case StepType.OPERATION:
                return [JobSpec.model_validate(record) for record in self.step_spec]

            case StepType.MAPPING:
                return [mapping.MappingRule(**record) for record in self.step_spec]
