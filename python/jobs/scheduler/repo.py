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

from adcm.settings import (
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_TURN_ON_MM_ACTION_NAME,
)
from cm.models import UNFINISHED_STATUS, Action, ConcernItem, ConcernType, JobLog, JobStatus, TaskLog
from core.job.types import ExecutionStatus
from core.types import ActionID, ConcernID, JobID, TaskID

from jobs.scheduler._types import ActionShortInfo, TaskShortInfo

_FIELDS = ("id", "executor", "status", "lock_id", "action_id", "action__name")
MM_ACTION_NAMES = {
    ADCM_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
}


def retrieve_task_orm(task_id: TaskID) -> TaskLog:
    return TaskLog.objects.get(id=task_id)


def retrieve_action_orm(action_id: ActionID) -> Action:
    return Action.objects.get(id=action_id)


def retrieve_task(task_id: TaskID) -> TaskShortInfo:
    return next(retrieve_tasks(id=task_id))


def retrieve_tasks(**kwargs) -> Generator[TaskShortInfo, None, None]:
    for id_, executor, status, lock_id, action_id, action_name in TaskLog.objects.filter(**kwargs).values_list(
        *_FIELDS
    ):
        yield TaskShortInfo(
            id=id_,
            worker=executor,
            status=ExecutionStatus[status.upper()],
            lock_id=lock_id,
            action=ActionShortInfo(id=action_id, is_mm_action=action_name in MM_ACTION_NAMES),
        )


def retrieve_unfinished_tasks() -> Generator[TaskShortInfo, None, None]:
    yield from retrieve_tasks(status__in=UNFINISHED_STATUS)


def retrieve_unfinished_task_jobs(task_id: TaskID) -> set[JobID]:
    return set(JobLog.objects.filter(task_id=task_id, status__in=UNFINISHED_STATUS).values_list("id", flat=True))


def retrieve_running_tasks() -> Generator[TaskShortInfo, None, None]:
    yield from retrieve_tasks(status=JobStatus.RUNNING)


def delete_concerns(ids: Sequence[ConcernID]) -> None:
    ConcernItem.objects.filter(id__in=ids).delete()


def retrieve_concern_tasks(
    type_: ConcernType = ConcernType.LOCK,
) -> Generator[tuple[ConcernID, TaskID | None], None, None]:
    yield from ConcernItem.objects.filter(type=type_).values_list("id", "tasklog")
