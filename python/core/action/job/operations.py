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

from collections.abc import Mapping, Sequence
from typing import Literal

from core.action.types import (
    UNFINISHED_STATUSES,
    ExecutionStatus,
    ExecutionStyle,
    JobHierarchyLevel,
    JobSpecV1,
    RichJob,
    RuntimeDates,
    StateChanges,
)
from core.result import Fail, Success
from core.spec.keys import level_keys_to_full_key
from core.spec.types import FullSpecKey, LevelSpecKey

TaskCompletionStatus = Literal[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.ABORTED]

# CREATED is the one unfinished status that says nothing is going on yet, so it's never "in progress"
_IN_PROGRESS_STATUSES = frozenset(UNFINISHED_STATUSES).difference((ExecutionStatus.CREATED,))
_FAILURE_STATUSES = frozenset((ExecutionStatus.FAILED, ExecutionStatus.BROKEN))


def calculate_task_final_status(
    plan: JobSpecV1, job_statuses: Mapping[FullSpecKey, ExecutionStatus], task_is_aborted: bool
) -> Success[TaskCompletionStatus] | Fail[str]:
    """
    Derive task's result from its plan: the root level is a node like any group (see `aggregate_group_status`).

    Terminated task is aborted whatever its jobs say, so nothing is calculated for it.
    """

    if task_is_aborted:
        return Success(ExecutionStatus.ABORTED)

    status = _calculate_level_status(level=plan.hierarchy, group_levels=(), job_statuses=job_statuses)

    if status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILED):
        return Success(status)

    if status in (ExecutionStatus.ABORTED, ExecutionStatus.REVOKED):
        return Success(ExecutionStatus.ABORTED)

    return Fail(
        f"Task's jobs are not finished (calculated status is {status.value}), so its result can't be determined"
    )


def calculate_owner_state_changes(
    task_result: TaskCompletionStatus,
    jobs: Sequence[RichJob],
    on_success: StateChanges,
    on_fail: StateChanges,
) -> StateChanges:
    """
    Calculate what should be applied to task owner, aborted task changes nothing.

    Failed task takes `on_fail` of the latest finished FAILED job that has one,
    each field falls back to task's `on_fail` independently.
    Jobs finished at the same time are resolved by greater id.
    """

    if task_result == ExecutionStatus.ABORTED:
        return StateChanges()

    if task_result == ExecutionStatus.SUCCESS:
        return on_success

    candidates = tuple(
        job for job in jobs if job.runtime.status == ExecutionStatus.FAILED and not job.spec.on_fail.is_empty
    )
    if not candidates:
        return on_fail

    finished_candidates = tuple(job for job in candidates if job.runtime.dates.finish is not None)
    if not finished_candidates:
        ids = ", ".join(str(job.runtime.id) for job in candidates)
        message = f"Failed jobs with on_fail have no finish date: {ids}"
        raise RuntimeError(message)

    latest_job = max(finished_candidates, key=lambda job: (job.runtime.dates.finish, job.runtime.id))
    job_on_fail = latest_job.spec.on_fail

    return StateChanges(
        state=job_on_fail.state or on_fail.state,
        multi_state_set=job_on_fail.multi_state_set or on_fail.multi_state_set,
        multi_state_unset=job_on_fail.multi_state_unset or on_fail.multi_state_unset,
    )


def aggregate_group_status(children: Sequence[ExecutionStatus], style: ExecutionStyle) -> ExecutionStatus:
    """
    Derive a node's status from its direct children's statuses, given in the node's level order.

    A subgroup counts as a single child with its own derived status, so subgroups are calculated first.
    Only the last rule reads the order: a sequential node's outcome is the outcome of its last child.

    Parallel node may flicker when celery stalls one of its branches:
    `SUCCESS-FAILED-CREATED` is `FAILED`, then the stalled branch starts and `SUCCESS-FAILED-RUNNING` is `RUNNING`.
    It's accepted: the node is still in progress after all.

    Raises `ValueError` when statuses fit no rule (e.g. a newly added status no rule knows about).
    """

    statuses = set(children)

    if statuses.intersection(_IN_PROGRESS_STATUSES):
        return ExecutionStatus.RUNNING

    if statuses.intersection(_FAILURE_STATUSES):
        return ExecutionStatus.FAILED

    if statuses == {ExecutionStatus.CREATED}:
        return ExecutionStatus.CREATED

    if statuses == {ExecutionStatus.SUCCESS}:
        return ExecutionStatus.SUCCESS

    if statuses == {ExecutionStatus.REVOKED}:
        return ExecutionStatus.REVOKED

    if ExecutionStatus.CREATED in statuses:
        return ExecutionStatus.RUNNING

    if not statuses.issubset({ExecutionStatus.SUCCESS, ExecutionStatus.ABORTED, ExecutionStatus.REVOKED}):
        message = f"Statuses {sorted(status.value for status in statuses)} fit no rule of group status calculation"
        raise ValueError(message)

    if style == ExecutionStyle.SEQUENTIAL and children[-1] == ExecutionStatus.SUCCESS:
        return ExecutionStatus.SUCCESS

    return ExecutionStatus.ABORTED


def aggregate_group_dates(children: Sequence[RuntimeDates]) -> RuntimeDates:
    """
    Derive a group's dates from its children's dates.

    A group is finished only when every child is: one child without a finish date
    (not started yet, still running or never finished) leaves the group's finish unset.
    """

    start = min((dates.start for dates in children if dates.start is not None), default=None)

    finishes = [dates.finish for dates in children if dates.finish is not None]

    if len(finishes) < len(children):
        return RuntimeDates(start=start, finish=None)

    return RuntimeDates(start=start, finish=max(finishes, default=None))


def is_terminatable_status(status: ExecutionStatus) -> bool:
    return status in (ExecutionStatus.CREATED, ExecutionStatus.SCHEDULED, ExecutionStatus.RUNNING)


def _calculate_level_status(
    level: JobHierarchyLevel,
    group_levels: tuple[LevelSpecKey, ...],
    job_statuses: Mapping[FullSpecKey, ExecutionStatus],
) -> ExecutionStatus:
    children = []

    for level_key in level.fields:
        own_levels = (*group_levels, level_key)
        child_level = level.child_groups.get(level_key)

        if child_level is None:
            children.append(job_statuses[level_keys_to_full_key(own_levels)])
            continue

        children.append(_calculate_level_status(level=child_level, group_levels=own_levels, job_statuses=job_statuses))

    return aggregate_group_status(children=children, style=level.rule)
