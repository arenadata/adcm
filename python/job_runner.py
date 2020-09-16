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

import adcm.init_django  # pylint: disable=unused-import

from cm.logger import log
import cm.config as config
import cm.job
from cm.status_api import Event
from cm.models import LogStorage


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


def set_pythonpath(env, stack_dir):
    pmod_path = f'./pmod:{stack_dir}/pmod'
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = pmod_path + ':' + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = pmod_path
    return env


def set_ansible_config(env, job_id):
    env['ANSIBLE_CONFIG'] = os.path.join(config.RUN_DIR, f'{job_id}/ansible.cfg')
    return env


def env_configuration(job_config):
    job_id = job_config['job']['id']
    stack_dir = job_config['env']['stack_dir']
    env = os.environ.copy()
    env = set_pythonpath(env, stack_dir)
    # This condition is intended to support compatibility.
    # Since older bundle versions may contain their own ansible.cfg
    if not os.path.exists(os.path.join(stack_dir, 'ansible.cfg')):
        env = set_ansible_config(env, job_id)
        log.info('set ansible config for job:%s', job_id)
    return env


def post_log(job_id, log_type, log_name):
    l1 = LogStorage.objects.filter(job__id=job_id, type=log_type, name=log_name).first()
    if l1:
        cm.status_api.post_event(
            'add_job_log',
            'job',
            job_id,
            {'id': l1.id, 'type': l1.type, 'name': l1.name, 'format': l1.format,},
        )


def run_ansible(job_id):
    log.debug("job_runner.py called as: %s", sys.argv)
    conf = read_config(job_id)
    playbook = conf['job']['playbook']
    out_file = open_file(config.RUN_DIR, 'ansible-stdout', job_id)
    err_file = open_file(config.RUN_DIR, 'ansible-stderr', job_id)
    post_log(job_id, 'stdout', 'ansible')
    post_log(job_id, 'stderr', 'ansible')
    event = Event()

    os.chdir(conf['env']['stack_dir'])
    cmd = [
        'ansible-playbook',
        '-e',
        f'@{config.RUN_DIR}/{job_id}/config.json',
        '-i',
        f'{config.RUN_DIR}/{job_id}/inventory.json',
        playbook,
    ]
    if 'params' in conf['job']:
        if 'ansible_tags' in conf['job']['params']:
            cmd.append('--tags=' + conf['job']['params']['ansible_tags'])

    proc = subprocess.Popen(cmd, env=env_configuration(conf), stdout=out_file, stderr=err_file)
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
