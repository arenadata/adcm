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
from typing import Any, TypeAlias

from pydantic import BaseModel, Field

from core.job.types import (
    AssociatedProcess,
    CallingProcess,
    ExecutionStatus,
    HostComponentChanges,
    TaskMappingDelta,
)
from core.types import ActionID, CoreObjectDescriptor, HostGroupDescriptor


class TaskUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None
    post_upgrade_hc_map: list[dict] | None = None
    hostcomponentmap: TaskMappingDelta | None = None
    executor: dict | None = None


class JobUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None
    objects_related_configs: list | None = None


class LogCreateDTO(BaseModel):
    job_id: int
    name: str
    type: str
    format: str


@dataclass(slots=True)
class TaskPayloadDTO:
    verbose: bool = False

    conf: dict | None = None
    attr: dict | None = None

    mapping_delta: TaskMappingDelta | None = None
    post_upgrade_hostcomponent: list[dict] | None = None

    is_blocking: bool = True

    process: CallingProcess | AssociatedProcess | None = None

    description: str = ""


class TaskMutableFieldsDTO(BaseModel):
    hostcomponent: HostComponentChanges


PreparedConfigValues: TypeAlias = dict[str, Any]


@dataclass(slots=True)
class LaunchOptions:
    is_verbose: bool = False
    is_blocking: bool = True


class TaskCreateDTO(BaseModel):
    owner: CoreObjectDescriptor
    target: CoreObjectDescriptor | HostGroupDescriptor
    action_id: ActionID
    launch: LaunchOptions = Field(default_factory=LaunchOptions)
    process: AssociatedProcess | None = None
    description: str = ""


class TaskUpdateMainFieldsDTO(BaseModel):
    mapping_delta: TaskMappingDelta | None
    configuration: PreparedConfigValues | None
