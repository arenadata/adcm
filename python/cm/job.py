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

from collections.abc import Hashable
from configparser import ConfigParser
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
from typing import Any
import copy
import json
import subprocess

from audit.cases.common import get_or_create_audit_obj
from audit.cef_logger import cef_logger
from audit.models import (
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
)
from core.types import CoreObjectDescriptor
from django.conf import settings
from django.db.transaction import atomic, on_commit
from django.utils import timezone
from rbac.roles import re_apply_policy_for_jobs

from cm.adcm_config.checks import check_attr
from cm.adcm_config.config import (
    check_config_spec,
    get_prototype_config,
    process_config_spec,
    process_file_type,
)
from cm.api import (
    check_hc,
    check_maintenance_mode,
    check_sub_key,
    get_hc,
    make_host_comp_list,
    save_hc,
)
from cm.converters import model_name_to_core_type
from cm.errors import AdcmEx, raise_adcm_ex
from cm.hierarchy import Tree
from cm.issue import (
    check_bound_components,
    check_component_constraint,
    check_hc_requires,
    check_service_requires,
    lock_affected_objects,
    unlock_affected_objects,
    update_hierarchy_issues,
)
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    ActionType,
    ADCMEntity,
    Cluster,
    ClusterObject,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    HostProvider,
    JobLog,
    JobStatus,
    LogStorage,
    MaintenanceMode,
    Prototype,
    ServiceComponent,
    SubAction,
    TaskLog,
    Upgrade,
    get_object_cluster,
)
from cm.services.config.spec import convert_to_flat_spec_from_proto_flat_spec
from cm.services.job.config import get_job_config
from cm.services.job.inventory import get_inventory_data
from cm.services.job.inventory._config import update_configuration_for_inventory_inplace
from cm.services.job.types import HcAclAction
from cm.services.job.utils import JobScope, get_selector
from cm.services.status.notify import reset_objects_in_mm
from cm.status_api import (
    send_object_update_event,
    send_prototype_and_state_update_event,
    send_task_status_update_event,
)
from cm.utils import get_env_with_venv_path
from cm.variant import process_variant


@dataclass
class ActionRunPayload:
    conf: dict = field(default_factory=dict)
    attr: dict = field(default_factory=dict)
    hostcomponent: list[dict] = field(default_factory=list)
    verbose: bool = False


def run_action(
    action: Action,
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    payload: ActionRunPayload,
    hosts: list[int],
) -> TaskLog:
    cluster: Cluster | None = get_object_cluster(obj=obj)

    if hosts:
        check_action_hosts(action=action, obj=obj, cluster=cluster, hosts=hosts)

    action_target = get_host_object(action=action, cluster=cluster) if action.host_action else obj

    object_locks = action_target.concerns.filter(type=ConcernType.LOCK)

    if action.name == settings.ADCM_DELETE_SERVICE_ACTION_NAME:
        object_locks = object_locks.exclude(owner_id=obj.id, owner_type=obj.content_type)

    if object_locks.exists():
        raise AdcmEx(code="LOCK_ERROR", msg=f"object {action_target} is locked")

    if (
        action.name not in settings.ADCM_SERVICE_ACTION_NAMES_SET
        and action_target.concerns.filter(type=ConcernType.ISSUE).exists()
    ):
        raise AdcmEx(code="ISSUE_INTEGRITY_ERROR", msg=f"object {action_target} has issues")

    if not action.allowed(obj=action_target):
        raise AdcmEx(code="TASK_ERROR", msg="action is disabled")

    spec, flat_spec = check_action_config(action=action, obj=obj, conf=payload.conf, attr=payload.attr)

    is_upgrade_action = hasattr(action, "upgrade")

    if is_upgrade_action and not action.hostcomponentmap:
        check_constraints_for_upgrade(
            cluster=cluster, upgrade=action.upgrade, host_comp_list=get_actual_hc(cluster=cluster)
        )

    host_map, post_upgrade_hc = check_hostcomponentmap(cluster=cluster, action=action, new_hc=payload.hostcomponent)

    with atomic():
        task = create_task(
            action=action,
            obj=obj,
            conf=payload.conf,
            attr=payload.attr,
            verbose=payload.verbose,
            hosts=hosts,
            hostcomponent=get_hc(cluster=cluster),
            post_upgrade_hc=post_upgrade_hc,
        )
        if host_map or (is_upgrade_action and host_map is not None):
            save_hc(cluster=cluster, host_comp_list=host_map)

        if payload.conf:
            new_conf = update_configuration_for_inventory_inplace(
                configuration=payload.conf,
                attributes=payload.attr,
                specification=convert_to_flat_spec_from_proto_flat_spec(prototypes_flat_spec=flat_spec),
                config_owner=CoreObjectDescriptor(
                    id=obj.pk, type=model_name_to_core_type(model_name=obj._meta.model_name)
                ),
            )
            process_file_type(obj=task, spec=spec, conf=payload.conf)
            task.config = new_conf
            task.save()

        on_commit(func=partial(send_task_status_update_event, object_=task, status=JobStatus.CREATED.value))

    re_apply_policy_for_jobs(action_object=obj, task=task)

    run_task(task)

    return task


