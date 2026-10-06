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

from collections.abc import Generator, Iterable
from configparser import ConfigParser
from functools import partial
from logging import getLogger
from pathlib import Path
from typing import Any, Literal
import json

from core.action import Task
from core.action.types import (
    AnsibleScript,
    ConfigApplyScript,
    HcApplyScript,
    PythonScript,
    RichJob,
    ServiceManageScript,
    SimpleInternalScript,
)
from core.cluster import ClusterService
from core.config import ConfigService
from core.legacy.cluster.types import ClusterTopology
from core.legacy.job.executors import ExecutorConfig
from core.legacy.job.runners import ExecutionTarget, ExecutionTargetFactoryI, ExternalSettings
from core.logs import LogsService
from core.types import ADCMCoreType
from django.contrib.contenttypes.models import ContentType
from use_cases.internal_scripts.before_upgrade_clean import BeforeUpgradeCleanInternalScript
from use_cases.internal_scripts.bundle_revert import BundleRevertInternalScript
from use_cases.internal_scripts.bundle_switch import BundleSwitchInternalScript
from use_cases.internal_scripts.config_apply import ConfigApplyInternalScript
from use_cases.internal_scripts.hc_apply import HcApplyInternalScript
from use_cases.internal_scripts.service_manage import ServiceManageInternalScript

from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.job import context as context_m
from cm.legacy.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    InternalExecutor,
    PythonExecutorConfig,
    PythonProcessExecutor,
)
from cm.legacy.services.job.types import (
    ADCMJobConfig,
    ClusterActionType,
    ComponentActionType,
    HostActionType,
    JobConfig,
    JobData,
    JobEnv,
    ProviderActionType,
    ServiceActionType,
)
from cm.legacy.utils import deep_merge
from cm.models import (
    ADCM,
    AnsibleConfig,
    Cluster,
    LogStorage,
    Process,
)

logger = getLogger("adcm")

_InternalScript = (
    BundleSwitchInternalScript
    | BundleRevertInternalScript
    | HcApplyInternalScript
    | ConfigApplyInternalScript
    | ServiceManageInternalScript
    | BeforeUpgradeCleanInternalScript
)


class ExecutionTargetFactory(ExecutionTargetFactoryI):
    def __init__(
        self,
        bundle_switch: BundleSwitchInternalScript,
        bundle_revert: BundleRevertInternalScript,
        hc_apply: HcApplyInternalScript,
        config_apply: ConfigApplyInternalScript,
        service_manage: ServiceManageInternalScript,
        before_upgrade_clean: BeforeUpgradeCleanInternalScript,
        logs_service: LogsService,
        config_service: ConfigService,
    ):
        self._default_ansible_finalizers = (
            lambda job: logs_service.finish_updating_check_logs_for_job(job_id=job.runtime.id),
        )
        self._config_service = config_service
        self._supported_internal_scripts: dict[str, _InternalScript] = {
            "bundle_switch": bundle_switch,
            "bundle_revert": bundle_revert,
            "hc_apply": hc_apply,
            "config_apply": config_apply,
            "service_manage": service_manage,
            "before_upgrade_clean": before_upgrade_clean,
        }

    def __call__(
        self, task: Task, jobs: Iterable[RichJob], configuration: ExternalSettings
    ) -> Generator[ExecutionTarget, None, None]:
        for job_info in jobs:
            work_dir = configuration.adcm.run_dir / str(job_info.runtime.id)
            finalizers = (
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stderr"),
                partial(save_fs_logs_to_db, work_dir=work_dir, log_type="stdout"),
            )
            # the script's own type is what tells one executor from another,
            # and it narrows the params each internal script is handed along the way
            match job_info.spec.script:
                case AnsibleScript() as script_spec:
                    executor = AnsibleProcessExecutor(
                        config=AnsibleExecutorConfig(
                            job_script=script_spec.path,
                            work_dir=work_dir,
                            bundle=task.bundle,
                            tags=script_spec.params.ansible_tags,
                            verbose=task.verbose,
                            venv=task.action.venv,
                            ansible_secret_script=configuration.ansible.ansible_secret_script,
                        )
                    )
                    finalizers = (*self._default_ansible_finalizers, *finalizers)
                    environment_builders = (partial(prepare_ansible_environment, config_service=self._config_service),)
                case PythonScript() as script_spec:
                    executor = PythonProcessExecutor(
                        config=PythonExecutorConfig(
                            job_script=script_spec.path,
                            work_dir=work_dir,
                            bundle=task.bundle,
                            venv=task.action.venv,
                        )
                    )
                    environment_builders = ()
                case SimpleInternalScript() | HcApplyScript() | ConfigApplyScript() | ServiceManageScript():
                    script = partial(self._internal_script(job_info).do, task=task, job=job_info)
                    executor = InternalExecutor(config=ExecutorConfig(work_dir=work_dir), script=script)
                    environment_builders = ()
                case _:
                    message = f"Can't convert job of type {job_info.spec.script.type}"
                    raise NotImplementedError(message)

            yield ExecutionTarget(
                job=job_info, executor=executor, environment_builders=environment_builders, finalizers=finalizers
            )

    def _internal_script(self, job: RichJob) -> _InternalScript:
        script_name = job.spec.script.path

        try:
            return self._supported_internal_scripts[script_name]
        except KeyError as err:
            message = f"Unknown internal script {script_name}, can't build runner for it"
            raise NotImplementedError(message) from err


