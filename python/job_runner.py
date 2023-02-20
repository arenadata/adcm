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

import json
import os
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.db import transaction

import adcm.init_django  # pylint: disable=unused-import # noqa: F401
import cm.job
from cm.ansible_plugin import finish_check
from cm.api import get_hc, save_hc
from cm.errors import AdcmEx
from cm.logger import logger
from cm.models import JobLog, JobStatus, LogStorage, Prototype, ServiceComponent
from cm.status_api import Event, post_event
from cm.upgrade import bundle_revert, bundle_switch


def open_file(root, tag, job_id):
    fname = f"{root}/{job_id}/{tag}.txt"
    f = open(fname, "w", encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with

    return f


def read_config(job_id):
    file_descriptor = open(  # pylint: disable=consider-using-with
        f"{settings.RUN_DIR}/{job_id}/config.json",
        encoding=settings.ENCODING_UTF_8,
    )
    conf = json.load(file_descriptor)
    file_descriptor.close()

    return conf


def set_job_status(job_id, ret, pid, event):
    if ret == 0:
        cm.job.set_job_status(job_id, JobStatus.SUCCESS, event, pid)
        return 0
    elif ret == -15:
        cm.job.set_job_status(job_id, JobStatus.ABORTED, event, pid)
        return 15
    else:
        cm.job.set_job_status(job_id, JobStatus.FAILED, event, pid)
        return ret


def set_pythonpath(env, stack_dir):
    pmod_path = f"./pmod:{stack_dir}/pmod"
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = pmod_path + ":" + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = pmod_path
    return env


def set_ansible_config(env, job_id):
    env["ANSIBLE_CONFIG"] = str(settings.RUN_DIR / f"{job_id}/ansible.cfg")
    return env


def env_configuration(job_config):
    job_id = job_config["job"]["id"]
    stack_dir = job_config["env"]["stack_dir"]
    env = os.environ.copy()
    env = set_pythonpath(env, stack_dir)

    # This condition is intended to support compatibility.
    # Since older bundle versions may contain their own ansible.cfg
    if not Path(stack_dir, "ansible.cfg").is_file():
        env = set_ansible_config(env, job_id)
        logger.info("set ansible config for job:%s", job_id)
    return env


def post_log(job_id, log_type, log_name):
    log_storage = LogStorage.objects.filter(job__id=job_id, type=log_type, name=log_name).first()
    if log_storage:
        post_event(
            event="add_job_log",
            obj=log_storage.job,
            details={
                "id": log_storage.id,
                "type": log_storage.type,
                "name": log_storage.name,
                "format": log_storage.format,
            },
        )


def get_venv(job_id: int) -> str:
    return JobLog.objects.get(id=job_id).action.venv


def process_err_out_file(job_id, job_type):
    out_file = open_file(settings.RUN_DIR, f"{job_type}-stdout", job_id)
    err_file = open_file(settings.RUN_DIR, f"{job_type}-stderr", job_id)
    post_log(job_id, "stdout", f"{job_type}")
    post_log(job_id, "stderr", f"{job_type}")
    return out_file, err_file


def start_subprocess(job_id, cmd, conf, out_file, err_file):
    event = Event()
    logger.info("job run cmd: %s", " ".join(cmd))
    proc = subprocess.Popen(  # pylint: disable=consider-using-with
        cmd,
        env=env_configuration(conf),
        stdout=out_file,
        stderr=err_file,
    )
    JobLog.objects.filter(pk=job_id).update(pid=proc.pid)
    cm.job.set_job_status(job_id, JobStatus.RUNNING, event, proc.pid)
    event.send_state()
    logger.info("run job #%s, pid %s", job_id, proc.pid)
    ret = proc.wait()
    finish_check(job_id)
    ret = set_job_status(job_id, ret, proc.pid, event)
    event.send_state()

    out_file.close()
    err_file.close()

    logger.info("finish job subprocess #%s, pid %s, ret %s", job_id, proc.pid, ret)
    return ret


def run_ansible(job_id):
    logger.debug("job_runner.py starts to run ansible job %s", job_id)
    conf = read_config(job_id)
    playbook = conf["job"]["playbook"]
    out_file, err_file = process_err_out_file(job_id, "ansible")

    os.chdir(conf["env"]["stack_dir"])
    cmd = [
        "/adcm/python/job_venv_wrapper.sh",
        get_venv(int(job_id)),
        "ansible-playbook",
        "--vault-password-file",
        f"{settings.CODE_DIR}/ansible_secret.py",
        "-e",
        f"@{settings.RUN_DIR}/{job_id}/config.json",
        "-i",
        f"{settings.RUN_DIR}/{job_id}/inventory.json",
        playbook,
    ]
    if "params" in conf["job"]:
        if "ansible_tags" in conf["job"]["params"]:
            cmd.append("--tags=" + conf["job"]["params"]["ansible_tags"])
    if "verbose" in conf["job"] and conf["job"]["verbose"]:
        cmd.append("-vvvv")
    ret = start_subprocess(job_id, cmd, conf, out_file, err_file)
    sys.exit(ret)


def run_upgrade(job):
    event = Event()
    cm.job.set_job_status(job.id, JobStatus.RUNNING, event)
    out_file, err_file = process_err_out_file(job.id, "internal")
    try:
        with transaction.atomic():
            script = job.sub_action.script if job.sub_action else job.action.script

            if script == "bundle_switch":
                bundle_switch(obj=job.task.task_object, upgrade=job.action.upgrade)
            elif script == "bundle_revert":
                bundle_revert(obj=job.task.task_object)

            switch_hc(task=job.task, action=job.action)
    except AdcmEx as e:
        err_file.write(e.msg)
        cm.job.set_job_status(job.id, JobStatus.FAILED, event)
        out_file.close()
        err_file.close()
        sys.exit(1)
    cm.job.set_job_status(job.id, JobStatus.SUCCESS, event)
    event.send_state()
    out_file.close()
    err_file.close()
    sys.exit(0)


def run_python(job):
    out_file, err_file = process_err_out_file(job.id, "python")
    conf = read_config(job.id)
    script_path = conf["job"]["playbook"]
    os.chdir(conf["env"]["stack_dir"])
    cmd = ["python", script_path]
    ret = start_subprocess(job.id, cmd, conf, out_file, err_file)
    sys.exit(ret)


def switch_hc(task, action):
    if task.task_object.prototype.type != "cluster":
        return

    cluster = task.task_object
    old_hc = get_hc(cluster)
    new_hc = []
    for hostcomponent in [*task.post_upgrade_hc_map, *old_hc]:
        if hostcomponent not in new_hc:
            new_hc.append(hostcomponent)

    task.hostcomponentmap = old_hc
    task.post_upgrade_hc_map = None
    task.save()

    for hostcomponent in new_hc:
        if "component_prototype_id" in hostcomponent:
            proto = Prototype.objects.get(type="component", id=hostcomponent.pop("component_prototype_id"))
            comp = ServiceComponent.objects.get(cluster=cluster, prototype=proto)
            hostcomponent["component_id"] = comp.id
            hostcomponent["service_id"] = comp.service.id

    host_map, _ = cm.job.check_hostcomponentmap(cluster, action, new_hc)
    if host_map is not None:
        save_hc(cluster, host_map)


def main(job_id):
    logger.debug("job_runner.py called as: %s", sys.argv)
    job = JobLog.objects.get(id=job_id)
    job_type = job.sub_action.script_type if job.sub_action else job.action.script_type
    if job_type == "internal":
        run_upgrade(job)
    elif job_type == "python":
        run_python(job)
    else:
        run_ansible(job_id)


def do_job():
    if len(sys.argv) < 2:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} job_id\n")
        sys.exit(4)
    else:
        main(sys.argv[1])


if __name__ == "__main__":
    do_job()
