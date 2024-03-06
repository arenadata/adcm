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
from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel

from core.types import ActionID, CoreObjectDescriptor, NamedCoreObject, PrototypeDescriptor


# str is required for pydantic to correctly cast enum to value when calling `.dict`
class ExecutionStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"
    BROKEN = "broken"


# str is required for pydantic to correctly cast enum to value when calling `.dict`
class ScriptType(str, Enum):
    ANSIBLE = "ansible"
    PYTHON = "python"
    INTERNAL = "internal"


class ActionInfo(NamedTuple):
    id: ActionID
    name: str
    owner_prototype: PrototypeDescriptor


class StateChanges(NamedTuple):
    state: str | None
    multi_state_set: tuple[str, ...]
    multi_state_unset: tuple[str, ...]


class HostComponentChanges(NamedTuple):
    to_set: list[dict] | None
    post_upgrade: list[dict] | None
    restore_on_fail: bool


class Task(BaseModel):
    id: int

    # Owner is an object on which action is defined
    owner: CoreObjectDescriptor | None
    bundle_root: Path | None

    # Target is an object on which action should be performed
    # it's the same as owner for all cases except `host_action: true`
    target: NamedCoreObject | None

    name: str
    display_name: str
    is_upgrade: bool
    verbose: bool
    venv: str
    hostcomponent: HostComponentChanges
    on_success: StateChanges
    on_fail: StateChanges


class JobSpec(BaseModel):
    # basic info
    name: str
    display_name: str
    script: str
    script_type: ScriptType
    allow_to_terminate: bool

    # states
    state_on_fail: str
    multi_state_on_fail_set: list
    multi_state_on_fail_unset: list

    # extra
    params: dict

    class Config:  # simplify existing objects retrieval
        orm_mode = True


# it is validated, because we want to fail here on incorrect data
# rather than when we will use it
class JobParams(BaseModel):
    ansible_tags: str


class Job(BaseModel):
    id: int
    pid: int
    type: ScriptType
    status: ExecutionStatus
    script: str

    params: JobParams

    on_fail: StateChanges
