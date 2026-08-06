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
import logging

from cm.impl.job.repo import JobRepo
from cm.legacy.services.concern.locks import delete_task_flag_concern, delete_task_lock_concern
from cm.legacy.status_api import send_task_status_update_event
from core.action import ExecutionStatus
from core.action.job import JobRepoI, JobUpdateDTO, TaskUpdateDTO
from core.types import PID
from django.db import connection
from django.db.transaction import atomic
from django.db.utils import ProgrammingError
from psycopg import errors as pg_errors

from jobs.scheduler import repo
from jobs.scheduler.types import CELERY_RUNNING_STATES, UTC, CeleryTaskState, TaskShortInfo, WorkerTaskID

logger = logging.getLogger("scheduler.main")


def set_status_on_success(from_status: ExecutionStatus, to_status: ExecutionStatus):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo: JobRepoI = kwargs["job_repo"]

            res = func(*args, **kwargs)
            updated = job_repo.change_task_status(id=task_id, previous=from_status, new=to_status)
            if updated:
                logger.info(f"Task #{task_id} is {to_status.value}")

                with suppress(Exception):
                    send_task_status_update_event(task_id=task_id, status=to_status.value)

            return res

        return wrapper

    return decorator


def set_status_on_fail(
    to_status: ExecutionStatus,
    errors: type[Exception] | tuple[type[Exception]],
    return_: bool = False,
    from_status: ExecutionStatus | None = None,
):
    if not isinstance(errors, tuple):
        errors = (errors,)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_id = kwargs["task_id"]
            job_repo: JobRepoI = kwargs["job_repo"]

            try:
                return func(*args, **kwargs)
            except errors:
                logger.exception("Something gone wrong, status of task #%d will be set to %s", task_id, to_status)

                status_set = None
                if from_status:
                    updated = job_repo.change_task_status(id=task_id, previous=from_status, new=to_status)
                    if updated:
                        status_set = to_status
                else:
                    job_repo.update_task(id=task_id, data=TaskUpdateDTO(status=to_status))
                    status_set = to_status

                if status_set:
                    logger.info("Task #%d is %s", task_id, to_status)

                    with suppress(Exception):
                        send_task_status_update_event(task_id=task_id, status=to_status.value)

                return return_

        return wrapper

    return decorator


def clear_concerns_on_error(func):
    scheduler_repo = repo

    @wraps(func)
    def wrapper(*args, **kwargs):
        task_id = kwargs["task_id"]

        try:
            return func(*args, **kwargs)
        except Exception:
            task = scheduler_repo.retrieve_task(task_id=task_id)

            if task.lock_id:
                delete_task_lock_concern(task_id=task.id)
            else:
                delete_task_flag_concern(task_id=task.id)

            raise

    return wrapper


def retrieve_celery_task_state(worker_id: WorkerTaskID) -> CeleryTaskState:
    from jobs.worker.celery.worker import app

    table = "celery_taskmeta"
    fields = "status, worker"
    condition = f"task_id = '{worker_id}'"

    try:
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {fields} FROM {table} WHERE {condition};")  # noqa: S608
            row = cursor.fetchone()
    except ProgrammingError as error:
        if not isinstance(error.__cause__, pg_errors.UndefinedTable):
            raise
        # Table is created lazily by celery's result backend (its SessionManager.prepare_models, race-safe via retry)
        # on first use; it's absent only when no worker has ever stored a result in this database,
        # which carries the same meaning as "no row for this task".
        row = None

    if not row:
        return CeleryTaskState.ADCM_UNREACHABLE

    status_raw, hostname = row

    status = CeleryTaskState(status_raw.upper())

    if status in CELERY_RUNNING_STATES:
        # ping() returns one single-entry dict per responding worker, keyed by its hostname:
        # [{"celery@host1": {"ok": "pong"}}, {"celery@host2": {"ok": "pong"}}]
        alive_workers: set[str] = set()
        for reply in app.control.ping():
            alive_workers.update(reply.keys())

        if hostname not in alive_workers:
            return CeleryTaskState.FAILURE

    return status


@atomic
def finalize_task(task: TaskShortInfo, status: ExecutionStatus):
    """Set `status` to task and all it's unfinished jobs, remove locks/flags"""

    job_repo = JobRepo()
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
