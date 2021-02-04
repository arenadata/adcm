#!/usr/bin/env python
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
import logging
from subprocess import call

ROOT_DIR = '/var/lib/ambari-agent'
LOG_DIR = '/var/lib/ambari-agent/data'
TOP_LOG = '/var/log/adcm.log'
TMP_DIR = '/tmp'
LOG_LEVEL = 'INFO'

log = logging.getLogger('command')
log.setLevel(logging.DEBUG)


def get_log_handler(fname):
    handler = logging.FileHandler(fname, 'a', 'utf-8')
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(module)s %(message)s", "%m-%d %H:%M:%S")
    handler.setFormatter(fmt)
    return handler


def open_file(root, tag, command_id):
    fname = "{}/{}-{}.txt".format(root, command_id, tag)
    f = open(fname, 'w')
    return f


def print_log(root, tag, command_id):
    fname = "{}/{}-{}.txt".format(root, command_id, tag)
    f = open(fname, 'r')
    flog = f.read()
    sys.stderr.write(flog)
    f.close()


def add_path(path):
    env = os.environ
    os_path = env['PATH']
    env['PATH'] = "{}:{}".format(os_path, path)
    return env


def run_python_script(base_dir, py_script, command, json_config, out_file, err_file):
    try:
        res = call([
            'python',
            py_script,
            command.upper(),
            json_config,
            base_dir,
            '/tmp/structured_out.json',
            LOG_LEVEL,
            TMP_DIR
        ], stdout=out_file, stderr=err_file, env=add_path(ROOT_DIR))
    # pylint: disable=bare-except
    except:    # noqa E722
        log.error("exception runnung python script")
        res = 42

    log.info("script %s ret: %s", py_script, res)
    return res


def cook_hook(root, hook, command):
    return ('{}/{}'.format(root, hook), '{}/{}/scripts/hook.py'.format(root, hook), command)


def cook_command_pipe(hook_dir, command_tuple):
    (_, _, command) = command_tuple
    pipe = []
    if command == 'install':
        pipe.append(cook_hook(hook_dir, 'before-INSTALL', 'install'))
        pipe.append(command_tuple)
        pipe.append(cook_hook(hook_dir, 'after-INSTALL', 'install'))
    elif command == 'start':
        pipe.append(cook_hook(hook_dir, 'before-START', 'start'))
        pipe.append(command_tuple)
    else:
        pipe.append(cook_hook(hook_dir, 'before-ANY', 'any'))
        pipe.append(command_tuple)
    return pipe


def cook_hook_folder(root, folder):
    stack = folder.split('/services/')[0]
    return "{}/cache/{}/hooks".format(root, stack)


def run_ambari_command(folder, script, command, command_id):
    base_dir = '{}/cache/{}'.format(ROOT_DIR, folder)
    hook_dir = cook_hook_folder(ROOT_DIR, folder)
    json_config = "{}/data/command-{}.json".format(ROOT_DIR, command_id)
    py_script = '{}/{}'.format(base_dir, script)

    log.debug("command.py called as: %s", sys.argv)
    log.info('%s run %s', command_id, command)

    out_file = open_file(LOG_DIR, 'out', command_id)
    err_file = open_file(LOG_DIR, 'err', command_id)

    pipe = cook_command_pipe(hook_dir, (base_dir, py_script, command))
    log.debug('%s %s pipe: %s', command_id, command, pipe)

    for (base, py, comm) in pipe:
        res = run_python_script(base, py, comm, json_config, out_file, err_file)
        if res != 0:
            break

    out_file.close()
    err_file.close()

    if res != 0:
        print_log(LOG_DIR, 'err', command_id)
        sys.exit(res)


def print_usage():
    print('''
    command.py folder script.py commnad command_id
    ''')


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print_usage()
        sys.exit(4)
    else:
        log.addHandler(get_log_handler(TOP_LOG))
        run_ambari_command(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
