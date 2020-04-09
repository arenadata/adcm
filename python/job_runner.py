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
import json
import subprocess

import adcm.init_django		# pylint: disable=unused-import

from cm.logger import log
import cm.config as config
import cm.job
from cm.status_api import Event


def open_file(root, tag, job_id):
    fname = '{}/{}/{}.txt'.format(root, job_id, tag)
    f = open(fname, 'w')
    return f


def read_config(job_id):
    fd = open('{}/{}/config.json'.format(config.RUN_DIR, job_id))
    conf = json.load(fd)
    fd.close()
    return conf


def set_job_status(job_id, ret, pid, event):
    if ret == 0:
        cm.job.set_job_status(job_id, config.Job.SUCCESS, event, pid)
        return 0
    elif ret == -15:
        cm.job.set_job_status(job_id, config.Job.ABORTED, event, pid)
        return 15
    else:
        cm.job.set_job_status(job_id, config.Job.FAILED, event, pid)
        return ret


def set_pythonpath():
    cmd_env = os.environ.copy()
    if "PYTHONPATH" in cmd_env:
        cmd_env["PYTHONPATH"] = "./pmod:" + cmd_env["PYTHONPATH"]
    else:
        cmd_env["PYTHONPATH"] = "./pmod"
    return cmd_env


def run_ansible(job_id):
    log.debug("job_runner.py called as: %s", sys.argv)
    conf = read_config(job_id)
    playbook = conf['job']['playbook']
    out_file = open_file(config.RUN_DIR, 'ansible-stdout', job_id)
    err_file = open_file(config.RUN_DIR, 'ansible-stderr', job_id)
    event = Event()

    os.chdir(conf['env']['stack_dir'])
    cmd = [
        'ansible-playbook',
        '-e',
        f'@{config.RUN_DIR}/{job_id}/config.json',
        '-i',
        f'{config.RUN_DIR}/{job_id}/inventory.json',
        playbook
    ]
    if 'params' in conf['job']:
        if 'ansible_tags' in conf['job']['params']:
            cmd.append('--tags=' + conf['job']['params']['ansible_tags'])

    proc = subprocess.Popen(cmd, env=set_pythonpath(), stdout=out_file, stderr=err_file)
    log.info("job #%s run cmd: %s", job_id, ' '.join(cmd))
    cm.job.set_job_status(job_id, config.Job.RUNNING, event, proc.pid)
    event.send_state()
    log.info("run ansible job #%s, pid %s, playbook %s", job_id, proc.pid, playbook)
    ret = proc.wait()
    cm.job.finish_check(job_id)
    ret = set_job_status(job_id, ret, proc.pid, event)
    event.send_state()

    out_file.close()
    err_file.close()

    log.info("finish ansible job #%s, pid %s, ret %s", job_id, proc.pid, ret)
    sys.exit(ret)


def do():
    if len(sys.argv) < 2:
        print("\nUsage:\n{} job_id\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    else:
        run_ansible(sys.argv[1])


if __name__ == '__main__':
    do()
