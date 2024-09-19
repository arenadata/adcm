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

from configparser import ConfigParser
from functools import partial
from pathlib import Path
from typing import Any, Generator, Iterable, Literal
import json

from ansible_plugin.utils import finish_check
from core.cluster.types import HostComponentEntry
from core.job.executors import BundleExecutorConfig, ExecutorConfig
from core.job.runners import ExecutionTarget, ExternalSettings
from core.job.types import Job, ScriptType, Task
from core.types import ADCMCoreType
from django.contrib.contenttypes.models import ContentType
from django.db.transaction import atomic
from rbac.roles import re_apply_policy_for_jobs

from cm.api import get_hc
from cm.models import (
    AnsibleConfig,
    Cluster,
    HostComponent,
    LogStorage,
    Prototype,
    ServiceComponent,
    TaskLog,
)
from cm.services.job._utils import cook_delta, get_old_hc
from cm.services.job.checks import check_hostcomponentmap
from cm.services.job.inventory import get_adcm_configuration, get_inventory_data
from cm.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    InternalExecutor,
    PythonProcessExecutor,
)
from cm.services.job.types import (
    ClusterActionType,
    ComponentActionType,
    HostActionType,
    HostProviderActionType,
    JobConfig,
    JobData,
    JobEnv,
    ServiceActionType,
)
from cm.services.mapping import change_host_component_mapping
from cm.status_api import send_prototype_and_state_update_event
from cm.utils import deep_merge


