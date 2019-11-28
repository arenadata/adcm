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

import os
import sys
import subprocess

import adcm.init_django  # pylint: disable=unused-import

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from cm.models import TaskLog, JobLog

from cm.logger import log
import cm.config as config
import cm.job


def open_file(root, tag, task_id):
    file_path = "{}/{}-{}.txt".format(root, task_id, tag)
    file_descriptor = open(file_path, 'w')
    return file_descriptor


def run_job(task_id, job_id, out_file, err_file):
    log.debug("run job #%s of task #%s", job_id, task_id, )
    try:
        process = subprocess.Popen([
            '{}/job_runner.py'.format(config.BASE_DIR),
            str(job_id)
        ], stdout=out_file, stderr=err_file)
        code = process.wait()
        return code
    except:  # pylint: disable=bare-except
        log.error("exception running job %s", job_id)
        return 1


def get_task(task_id):
    try:
        return TaskLog.objects.get(id=task_id)
    except ObjectDoesNotExist:
        log.error("no task %s", task_id)
        return


def get_jobs(task):
    jobs = JobLog.objects.filter(task_id=task.id).order_by('id')
    return jobs


def run_task(task_id, args=None):
    log.debug("task_runner.py called as: %s", sys.argv)
    task = get_task(task_id)
    if task is None:
        return

    jobs = get_jobs(task)
    if not jobs:
        log.error("no jobs for task %s", task.id)
        cm.job.finish_task(task, None, config.Job.FAILED)
        return

    out_file = open_file(config.LOG_DIR, 'task-out', task_id)
    err_file = open_file(config.LOG_DIR, 'task-err', task_id)

    log.info("run task #%s", task_id)
    cm.job.set_task_status(task, config.Job.RUNNING)

    job = None
    code = 1
    count = 0
    for job in jobs:
        if args == 'restart' and job.status == config.Job.SUCCESS:
            log.info('skip job #%s status "%s" of task #%s', job.id, job.status, task_id)
            continue
        if count:
            cm.job.re_prepare_job(task, job)
        job.start_date = timezone.now()
        job.save()
        code = run_job(task.id, job.id, out_file, err_file)
        count += 1
        if code != 0:
            break

    if code == 0:
        cm.job.finish_task(task, job, config.Job.SUCCESS)
    else:
        cm.job.finish_task(task, job, config.Job.FAILED)

    out_file.close()
    err_file.close()

    log.info("finish task #%s, ret %s", task_id, code)


def do():
    if len(sys.argv) < 2:
        print("\nUsage:\n{} task_id [restart]\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    elif len(sys.argv) > 2:
        run_task(sys.argv[1], sys.argv[2])
    else:
        run_task(sys.argv[1])


if __name__ == '__main__':
    do()
