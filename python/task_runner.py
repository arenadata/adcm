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

# pylint: disable=unused-import
# pylint: disable=useless-return
# pylint: disable=protected-access
# pylint: disable=bare-except
# pylint: disable=global-statement


import os
import json
import signal
import subprocess
import sys
import time
from datetime import timedelta
import shutil

import adcm.init_django
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

import cm.config as config
import cm.job
from cm.logger import log
from cm.models import TaskLog, JobLog, LogStorage, ADCM, ConfigLog


TASK_ID = 0


def log_rotation():
    adcm_object = ADCM.objects.get(id=1)
    config_log = ConfigLog.objects.get(obj_ref=adcm_object.config)
    adcm_config = json.loads(config_log.config)
    log_rotation_on_db = adcm_config['job_log']['log_rotation_in_db']
    log_rotation_on_fs = adcm_config['job_log']['log_rotation_on_fs']
    rotation_jobs_on_db = []
    rotation_jobs_on_fs = []

    for job in JobLog.objects.all():
        finish_date = job.finish_date

        if log_rotation_on_db > 0:
            if finish_date < timezone.now() - timedelta(days=log_rotation_on_db):
                rotation_jobs_on_db.append(job.id)

        if log_rotation_on_fs > 0:
            if finish_date < timezone.now() - timedelta(days=log_rotation_on_fs):
                rotation_jobs_on_fs.append(job.id)

    LogStorage.objects.filter(job_id__in=rotation_jobs_on_db).delete()
    log.info('rotation log from db, jobs: %s',
             ', '.join([str(job_id) for job_id in rotation_jobs_on_db]))

    for job_id in rotation_jobs_on_fs:
        shutil.rmtree(os.path.join(config.RUN_DIR, str(job_id)))

    log.info('rotation log from fs, jobs: %s',
             ', '.join([str(job_id) for job_id in rotation_jobs_on_fs]))


def terminate_job(task, jobs):
    running_job = jobs.get(status=config.Job.RUNNING)

    if running_job.pid:
        os.kill(running_job.pid, signal.SIGTERM)
        cm.job.finish_task(task, running_job, config.Job.ABORTED)
    else:
        cm.job.finish_task(task, None, config.Job.ABORTED)


def terminate_task(signum, frame):
    log.info("cancel task #%s, signal: #%s", TASK_ID, signum)
    task = TaskLog.objects.get(id=TASK_ID)
    jobs = JobLog.objects.filter(task_id=TASK_ID)

    i = 0
    while i < 10:
        if jobs.filter(status=config.Job.RUNNING):
            terminate_job(task, jobs)
            break
        i += 1
        time.sleep(0.5)

    if i == 10:
        log.warning("no jobs running for task #%s", TASK_ID)
        cm.job.finish_task(task, None, config.Job.ABORTED)

    os._exit(signum)


signal.signal(signal.SIGTERM, terminate_task)


def run_job(task_id, job_id, err_file):
    log.debug("run job #%s of task #%s", job_id, task_id)
    try:
        proc = subprocess.Popen([
            os.path.join(config.CODE_DIR, 'job_runner.py'),
            str(job_id)
        ], stderr=err_file)
        res = proc.wait()
        return res
    except:
        log.error("exception runnung job %s", job_id)
        return 1


def set_body_ansible(job):
    log_storage = LogStorage.objects.filter(job=job, name='ansible')
    for ls in log_storage:
        file_path = os.path.join(config.RUN_DIR, f'{ls.job.id}', f'ansible-{ls.type}.{ls.format}')
        with open(file_path, 'r') as f:
            body = f.read()
        LogStorage.objects.filter(job=job, name=ls.name, type=ls.type).update(body=body)


def run_task(task_id, args=None):
    log.debug("task_runner.py called as: %s", sys.argv)
    try:
        task = TaskLog.objects.get(id=task_id)
    except ObjectDoesNotExist:
        log.error("no task %s", task_id)
        return

    jobs = JobLog.objects.filter(task_id=task.id).order_by('id')
    if not jobs:
        log.error("no jobs for task %s", task.id)
        cm.job.finish_task(task, None, config.Job.FAILED)
        return

    err_file = open(os.path.join(config.LOG_DIR, 'job_runner.err'), 'a+')

    log.info("run task #%s", task_id)

    job = None
    count = 0
    res = 0
    for job in jobs:
        if args == 'restart' and job.status == config.Job.SUCCESS:
            log.info('skip job #%s status "%s" of task #%s', job.id, job.status, task_id)
            continue
        if count:
            cm.job.re_prepare_job(task, job)
        job.start_date = timezone.now()
        job.save()
        res = run_job(task.id, job.id, err_file)
        set_body_ansible(job)
        count += 1
        if res != 0:
            break

    if res == 0:
        cm.job.finish_task(task, job, config.Job.SUCCESS)
    else:
        cm.job.finish_task(task, job, config.Job.FAILED)

    err_file.close()

    log.info("finish task #%s, ret %s", task_id, res)

    log_rotation()


def do():
    global TASK_ID
    if len(sys.argv) < 2:
        print("\nUsage:\n{} task_id [restart]\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    elif len(sys.argv) > 2:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1], sys.argv[2])
    else:
        TASK_ID = sys.argv[1]
        run_task(sys.argv[1])


if __name__ == '__main__':
    do()
