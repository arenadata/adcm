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

# str is required for pydantic to correctly cast enum to value when calling `.dict`
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from itertools import chain
from pathlib import Path
from typing import Annotated, Any, Generic, Literal, NamedTuple, TypeAlias, TypedDict, TypeGuard, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import MM_ACTION_NAMES
from core.templates import Template
from core.types import (
    ActionID,
    ADCMCoreType,
    ComponentID,
    ConcernID,
    Descriptor,
    HostID,
    JobID,
    NamedActionObject,
    NamedCoreObjectWithPrototype,
    ObjectID,
    PrototypeDescriptor,
    PrototypeID,
    TaskID,
)

T = TypeVar("T")
V = TypeVar("V")
CT = TypeVar("CT", bound=ADCMCoreType)


class ScriptType(str, Enum):
    ANSIBLE = "ansible"
    PYTHON = "python"
    INTERNAL = "internal"


# str is required for pydantic to correctly cast enum to value when calling `.dict`
class ExecutionStatus(str, Enum):
    ABORTED = "aborted"
    BROKEN = "broken"
    CREATED = "created"
    FAILED = "failed"
    QUEUED = "queued"
    REVOKED = "revoked"
    REVOKING = "revoking"
    RUNNING = "running"
    SCHEDULED = "scheduled"
    SUCCESS = "success"
    TERMINATING = "terminating"


# should be unified and distinct
UNFINISHED_STATUSES = (
    ExecutionStatus.CREATED,
    ExecutionStatus.SCHEDULED,
    ExecutionStatus.QUEUED,
    ExecutionStatus.RUNNING,
    ExecutionStatus.REVOKING,
    ExecutionStatus.TERMINATING,
)


@dataclass(slots=True)
class ExecutionEnvironment:
    pid: int
    worker_id: int | str | None


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


class AssociatedProcess(BaseModel):
    # The process passed explicitly when launching the action.
    id: int


class CallingProcess(BaseModel):
    # The process in which this task is called.
    id: int
    sync_key: UUID
    step_id: int


@dataclass(slots=True)
class TaskMappingDelta:
    add: dict[ComponentID, set[HostID]] = field(default_factory=dict)
    remove: dict[ComponentID, set[HostID]] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        host_sets = chain(self.add.values(), self.remove.values())

        return not any(host_sets)


class StateChanges(NamedTuple):
    state: str | None
    multi_state_set: tuple[str, ...]
    multi_state_unset: tuple[str, ...]


class HcAclRule(NamedTuple):
    component: str
    service: str
    action: Literal["add", "remove"]


class ActionInfo(BaseModel):
    id: ActionID
    name: str
    owner_prototype: PrototypeDescriptor
    wizard_template: Template | None
    scripts_template: Template | None = None


class ServiceManageConfigChange(BaseModel):
    key: str
    value: Any


class ServiceManageHostComponentChange(BaseModel):
    component: str
    hosts: list[str]


class ServiceManageServiceEntry(BaseModel):
    name: str
    config_changes: Annotated[list[ServiceManageConfigChange] | None, Field(default=None)]
    hc_changes: Annotated[list[ServiceManageHostComponentChange] | None, Field(default=None)]


# SCRIPT PARAMS
#
# Params are typed per script_type + script (for internal scripts), mirroring the split
# already enforced at bundle-parsing time.
# It is validated, because we want to fail here on incorrect data rather than when we will use it.


class AnsibleScriptParams(BaseModel):
    model_config = ConfigDict(extra="allow")

    ansible_tags: str = ""


@dataclass(slots=True)
class HcApplyScriptParams:
    rules: list[HcAclRule] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class TypeBasedConfigApplyTarget:
    type: Literal["adcm", "provider", "host", "cluster"]


@dataclass(slots=True, frozen=True)
class ServiceConfigApplyTarget:
    type: Literal["service"]
    service_name: str


@dataclass(slots=True, frozen=True)
class ComponentConfigApplyTarget:
    type: Literal["component"]
    service_name: str
    component_name: str


@dataclass(slots=True, frozen=True)
class ConfigApplyParameterEntry:
    key: str
    value: Any


@dataclass(slots=True, frozen=True)
class ConfigApplyChangeEntry:
    object: Annotated[
        TypeBasedConfigApplyTarget | ServiceConfigApplyTarget | ComponentConfigApplyTarget,
        Field(discriminator="type"),
    ]
    parameters: list[ConfigApplyParameterEntry]


@dataclass(slots=True)
class ConfigApplyScriptParams:
    changes: list[ConfigApplyChangeEntry]


@dataclass(slots=True)
class ServiceManageScriptParams:
    operation: Literal["add"]
    services: list[ServiceManageServiceEntry]


