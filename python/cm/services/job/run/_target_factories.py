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

from functools import partial
from pathlib import Path
from typing import Generator, Iterable, Literal

from core.job.executors import BundleExecutorConfig, ExecutorConfig
from core.job.runners import ExecutionTarget, ExternalSettings
from core.job.types import Job, ScriptType, Task

from cm.ansible_plugin import finish_check
from cm.api import get_hc, save_hc
from cm.job import check_hostcomponentmap, re_prepare_job
from cm.models import JobLog, LogStorage, Prototype, ServiceComponent, TaskLog
from cm.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    InternalExecutor,
    PythonProcessExecutor,
)
from cm.services.job.utils import JobScope
from cm.status_api import send_prototype_and_state_update_event
from cm.upgrade import bundle_revert, bundle_switch


def _prepare_ansible_environment(job: Job) -> None:
    # todo rework re-prepare, so it won't request what is shouldn't
    #  probably will require something else but job_info here

    # fixme with null object will fail at
    #  `cm.services.job.config.get_job_config` | line: object_type=job_scope.object.prototype.type,
    re_prepare_job(job_scope=JobScope(job_id=job.id, object=JobLog.objects.get(id=job.id).task.task_object))


def _finish_check_logs(job: Job) -> None:
    finish_check(job.id)


def _save_fs_logs_to_db(job: Job, work_dir: Path, log_type: Literal["stdout", "stderr"]) -> None:
    # todo maybe format can be unified with one that's used by `WithErrOutLogsMixin`
    log_path = work_dir / f"{job.type.value}-{log_type}.txt"
    if not log_path.is_file():
        # todo raise exception? - only if each step "is catchable"
        return

    corresponding_log = LogStorage.objects.filter(job_id=job.id, name=job.type.value, type=log_type).first()
    if not corresponding_log:
        return

    corresponding_log.body = log_path.read_text(encoding="utf-8")
    corresponding_log.save(update_fields=["body"])


def _switch_hc_if_required(task: TaskLog):
    """
    Should be performed during upgrade of cluster, if not cluster, no need in HC update.
    Because it's upgrade, it will be called either on cluster or hostprovider,
    so task object will be one of those too.
    """
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

    host_map, _ = check_hostcomponentmap(cluster, task.action, new_hc)
    if host_map is not None:
        save_hc(cluster, host_map)


def _internal_script_bundle_switch(task: Task) -> int:
    task_ = TaskLog.objects.get(id=task.id)

    bundle_switch(obj=task_.task_object, upgrade=task_.action.upgrade)
    _switch_hc_if_required(task=task_)

    return 0


def _internal_script_bundle_revert(task: Task) -> int:
    task = TaskLog.objects.get(id=task.id)

    try:
        bundle_revert(obj=task.task_object)
    finally:
        send_prototype_and_state_update_event(object_=task.task_object)

    _switch_hc_if_required(task=task)

    return 0


def _internal_script_hc_apply(task: Task) -> int:
    TaskLog.objects.filter(id=task.id).update(restore_hc_on_fail=False)

    return 0


class ExecutionTargetFactory:
    def __init__(self):
        self._default_ansible_finalizers = (_finish_check_logs,)
        self._supported_internal_scripts = {
            "bundle_switch": _internal_script_bundle_switch,
            "bundle_revert": _internal_script_bundle_revert,
            "hc_apply": _internal_script_hc_apply,
        }

    def __call__(
        self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        for job_info in jobs:
            work_dir = configuration.adcm.run_dir / str(job_info.id)
            finalizers = (
                partial(_save_fs_logs_to_db, work_dir=work_dir, log_type="stderr"),
                partial(_save_fs_logs_to_db, work_dir=work_dir, log_type="stdout"),
            )
            match job_info.type:
                case ScriptType.ANSIBLE:
                    executor = AnsibleProcessExecutor(
                        config=AnsibleExecutorConfig(
                            script_file=Path(job_info.script),
                            work_dir=work_dir,
                            bundle_root=task.bundle_root,
                            tags=job_info.params.ansible_tags,
                            verbose=task.verbose,
                            venv=task.venv,
                            ansible_secret_script=configuration.ansible.ansible_secret_script,
                        )
                    )
                    finalizers = (*self._default_ansible_finalizers, *finalizers)
                    environment_builders = (_prepare_ansible_environment,)
                case ScriptType.PYTHON:
                    executor = PythonProcessExecutor(
                        config=BundleExecutorConfig(
                            script_file=Path(job_info.script),
                            work_dir=work_dir,
                            bundle_root=task.bundle_root,
                        )
                    )
                    environment_builders = ()
                case ScriptType.INTERNAL:
                    internal_script_func = self._supported_internal_scripts.get(job_info.script)
                    if not internal_script_func:
                        message = f"Unknown internal script {job_info.type}, can't build runner for it"
                        raise NotImplementedError(message)

                    script = partial(internal_script_func, task=task)
                    executor = InternalExecutor(config=ExecutorConfig(work_dir=work_dir), script=script)
                    environment_builders = ()
                case _:
                    message = f"Can't convert job of type {job_info.type}"
                    raise NotImplementedError(message)

            yield ExecutionTarget(
                job=job_info, executor=executor, environment_builders=environment_builders, finalizers=finalizers
            )
