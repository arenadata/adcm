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

import os
import time
import errno

from celery.result import AsyncResult
from cm.services.job.run.repo import JobRepoImpl
from core.job.dto import JobUpdateDTO, TaskUpdateDTO
from core.job.types import ExecutionStatus
from jobs.scheduler import repo as SchedulerRepo  # noqa: N812
from jobs.scheduler._logger import logger
from jobs.scheduler._types import TaskRunnerEnvironment, TaskShortInfo

TASK_HEALTHCHECK_INTERVAL = int(os.environ.get("TASK_HEALTHCHECK_INTERVAL", 60))
CELERY_RUNNING_STATES = {"PENDING", "STARTED", "RETRY"}


def _is_alive_local(task: TaskShortInfo) -> bool:
    worker_id = task.worker.get("worker_id")
    if not worker_id:
        logger.warning(f"Task #{task.id} worker is not specified.")
        return False

    if worker_id <= 1:
        raise ValueError("Specify a valid PID (>=2)")

    try:
        os.kill(worker_id, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:  # No such process
            return False

        elif err.errno == errno.EPERM:  # Permission error, process exists
            return True

        else:  # According to "man 2 kill" possible error values are (EINVAL, EPERM, ESRCH)
            raise

    return True


def _is_alive_celery(task: TaskShortInfo) -> bool:
    worker_id = task.worker.get("worker_id")
    if not worker_id:
        logger.info(f"Task #{task.id} worker is not specified. Considering ABORTED")
        return False

    result = AsyncResult(worker_id)

    try:
        return result.state in CELERY_RUNNING_STATES
    except AttributeError:
        logger.exception(f"Can't check celery worker {worker_id}, considering task #{task.id} ABORTED")
        return False


ALIVE_CHECKS_REGISTRY = {
    TaskRunnerEnvironment.LOCAL: _is_alive_local,
    TaskRunnerEnvironment.CELERY: _is_alive_celery,
}


def run_monitor_in_loop() -> None:
    scheduler_repo = SchedulerRepo
    job_repo = JobRepoImpl

    logger.info(f"Monitor started (pid: {os.getpid()})")

    while True:
        time.sleep(TASK_HEALTHCHECK_INTERVAL)

        for running_task in scheduler_repo.retrieve_running_tasks():
            env = running_task.worker.get("environment")
            if not ALIVE_CHECKS_REGISTRY[env](task=running_task):
                job_repo.update_task(id=running_task.id, data=TaskUpdateDTO(status=ExecutionStatus.ABORTED))

                for job_id in scheduler_repo.retrieve_unfinished_task_jobs(task_id=running_task.id):
                    job_repo.update_job(id=job_id, data=JobUpdateDTO(status=ExecutionStatus.ABORTED))
