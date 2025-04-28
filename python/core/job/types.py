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
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from core.types import (
    ActionID,
    ADCMCoreType,
    ComponentID,
    HostID,
    NamedActionObject,
    NamedCoreObjectWithPrototype,
    ObjectID,
    PrototypeDescriptor,
    PrototypeID,
)


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
    scripts_jinja: str


class StateChanges(NamedTuple):
    state: str | None
    multi_state_set: tuple[str, ...]
    multi_state_unset: tuple[str, ...]


@dataclass(slots=True)
class TaskMappingDelta:
    add: dict[ComponentID, set[HostID]] = field(default_factory=dict)
    remove: dict[ComponentID, set[HostID]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (self.add or self.remove)


class HostComponentChanges(NamedTuple):
    post_upgrade: list[dict] | None
    mapping_delta: TaskMappingDelta | None


class BundleInfo(NamedTuple):
    # root is directory of bundle like /adcm/data/bundle/somehash
    root: Path
    # relative path to directory with `config.yaml` within `root`
    #
    # should point to directory with `config.yaml` where task owner is defined
    config_dir: Path


class RelatedObjects(NamedTuple):
    # must be specified for Service/Component and Host (if linked)
    cluster: NamedCoreObjectWithPrototype | None = None
    # must be specified for Component
    service: NamedCoreObjectWithPrototype | None = None
    # must be specified for Host
    provider: NamedCoreObjectWithPrototype | None = None


class TaskOwner(NamedTuple):
    id: ObjectID
    type: ADCMCoreType
    name: str
    prototype_id: PrototypeID

    related_objects: RelatedObjects


class TaskActionInfo(NamedTuple):
    name: str
    display_name: str

    venv: str
    hc_acl: list[dict]

    is_upgrade: bool
    is_host_action: bool


class Task(BaseModel):
    id: int

    # Owner is an object on which action is defined
    owner: TaskOwner | None
    bundle: BundleInfo | None

    # Target is an object on which action should be performed
    # it's the same as owner for all cases except `host_action: true`
    target: NamedActionObject | None

    selector: dict

    action: TaskActionInfo

    verbose: bool
    hostcomponent: HostComponentChanges
    config: dict | None

    on_success: StateChanges
    on_fail: StateChanges

    is_blocking: bool


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


class HcApply(NamedTuple):
    component: str
    service: str
    action: Literal["add", "remove"]


# it is validated, because we want to fail here on incorrect data
# rather than when we will use it
class JobParams(BaseModel):
    ansible_tags: str
    hc_apply: Annotated[list[HcApply], Field(default_factory=list)]

    model_config = ConfigDict(extra="allow")


class Job(BaseModel):
    id: int
    pid: int
    name: str
    type: ScriptType
    status: ExecutionStatus
    script: str

    params: JobParams

    on_fail: StateChanges
