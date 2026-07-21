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
from itertools import chain
from pathlib import Path
from typing import Annotated, Generic, Literal, NamedTuple, TypeAlias, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.action import JobSpec  # noqa
from core.templates import Template
from core.types import (
    ActionID,
    ADCMCoreType,
    ComponentID,
    Descriptor,
    HostID,
    NamedActionObject,
    NamedCoreObjectWithPrototype,
    ObjectID,
    PrototypeDescriptor,
    PrototypeID,
)

T = TypeVar("T")
V = TypeVar("V")
CT = TypeVar("CT", bound=ADCMCoreType)


# str is required for pydantic to correctly cast enum to value when calling `.dict`
class ExecutionStatus(str, Enum):
    REVOKED = "revoked"
    CREATED = "created"
    SCHEDULED = "scheduled"
    QUEUED = "queued"
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


class ActionInfo(BaseModel):
    id: ActionID
    name: str
    owner_prototype: PrototypeDescriptor
    scripts_jinja: str
    wizard_template: Template | None
    scripts_template: Template | None = None


ClusterActionTarget: TypeAlias = Literal["owner", "host", "host-group"]


@dataclass(slots=True)
class DynamicSection(Generic[T, V]):
    type: T
    value: V


StaticScripts: TypeAlias = Literal["static"]
StaticConfig: TypeAlias = Literal["static"]

ActionScripts: TypeAlias = (
    StaticScripts | DynamicSection[Literal["jinja"], str] | DynamicSection[Literal["template"], Template]
)
ActionConfig: TypeAlias = (
    StaticConfig | DynamicSection[Literal["jinja"], str] | DynamicSection[Literal["template"], Template]
)


class _ClusterAction(BaseModel):
    id: ActionID
    name: str

    owner_prototype: PrototypeDescriptor

    scripts: ActionScripts
    config: ActionConfig


class ClusterRegularAction(_ClusterAction):
    target: ClusterActionTarget
    process: Template | None


class ClusterUpgradeAction(_ClusterAction):
    ...


class _StaticAction(BaseModel):
    id: ActionID
    name: str

    owner_prototype: PrototypeDescriptor

    scripts: StaticScripts
    config: StaticConfig


class ProviderRegularAction(_StaticAction):
    ...


class ProviderUpgradeAction(_StaticAction):
    ...


class ADCMAction(_StaticAction):
    ...


ClusterAction: TypeAlias = ClusterRegularAction | ClusterUpgradeAction
ProviderAction: TypeAlias = ProviderRegularAction | ProviderUpgradeAction


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
        host_sets = chain(self.add.values(), self.remove.values())

        return not any(host_sets)


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


@dataclass(slots=True)
class TaskOwner(Generic[CT]):
    id: ObjectID
    type: CT
    name: str
    prototype_id: PrototypeID

    related_objects: RelatedObjects

    @property
    def as_descriptor(self) -> Descriptor[CT]:
        return Descriptor(id=self.id, type=self.type)


class HcAclRule(NamedTuple):
    component: str
    service: str
    action: Literal["add", "remove"]


class TaskActionInfo(NamedTuple):
    id: ObjectID
    name: str
    display_name: str

    venv: str
    hc_acl: list[HcAclRule]

    is_upgrade: bool
    is_host_action: bool


class AssociatedProcess(BaseModel):
    # The process passed explicitly when launching the action.
    id: int


class CallingProcess(BaseModel):
    # The process in which this task is called.
    id: int
    sync_key: UUID
    step_id: int


class Task(BaseModel):
    id: int

    # Owner is an object on which action is defined
    owner: TaskOwner[ADCMCoreType] | None
    bundle: BundleInfo | None

    # Target is an object on which action should be performed
    # it's the same as owner for all cases except `host_action: true` or action_host_group
    target: NamedActionObject | None

    selector: dict

    action: TaskActionInfo
    action_process: CallingProcess | AssociatedProcess | None

    verbose: bool
    hostcomponent: HostComponentChanges
    config: dict | None

    on_success: StateChanges
    on_fail: StateChanges

    is_blocking: bool

    description: str

    @property
    def is_operation_step_task(self) -> bool:
        return isinstance(self.action_process, CallingProcess)


# it is validated, because we want to fail here on incorrect data
# rather than when we will use it
class JobParams(BaseModel):
    ansible_tags: str
    rules: Annotated[list[HcAclRule], Field(default_factory=list)]

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
