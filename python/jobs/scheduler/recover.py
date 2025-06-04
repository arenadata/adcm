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

import datetime

from cm.services.concern.locks import delete_task_flag_concern, delete_task_lock_concern
from cm.services.job.run.repo import JobRepoImpl
from core.job.dto import JobUpdateDTO, TaskUpdateDTO
from core.job.types import ExecutionStatus
from jobs.scheduler import repo as SchedulerRepo  # noqa: N812
from jobs.scheduler._logger import logger
from jobs.scheduler._types import LiveCheckResult, TaskRunnerEnvironment, TaskShortInfo
import zoneinfo

UTC = zoneinfo.ZoneInfo("UTC")


def _is_alive_local(task: TaskShortInfo) -> LiveCheckResult:
    _ = task
    # tasks in local environment are always considered dead on ADCM restart
    return LiveCheckResult(is_dead=True, status=ExecutionStatus.ABORTED)


LIVE_CHECKERS = {
    TaskRunnerEnvironment.LOCAL: _is_alive_local,
    TaskRunnerEnvironment.CELERY: ...,  # TODO
}


def recover_statuses() -> None:
    scheduler_repo = SchedulerRepo
    job_repo = JobRepoImpl
    now = datetime.datetime.now(tz=UTC)

    logger.info("Actualizing task statuses...")

    for task in scheduler_repo.retrieve_unfinished_tasks():
        env = task.worker.get("environment")
        if not env:
            logger.debug(f"Task #{task.id} skipped, worker environment is not specified")
            continue

        live_check_result: LiveCheckResult = LIVE_CHECKERS[env](task)

        if live_check_result.is_dead:
            job_repo.update_task(id=task.id, data=TaskUpdateDTO(status=live_check_result.status, finish_date=now))

            for job_id in scheduler_repo.retrieve_unfinished_task_jobs(task_id=task.id):
                job_repo.update_job(id=job_id, data=JobUpdateDTO(status=live_check_result.status, finish_date=now))

            if task.lock_id:
                delete_task_lock_concern(task_id=task.id)
            else:
                delete_task_flag_concern(task_id=task.id)

    logger.info("Task statuses updated")
