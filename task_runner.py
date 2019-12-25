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
import signal
import subprocess
import sys
import time

import adcm.init_django  # pylint: disable=unused-import
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

import cm.config as config
import cm.job
from cm.logger import log
from cm.models import TaskLog, JobLog


def open_file(root, tag, task_id):
    fname = "{}/{}-{}.txt".format(root, task_id, tag)
    f = open(fname, 'w')
    return f


def run_job(task_id, job_id, out_file, err_file):
    log.debug("run job #%s of task #%s", job_id, task_id)
    try:
        proc = subprocess.Popen([
            '{}/job_runner.py'.format(config.BASE_DIR),
            str(job_id)
        ], stdout=out_file, stderr=err_file)
        res = proc.wait()
        return res
    except:  # pylint: disable=bare-except
        log.error("exception runnung job %s", job_id)
        return 1


def run_task(task_id, args=None):
    def terminate_task(signum, frame):  # pylint: disable=useless-return
        log.info("cancel task #%s, signal: #%s", task_id, signum)
        _task = TaskLog.objects.get(id=task_id)
        if _task.status == config.Job.CREATED:
            cm.job.finish_task(_task, None, config.Job.ABORTED)
        else:
            created_jobs = JobLog.objects.filter(task_id=task_id, status=config.Job.CREATED)
            if created_jobs:
                while True:
                    time.sleep(0.5)
                    try:
                        running_job = JobLog.objects.get(task_id=task_id, status=config.Job.RUNNING)
                        break
                    except JobLog.DoesNotExist:
                        pass
            else:
                running_job = JobLog.objects.get(task_id=task_id, status=config.Job.RUNNING)

            if running_job and running_job.pid:
                os.kill(running_job.pid, signal.SIGTERM)
                cm.job.finish_task(_task, running_job, config.Job.ABORTED)
            else:
                cm.job.finish_task(_task, None, config.Job.ABORTED)

        out_file.close()
        err_file.close()
        os._exit(signum)  # pylint: disable=protected-access

    signal.signal(signal.SIGTERM, terminate_task)

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

    out_file = open_file(config.LOG_DIR, 'task-out', task_id)
    err_file = open_file(config.LOG_DIR, 'task-err', task_id)

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
        res = run_job(task.id, job.id, out_file, err_file)
        count += 1
        if res != 0:
            break

    if res == 0:
        cm.job.finish_task(task, job, config.Job.SUCCESS)
    else:
        cm.job.finish_task(task, job, config.Job.FAILED)

    out_file.close()
    err_file.close()

    log.info("finish task #%s, ret %s", task_id, res)


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
