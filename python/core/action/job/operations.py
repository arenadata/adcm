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
from itertools import chain
from typing import Literal

from core.action.types import (
    UNFINISHED_STATUSES,
    ExecutionStatus,
    RichJob,
    StateChanges,
)
from core.result import Fail, Success

TaskCompletionStatus = Literal[ExecutionStatus.SUCCESS, ExecutionStatus.FAILED, ExecutionStatus.ABORTED]


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

    `jobs` are expected in `flatten_execution_plan` order, "first" is relative to it.
    """

    if task_result == ExecutionStatus.ABORTED:
        return StateChanges()

    if task_result == ExecutionStatus.SUCCESS:
        return on_success

    failed_on_fail = tuple(job.spec.on_fail for job in jobs if job.runtime.status == ExecutionStatus.FAILED)

    state = next((changes.state for changes in failed_on_fail if changes.state), None) or on_fail.state
    multi_state_set = (
        tuple(set(chain.from_iterable(changes.multi_state_set for changes in failed_on_fail)))
        or on_fail.multi_state_set
    )
    multi_state_unset = (
        tuple(set(chain.from_iterable(changes.multi_state_unset for changes in failed_on_fail)))
        or on_fail.multi_state_unset
    )

    return StateChanges(state=state, multi_state_set=multi_state_set, multi_state_unset=multi_state_unset)


def is_terminatable_status(status: ExecutionStatus) -> bool:
    return status in (ExecutionStatus.CREATED, ExecutionStatus.SCHEDULED, ExecutionStatus.RUNNING)