def check_action_hosts(action: Action, obj: ADCMEntity, cluster: Cluster | None, hosts: list[int]) -> None:
    if not action.partial_execution:
        raise AdcmEx(code="TASK_ERROR", msg="Only action with partial_execution permission can receive host list")

    provider = obj if obj.prototype.type == "provider" else None

    hosts = Host.objects.filter(id__in=hosts)

    if cluster and hosts.exclude(cluster=cluster).exists():
        raise AdcmEx(code="TASK_ERROR", msg=f"One of hosts does not belong to cluster #{cluster.pk}")

    if provider and hosts.exclude(provider=provider).exists():
        raise AdcmEx(code="TASK_ERROR", msg=f"One of hosts does not belong to host provider #{provider.pk}")


def restart_task(task: TaskLog):
    if task.status in (JobStatus.CREATED, JobStatus.RUNNING):
        raise_adcm_ex("TASK_ERROR", f"task #{task.pk} is running")
    elif task.status == JobStatus.SUCCESS:
        run_task(task)
    elif task.status in (JobStatus.FAILED, JobStatus.ABORTED):
        run_task(task, "restart")
    else:
        raise_adcm_ex("TASK_ERROR", f"task #{task.pk} has unexpected status: {task.status}")


def get_host_object(action: Action, cluster: Cluster | None) -> ADCMEntity | None:
    obj = None
    if action.prototype.type == "service":
        obj = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "component":
        obj = ServiceComponent.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "cluster":
        obj = cluster

    return obj


def check_action_config(action: Action, obj: ADCMEntity, conf: dict, attr: dict) -> tuple[dict, dict]:
    proto = action.prototype
    spec, flat_spec, _, _ = get_prototype_config(prototype=proto, action=action, obj=obj)
    if not spec:
        if conf:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Absent config in action prototype")

        return {}, {}

    if not conf:
        raise AdcmEx("TASK_ERROR", "action config is required")

    check_attr(proto, action, attr, flat_spec)

    object_config = {}
    if obj.config is not None:
        object_config = ConfigLog.objects.get(id=obj.config.current).config

    process_variant(obj=obj, spec=spec, conf=object_config)
    check_config_spec(proto=proto, obj=action, spec=spec, flat_spec=flat_spec, conf=conf, attr=attr)

    process_config_spec(obj=obj, spec=spec, new_config=conf)

    return spec, flat_spec


def add_to_dict(my_dict: dict, key: Hashable, subkey: Hashable, value: Any):
    if key not in my_dict:
        my_dict[key] = {}

    my_dict[key][subkey] = value


def check_action_hc(
    action_hc: list[dict],
    service: ClusterObject,
    component: ServiceComponent,
    action: Action,
) -> bool:
    for item in action_hc:
        if item["service"] == service and item["component"] == component and item["action"] == action:
            return True

    return False


def cook_comp_key(name, subname):
    return f"{name}.{subname}"


