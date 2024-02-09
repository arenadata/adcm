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

from pathlib import Path
import os
import sys
import json
import subprocess

import adcm.init_django  # noqa: F401, isort:skip

from cm.ansible_plugin import finish_check
from cm.api import get_hc, save_hc
from cm.errors import AdcmEx
from cm.job import check_hostcomponentmap, set_job_final_status, set_job_start_status
from cm.logger import logger
from cm.models import JobLog, JobStatus, Prototype, ServiceComponent
from cm.status_api import send_prototype_and_state_update_event
from cm.upgrade import bundle_revert, bundle_switch
from cm.utils import get_env_with_venv_path
from django.conf import settings
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs


def open_file(root, tag, job_id):
    fname = f"{root}/{job_id}/{tag}.txt"
    return Path(fname).open(mode="w", encoding=settings.ENCODING_UTF_8)  # noqa: SIM115


def read_config(job_id):
    with Path(f"{settings.RUN_DIR}/{job_id}/config.json").open(encoding=settings.ENCODING_UTF_8) as file_descriptor:
        return json.load(file_descriptor)


def set_job_status(job_id: int, return_code: int) -> int:
    if return_code == 0:
        set_job_final_status(job_id=job_id, status=JobStatus.SUCCESS)
        return 0
    elif return_code == -15:  # noqa: RET505
        set_job_final_status(job_id=job_id, status=JobStatus.ABORTED)
        return 15
    else:
        set_job_final_status(job_id=job_id, status=JobStatus.FAILED)
        return return_code


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


def get_configured_env(job_config: dict) -> dict:
    job_id = job_config["job"]["id"]
    stack_dir = job_config["env"]["stack_dir"]
    env = os.environ.copy()
    env = set_pythonpath(env=env, stack_dir=stack_dir)
    env = get_env_with_venv_path(venv=JobLog.objects.get(id=job_id).action.venv, existing_env=env)

    # This condition is intended to support compatibility.
    # Since older bundle versions may contain their own ansible.cfg
    if not Path(stack_dir, "ansible.cfg").is_file():
        env = set_ansible_config(env=env, job_id=job_id)
        logger.info("set ansible config for job:%s", job_id)

    return env


def get_venv(job_id: int) -> str:
    return JobLog.objects.get(id=job_id).action.venv


def process_err_out_file(job_id, job_type):
    out_file = open_file(settings.RUN_DIR, f"{job_type}-stdout", job_id)
    err_file = open_file(settings.RUN_DIR, f"{job_type}-stderr", job_id)
    return out_file, err_file


def start_subprocess(job_id, cmd, conf, out_file, err_file):
    logger.info("job run cmd: %s", " ".join(cmd))
    process = subprocess.Popen(  # noqa: SIM115
        cmd,  # noqa: S603
        env=get_configured_env(job_config=conf),
        stdout=out_file,
        stderr=err_file,
    )
    set_job_start_status(job_id=job_id, pid=process.pid)
    logger.info("run job #%s, pid %s", job_id, process.pid)
    return_code = process.wait()
    finish_check(job_id)
    return_code = set_job_status(job_id=job_id, return_code=return_code)

    out_file.close()
    err_file.close()

    logger.info("finish job subprocess #%s, pid %s, ret %s", job_id, process.pid, return_code)
    return return_code


def run_ansible(job_id: int) -> None:
    logger.debug("job_runner.py starts to run ansible job %s", job_id)
    conf = read_config(job_id)
    playbook = conf["job"]["playbook"]
    out_file, err_file = process_err_out_file(job_id, "ansible")

    os.chdir(conf["env"]["stack_dir"])
    cmd = [
        "ansible-playbook",
        "--vault-password-file",
        f"{settings.CODE_DIR}/ansible_secret.py",
        "-e",
        f"@{settings.RUN_DIR}/{job_id}/config.json",
        "-i",
        f"{settings.RUN_DIR}/{job_id}/inventory.json",
        playbook,
    ]
    if "params" in conf["job"] and "ansible_tags" in conf["job"]["params"]:
        cmd.append("--tags=" + conf["job"]["params"]["ansible_tags"])
    if "verbose" in conf["job"] and conf["job"]["verbose"]:
        cmd.append("-vvvv")
    ret = start_subprocess(job_id, cmd, conf, out_file, err_file)
    sys.exit(ret)


def run_internal(job: JobLog) -> None:
    set_job_start_status(job_id=job.id, pid=0)
    out_file, err_file = process_err_out_file(job_id=job.id, job_type="internal")
    script = job.sub_action.script if job.sub_action else job.action.script
    return_code = 0
    status = JobStatus.SUCCESS

    try:
        with atomic():
            object_ = job.task.task_object
            if script == "bundle_switch":
                bundle_switch(obj=object_, upgrade=job.action.upgrade)
            elif script == "bundle_revert":
                bundle_revert(obj=object_)
            elif script == "hc_apply":
                job.task.restore_hc_on_fail = False
                job.task.save(update_fields=["restore_hc_on_fail"])

            if script != "hc_apply":
                switch_hc(task=job.task, action=job.action)

            re_apply_policy_for_jobs(action_object=object_, task=job.task)
    except AdcmEx as e:
        err_file.write(e.msg)
        return_code = 1
        status = JobStatus.FAILED
    finally:
        if script == "bundle_revert":
            send_prototype_and_state_update_event(object_=object_)

        set_job_final_status(job_id=job.id, status=status)
        out_file.close()
        err_file.close()
        sys.exit(return_code)


def run_python(job: JobLog) -> None:
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

    host_map, _ = check_hostcomponentmap(cluster, action, new_hc)
    if host_map is not None:
        save_hc(cluster, host_map)


def main(job_id):
    logger.debug("job_runner.py called as: %s", sys.argv)
    job = JobLog.objects.get(id=job_id)
    job_type = job.sub_action.script_type if job.sub_action else job.action.script_type
    if job_type == "internal":
        run_internal(job=job)
    elif job_type == "python":
        run_python(job=job)
    else:
        run_ansible(job_id=job_id)


def do_job():
    if len(sys.argv) < 2:
        print(f"\nUsage:\n{os.path.basename(sys.argv[0])} job_id\n")  # noqa: PTH119
        sys.exit(4)
    else:
        main(sys.argv[1])


if __name__ == "__main__":
    do_job()
