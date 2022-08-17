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

import json
import os
import subprocess
import sys

import cm.job
from cm import config
from cm.ansible_plugin import finish_check
from cm.errors import AdcmEx
from cm.logger import log
from cm.models import JobLog, LogStorage
from cm.status_api import Event
from cm.upgrade import bundle_switch

import adcm.init_django  # DO NOT DELETE !!!


def open_file(root, tag, job_id):
    fname = f'{root}/{job_id}/{tag}.txt'
    f = open(fname, 'w', encoding='utf_8')
    return f


def read_config(job_id):
    fd = open(f'{config.RUN_DIR}/{job_id}/config.json', encoding='utf_8')
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
            {
                'id': l1.id,
                'type': l1.type,
                'name': l1.name,
                'format': l1.format,
            },
        )


def get_venv(job_id: int) -> str:
    return JobLog.objects.get(id=job_id).action.venv


def process_err_out_file(job_id, job_type):
    out_file = open_file(config.RUN_DIR, f'{job_type}-stdout', job_id)
    err_file = open_file(config.RUN_DIR, f'{job_type}-stderr', job_id)
    post_log(job_id, 'stdout', f'{job_type}')
    post_log(job_id, 'stderr', f'{job_type}')
    return out_file, err_file


def start_subprocess(job_id, cmd, conf, out_file, err_file):
    event = Event()
    log.info("job run cmd: %s", ' '.join(cmd))
    proc = subprocess.Popen(cmd, env=env_configuration(conf), stdout=out_file, stderr=err_file)
    cm.job.set_job_status(job_id, config.Job.RUNNING, event, proc.pid)
    event.send_state()
    log.info("run job #%s, pid %s", job_id, proc.pid)
    ret = proc.wait()
    finish_check(job_id)
    ret = set_job_status(job_id, ret, proc.pid, event)
    event.send_state()

    out_file.close()
    err_file.close()

    log.info("finish job subprocess #%s, pid %s, ret %s", job_id, proc.pid, ret)
    return ret


def run_ansible(job_id):
    log.debug("job_runner.py called as: %s", sys.argv)
    conf = read_config(job_id)
    playbook = conf['job']['playbook']
    out_file, err_file = process_err_out_file(job_id, 'ansible')

    os.chdir(conf['env']['stack_dir'])
    cmd = [
        '/adcm/python/job_venv_wrapper.sh',
        get_venv(int(job_id)),
        'ansible-playbook',
        '--vault-password-file',
        f'{config.CODE_DIR}/ansible_secret.py',
        '-e',
        f'@{config.RUN_DIR}/{job_id}/config.json',
        '-i',
        f'{config.RUN_DIR}/{job_id}/inventory.json',
        playbook,
    ]
    if 'params' in conf['job']:
        if 'ansible_tags' in conf['job']['params']:
            cmd.append('--tags=' + conf['job']['params']['ansible_tags'])
    if 'verbose' in conf['job'] and conf['job']['verbose']:
        cmd.append('-vvvv')
    ret = start_subprocess(job_id, cmd, conf, out_file, err_file)
    sys.exit(ret)


def run_upgrade(job):
    event = Event()
    cm.job.set_job_status(job.id, config.Job.RUNNING, event)
    out_file, err_file = process_err_out_file(job.id, 'internal')
    try:
        bundle_switch(job.task.task_object, job.action.upgrade)
    except AdcmEx as e:
        err_file.write(e.msg)
        cm.job.set_job_status(job.id, config.Job.FAILED, event)
        out_file.close()
        err_file.close()
        sys.exit(1)
    cm.job.set_job_status(job.id, config.Job.SUCCESS, event)
    event.send_state()
    out_file.close()
    err_file.close()
    sys.exit(0)


def run_python(job):
    out_file, err_file = process_err_out_file(job.id, 'python')
    conf = read_config(job.id)
    script_path = conf['job']['playbook']
    os.chdir(conf['env']['stack_dir'])
    cmd = ['python', script_path]
    ret = start_subprocess(job.id, cmd, conf, out_file, err_file)
    sys.exit(ret)


def main(job_id):
    job = JobLog.objects.get(id=job_id)
    job_type = job.sub_action.script_type if job.sub_action else job.action.script_type
    if job_type == 'internal':
        run_upgrade(job)
    elif job_type == 'python':
        run_python(job)
    else:
        run_ansible(job_id)


def do():
    if len(sys.argv) < 2:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} job_id\n")
        sys.exit(4)
    else:
        main(sys.argv[1])


if __name__ == '__main__':
    do()