# ENVIRONMENT BUILDERS


def prepare_ansible_environment(
    task: Task,
    job: RichJob,
    configuration: ExternalSettings,
    cluster_service: ClusterService,
    config_service: ConfigService,
) -> None:
    cluster_id, topology = None, None
    if task.owner:
        if task.owner.type == ADCMCoreType.CLUSTER:
            cluster_id = task.owner.id
        elif task.owner.related_objects.cluster is not None:
            cluster_id = task.owner.related_objects.cluster.id

    if cluster_id:
        topology = retrieve_cluster_topology(cluster_id)

    job_config = prepare_ansible_job_config(
        task=task, job=job, configuration=configuration, config_service=config_service, topology=topology
    )
    job_run_dir = configuration.adcm.run_dir / str(job.runtime.id)

    with (job_run_dir / "config.json").open(mode="w", encoding="utf-8") as config_file:
        json.dump(obj=job_config, fp=config_file, sort_keys=True, separators=(",", ":"))

    inventory = prepare_ansible_inventory(
        task=task, topology=topology, cluster_service=cluster_service, config_service=config_service
    )
    with (job_run_dir / "inventory.json").open(mode="w", encoding="utf-8") as file_descriptor:
        json.dump(obj=inventory, fp=file_descriptor, separators=(",", ":"))

    ansible_cfg_config_parser: ConfigParser = prepare_ansible_cfg(task=task)
    with (job_run_dir / "ansible.cfg").open(mode="w", encoding="utf-8") as config_file:
        ansible_cfg_config_parser.write(config_file)


def prepare_ansible_inventory(
    task: Task,
    cluster_service: ClusterService,
    config_service: ConfigService,
    topology: ClusterTopology | None = None,
) -> dict[str, Any]:
    delta, process_context, process_mapping_delta = None, None, {}

    if task.action.hc_acl:
        delta = task.hostcomponent.mapping_delta

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = context_m.get_action_process_context(process, topology, config_service=config_service)
        process_mapping_delta = process_context.cumulative_delta

    return context_m.get_inventory_data(
        target=task.target,
        is_host_action=task.action.is_host_action,
        delta=delta,
        related_objects=task.owner.related_objects,
        process_mapping_delta=process_mapping_delta,
        cluster_service=cluster_service,
        config_service=config_service,
    )


def prepare_ansible_job_config(
    task: Task,
    job: RichJob,
    configuration: ExternalSettings,
    config_service: ConfigService,
    topology: ClusterTopology | None = None,
) -> dict[str, Any]:
    job_data = JobData(
        id=job.runtime.id,
        action=task.action.name,
        job_name=job.spec.names.internal,
        command=job.spec.names.internal,
        script=job.spec.script.path,
        verbose=task.verbose,
        playbook=str(task.bundle.root / job.spec.script.path),
        action_type_specification=_get_owner_specific_data(task=task),
    )

    if task.owner and topology:
        job_data.cluster_id = topology.cluster_id

    if task.config:
        job_data.config = task.config

    params: dict = job.spec.script.params.model_dump()
    if not params["ansible_tags"]:
        # if it's empty, it shouldn't be included
        # and since it's the only "pre-defined" field we want empty dict if that's the case
        params.pop("ansible_tags")

    if params:
        job_data.params = params

    process_context = None

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = context_m.get_action_process_context(process, topology, config_service=config_service)

    adcm = ADCM.objects.select_related("config").get()

    return JobConfig(
        adcm=ADCMJobConfig(
            uuid=adcm.uuid, config=context_m.get_adcm_configuration(adcm, config_service=config_service)
        ),
        context=context_m.get_run_context(task=task),
        env=JobEnv(
            run_dir=str(configuration.adcm.run_dir),
            log_dir=str(configuration.adcm.log_dir),
            tmp_dir=str(configuration.adcm.run_dir / str(job.runtime.id) / "tmp"),
            stack_dir=str(task.bundle.root),
            status_api_token=configuration.integrations.status_server_token,
            consul_url=configuration.consul.url,
            consul_datacenter=configuration.consul.datacenter,
            consul_cacert_file=configuration.consul.cacert_file,
        ),
        job=job_data,
        process=process_context.to_context() if process_context else None,
    ).model_dump(mode="json", exclude_unset=True)


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
) -> ClusterActionType | ServiceActionType | ComponentActionType | ProviderActionType | HostActionType:
    owner = task.owner
    if not owner:
        message = "Can't get owner task data for task without owner"
        raise RuntimeError(message)

    match owner.type:
        case ADCMCoreType.CLUSTER:
            return ClusterActionType(action_proto_type="cluster", hostgroup="CLUSTER")
        case ADCMCoreType.PROVIDER:
            return ProviderActionType(
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
                provider_id=task.owner.related_objects.provider.id,
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


def save_fs_logs_to_db(job: RichJob, work_dir: Path, log_type: Literal["stdout", "stderr"]) -> None:
    log_path = work_dir / f"{job.spec.script.type.value}-{log_type}.txt"
    if not log_path.is_file():
        return

    corresponding_log = LogStorage.objects.filter(
        job_id=job.runtime.id, name=job.spec.script.type.value, type=log_type
    ).first()
    if not corresponding_log:
        return

    corresponding_log.body = log_path.read_text(encoding="utf-8")
    corresponding_log.save(update_fields=["body"])
