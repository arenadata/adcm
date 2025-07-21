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

from functools import partial

from core.job.types import ExecutionStatus
from core.types import ConcernID

from jobs.scheduler import repo
from jobs.scheduler._types import (
    CELERY_STATE_ADCM_STATUS_MAP,
    CeleryTaskState,
    LiveCheckResult,
    TaskRunnerEnvironment,
    TaskShortInfo,
)
from jobs.scheduler.logger import logger
from jobs.scheduler.utils import finalize_task, retrieve_celery_task_state


def _is_alive_local(task: TaskShortInfo) -> LiveCheckResult:
    _ = task
    # tasks in local environment are always considered dead on ADCM restart
    return LiveCheckResult(is_dead=True, status=ExecutionStatus.ABORTED)


def _is_alive_celery(task: TaskShortInfo) -> LiveCheckResult:
    if task.status == ExecutionStatus.SCHEDULED:
        return LiveCheckResult(is_dead=True, status=ExecutionStatus.REVOKED)

    celery_state = retrieve_celery_task_state(worker_id=task.worker["worker_id"])
    if celery_state == CeleryTaskState.ADCM_UNREACHABLE:
        logger.warning(f"Can't check Task #{task.id} status ({task.worker}). Considering broken.")
        return LiveCheckResult(is_dead=True, status=ExecutionStatus.BROKEN)

    adcm_task_status = CELERY_STATE_ADCM_STATUS_MAP[celery_state]

    return LiveCheckResult(is_dead=adcm_task_status.is_final, status=adcm_task_status.recover_status)


LIVE_CHECKERS = {
    TaskRunnerEnvironment.LOCAL: _is_alive_local,
    TaskRunnerEnvironment.CELERY: _is_alive_celery,
}


def recover_statuses(tasks_filter: dict | None = None) -> None:
    logger.info(f"Actualizing task statuses ({tasks_filter=}) ...")

    retriever = repo.retrieve_unfinished_tasks if tasks_filter is None else partial(repo.retrieve_tasks, **tasks_filter)
    for task in retriever():
        env = task.worker.get("environment")

        if not env:
            logger.warning(f"Task #{task.id} skipped, worker environment is not specified")
            continue

        live_check_result: LiveCheckResult = LIVE_CHECKERS[env](task)
        if live_check_result.is_dead:
            finalize_task(task=task, status=live_check_result.status)

    logger.info("Task statuses updated")


def actualize_locks():
    to_delete: set[ConcernID] = set()
    to_recheck: set[ConcernID] = set()

    for lock_id, task_id in repo.retrieve_concern_tasks():
        if task_id:
            to_recheck.add(task_id)
        else:
            to_delete.add(lock_id)

    if to_delete:
        repo.delete_concerns(ids=to_delete)

    if to_recheck:
        recover_statuses(tasks_filter={"id__in": to_recheck})