class ExecutionTargetFactory:
    def __init__(self):
        self._default_ansible_finalizers = (finish_check_logs,)
        self._supported_internal_scripts = {
            "bundle_switch": internal_script_bundle_switch,
            "bundle_revert": internal_script_bundle_revert,
            "hc_apply": internal_script_hc_apply,
        }

    def __call__(
        self, task: Task, jobs: Iterable[Job], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        for job_info in jobs:
            work_dir = configuration.adcm.run_dir / str(job_info.id)
            finalizers = (
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stderr"),
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stdout"),
            )
            match job_info.type:
                case ScriptType.ANSIBLE:
                    executor = AnsibleProcessExecutor(
                        config=AnsibleExecutorConfig(
                            job_script=job_info.script,
                            work_dir=work_dir,
                            bundle=task.bundle,
                            tags=job_info.params.ansible_tags,
                            verbose=task.verbose,
                            venv=task.action.venv,
                            ansible_secret_script=configuration.ansible.ansible_secret_script,
                        )
                    )
                    finalizers = (*self._default_ansible_finalizers, *finalizers)
                    environment_builders = (prepare_ansible_environment,)
                case ScriptType.PYTHON:
                    executor = PythonProcessExecutor(
                        config=BundleExecutorConfig(
                            job_script=job_info.script,
                            work_dir=work_dir,
                            bundle=task.bundle,
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


# INTERNAL SCRIPTS


@atomic()
def internal_script_bundle_switch(task: Task) -> int:
    from cm.upgrade import bundle_switch

    task_ = TaskLog.objects.get(id=task.id)

    bundle_switch(obj=task_.task_object, upgrade=task_.action.upgrade)
    _switch_hc_if_required(task=task_)

    re_apply_policy_for_jobs(action_object=task_.task_object, task=task_)

    return 0


@atomic()
def internal_script_bundle_revert(task: Task) -> int:
    from cm.upgrade import bundle_revert

    task_ = TaskLog.objects.get(id=task.id)

    try:
        bundle_revert(obj=task_.task_object)
    finally:
        send_prototype_and_state_update_event(object_=task_.task_object)

    _switch_hc_if_required(task=task_)

    re_apply_policy_for_jobs(action_object=task_.task_object, task=task_)

    return 0


@atomic()
def internal_script_hc_apply(task: Task) -> int:
    TaskLog.objects.filter(id=task.id).update(restore_hc_on_fail=False)

    return 0


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
    for hostcomponent in [*(task.post_upgrade_hc_map or ()), *(old_hc or ())]:
        if hostcomponent not in new_hc:
            new_hc.append(hostcomponent)

    task.hostcomponentmap = old_hc
    task.post_upgrade_hc_map = None
    task.save(update_fields=["hostcomponentmap", "post_upgrade_hc_map"])

    for hostcomponent in new_hc:
        if "component_prototype_id" in hostcomponent:
            proto = Prototype.objects.get(type="component", id=hostcomponent.pop("component_prototype_id"))
            comp = ServiceComponent.objects.get(cluster=cluster, prototype=proto)
            hostcomponent["component_id"] = comp.id
            hostcomponent["service_id"] = comp.service.id

    host_map, *_ = check_hostcomponentmap(cluster, task.action, new_hc)
    if host_map is not None:
        change_host_component_mapping(
            cluster_id=cluster.id,
            bundle_id=cluster.bundle_id,
            flat_mapping=(
                HostComponentEntry(host_id=host.id, component_id=component.id) for (_, host, component) in host_map
            ),
            skip_checks=True,
        )


# ENVIRONMENT BUILDERS


def prepare_ansible_environment(task: Task, job: Job, configuration: ExternalSettings) -> None:
    job_config = prepare_ansible_job_config(task=task, job=job, configuration=configuration)
    job_run_dir = configuration.adcm.run_dir / str(job.id)
    with (job_run_dir / "config.json").open(mode="w", encoding="utf-8") as config_file:
        json.dump(obj=job_config, fp=config_file, sort_keys=True, separators=(",", ":"))

    inventory = prepare_ansible_inventory(task=task)
    with (job_run_dir / "inventory.json").open(mode="w", encoding="utf-8") as file_descriptor:
        json.dump(obj=inventory, fp=file_descriptor, separators=(",", ":"))

    ansible_cfg_config_parser: ConfigParser = prepare_ansible_cfg(task=task)
    with (job_run_dir / "ansible.cfg").open(mode="w", encoding="utf-8") as config_file:
        ansible_cfg_config_parser.write(config_file)


def prepare_ansible_inventory(task: Task) -> dict[str, Any]:
    delta = {}
    if task.action.hc_acl:
        cluster_id = None
        if task.owner:
            if task.owner.type == ADCMCoreType.CLUSTER:
                cluster_id = task.owner.id
            elif task.owner.related_objects.cluster:
                cluster_id = task.owner.related_objects.cluster.id

        if not cluster_id:
            message = f"Can't detect cluster id for {task.id} {task.action.name} based on: {task.owner=}"
            raise RuntimeError(message)

        new_hc = []
        for hostcomponent in HostComponent.objects.select_related("service", "host", "component").filter(
            cluster_id=cluster_id
        ):
            new_hc.append((hostcomponent.service, hostcomponent.host, hostcomponent.component))

        delta = cook_delta(
            cluster=Cluster.objects.get(id=cluster_id),
            new_hc=new_hc,
            action_hc=task.action.hc_acl,
            old=get_old_hc(saved_hostcomponent=task.hostcomponent.saved),
        )

    return get_inventory_data(
        target=task.target,
        is_host_action=task.action.is_host_action,
        delta=delta,
        related_objects=task.owner.related_objects,
    )


def prepare_ansible_job_config(task: Task, job: Job, configuration: ExternalSettings) -> dict[str, Any]:
    # prepare context
    context = {f"{k}_id": v["id"] for k, v in task.selector.items() if k != "action_host_group"}
    context["type"] = task.owner.type.value.replace("hostp", "p")

    job_data = JobData(
        id=job.id,
        action=task.action.name,
        job_name=job.name,
        command=job.name,
        script=job.script,
        verbose=task.verbose,
        playbook=str(task.bundle.root / job.script),
        action_type_specification=_get_owner_specific_data(task=task),
    )

    if task.owner:
        if task.owner.type == ADCMCoreType.CLUSTER:
            job_data.cluster_id = task.owner.id
        elif task.owner.related_objects.cluster is not None:
            job_data.cluster_id = task.owner.related_objects.cluster.id

    if task.config:
        job_data.config = task.config

    params: dict = job.params.dict()
    if not params["ansible_tags"]:
        # if it's empty, it shouldn't be included
        # and since it's the only "pre-defined" field we want empty dict if that's the case
        params.pop("ansible_tags")

    if params:
        job_data.params = params

    return JobConfig(
        adcm={"config": get_adcm_configuration()},
        context=context,
        env=JobEnv(
            run_dir=str(configuration.adcm.run_dir),
            log_dir=str(configuration.adcm.log_dir),
            tmp_dir=str(configuration.adcm.run_dir / str(job.id) / "tmp"),
            stack_dir=str(task.bundle.root),
            status_api_token=configuration.integrations.status_server_token,
        ),
        job=job_data,
    ).model_dump(exclude_unset=True)


def prepare_ansible_cfg(task: Task) -> ConfigParser:
    config_parser = ConfigParser()

    ansible_cfg_from_bundle = task.bundle.root / "ansible.cfg"
    if ansible_cfg_from_bundle.is_file():
        config_parser.read(filenames=ansible_cfg_from_bundle, encoding="utf-8")
    else:
        config_parser["defaults"] = {
            "deprecation_warnings": False,
            "callback_whitelist": "profile_tasks",
            "stdout_callback": "yaml",
        }
        config_parser["ssh_connection"] = {"retries": "3"}

    if task.owner.type in {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        cluster_id = task.owner.id if task.owner.type == ADCMCoreType.CLUSTER else task.owner.related_objects.cluster.id

        settings_to_override = (
            AnsibleConfig.objects.values_list("value", flat=True)
            .filter(object_id=cluster_id, object_type=ContentType.objects.get_for_model(Cluster))
            .first()
        )
        # we consider that if we got settings, they are of correct form (string values),
        # otherwise `deep_merge` might fail
        deep_merge(origin=config_parser, renovator=settings_to_override or {})

    return config_parser


def _get_owner_specific_data(
    task: Task,
) -> ClusterActionType | ServiceActionType | ComponentActionType | HostProviderActionType | HostActionType:
    owner = task.owner
    if not owner:
        message = "Can't get owner task data for task without owner"
        raise RuntimeError(message)

    match owner.type:
        case ADCMCoreType.CLUSTER:
            return ClusterActionType(action_proto_type="cluster", hostgroup="CLUSTER")
        case ADCMCoreType.HOSTPROVIDER:
            return HostProviderActionType(
                action_proto_type="provider",
                hostgroup="PROVIDER",
                provider_id=task.owner.id,
            )
        case ADCMCoreType.HOST:
            return HostActionType(
                action_proto_type="host",
                hostgroup="HOST",
                hostname=task.owner.name,
                host_id=task.owner.id,
                host_type_id=task.owner.prototype_id,
                provider_id=task.owner.related_objects.hostprovider.id,
            )
        case ADCMCoreType.SERVICE:
            return ServiceActionType(
                action_proto_type="service",
                hostgroup=task.owner.name,
                service_id=task.owner.id,
                service_type_id=task.owner.prototype_id,
            )
        case ADCMCoreType.COMPONENT:
            return ComponentActionType(
                action_proto_type="component",
                hostgroup=f"{owner.related_objects.service.name}.{owner.name}",
                service_id=owner.related_objects.service.id,
                component_id=owner.id,
                component_type_id=owner.prototype_id,
            )
        case _:
            message = f"Can't get task data for task with owner {owner.type}"
            raise NotImplementedError(message)


# FINALIZERS


def finish_check_logs(job: Job) -> None:
    finish_check(job.id)


def save_fs_logs_to_db(job: Job, work_dir: Path, log_type: Literal["stdout", "stderr"]) -> None:
    log_path = work_dir / f"{job.type.value}-{log_type}.txt"
    if not log_path.is_file():
        return

    corresponding_log = LogStorage.objects.filter(job_id=job.id, name=job.type.value, type=log_type).first()
    if not corresponding_log:
        return

    corresponding_log.body = log_path.read_text(encoding="utf-8")
    corresponding_log.save(update_fields=["body"])