def cook_delta(
    cluster: Cluster,
    new_hc: list[tuple[ClusterObject, Host, ServiceComponent]],
    action_hc: list[dict],
    old: dict = None,
) -> dict:
    def add_delta(_delta, action, _key, fqdn, _host):
        _service, _comp = _key.split(".")
        if not check_action_hc(action_hc, _service, _comp, action):
            msg = (
                f'no permission to "{action}" component "{_comp}" of ' f'service "{_service}" to/from hostcomponentmap'
            )
            raise_adcm_ex("WRONG_ACTION_HC", msg)

        add_to_dict(_delta[action], _key, fqdn, _host)

    new = {}
    for service, host, comp in new_hc:
        key = cook_comp_key(service.prototype.name, comp.prototype.name)
        add_to_dict(new, key, host.fqdn, host)

    if old is None:
        old = {}
        for hostcomponent in HostComponent.objects.filter(cluster=cluster):
            key = cook_comp_key(hostcomponent.service.prototype.name, hostcomponent.component.prototype.name)
            add_to_dict(old, key, hostcomponent.host.fqdn, hostcomponent.host)

    delta = {HcAclAction.ADD.value: {}, HcAclAction.REMOVE.value: {}}
    for key, value in new.items():
        if key in old:
            for host in value:
                if host not in old[key]:
                    add_delta(_delta=delta, action=HcAclAction.ADD.value, _key=key, fqdn=host, _host=value[host])

            for host in old[key]:
                if host not in value:
                    add_delta(_delta=delta, action=HcAclAction.REMOVE.value, _key=key, fqdn=host, _host=old[key][host])
        else:
            for host in value:
                add_delta(_delta=delta, action=HcAclAction.ADD.value, _key=key, fqdn=host, _host=value[host])

    for key, value in old.items():
        if key not in new:
            for host in value:
                add_delta(_delta=delta, action=HcAclAction.REMOVE.value, _key=key, fqdn=host, _host=value[host])

    logger.debug("OLD: %s", old)
    logger.debug("NEW: %s", new)
    logger.debug("DELTA: %s", delta)

    return delta


def check_hostcomponentmap(
    cluster: Cluster | None, action: Action, new_hc: list[dict]
) -> tuple[list[tuple[ClusterObject, Host, ServiceComponent]] | None, list]:
    if not action.hostcomponentmap:
        return None, []

    if not new_hc:
        raise_adcm_ex(code="TASK_ERROR", msg="hc is required")

    if not cluster:
        raise_adcm_ex(code="TASK_ERROR", msg="Only cluster objects can have action with hostcomponentmap")

    if not hasattr(action, "upgrade"):
        for host_comp in new_hc:
            host = Host.obj.get(id=host_comp.get("host_id", 0))
            if host.concerns.filter(type=ConcernType.LOCK).exists():
                raise_adcm_ex(code="LOCK_ERROR", msg=f"object {host} is locked")

            if host.concerns.filter(type=ConcernType.ISSUE).exists():
                raise_adcm_ex(code="ISSUE_INTEGRITY_ERROR", msg=f"object {host} has issues")

    post_upgrade_hc, clear_hc = check_upgrade_hc(action=action, new_hc=new_hc)

    old_hc = get_old_hc(saved_hostcomponent=get_hc(cluster=cluster))
    if not hasattr(action, "upgrade"):
        prepared_hc_list = check_hc(cluster=cluster, hc_in=clear_hc)
    else:
        check_sub_key(hc_in=clear_hc)
        prepared_hc_list = make_host_comp_list(cluster=cluster, hc_in=clear_hc)
        check_constraints_for_upgrade(cluster=cluster, upgrade=action.upgrade, host_comp_list=prepared_hc_list)

    cook_delta(cluster=cluster, new_hc=prepared_hc_list, action_hc=action.hostcomponentmap, old=old_hc)

    return prepared_hc_list, post_upgrade_hc


def check_constraints_for_upgrade(cluster, upgrade, host_comp_list):
    try:
        for service in ClusterObject.objects.filter(cluster=cluster):
            try:
                prototype = Prototype.objects.get(name=service.name, type="service", bundle=upgrade.bundle)
                check_component_constraint(
                    cluster=cluster,
                    service_prototype=prototype,
                    hc_in=[i for i in host_comp_list if i[0] == service],
                    old_bundle=cluster.prototype.bundle,
                )
                check_service_requires(cluster=cluster, proto=prototype)
            except Prototype.DoesNotExist:
                pass

        check_hc_requires(shc_list=host_comp_list)
        check_bound_components(shc_list=host_comp_list)
        check_maintenance_mode(cluster=cluster, host_comp_list=host_comp_list)
    except AdcmEx as e:
        if e.code == "COMPONENT_CONSTRAINT_ERROR":
            e.msg = (
                f"Host-component map of upgraded cluster should satisfy "
                f"constraints of new bundle. Now error is: {e.msg}"
            )

        raise_adcm_ex(e.code, e.msg)


