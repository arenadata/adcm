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

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, TypeAlias

from pydantic import BaseModel, Field

from core.action._types import (
    ActionInfo,
    AssociatedProcess,
    CallingProcess,
    ExecutionStatus,
    HostComponentChanges,
    Job,
    JobShortInfo,
    JobSpec,
    Task,
    TaskMappingDelta,
    TaskShortInfo,
)
from core.types import (
    ActionID,
    ActionTargetDescriptor,
    ConcernID,
    CoreObjectDescriptor,
    HostGroupDescriptor,
    JobID,
    TaskID,
)

PreparedConfigValues: TypeAlias = dict[str, Any]
HasChanged: TypeAlias = bool
ChangedAmount: TypeAlias = int


@dataclass(slots=True)
class LaunchOptions:
    is_verbose: bool = False
    is_blocking: bool = True


@dataclass(slots=True)
class TaskExtraInfo:
    name: str
    display_name: str
    description: str


class TaskCreateDTO(BaseModel):
    owner: CoreObjectDescriptor
    target: CoreObjectDescriptor | HostGroupDescriptor
    action_id: ActionID
    extra: TaskExtraInfo
    launch: LaunchOptions = Field(default_factory=LaunchOptions)
    process: AssociatedProcess | CallingProcess | None = None


# REVIEW probably required only in tests
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


class LogCreateDTO(BaseModel):
    job_id: int
    name: str
    type: str
    format: str


class TaskUpdateMainFieldsDTO(BaseModel):
    mapping_delta: TaskMappingDelta | None
    configuration: PreparedConfigValues | None


class TaskMutableFieldsDTO(BaseModel):
    hostcomponent: HostComponentChanges


class TaskUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None
    post_upgrade_hc_map: list[dict] | None = None
    hostcomponentmap: TaskMappingDelta | None = None
    executor: dict | None = None
    lock_id: ConcernID | None = None


class JobUpdateDTO(BaseModel):
    pid: int | None = None
    start_date: datetime | None = None
    finish_date: datetime | None = None
    status: ExecutionStatus | None = None
    objects_related_configs: list | None = None
    executor: dict | None = None


@dataclass(slots=True)
class TaskShortFilter:
    # `None` means "don't filter by this field", not "match `None`"
    ids: Iterable[TaskID] | None = None
    statuses: Iterable[ExecutionStatus] | None = None


@dataclass(slots=True)
class JobShortFilter:
    # `None` means "don't filter by this field", not "match `None`"
    ids: Iterable[JobID] | None = None
    task_ids: Iterable[TaskID] | None = None
    statuses: Iterable[ExecutionStatus] | None = None


class JobRepoI(Protocol):
    # retrieve

    def get_task(self, id: int) -> Task:  # noqa: A002
        """Should raise `NotFoundError` on fail"""
        ...

    def get_job(self, id: int) -> Job:  # noqa: A002
        """Should raise `NotFoundError` on fail"""
        ...

    def find_jobs_of_task(self, task_id: TaskID) -> tuple[Job, ...]:
        ...

    # DEPRECATED, duplicate of `find_jobs_of_task`
    def get_task_jobs(self, task_id: int) -> Iterable[Job]:
        ...

    def find_scripts_of_action(self, action_id: ActionID) -> tuple[JobSpec, ...]:
        ...

    def find_action_owner(self, action_id: ActionID, target: ActionTargetDescriptor) -> CoreObjectDescriptor:
        ...

    def find_tasks_short(self, filter_: TaskShortFilter) -> Iterable[TaskShortInfo]:
        """
        Cheaper, slimmer alternative to `get_task`, meant for tight polling loops.
        """
        ...

    def find_jobs_short(self, filter_: JobShortFilter) -> Iterable[JobShortInfo]:
        """
        Cheaper, slimmer alternative to `get_job`, meant for tight polling loops.
        """
        ...

    # NEED REVIEW, from ActionRepoInterface
    def get_action(self, id: ActionID) -> ActionInfo:  # noqa: A002
        ...

    # NEED REVIEW, from ActionRepoInterface
    def get_job_specs(self, id: ActionID) -> Iterable[JobSpec]:  # noqa: A002
        ...

    # NEED REVIEW
    def get_related_wizard_process(self, job_id: JobID) -> CallingProcess | AssociatedProcess | None:
        """
        For cases when task to wizard process relation is important, but other task info is not
        """
        ...

    # NEED REVIEW
    def get_task_mutable_fields(self, id: int) -> TaskMutableFieldsDTO:  # noqa: A002
        ...

    # create

    def create_task(self, payload: TaskCreateDTO) -> TaskID:
        ...

    def create_jobs(self, task_id: TaskID, scripts: Iterable[JobSpec]) -> None:
        ...

    def create_logs(self, logs: Iterable[LogCreateDTO]) -> None:
        ...

    # update

    def fill_task_mapping_and_configuration(self, task_id: TaskID, payload: TaskUpdateMainFieldsDTO) -> None:
        ...

    def change_task_status(self, id: TaskID, previous: ExecutionStatus, new: ExecutionStatus) -> HasChanged:  # noqa: A002
        """
        Change task's status from `previous` to `new`, return flag if change was performed
        """
        ...

    def change_job_status(self, id: JobID, previous: ExecutionStatus, new: ExecutionStatus) -> HasChanged:  # noqa: A002
        """
        Change job's status from `previous` to `new`, return flag if change was performed
        """
        ...

    def change_status_of_task_jobs(
        self, task_id: TaskID, previous: ExecutionStatus, new: ExecutionStatus
    ) -> ChangedAmount:
        """
        Change status of all jobs in task from `previous` to `new` returning amount of records changed
        """
        ...

    def update_task(self, id: int, data: TaskUpdateDTO) -> None:  # noqa: A002
        ...

    def update_job(self, id: int, data: JobUpdateDTO) -> None:  # noqa: A002
        ...

    # NEED REVIEW, maybe belongs to service layer + separate repo for objects
    def update_owner_state(self, owner: CoreObjectDescriptor, state: str) -> None:
        ...

    # NEED REVIEW, maybe belongs to service layer + separate repo for objects
    def update_owner_multi_states(
        self, owner: CoreObjectDescriptor, add_multi_states: Collection[str], remove_multi_states: Collection[str]
    ) -> None:
        ...

    # misc

    # NEED REVIEW, probably shouldn't be here, infra level
    def close_old_connections(self) -> None:
        ...

    # NEED REVIEW, breaks isolation levels
    def get_target_orm(self, task_id: TaskID) -> Any:
        ...
