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

from contextlib import suppress
from datetime import datetime
from functools import wraps
import os
import errno

from celery.result import AsyncResult
from cm.services.concern.locks import delete_task_flag_concern, delete_task_lock_concern
from cm.services.job.run.repo import JobRepoImpl
from cm.status_api import send_task_status_update_event
from core.job.dto import JobUpdateDTO, TaskUpdateDTO
from core.job.types import ExecutionStatus
from core.types import PID
from django.db.transaction import atomic

from jobs.scheduler import repo
from jobs.scheduler._types import UTC, CeleryTaskState, TaskShortInfo, WorkerID
from jobs.scheduler.logger import logger
from jobs.worker.app import app


def set_status_on_success(status: ExecutionStatus):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo = kwargs["job_repo"]

            res = func(*args, **kwargs)
            job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=status))
            logger.info(f"Task #{task_id} is {status}")

            with suppress(Exception):
                send_task_status_update_event(task_id=task_id, status=status.value)

            return res

        return wrapper

    return decorator


def set_status_on_fail(
    status: ExecutionStatus, errors: type[Exception] | tuple[type[Exception]], return_: bool = False
):
    if not isinstance(errors, tuple):
        errors = (errors,)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo = kwargs["job_repo"]

            try:
                return func(*args, **kwargs)
            except errors:
                job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=status))
                logger.exception(f"Task #{task_id} is {status}")

                with suppress(Exception):
                    send_task_status_update_event(task_id=task_id, status=status.value)

                return return_

        return wrapper

    return decorator


def retrieve_celery_task_state(worker_id: WorkerID) -> CeleryTaskState:
    async_result = AsyncResult(worker_id, app=app)

    try:
        return CeleryTaskState(async_result.state.upper())
    except AttributeError:
        return CeleryTaskState.ADCM_UNREACHABLE


@atomic
def finalize_task(task: TaskShortInfo, status: ExecutionStatus):
    """Set `status` to task and all it's unfinished jobs, remove locks/flags"""

    job_repo = JobRepoImpl
    scheduler_repo = repo

    now = datetime.now(tz=UTC)

    job_repo.update_task(id=task.id, data=TaskUpdateDTO(status=status, finish_date=now))

    for job_id in scheduler_repo.retrieve_unfinished_task_jobs(task_id=task.id):
        job_repo.update_job(id=job_id, data=JobUpdateDTO(status=status, finish_date=now))

    if task.lock_id:
        delete_task_lock_concern(task_id=task.id)
    else:
        delete_task_flag_concern(task_id=task.id)

    logger.debug(f"Task #{task.id} is finalized with status {status}")


def is_pid_exists(pid: PID) -> bool:
    """
    Sends a special signal `0` to `pid`.
    `0` signal is not sends an actual signal, but performs error checking.
    Possible errors are: EINVAL (invalid signal), EPERM (no permissions), ESRCH (no process)
        Source: man 2 kill
    """

    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:  # No such process
            return False

        elif err.errno == errno.EPERM:  # Permission error, process exists
            return True

        raise

    return True