# JOB
#
# `type` and `script` act as discriminators of the `Job` union below, so they're mandatory here.
# Unlike loosely-typed intermediate bundle-parsing dicts (where their presence can't always
# be relied on), construction of any of these types must supply both explicitly.

ScriptTypeT = TypeVar("ScriptTypeT", bound=ScriptType)
ScriptNameT = TypeVar("ScriptNameT", bound=str)
ParamsT = TypeVar("ParamsT")


class _BaseJob(BaseModel, Generic[ScriptTypeT, ScriptNameT, ParamsT]):
    id: int
    pid: int
    name: str
    display_name: str
    type: ScriptTypeT
    script: ScriptNameT
    status: ExecutionStatus

    params: ParamsT

    on_fail: StateChanges

    is_termination_allowed: bool

    execution_env: ExecutionEnvironment


class AnsibleJob(_BaseJob[Literal[ScriptType.ANSIBLE], str, AnsibleScriptParams]):
    pass


class PythonJob(_BaseJob[Literal[ScriptType.PYTHON], str, None]):
    pass


# common parent of all internal scripts, so it's possible to match/isinstance-check
# against "any internal script job" without enumerating every concrete script
class InternalJob(_BaseJob[Literal[ScriptType.INTERNAL], ScriptNameT, ParamsT], Generic[ScriptNameT, ParamsT]):
    pass


class SimpleInternalJob(InternalJob[Literal["bundle_switch", "bundle_revert", "before_upgrade_clean"], None]):
    pass


class HcApplyJob(InternalJob[Literal["hc_apply"], HcApplyScriptParams | None]):
    pass


class ConfigApplyJob(InternalJob[Literal["config_apply"], ConfigApplyScriptParams]):
    pass


class ServiceManageJob(InternalJob[Literal["service_manage"], ServiceManageScriptParams]):
    pass


_InternalJobVariants = Annotated[
    SimpleInternalJob | HcApplyJob | ConfigApplyJob | ServiceManageJob,
    Field(discriminator="script"),
]

Job = Annotated[AnsibleJob | PythonJob | _InternalJobVariants, Field(discriminator="type")]


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


@dataclass(slots=True, frozen=True)
class TaskOwner(Descriptor[ADCMCoreType]):
    name: str
    prototype_id: PrototypeID

    related_objects: RelatedObjects

    @property
    def as_descriptor(self) -> Descriptor[ADCMCoreType]:
        return Descriptor(id=self.id, type=self.type)


class TaskActionInfo(NamedTuple):
    id: ObjectID
    name: str
    display_name: str

    venv: str
    hc_acl: list[HcAclRule]

    is_upgrade: bool
    is_host_action: bool


class HostComponentChanges(NamedTuple):
    post_upgrade: list[dict] | None
    mapping_delta: TaskMappingDelta | None


class Task(BaseModel):
    id: int
    name: str = ""
    display_name: str = ""

    # Owner is an object on which action is defined
    owner: TaskOwner | None
    bundle: BundleInfo | None

    # Target is an object on which action should be performed
    # it's the same as owner for all cases except `host_action: true` or action_host_group
    target: NamedActionObject | None

    status: ExecutionStatus

    selector: dict

    action: TaskActionInfo
    action_process: CallingProcess | AssociatedProcess | None

    verbose: bool
    hostcomponent: HostComponentChanges
    config: dict | None

    on_success: StateChanges
    on_fail: StateChanges

    is_blocking: bool
    # currently it's action's property,
    # but for similarity with job we'll put it in here
    is_termination_allowed: bool

    description: str

    execution_env: ExecutionEnvironment


def is_operation_step_task(task_process: CallingProcess | AssociatedProcess | None) -> TypeGuard[CallingProcess]:
    return isinstance(task_process, CallingProcess)


WorkerTaskID: TypeAlias = int | str


class TaskRunnerEnvironment(str, Enum):
    LOCAL = "local"
    CELERY = "celery"


class WorkerInfo(TypedDict):
    environment: TaskRunnerEnvironment
    worker_id: WorkerTaskID


@dataclass
class ActionShortInfo:
    id: ActionID
    name: str
    venv: str

    # NOTE: name-based MM action detection is a placeholder, to be revisited in a follow-up iteration
    @property
    def is_mm_action(self) -> bool:
        return self.name in MM_ACTION_NAMES


@dataclass(slots=True, frozen=True)
class TaskShortInfo:
    id: TaskID
    worker: WorkerInfo
    status: ExecutionStatus
    lock_id: ConcernID | None
    action: ActionShortInfo


@dataclass(slots=True, frozen=True)
class JobShortInfo:
    id: JobID
    task_id: TaskID
    finish_date: datetime | None
    worker: WorkerInfo
    status: ExecutionStatus
