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

from collections import defaultdict
from configparser import ConfigParser
from functools import partial
from logging import getLogger
from pathlib import Path
from typing import Any, Generator, Iterable, Literal
from uuid import UUID
import json
import traceback

from adcm.feature_flags import use_new_config_processing
from ansible_plugin.utils import finish_check
from core.legacy.cluster.types import ClusterTopology
from core.legacy.job.dto import TaskUpdateDTO
from core.legacy.job.executors import BundleExecutorConfig, ExecutorConfig
from core.legacy.job.runners import ExecutionTarget, ExternalSettings
from core.legacy.job.types import AssociatedProcess, HcAclRule, Job, ScriptType, Task, TaskMappingDelta
from core.types import ADCMCoreType, ClusterID, ComponentNameKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.transaction import atomic
from infra.services import get_config_service
from rbac.roles import re_apply_policy_for_jobs
import core

from cm.converters import CoreObject, core_type_to_model, orm_object_to_core_descriptor
from cm.errors import AdcmEx
from cm.legacy.services.action_process.types import ProcessStepState
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.config import ConfigAttrPair
from cm.legacy.services.config.spec import retrieve_flat_spec_for_objects
from cm.legacy.services.job import context as context_m
from cm.legacy.services.job import inventory as inventory_m
from cm.legacy.services.job.run.executors import (
    AnsibleExecutorConfig,
    AnsibleProcessExecutor,
    InternalExecutor,
    PythonProcessExecutor,
)
from cm.legacy.services.job.run.repo import JobRepoImpl
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
from cm.legacy.services.mapping import change_host_component_mapping_no_lock, check_nothing, lock_cluster_mapping
from cm.legacy.status_api import send_prototype_and_state_update_event
from cm.legacy.utils import deep_merge
from cm.models import (
    ADCM,
    AnsibleConfig,
    Cluster,
    Component,
    ConfigLog,
    LogStorage,
    Process,
    Prototype,
    TaskLog,
)

logger = getLogger("adcm")


class ExecutionTargetFactory:
    def __init__(self):
        self._default_ansible_finalizers = (finish_check_logs,)
        self._supported_internal_scripts = {
            "bundle_switch": internal_script_bundle_switch,
            "bundle_revert": internal_script_bundle_revert,
            "hc_apply": internal_script_hc_apply,
            "config_apply": internal_script_config_apply,
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

                    script = partial(internal_script_func, task=task, job=job_info)
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
def internal_script_bundle_switch(task: Task, job: Job) -> int:
    _ = job

    task_ = TaskLog.objects.get(id=task.id)

    if use_new_config_processing():
        from use_cases.legacy.upgrade import build_switch_revert_callbacks

        from cm.legacy.bundle_switch_revert import bundle_switch

        config_service = get_config_service()
        callbacks = build_switch_revert_callbacks(config_service=config_service)
        bundle_switch(
            obj=task_.task_object, upgrade=task_.action.upgrade, callbacks=callbacks, config_service=config_service
        )
    else:
        from cm.legacy.upgrade import bundle_switch

        bundle_switch(obj=task_.task_object, upgrade=task_.action.upgrade)

    _switch_hc_if_required(task=task)

    re_apply_policy_for_jobs(action_object=task_.task_object, task=task_)

    return 0


@atomic()
def internal_script_bundle_revert(task: Task, job: Job) -> int:
    _ = job

    task_ = TaskLog.objects.get(id=task.id)

    try:
        if use_new_config_processing():
            from use_cases.legacy.upgrade import build_switch_revert_callbacks

            from cm.legacy.bundle_switch_revert import bundle_revert

            config_service = get_config_service()
            callbacks = build_switch_revert_callbacks(config_service=config_service)

            bundle_revert(obj=task_.task_object, callbacks=callbacks, config_service=config_service)
        else:
            from cm.legacy.upgrade import bundle_revert

            bundle_revert(obj=task_.task_object)
    except ObjectDoesNotExist as error:
        # This is a hack. We can do this, since all AdcmEx are intercepted in the Executer,
        # and a message is generated in the log there.
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"The configuration cannot be restored because the record was deleted.\n\n{traceback.format_exc()}",
        ) from error
    finally:
        send_prototype_and_state_update_event(object_=task_.task_object)

    _switch_hc_if_required(task=task)

    re_apply_policy_for_jobs(action_object=task_.task_object, task=task_)

    return 0


