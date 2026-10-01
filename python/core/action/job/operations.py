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

from collections.abc import Iterable, Sequence
from typing import Literal

from core.action.types import (
    UNFINISHED_STATUSES,
    ExecutionStatus,
    RichJob,
    RuntimeDates,
    StateChanges,
)
from core.result import Fail, Success

TaskCompletionStatus = Literal[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.ABORTED]

# CREATED is the one unfinished status that says nothing is going on yet, so it's never "in progress"
_IN_PROGRESS_STATUSES = frozenset(UNFINISHED_STATUSES).difference((ExecutionStatus.CREATED,))
_FAILURE_STATUSES = frozenset((ExecutionStatus.FAILED, ExecutionStatus.BROKEN))


_TERMINATION_FLOW_STATUSES = frozenset(
    {ExecutionStatus.REVOKING, ExecutionStatus.TERMINATING, ExecutionStatus.REVOKED, ExecutionStatus.ABORTED}
)


def calculate_task_final_status(
    job_statuses: Iterable[ExecutionStatus], task_is_aborted: bool
) -> Success[TaskCompletionStatus] | Fail[str]:
    if task_is_aborted:
        return Success(ExecutionStatus.ABORTED)

    # broken job is a leftover of runner's crash, not a result of its execution,
    # so it can't tell whether task succeeded or not
    considered = set(job_statuses).difference(UNFINISHED_STATUSES).difference({ExecutionStatus.BROKEN})

    if not considered:
        return Fail("Task has no jobs in a final status, so its result can't be determined")

    if considered.issubset(_TERMINATION_FLOW_STATUSES):
        return Success(ExecutionStatus.ABORTED)

    if ExecutionStatus.FAILED in considered:
        return Success(ExecutionStatus.FAILED)

    return Success(ExecutionStatus.SUCCESS)


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


def aggregate_group_status(children: Iterable[ExecutionStatus]) -> ExecutionStatus:
    """
    Derive a group's status from its children's statuses.

    A subgroup counts as a single child with its own derived status.
    """

    statuses = set(children)

    if statuses.intersection(_IN_PROGRESS_STATUSES):
        return ExecutionStatus.RUNNING

    if statuses.intersection(_FAILURE_STATUSES):
        return ExecutionStatus.FAILED

    if statuses == {ExecutionStatus.CREATED}:
        return ExecutionStatus.CREATED

    if ExecutionStatus.CREATED in statuses:
        return ExecutionStatus.RUNNING

    if statuses == {ExecutionStatus.SUCCESS}:
        return ExecutionStatus.SUCCESS

    if statuses == {ExecutionStatus.REVOKED}:
        return ExecutionStatus.REVOKED

    # what's left is a mix of SUCCESS, ABORTED and REVOKED
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
