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
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, Literal, TypeAlias, Union, overload
from uuid import UUID

from core.legacy.bundle_alt.schema import ActionProcessStage
from core.legacy.job.types import ActionInfo
from core.types import (
    ActionProcessID,
    ActionProcessStepID,
    ActionTargetDescriptor,
    ADCMCoreType,
    CoreObjectDescriptor,
    ExtraActionTargetType,
    ObjectID,
    TaskID,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator
import core

from cm.legacy.services.action_process.schema_validation import HostComponentMapDelta

if TYPE_CHECKING:
    from cm.models import Action, ActionHostGroup, Cluster, Component, Host, Service


ProcessOwner: TypeAlias = Union["Cluster", "Service", "Component"]
ProcessTarget: TypeAlias = Union["Cluster", "Service", "Component", "Host", "ActionHostGroup"]
ClusterRelativeObjectORM: TypeAlias = Union["Cluster", "Service", "Component", "Host"]


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


class MappingInputDTO(BaseModel):
    delta: HostComponentMapDelta
    cumulative_delta: HostComponentMapDelta | None = None


class MappingStepInput(BaseModel):
    step_id: ActionProcessStepID
    mapping: MappingInputDTO


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
    target_id: ObjectID
    target_type: ADCMCoreType | ExtraActionTargetType
    owner_id: ObjectID
    owner_type: ADCMCoreType
    flow_spec: list[core.action.wizard.Stage] = Field(..., min_length=1)
    current_step_id: ActionProcessStepID | None = None
    last_completed_step_id: ActionProcessStepID | None = None


class Step(BaseModel):
    id: ActionProcessStepID
    process_id: ActionProcessID
    name: str
    stage: str
    display_name: str
    step_spec: list[dict] | None = None
    type: core.action.wizard.StepType
    state: ProcessStepState

    model_config = ConfigDict(extra="allow", use_enum_values=True)

    @property
    def is_render_required(self) -> bool:
        return self.step_spec is None

    @cached_property
    def spec(
        self,
    ) -> (
        core.action.wizard.ConfigStepSpec
        | core.action.wizard.OperationStepSpec
        | core.action.wizard.MappingStepSpec
        | None
    ):
        if self.step_spec is None:
            return None

        match self.type:
            case core.action.wizard.StepType.CONFIGURATION:
                raw_spec, raw_defaults = self.step_spec
                config_spec = core.config.spec.FullSpec.model_validate(raw_spec)
                config_defaults = core.config.Defaults(**raw_defaults)
                return config_spec, config_defaults

            case core.action.wizard.StepType.OPERATION:
                return [core.action.JobSpec.model_validate(record) for record in self.step_spec]

            case core.action.wizard.StepType.MAPPING:
                return [core.mapping.MappingRule(**record) for record in self.step_spec]


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


@dataclass(frozen=True, slots=True)
class ProcessContext:
    action: ActionInfo
    action_orm: "Action"
    target: ActionTargetDescriptor
    target_orm: ProcessTarget
    owner: CoreObjectDescriptor
    owner_orm: ProcessOwner

    @overload
    def cluster_relative_object(self, as_descriptor: Literal[True]) -> CoreObjectDescriptor:
        ...

    @overload
    def cluster_relative_object(self, as_descriptor: Literal[False] = False) -> ClusterRelativeObjectORM:
        ...

    def cluster_relative_object(self, as_descriptor: bool = False) -> ClusterRelativeObjectORM | CoreObjectDescriptor:
        if self.target.type == ExtraActionTargetType.ACTION_HOST_GROUP:
            return self.owner if as_descriptor else self.owner_orm
        else:
            return CoreObjectDescriptor(id=self.target.id, type=self.target.type) if as_descriptor else self.target_orm