def internal_script_hc_apply(task: Task, job: Job) -> int:
    if task.owner and task.owner.type not in {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
        raise AdcmEx(
            code="WRONG_OWNER",
            msg="Internal script `hc_apply` can only be defined in cluster, service or component context`",
        )

    hc_apply_rules = job.params.rules

    if not hc_apply_rules:
        hc_apply_rules = task.action.hc_acl

    if task.owner.type == ADCMCoreType.CLUSTER:
        cluster_id = task.owner.id
        cluster_prototype_id = task.owner.prototype_id
    else:
        cluster_id = task.owner.related_objects.cluster.id
        cluster_prototype_id = task.owner.related_objects.cluster.prototype_id

    bundle_id = Prototype.objects.values_list("bundle_id", flat=True).get(id=cluster_prototype_id)

    with atomic():
        lock_cluster_mapping(cluster_id=cluster_id)

        if (
            isinstance(task.action_process, AssociatedProcess)
            and (process := Process.objects.filter(id=task.action_process.id)).exists()
        ):
            mapping_delta = _extract_hc_apply_delta_for_process(process.first())
            #  hc rule for process are validated during step submissions hence cumulative delta is valid
            delta_part = mapping_delta
        else:
            mapping_delta = task.hostcomponent.mapping_delta
            delta_part = _extract_mapping_delta_part(
                cluster_id=cluster_id, mapping_delta=mapping_delta, hc_apply_rules=hc_apply_rules
            )
        change_host_component_mapping_no_lock(
            cluster_id=cluster_id,
            bundle_id=bundle_id,
            mapping_delta=delta_part,
            checks_func=check_nothing,
        )

    return 0


def internal_script_config_apply(task: Task, job: Job) -> int:
    owner_model = core_type_to_model(core_type=task.owner.type)
    # need to think if the owner object may be deleted during execution, need we check?
    owner = owner_model.objects.get(id=task.owner.id)

    func = _apply_config_changes_new if use_new_config_processing() else _apply_config_changes

    # are we going to allow to change one component from context of another?
    for change in job.params.changes:
        changing_object = _extract_apply_config_target(owner, change)
        func(job.id, changing_object, change["parameters"], f"{task.action.display_name} process update")
    return 0


def _apply_config_changes_new(
    job_id: int, db_object: ADCM | CoreObject, parameters: list[dict], changes_description: str
) -> None:
    from use_cases.transition.config import update_configuration_from_job

    _check_parameters_unique(parameters)

    config_service = get_config_service()
    update_configuration_from_job(
        owner=orm_object_to_core_descriptor(db_object),
        changes_input=parameters,
        convert=_prepare_changes_new,
        job_id=job_id,
        description=changes_description,
        config_service=config_service,
        owner_orm=db_object,
    )


def _apply_config_changes(
    job_id: int, db_object: ADCM | CoreObject, parameters: list[dict], changes_description: str
) -> tuple[dict, bool]:
    from ansible_plugin.executors.config_old import _fill_config_and_attr

    from cm.legacy.api import set_object_config_with_plugin

    configuration = ConfigAttrPair(**ConfigLog.objects.values("config", "attr").get(id=db_object.config.current))
    spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(db_object.prototype_id,)).values()))

    changes = _prepare_changes(parameters, spec)

    changed = _fill_config_and_attr(target=configuration, changes=changes, spec=spec)

    if not changed:
        return changes.config, False

    set_object_config_with_plugin(
        job_id=job_id,
        obj=db_object,
        config=configuration.config,
        attr=configuration.attr,
        description=changes_description,
    )

    return changes.config, True


def _extract_hc_apply_delta_for_process(process: Process) -> TaskMappingDelta:
    last_mapping_step = (
        process.steps.filter(state=ProcessStepState.COMPLETED)
        .exclude(Q(processstepinput__mapping__isnull=True) | Q(processstepinput__mapping={}))
        .order_by("-id")
        .first()
    )

    if not last_mapping_step:
        return TaskMappingDelta(add={}, remove={})

    cumulative_delta = last_mapping_step.processstepinput.mapping["cumulative_delta"]

    add_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("add", []):
        add_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    remove_mapping: dict[int, set[int]] = {}
    for entry in cumulative_delta.get("remove", []):
        remove_mapping.setdefault(entry["component_id"], set()).add(entry["host_id"])

    return TaskMappingDelta(add=add_mapping, remove=remove_mapping)