def check_upgrade_hc(action, new_hc):
    post_upgrade_hc = []
    clear_hc = copy.deepcopy(new_hc)
    buff = 0
    for host_comp in new_hc:
        if "component_prototype_id" in host_comp:
            if not hasattr(action, "upgrade"):
                raise_adcm_ex(
                    "WRONG_ACTION_HC",
                    "Hc map with components prototype available only in upgrade action",
                )

            proto = Prototype.obj.get(
                type="component",
                id=host_comp["component_prototype_id"],
                bundle=action.upgrade.bundle,
            )
            for hc_acl in action.hostcomponentmap:
                if proto.name == hc_acl["component"]:
                    buff += 1
                    if hc_acl["action"] != HcAclAction.ADD.value:
                        raise_adcm_ex(
                            "WRONG_ACTION_HC",
                            "New components from bundle with upgrade you can only add, not remove",
                        )

            if buff == 0:
                raise_adcm_ex("INVALID_INPUT", "hc_acl doesn't allow actions with this component")

            post_upgrade_hc.append(host_comp)
            clear_hc.remove(host_comp)

    return post_upgrade_hc, clear_hc


def check_service_task(cluster_id: int, action: Action) -> ClusterObject | None:
    cluster = Cluster.obj.get(id=cluster_id)
    try:
        return ClusterObject.objects.get(cluster=cluster, prototype=action.prototype)  # noqa: TRY300
    except ClusterObject.DoesNotExist:
        msg = f"service #{action.prototype.pk} for action " f'"{action.name}" is not installed in cluster #{cluster.pk}'
        raise_adcm_ex("CLUSTER_SERVICE_NOT_FOUND", msg)

    return None


def check_cluster(cluster_id: int) -> Cluster:
    return Cluster.obj.get(id=cluster_id)


def get_actual_hc(cluster: Cluster):
    new_hc = []
    for hostcomponent in HostComponent.objects.filter(cluster=cluster):
        new_hc.append((hostcomponent.service, hostcomponent.host, hostcomponent.component))
    return new_hc


def get_old_hc(saved_hostcomponent: list[dict]):
    if not saved_hostcomponent:
        return {}

    old_hostcomponent = {}
    for hostcomponent in saved_hostcomponent:
        service = ClusterObject.objects.get(id=hostcomponent["service_id"])
        comp = ServiceComponent.objects.get(id=hostcomponent["component_id"])
        host = Host.objects.get(id=hostcomponent["host_id"])
        key = cook_comp_key(service.prototype.name, comp.prototype.name)
        add_to_dict(old_hostcomponent, key, host.fqdn, host)

    return old_hostcomponent


def re_prepare_job(job_scope: JobScope) -> None:
    cluster = get_object_cluster(obj=job_scope.object)

    delta = {}
    if job_scope.action.hostcomponentmap:
        delta = cook_delta(
            cluster=cluster,
            new_hc=get_actual_hc(cluster=cluster),
            action_hc=job_scope.action.hostcomponentmap,
            old=get_old_hc(saved_hostcomponent=job_scope.task.hostcomponentmap),
        )

    prepare_job(job_scope=job_scope, delta=delta)


def write_job_config(job_id: int, config: dict[str, Any]) -> None:
    config_path = Path(settings.RUN_DIR, str(job_id), "config.json")
    with config_path.open(mode="w", encoding=settings.ENCODING_UTF_8) as config_file:
        json.dump(obj=config, fp=config_file, sort_keys=True, separators=(",", ":"))


def prepare_job(job_scope: JobScope, delta: dict):
    write_job_config(job_id=job_scope.job_id, config=get_job_config(job_scope=job_scope))

    inventory = get_inventory_data(obj=job_scope.object, action=job_scope.action, delta=delta)
    with (settings.RUN_DIR / f"{job_scope.job_id}" / "inventory.json").open(
        mode="w", encoding=settings.ENCODING_UTF_8
    ) as file_descriptor:
        json.dump(obj=inventory, fp=file_descriptor, separators=(",", ":"))

    prepare_ansible_config(job_id=job_scope.job_id, action=job_scope.action, sub_action=job_scope.sub_action)


