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


class ReadConfigError(Exception):
    pass


class ConfigError(Exception):
    pass


class RunPlaybookError(Exception):
    pass


def open_file(root, tag, job_id):
    f = open('{}/{}-{}.txt'.format(root, job_id, tag), 'w')
    return f


def read_config(job_id):
    try:
        with open('{}/{}-config.json'.format(config.RUN_DIR, job_id)) as f:
            conf = json.load(f)
    except FileNotFoundError:
        raise ReadConfigError
    except json.decoder.JSONDecodeError:
        raise ReadConfigError
    return conf


def set_job_status(job_id, ret, pid):
    if ret == 0:
        cm.job.set_job_status(job_id, config.Job.SUCCESS, pid)
    else:
        cm.job.set_job_status(job_id, config.Job.FAILED, pid)
    return ret


def set_pythonpath():
    cmd_env = os.environ.copy()
    if "PYTHONPATH" in cmd_env:
        cmd_env["PYTHONPATH"] = "./pmod:" + cmd_env["PYTHONPATH"]
    else:
        cmd_env["PYTHONPATH"] = "./pmod"
    return cmd_env


def run_playbook(cmd, job_id, playbook, out_file, err_file):
    try:
        process = subprocess.Popen(cmd, env=set_pythonpath(), stdout=out_file, stderr=err_file)
        log.info("job #%s run cmd: %s", job_id, ' '.join(cmd))
        cm.job.set_job_status(job_id, config.Job.RUNNING, process.pid)
        log.info("run ansible job #%s, pid %s, playbook %s", job_id, process.pid, playbook)
        code = process.wait()
        return process, code
    except subprocess.SubprocessError:
        log.error("exception running ansible-playbook")
        raise RunPlaybookError


def run_ansible(job_id):
    try:
        log.debug("job_runner.py called as: %s", sys.argv)
        conf = read_config(job_id)
        try:
            playbook = conf['job']['playbook']
        except KeyError:
            raise ConfigError
        out_file = open_file(config.LOG_DIR, 'ansible-out', job_id)
        err_file = open_file(config.LOG_DIR, 'ansible-err', job_id)

        os.chdir(conf['env']['stack_dir'])
        cmd = [
            'ansible-playbook',
            '-e',
            '@{}/{}-config.json'.format(config.RUN_DIR, job_id),
            '-i',
            '{}/{}-inventory.json'.format(config.RUN_DIR, job_id),
            playbook
        ]
        if 'params' in conf['job']:
            if 'ansible_tags' in conf['job']['params']:
                cmd.append('--tags=' + conf['job']['params']['ansible_tags'])

        process, ret = run_playbook(cmd, job_id, playbook, out_file, err_file)
        code = set_job_status(job_id, ret, process.pid)

        out_file.close()
        err_file.close()

        log.info("finish ansible job #%s, pid %s, ret %s", job_id, process.pid, code)
        sys.exit(code)
    except ReadConfigError:
        log.error("error read config file")
        sys.exit(1)
    except ConfigError:
        log.error("error configuration")
        sys.exit(1)
    except RunPlaybookError:
        sys.exit(1)


def do():
    if len(sys.argv) < 2:
        print("\nUsage:\n{} job_id\n".format(os.path.basename(sys.argv[0])))
        sys.exit(4)
    else:
        run_ansible(sys.argv[1])


if __name__ == '__main__':
    do()