def _check_parameters_unique(parameters: list[dict]) -> None:
    checked = set()

    for entry in parameters:
        key = entry["key"]
        if key not in checked:
            checked.add(key)
        else:
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{key} is not unique within parameters")


def _prepare_changes_new(parameters: list[dict], spec: core.config.spec.FullSpec) -> list[core.config.ChangeRequest]:
    changes = []

    for parameter_change in parameters:
        full_name = core.config.names.ensure_full_name(parameter_change["key"])
        value = parameter_change["value"]

        if full_name not in spec.groups:
            change = core.config.ChangeRequest.for_value(name=full_name, value=value)
            changes.append(change)
            continue

        group_spec = spec.groups[full_name]
        if group_spec.selection:
            change = core.config.ChangeRequest.for_group_selection(name=full_name, value=value)
            changes.append(change)
            continue

        if not spec.groups[full_name].activation:
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{full_name}: only activatable groups may be (de)activated")

        if not isinstance(value, bool):
            raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"{full_name}: value expected to be boolean")

        change = core.config.ChangeRequest.for_activation_attribute(name=full_name, value=value)
        changes.append(change)

    return changes


def _prepare_changes(parameters: list[dict], spec: dict) -> ConfigAttrPair:
    changes = ConfigAttrPair(config={}, attr={})

    for parameter in parameters:
        key = parameter["key"]
        value = parameter.get("value")

        if "/" not in key:
            key = f"{key}/"

        param_spec = spec.get(key)
        if not param_spec:
            continue

        if param_spec.type == "group" and param_spec.limits["activatable"]:
            if not isinstance(value, bool):
                raise AdcmEx(code="INTERNAL_SERVER_ERROR", msg=f"Value for {key} expected to be boolean")
            changes.attr[key] = {"active": bool(value)}
        else:
            changes.config[key] = value

    return changes


def _extract_apply_config_target(owner: ADCM | CoreObject, change: dict) -> ADCM | CoreObject:
    # in order to preserve single mechanism with adcm_config plugin.
    # Requires refactoring to move it common location with plugins
    from ansible_plugin.base import (
        CoreObjectTargetDescription,
        _from_target_description,
        build_vars_context_from_descriptor,
    )
    from ansible_plugin.errors import PluginTargetDetectionError

    context = build_vars_context_from_descriptor(orm_object_to_core_descriptor(owner))
    target_description = CoreObjectTargetDescription(**change["object"])

    try:
        target = _from_target_description(target_description, context)
    except PluginTargetDetectionError as e:
        raise AdcmEx(
            code="INTERNAL_SERVER_ERROR",
            msg=f"The configuration contains non-existing object of owner {change['object']}",
        ) from e

    return core_type_to_model(core_type=target.type).objects.get(pk=target.id)


def _extract_mapping_delta_part(
    cluster_id: ClusterID, mapping_delta: TaskMappingDelta, hc_apply_rules: list[HcAclRule]
) -> TaskMappingDelta:
    topology = retrieve_cluster_topology(cluster_id=cluster_id)
    components_map = topology.component_full_name_id_mapping

    delta_data = defaultdict(lambda: defaultdict(set))
    for hc_rule in hc_apply_rules:
        component_id = components_map.get(ComponentNameKey(service=hc_rule.service, component=hc_rule.component))
        if component_id is None:
            continue
        delta_data[hc_rule.action][component_id].update(
            getattr(mapping_delta, hc_rule.action, {}).get(component_id, ())
        )

    return TaskMappingDelta(**delta_data)


def _switch_hc_if_required(task: Task) -> None:
    """
    Should be performed during upgrade of cluster, if not cluster, no need in HC update.
    Because it's upgrade, it will be called either on cluster or provider,
    so task object will be one of those too.
    """

    if not task.hostcomponent.post_upgrade:
        return

    if task.target.type != ADCMCoreType.CLUSTER:
        return

    delta = task.hostcomponent.mapping_delta

    # `post_upgrade_hc_map` contains records with "component_prototype_id" which are "extra" to regular hc
    for new_entry in task.hostcomponent.post_upgrade:
        if "component_prototype_id" in new_entry:
            # if optimized to 1 request, it's probably good to filter by prototype__type="component"
            component_id = Component.objects.values_list("id", flat=True).get(
                cluster_id=task.target.id, prototype_id=new_entry["component_prototype_id"]
            )
            if component_id not in delta.add:
                delta.add[component_id] = {new_entry["host_id"]}
            else:
                delta.add[component_id].add(new_entry["host_id"])

    JobRepoImpl.update_task(id=task.id, data=TaskUpdateDTO(post_upgrade_hc_map=None, hostcomponentmap=delta))