def create_task(
    action: Action,
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    conf: dict,
    attr: dict,
    hostcomponent: list[dict],
    hosts: list[int],
    verbose: bool,
    post_upgrade_hc: list[dict],
) -> TaskLog:
    selector = get_selector(obj=obj, action=action)
    task = TaskLog.objects.create(
        action=action,
        task_object=obj,
        config=conf,
        attr=attr,
        hostcomponentmap=hostcomponent,
        hosts=hosts,
        post_upgrade_hc_map=post_upgrade_hc,
        verbose=verbose,
        status=JobStatus.CREATED,
        selector=selector,
    )

    if action.type == ActionType.JOB.value:
        sub_actions = [None]
    else:
        sub_actions = SubAction.objects.filter(action=action).order_by("id")

    for sub_action in sub_actions:
        job = JobLog.obj.create(
            task=task,
            action=action,
            sub_action=sub_action,
            log_files=action.log_files,
            status=JobStatus.CREATED,
            selector=selector,
        )
        log_type = sub_action.script_type if sub_action else action.script_type
        LogStorage.objects.create(job=job, name=log_type, type="stdout", format="txt")
        LogStorage.objects.create(job=job, name=log_type, type="stderr", format="txt")
        Path(settings.RUN_DIR, f"{job.pk}", "tmp").mkdir(parents=True, exist_ok=True)

    return task


def get_state(action: Action, job: JobLog, status: str) -> tuple[str | None, list[str], list[str]]:
    sub_action = None
    if job and job.sub_action:
        sub_action = job.sub_action

    if status == JobStatus.SUCCESS:
        multi_state_set = action.multi_state_on_success_set
        multi_state_unset = action.multi_state_on_success_unset
        state = action.state_on_success
        if not state:
            logger.warning('action "%s" success state is not set', action.name)
    elif status == JobStatus.FAILED:
        state = getattr_first("state_on_fail", sub_action, action)
        multi_state_set = getattr_first("multi_state_on_fail_set", sub_action, action)
        multi_state_unset = getattr_first("multi_state_on_fail_unset", sub_action, action)
        if not state:
            logger.warning('action "%s" fail state is not set', action.name)
    else:
        if status != JobStatus.ABORTED:
            logger.error("unknown task status: %s", status)
        state = None
        multi_state_set = []
        multi_state_unset = []

    return state, multi_state_set, multi_state_unset


def set_action_state(
    action: Action,
    task: TaskLog,
    obj: ADCMEntity,
    state: str = None,
    multi_state_set: list[str] = None,
    multi_state_unset: list[str] = None,
):
    if not obj:
        logger.warning("empty object for action %s of task #%s", action.name, task.pk)

        return

    logger.info(
        'action "%s" of task #%s will set %s state to "%s" '
        'add to multi_states "%s" and remove from multi_states "%s"',
        action.name,
        task.pk,
        obj,
        state,
        multi_state_set,
        multi_state_unset,
    )

    if state:
        obj.set_state(state)
        if hasattr(action, "upgrade"):
            send_prototype_and_state_update_event(object_=obj)
        else:
            send_object_update_event(object_=obj, changes={"state": state})

    for m_state in multi_state_set or []:
        obj.set_multi_state(m_state)

    for m_state in multi_state_unset or []:
        obj.unset_multi_state(m_state)


def restore_hc(task: TaskLog, action: Action, status: str):
    if any(
        (status not in {JobStatus.FAILED, JobStatus.ABORTED}, not action.hostcomponentmap, not task.restore_hc_on_fail)
    ):
        return

    cluster = get_object_cluster(task.task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task.pk)

        return

    host_comp_list = []
    for hostcomponent in task.hostcomponentmap:
        host = Host.objects.get(id=hostcomponent["host_id"])
        service = ClusterObject.objects.get(id=hostcomponent["service_id"], cluster=cluster)
        comp = ServiceComponent.objects.get(id=hostcomponent["component_id"], cluster=cluster, service=service)
        host_comp_list.append((service, host, comp))

    logger.warning("task #%s is failed, restore old hc", task.pk)
    save_hc(cluster, host_comp_list)


def audit_task(
    action: Action, object_: Cluster | ClusterObject | ServiceComponent | HostProvider | Host, status: str
) -> None:
    upgrade = Upgrade.objects.filter(action=action).first()

    if upgrade:
        operation_name = f"{action.display_name} upgrade completed"
    else:
        operation_name = f"{action.display_name} action completed"

    obj_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP.get(object_.__class__)

    if not obj_type:
        return

    audit_object = get_or_create_audit_obj(
        object_id=object_.pk,
        object_name=object_.name,
        object_type=obj_type,
    )
    operation_result = AuditLogOperationResult.SUCCESS if status == "success" else AuditLogOperationResult.FAIL

    audit_log = AuditLog.objects.create(
        audit_object=audit_object,
        operation_name=operation_name,
        operation_type=AuditLogOperationType.UPDATE,
        operation_result=operation_result,
        object_changes={},
    )
    cef_logger(audit_instance=audit_log, signature_id="Action completion")


