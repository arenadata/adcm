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

from typing import Generator, Sequence

from cm.models import UNFINISHED_STATUS, Action, ConcernItem, JobLog, TaskLog
from core.job.types import ExecutionStatus
from core.types import ActionID, ConcernID, JobID, TaskID
from jobs.scheduler._types import TaskShortInfo


def retrieve_task_orm(task_id: TaskID) -> TaskLog:
    return TaskLog.objects.get(id=task_id)


def retrieve_action_orm(action_id: ActionID) -> Action:
    return Action.objects.get(id=action_id)


def retrieve_unfinished_tasks() -> Generator[TaskShortInfo, None, None]:
    for id_, executor, status, lock_id in TaskLog.objects.filter(status__in=UNFINISHED_STATUS).values_list(
        "id", "executor", "status", "lock_id"
    ):
        yield TaskShortInfo(id=id_, worker=executor, status=ExecutionStatus[status.upper()], lock_id=lock_id)


def retrieve_unfinished_task_jobs(task_id: TaskID) -> set[JobID]:
    return set(JobLog.objects.filter(task_id=task_id, status__in=UNFINISHED_STATUS).values_list("id", flat=True))


def delete_concerns(ids: Sequence[ConcernID]) -> None:
    ConcernItem.objects.filter(id__in=ids).delete()