# ENVIRONMENT BUILDERS


class UiidJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def prepare_ansible_environment(task: Task, job: Job, configuration: ExternalSettings) -> None:
    cluster_id, topology = None, None
    if task.owner:
        if task.owner.type == ADCMCoreType.CLUSTER:
            cluster_id = task.owner.id
        elif task.owner.related_objects.cluster is not None:
            cluster_id = task.owner.related_objects.cluster.id

    if cluster_id:
        topology = retrieve_cluster_topology(cluster_id)

    job_config = prepare_ansible_job_config(task=task, job=job, configuration=configuration, topology=topology)
    job_run_dir = configuration.adcm.run_dir / str(job.id)

    with (job_run_dir / "config.json").open(mode="w", encoding="utf-8") as config_file:
        json.dump(obj=job_config, fp=config_file, sort_keys=True, separators=(",", ":"))

    inventory = prepare_ansible_inventory(task=task, topology=topology)
    with (job_run_dir / "inventory.json").open(mode="w", encoding="utf-8") as file_descriptor:
        json.dump(obj=inventory, fp=file_descriptor, cls=UiidJSONEncoder, separators=(",", ":"))

    ansible_cfg_config_parser: ConfigParser = prepare_ansible_cfg(task=task)
    with (job_run_dir / "ansible.cfg").open(mode="w", encoding="utf-8") as config_file:
        ansible_cfg_config_parser.write(config_file)


def prepare_ansible_inventory(task: Task, topology: ClusterTopology | None = None) -> dict[str, Any]:
    delta, process_context, process_mapping_delta = None, None, {}

    if task.action.hc_acl:
        delta = task.hostcomponent.mapping_delta

    module = context_m if use_new_config_processing() else inventory_m

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = module.get_action_process_context(process, topology)
        process_mapping_delta = process_context.cumulative_delta

    return module.get_inventory_data(
        target=task.target,
        is_host_action=task.action.is_host_action,
        delta=delta,
        related_objects=task.owner.related_objects,
        process_mapping_delta=process_mapping_delta,
    )


def prepare_ansible_job_config(
    task: Task, job: Job, configuration: ExternalSettings, topology: ClusterTopology | None = None
) -> dict[str, Any]:
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

    if task.owner and topology:
        job_data.cluster_id = topology.cluster_id

    if task.config:
        job_data.config = task.config

    params: dict = job.params.model_dump()
    if not params["ansible_tags"]:
        # if it's empty, it shouldn't be included
        # and since it's the only "pre-defined" field we want empty dict if that's the case
        params.pop("ansible_tags")

    if params:
        job_data.params = params

    process_context = None

    if use_new_config_processing():
        config_service = get_config_service()
        get_action_process_context = context_m.get_action_process_context
        get_adcm_configuration = partial(context_m.get_adcm_configuration, config_service=config_service)
    else:
        get_action_process_context = inventory_m.get_action_process_context
        get_adcm_configuration = inventory_m.get_adcm_configuration

    if task.action_process and topology:
        process = Process.objects.get(id=task.action_process.id)
        process_context = get_action_process_context(process, topology)

    adcm = ADCM.objects.select_related("config").get()

    return JobConfig(
        adcm=ADCMJobConfig(uuid=str(adcm.uuid), config=get_adcm_configuration(adcm)),
        context=context,
        env=JobEnv(
            run_dir=str(configuration.adcm.run_dir),
            log_dir=str(configuration.adcm.log_dir),
            tmp_dir=str(configuration.adcm.run_dir / str(job.id) / "tmp"),
            stack_dir=str(task.bundle.root),
            status_api_token=configuration.integrations.status_server_token,
            consul_url=configuration.consul.url,
            consul_datacenter=configuration.consul.datacenter,
            consul_client_cert_file=configuration.consul.client_cert_file,
            consul_client_key_file=configuration.consul.client_key_file,
            consul_client_cacert_file=configuration.consul.client_cacert_file,
        ),
        job=job_data,
        process=process_context.to_context() if process_context else None,
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
