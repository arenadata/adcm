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
from typing import Literal
from uuid import UUID

from core.action import wizard
from core.types import ActionProcessStepID
from pydantic import BaseModel, ConfigDict, Field

# Common


class ProcessOperationType(str, Enum):
    SUBMIT = "submit_step"
    COMPLETE = "complete"
    RESET = "reset_step"
    SKIP = "skip_step"


class Configuration(BaseModel):
    config: dict = Field(default_factory=dict)
    adcm_meta: dict = Field(default_factory=dict)


class _SyncKeyParam(BaseModel):
    process_sync_key: UUID


class _StepIDParam(BaseModel):
    step_id: ActionProcessStepID


# Submit


class SubmitOperationStepParams(_SyncKeyParam, _StepIDParam):
    ...


class SubmitConfigurationStepParams(_SyncKeyParam, _StepIDParam):
    configuration: Configuration


class SubmitMappingStepParams(_SyncKeyParam, _StepIDParam):
    host_component_map_delta: wizard.HostComponentMapDelta


class SubmitStepPayload(BaseModel):
    method: Literal[ProcessOperationType.SUBMIT]
    params: SubmitMappingStepParams | SubmitConfigurationStepParams | SubmitOperationStepParams


# Complete


class CompleteProcessPayload(BaseModel):
    method: Literal[ProcessOperationType.COMPLETE]
    params: _SyncKeyParam


# Reset


class _ResetStepParams(_SyncKeyParam, _StepIDParam):
    ...


class ResetStepPayload(BaseModel):
    method: Literal[ProcessOperationType.RESET]
    params: _ResetStepParams


# Skip


class SkipOperationStepParams(_SyncKeyParam, _StepIDParam):
    ...


class SkipStepPayload(BaseModel):
    method: Literal[ProcessOperationType.SKIP]
    params: SkipOperationStepParams


# Payload


class OperationPayloadSchema(BaseModel):
    payload: SubmitStepPayload | CompleteProcessPayload | ResetStepPayload | SkipStepPayload = Field(
        discriminator="method"
    )

    model_config = ConfigDict(extra="forbid")