def finish_task(task: TaskLog, job: JobLog | None, status: str) -> None:
    action = task.action
    obj = task.task_object

    state, multi_state_set, multi_state_unset = get_state(action=action, job=job, status=status)

    set_action_state(
        action=action,
        task=task,
        obj=obj,
        state=state,
        multi_state_set=multi_state_set,
        multi_state_unset=multi_state_unset,
    )
    restore_hc(task=task, action=action, status=status)
    unlock_affected_objects(task=task)

    if obj is not None:
        update_hierarchy_issues(obj=obj)

        if (
            action.name in {settings.ADCM_TURN_ON_MM_ACTION_NAME, settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME}
            and obj.maintenance_mode == MaintenanceMode.CHANGING
        ):
            obj.maintenance_mode = MaintenanceMode.OFF
            obj.save()

        if (
            action.name in {settings.ADCM_TURN_OFF_MM_ACTION_NAME, settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME}
            and obj.maintenance_mode == MaintenanceMode.CHANGING
        ):
            obj.maintenance_mode = MaintenanceMode.ON
            obj.save()

        audit_task(action=action, object_=obj, status=status)

    set_task_final_status(task=task, status=status)

    send_task_status_update_event(object_=task, status=status)

    try:
        reset_objects_in_mm()
    except Exception as error:  # noqa: BLE001
        logger.warning("Error loading mm objects on task finish")
        logger.exception(error)


def run_task(task: TaskLog, args: str = ""):
    err_file = open(  # noqa: SIM115
        Path(settings.LOG_DIR, "task_runner.err"),
        "a+",
        encoding=settings.ENCODING_UTF_8,
    )
    cmd = [
        str(Path(settings.CODE_DIR, "task_runner.py")),
        str(task.pk),
        args,
    ]
    logger.info("task run cmd: %s", " ".join(cmd))
    proc = subprocess.Popen(  # noqa: SIM115
        args=cmd, stderr=err_file, env=get_env_with_venv_path(venv=task.action.venv)
    )
    logger.info("task run #%s, python process %s", task.pk, proc.pid)

    tree = Tree(obj=task.task_object)
    affected_objs = (node.value for node in tree.get_all_affected(node=tree.built_from))
    lock_affected_objects(task=task, objects=affected_objs)


def prepare_ansible_config(job_id: int, action: Action, sub_action: SubAction):
    config_parser = ConfigParser()
    config_parser["defaults"] = {
        "stdout_callback": "yaml",
        "callback_whitelist": "profile_tasks",
    }
    adcm_object = ADCM.objects.first()
    config_log = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    adcm_conf = config_log.config

    forks = adcm_conf["ansible_settings"]["forks"]
    config_parser["defaults"]["forks"] = str(forks)
    params = action.params

    if sub_action:
        params = sub_action.params

    if "jinja2_native" in params:
        config_parser["defaults"]["jinja2_native"] = str(params["jinja2_native"])

    with Path(settings.RUN_DIR, f"{job_id}", "ansible.cfg").open(
        mode="w", encoding=settings.ENCODING_UTF_8
    ) as config_file:
        config_parser.write(config_file)


def set_task_final_status(task: TaskLog, status: str):
    task.status = status
    task.finish_date = timezone.now()
    task.save(update_fields=["status", "finish_date"])


def set_job_start_status(job_id: int, pid: int) -> None:
    job = JobLog.objects.get(id=job_id)
    job.status = JobStatus.RUNNING
    job.start_date = timezone.now()
    job.pid = pid
    job.save(update_fields=["status", "start_date", "pid"])

    if job.task.lock and job.task.task_object:
        job.task.lock.reason = job.cook_reason()
        job.task.lock.save(update_fields=["reason"])


def set_job_final_status(job_id: int, status: str) -> None:
    JobLog.objects.filter(id=job_id).update(status=status, finish_date=timezone.now())


def abort_all():
    for task in TaskLog.objects.filter(status=JobStatus.RUNNING):
        set_task_final_status(task, JobStatus.ABORTED)
        unlock_affected_objects(task=task)

    for job in JobLog.objects.filter(status=JobStatus.RUNNING):
        set_job_final_status(job_id=job.pk, status=JobStatus.ABORTED)


def getattr_first(attr: str, *objects: Any, default: Any = None) -> Any:
    """Get first truthy attr from list of object or use last one or default if set"""
    result = None
    for obj in objects:
        result = getattr(obj, attr, None)
        if result:
            return result
    if default is not None:
        return default
    return result  # it could any falsy value from objects
