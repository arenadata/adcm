#!/usr/bin/env python3
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
# pylint: disable=wrong-import-order

import os
import signal
import subprocess
import sys
import time
from logging import getLogger

import adcm.init_django  # pylint: disable=unused-import

from cm.errors import AdcmEx
from cm.job import finish_task, re_prepare_job
from cm.logger import logger
from cm.models import JobLog, JobStatus, LogStorage, TaskLog
from cm.status_api import UpdateEventType, update_event
from cm.utils import get_env_with_venv_path
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

error_logger = getLogger("task_runner_err")
TASK_ID = 0


def terminate_job(task, jobs):
    running_job = jobs.get(status=JobStatus.RUNNING)

    if running_job.pid:
        try:
            os.kill(running_job.pid, signal.SIGTERM)
        except OSError as e:
            raise AdcmEx("NOT_ALLOWED_TERMINATION", f"Failed to terminate process: {e}") from e
        finish_task(task, running_job, JobStatus.ABORTED)
    else:
        finish_task(task, None, JobStatus.ABORTED)


def terminate_task(signum, frame):  # pylint: disable=unused-argument
    logger.info("cancel task #%s, signal: #%s", TASK_ID, signum)
    task = TaskLog.objects.get(id=TASK_ID)
    jobs = JobLog.objects.filter(task_id=TASK_ID)

    i = 0
    while i < 10:
        if jobs.filter(status=JobStatus.RUNNING):
            terminate_job(task, jobs)
            break
        i += 1
        time.sleep(0.5)

    if i == 10:
        logger.warning("no jobs running for task #%s", TASK_ID)
        finish_task(task, None, JobStatus.ABORTED)

    sys.exit(signum)


signal.signal(signal.SIGTERM, terminate_task)


def run_job(task_id, job_id, err_file):
    logger.debug("task run job #%s of task #%s", job_id, task_id)
    cmd = [
        str(settings.CODE_DIR / "job_runner.py"),
        str(job_id),
    ]
    logger.info("task run job cmd: %s", " ".join(cmd))

    try:
        # pylint: disable=consider-using-with
        proc = subprocess.Popen(
            args=cmd, stderr=err_file, env=get_env_with_venv_path(venv=TaskLog.objects.get(id=task_id).action.venv)
        )
        res = proc.wait()
        return res
    except Exception as error:  # pylint: disable=broad-except
        logger.error("exception running job %s: %s", job_id, error)
        return 1


def set_log_body(job):
    name = job.sub_action.script_type if job.sub_action else job.action.script_type
    log_storages = LogStorage.objects.filter(job=job, name=name, type__in=["stdout", "stderr"])
    for log_storage in log_storages:
        file_path = (
            settings.RUN_DIR / f"{log_storage.job.id}" / f"{log_storage.name}-{log_storage.type}.{log_storage.format}"
        )
        with open(file_path, encoding=settings.ENCODING_UTF_8) as f:
            body = f.read()

        LogStorage.objects.filter(job=job, name=log_storage.name, type=log_storage.type).update(body=body)


def run_task(task_id: int, args: str | None = None) -> None:  # pylint: disable=too-many-statements,too-many-branches
    logger.debug("task_runner.py called as: %s", sys.argv)
    try:
        task = TaskLog.objects.get(id=task_id)
    except ObjectDoesNotExist:
        logger.error("no task %s", task_id)

        return

    task.pid = os.getpid()
    task.restore_hc_on_fail = True
    task.start_date = timezone.now()
    task.status = JobStatus.RUNNING
    task.save(update_fields=["pid", "restore_hc_on_fail", "start_date", "status"])

    update_event(object_=task, update=(UpdateEventType.STATUS, JobStatus.RUNNING))

    jobs = JobLog.objects.filter(task_id=task.id).order_by("id")
    if not jobs:
        logger.error("no jobs for task %s", task.id)
        finish_task(task, None, JobStatus.FAILED)

        return

    err_file = open(  # pylint: disable=consider-using-with
        settings.LOG_DIR / "job_runner.err",
        "a+",
        encoding=settings.ENCODING_UTF_8,
    )

    logger.info("run task #%s", task_id)

    job = None
    count = 0
    res = 0
    for job in jobs:
        try:
            job.refresh_from_db()
            if args == "restart" and job.status == JobStatus.SUCCESS:
                logger.info('skip job #%s status "%s" of task #%s', job.id, job.status, task_id)
                continue

            task.refresh_from_db()
            re_prepare_job(task, job)
            res = run_job(task.id, job.id, err_file)
            set_log_body(job)

            # For multi jobs task object state and/or config can be changed by adcm plugins
            if task.task_object is not None:
                try:
                    task.task_object.refresh_from_db()
                except ObjectDoesNotExist:
                    task.object_id = 0
                    task.object_type = None

            job.refresh_from_db()
            count += 1
            if res != 0:
                task.refresh_from_db()
                if job.status == JobStatus.ABORTED and task.status != JobStatus.ABORTED:
                    continue

                break
        except Exception:  # pylint: disable=broad-exception-caught
            error_logger.exception("Task #%s: Error processing job #%s", task_id, job.pk)
            res = 1
            break

    if job is not None:
        job.refresh_from_db()

    if job is not None and job.status == JobStatus.ABORTED:
        finish_task(task, job, JobStatus.ABORTED)
    elif res == 0:
        finish_task(task, job, JobStatus.SUCCESS)
    else:
        finish_task(task, job, JobStatus.FAILED)

    err_file.close()

    logger.info("finish task #%s, ret %s", task_id, res)


def do_task():
    global TASK_ID  # pylint: disable=global-statement

    if len(sys.argv) < 2:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} task_id [restart]\n")
        sys.exit(4)
    elif len(sys.argv) > 2:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1], sys.argv[2])
    else:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1])


if __name__ == "__main__":
    do_task()
