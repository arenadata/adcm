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

import copy
import json
import subprocess
from configparser import ConfigParser
from pathlib import Path
from typing import Any, Hashable, List, Optional, Tuple, Union

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from audit.cases.common import get_or_create_audit_obj
from audit.cef_logger import cef_logger
from audit.models import (
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
)
from cm.adcm_config import (
    check_attr,
    check_config_spec,
    get_prototype_config,
    process_file_type,
)
from cm.api import (
    check_hc,
    check_maintenance_mode,
    check_sub_key,
    get_hc,
    load_mm_objects,
    make_host_comp_list,
    save_hc,
)
from cm.api_context import ctx
from cm.errors import AdcmEx, raise_adcm_ex
from cm.hierarchy import Tree
from cm.inventory import get_obj_config, prepare_job_inventory, process_config_and_attr
from cm.issue import (
    check_bound_components,
    check_component_constraint,
    check_component_requires,
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
    DummyData,
    Host,
    HostComponent,
    HostProvider,
    JobLog,
    JobStatus,
    LogStorage,
    ObjectType,
    Prototype,
    ServiceComponent,
    SubAction,
    TaskLog,
    Upgrade,
    get_object_cluster,
)
from cm.status_api import post_event
from cm.variant import process_variant
from rbac.roles import re_apply_policy_for_jobs


def start_task(
    action: Action,
    obj: ADCMEntity,
    conf: dict,
    attr: dict,
    hc: List[HostComponent],
    hosts: List[Host],
    verbose: bool,
) -> TaskLog:
    if action.type not in ActionType.values:
        msg = f'unknown type "{action.type}" for action {action} on {obj}'
        raise_adcm_ex("WRONG_ACTION_TYPE", msg)

    task = prepare_task(action, obj, conf, attr, hc, hosts, verbose)
    ctx.event.send_state()
    run_task(task, ctx.event)
    ctx.event.send_state()

    return task


def check_action_hosts(action: Action, obj: ADCMEntity, cluster: Cluster, hosts: List[Host]):
    provider = None
    if obj.prototype.type == "provider":
        provider = obj

    if not hosts:
        return

    if not action.partial_execution:
        raise_adcm_ex("TASK_ERROR", "Only action with partial_execution permission can receive host list")

    if not isinstance(hosts, list):
        raise_adcm_ex("TASK_ERROR", "Hosts should be array")

    for host_id in hosts:
        if not isinstance(host_id, int):
            raise_adcm_ex("TASK_ERROR", f"host id should be integer ({host_id})")

        host = Host.obj.get(id=host_id)
        if cluster and host.cluster != cluster:
            raise_adcm_ex("TASK_ERROR", f"host #{host_id} does not belong to cluster #{cluster.pk}")

        if provider and host.provider != provider:
            raise_adcm_ex("TASK_ERROR", f"host #{host_id} does not belong to host provider #{provider.pk}")


def prepare_task(
    action: Action,
    obj: ADCMEntity,
    conf: dict,
    attr: dict,
    hc: List[HostComponent],
    hosts: List[Host],
    verbose: bool,
) -> TaskLog:  # pylint: disable=too-many-locals
    cluster = get_object_cluster(obj)
    check_action_state(action, obj, cluster)
    _, spec = check_action_config(action, obj, conf, attr)
    if conf and not spec:
        raise_adcm_ex("CONFIG_VALUE_ERROR", "Absent config in action prototype")

    check_action_hosts(action, obj, cluster, hosts)
    old_hc = get_hc(cluster)
    host_map, post_upgrade_hc = check_hostcomponentmap(cluster, action, hc)

    if hasattr(action, "upgrade") and not action.hostcomponentmap:
        check_constraints_for_upgrade(cluster, action.upgrade, get_actual_hc(cluster))

    if not attr:
        attr = {}

    with transaction.atomic():  # pylint: disable=too-many-locals
        DummyData.objects.filter(id=1).update(date=timezone.now())

        task = create_task(action, obj, conf, attr, old_hc, hosts, verbose, post_upgrade_hc)
        if host_map or (hasattr(action, "upgrade") and host_map is not None):
            save_hc(cluster, host_map)

        if conf:
            new_conf = process_config_and_attr(task, conf, attr, spec)
            process_file_type(task, spec, conf)
            task.config = new_conf
            task.save()

    re_apply_policy_for_jobs(obj, task)

    return task


def restart_task(task: TaskLog):
    if task.status in (JobStatus.CREATED, JobStatus.RUNNING):
        raise_adcm_ex("TASK_ERROR", f"task #{task.pk} is running")
    elif task.status == JobStatus.SUCCESS:
        run_task(task, ctx.event)
        ctx.event.send_state()
    elif task.status in (JobStatus.FAILED, JobStatus.ABORTED):
        run_task(task, ctx.event, "restart")
        ctx.event.send_state()
    else:
        raise_adcm_ex("TASK_ERROR", f"task #{task.pk} has unexpected status: {task.status}")


def cancel_task(task: TaskLog):
    task.cancel(ctx.event)


def get_host_object(action: Action, cluster: Cluster) -> Optional[ADCMEntity]:
    obj = None
    if action.prototype.type == "service":
        obj = ClusterObject.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "component":
        obj = ServiceComponent.obj.get(cluster=cluster, prototype=action.prototype)
    elif action.prototype.type == "cluster":
        obj = cluster

    return obj


def check_action_state(action: Action, task_object: ADCMEntity, cluster: Cluster):
    if action.host_action:
        obj = get_host_object(action, cluster)
    else:
        obj = task_object

    if obj.concerns.filter(type=ConcernType.Lock).exists():
        raise_adcm_ex("LOCK_ERROR", f"object {obj} is locked")

    if (
        action.name not in settings.ADCM_SERVICE_ACTION_NAMES_SET
        and obj.concerns.filter(type=ConcernType.Issue).exists()
    ):
        raise_adcm_ex("ISSUE_INTEGRITY_ERROR", f"object {obj} has issues")

    if action.allowed(obj):
        return

    raise_adcm_ex("TASK_ERROR", "action is disabled")


def check_action_config(action: Action, obj: ADCMEntity, conf: dict, attr: dict) -> Tuple[dict, dict]:
    proto = action.prototype
    spec, flat_spec, _, _ = get_prototype_config(proto, action)
    if not spec:
        return {}, {}

    if not conf:
        raise_adcm_ex("TASK_ERROR", "action config is required")

    check_attr(proto, action, attr, flat_spec)
    process_variant(obj, spec, conf)
    new_conf = check_config_spec(proto, action, spec, flat_spec, conf, None, attr)

    return new_conf, spec


def add_to_dict(my_dict: dict, key: Hashable, subkey: Hashable, value: Any):
    if key not in my_dict:
        my_dict[key] = {}

    my_dict[key][subkey] = value


def check_action_hc(action_hc: List[dict], service: ClusterObject, component: ServiceComponent, action: Action) -> bool:
    for item in action_hc:
        if item["service"] == service and item["component"] == component:
            if item["action"] == action:
                return True

    return False


def cook_comp_key(name, subname):
    return f"{name}.{subname}"


def cook_delta(  # pylint: disable=too-many-branches
    cluster: Cluster,
    new_hc: List[Tuple[ClusterObject, Host, ServiceComponent]],
    action_hc: List[dict],
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
        for hc in HostComponent.objects.filter(cluster=cluster):
            key = cook_comp_key(hc.service.prototype.name, hc.component.prototype.name)
            add_to_dict(old, key, hc.host.fqdn, hc.host)

    delta = {"add": {}, "remove": {}}
    for key, value in new.items():
        if key in old:
            for host in value:
                if host not in old[key]:
                    add_delta(delta, "add", key, host, value[host])

            for host in old[key]:
                if host not in value:
                    add_delta(delta, "remove", key, host, old[key][host])
        else:
            for host in value:
                add_delta(delta, "add", key, host, value[host])

    for key, value in old.items():
        if key not in new:
            for host in value:
                add_delta(delta, "remove", key, host, value[host])

    logger.debug("OLD: %s", old)
    logger.debug("NEW: %s", new)
    logger.debug("DELTA: %s", delta)

    return delta


def check_hostcomponentmap(cluster: Cluster, action: Action, new_hc: List[dict]):
    if not action.hostcomponentmap:
        return None, []

    if not new_hc:
        raise_adcm_ex("TASK_ERROR", "hc is required")

    if not cluster:
        raise_adcm_ex("TASK_ERROR", "Only cluster objects can have action with hostcomponentmap")

    for host_comp in new_hc:
        if not hasattr(action, "upgrade"):
            host = Host.obj.get(id=host_comp.get("host_id", 0))
            if host.concerns.filter(type=ConcernType.Lock).exists():
                raise_adcm_ex("LOCK_ERROR", f"object {host} is locked")

            if host.concerns.filter(type=ConcernType.Issue).exists():
                raise_adcm_ex("ISSUE_INTEGRITY_ERROR", f"object {host} has issues")

    post_upgrade_hc, clear_hc = check_upgrade_hc(action, new_hc)

    old_hc = get_old_hc(get_hc(cluster))
    if not hasattr(action, "upgrade"):
        prepared_hc_list = check_hc(cluster, clear_hc)
    else:
        check_sub_key(clear_hc)
        prepared_hc_list = make_host_comp_list(cluster, clear_hc)
        check_constraints_for_upgrade(cluster, action.upgrade, prepared_hc_list)

    cook_delta(cluster, prepared_hc_list, action.hostcomponentmap, old_hc)

    return prepared_hc_list, post_upgrade_hc


def check_constraints_for_upgrade(cluster, upgrade, host_comp_list):
    try:
        for service in ClusterObject.objects.filter(cluster=cluster):
            try:
                prototype = Prototype.objects.get(name=service.name, type="service", bundle=upgrade.bundle)
                check_component_constraint(
                    cluster,
                    prototype,
                    [i for i in host_comp_list if i[0] == service],
                    cluster.prototype.bundle,
                )
            except Prototype.DoesNotExist:
                pass

        check_component_requires(host_comp_list)
        check_bound_components(host_comp_list)
        check_maintenance_mode(cluster, host_comp_list)
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
                    if hc_acl["action"] != "add":
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
        service = ClusterObject.objects.get(cluster=cluster, prototype=action.prototype)
        return service
    except ClusterObject.DoesNotExist:
        msg = f"service #{action.prototype.pk} for action " f'"{action.name}" is not installed in cluster #{cluster.pk}'
        raise_adcm_ex("CLUSTER_SERVICE_NOT_FOUND", msg)

    return None


def check_component_task(cluster_id: int, action: Action) -> ServiceComponent | None:
    cluster = Cluster.obj.get(id=cluster_id)
    try:
        component = ServiceComponent.objects.get(cluster=cluster, prototype=action.prototype)

        return component
    except ServiceComponent.DoesNotExist:
        msg = (
            f"component #{action.prototype.pk} for action " f'"{action.name}" is not installed in cluster #{cluster.pk}'
        )
        raise_adcm_ex("COMPONENT_NOT_FOUND", msg)

    return None


def check_cluster(cluster_id: int) -> Cluster:
    return Cluster.obj.get(id=cluster_id)


def check_provider(provider_id: int) -> HostProvider:
    return HostProvider.obj.get(id=provider_id)


def check_adcm(adcm_id: int) -> ADCM:
    return ADCM.obj.get(id=adcm_id)


def get_bundle_root(action: Action) -> str:
    if action.prototype.type == "adcm":
        return str(Path(settings.BASE_DIR, "conf"))

    return str(settings.BUNDLE_DIR)


def cook_script(action: Action, sub_action: SubAction):
    prefix = action.prototype.bundle.hash
    script = action.script

    if sub_action:
        script = sub_action.script

    if script[0:2] == "./":
        script = Path(action.prototype.path, script[2:])

    return str(Path(get_bundle_root(action), prefix, script))


def get_adcm_config():
    return get_obj_config(ADCM.obj.get())


def get_actual_hc(cluster: Cluster):
    new_hc = []
    for hc in HostComponent.objects.filter(cluster=cluster):
        new_hc.append((hc.service, hc.host, hc.component))
    return new_hc


def get_old_hc(saved_hc: List[dict]):
    if not saved_hc:
        return {}

    old_hc = {}
    for hc in saved_hc:
        service = ClusterObject.objects.get(id=hc["service_id"])
        comp = ServiceComponent.objects.get(id=hc["component_id"])
        host = Host.objects.get(id=hc["host_id"])
        key = cook_comp_key(service.prototype.name, comp.prototype.name)
        add_to_dict(old_hc, key, host.fqdn, host)

    return old_hc


def re_prepare_job(task: TaskLog, job: JobLog):
    conf = None
    hosts = None
    delta = {}
    if task.config:
        conf = task.config

    if task.hosts:
        hosts = task.hosts

    action = task.action
    obj = task.task_object
    cluster = get_object_cluster(obj)
    sub_action = None
    if job.sub_action_id:
        sub_action = job.sub_action

    if action.hostcomponentmap:
        new_hc = get_actual_hc(cluster)
        old_hc = get_old_hc(task.hostcomponentmap)
        delta = cook_delta(cluster, new_hc, action.hostcomponentmap, old_hc)

    prepare_job(action, sub_action, job.pk, obj, conf, delta, hosts, task.verbose)


def prepare_job(
    action: Action,
    sub_action: SubAction,
    job_id: int,
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    conf: dict,
    delta: dict,
    hosts: List[Host],
    verbose: bool,
):
    prepare_job_config(action, sub_action, job_id, obj, conf, verbose)
    prepare_job_inventory(obj, job_id, action, delta, hosts)
    prepare_ansible_config(job_id, action, sub_action)


def get_selector(obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host, action: Action) -> dict:
    selector = {obj.prototype.type: {"id": obj.pk, "name": obj.display_name}}

    if obj.prototype.type == ObjectType.Service:
        selector[ObjectType.Cluster] = {"id": obj.cluster.pk, "name": obj.cluster.display_name}
    elif obj.prototype.type == ObjectType.Component:
        selector[ObjectType.Service] = {"id": obj.service.pk, "name": obj.service.display_name}
        selector[ObjectType.Cluster] = {"id": obj.cluster.pk, "name": obj.cluster.display_name}
    elif obj.prototype.type == ObjectType.Host:
        if action.host_action:
            cluster = obj.cluster
            selector[ObjectType.Cluster] = {"id": cluster.pk, "name": cluster.display_name}
            if action.prototype.type == ObjectType.Service:
                service = ClusterObject.objects.get(prototype=action.prototype, cluster=cluster)
                selector[ObjectType.Service] = {"id": service.pk, "name": service.display_name}
            elif action.prototype.type == ObjectType.Component:
                service = ClusterObject.objects.get(prototype=action.prototype.parent, cluster=cluster)
                selector[ObjectType.Service] = {"id": service.pk, "name": service.display_name}
                component = ServiceComponent.objects.get(prototype=action.prototype, cluster=cluster, service=service)
                selector[ObjectType.Component] = {
                    "id": component.pk,
                    "name": component.display_name,
                }
        else:
            selector[ObjectType.Provider] = {
                "id": obj.provider.pk,
                "name": obj.provider.display_name,
            }

    return selector


def prepare_context(
    action: Action, obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host
) -> dict:

    selector = get_selector(obj, action)
    context = {f"{k}_id": v["id"] for k, v in selector.items()}
    context["type"] = obj.prototype.type

    if obj.prototype.type == ObjectType.Host and action.host_action:
        context["type"] = action.prototype.type

    return context


def prepare_job_config(
    action: Action,
    sub_action: SubAction,
    job_id: int,
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    conf: dict,
    verbose: bool,
):
    # pylint: disable=too-many-branches,too-many-statements

    job_conf = {
        "adcm": {"config": get_adcm_config()},
        "context": prepare_context(action, obj),
        "env": {
            "run_dir": str(settings.RUN_DIR),
            "log_dir": str(settings.LOG_DIR),
            "tmp_dir": str(Path(settings.RUN_DIR, f"{job_id}", "tmp")),
            "stack_dir": str(Path(get_bundle_root(action), action.prototype.bundle.hash)),
            "status_api_token": str(settings.STATUS_SECRET_KEY),
        },
        "job": {
            "id": job_id,
            "action": action.name,
            "job_name": action.name,
            "command": action.name,
            "script": action.script,
            "verbose": verbose,
            "playbook": cook_script(action, sub_action),
        },
    }

    if action.params:
        job_conf["job"]["params"] = action.params

    if sub_action:
        job_conf["job"]["script"] = sub_action.script
        job_conf["job"]["job_name"] = sub_action.name
        job_conf["job"]["command"] = sub_action.name
        if sub_action.params:
            job_conf["job"]["params"] = sub_action.params

    cluster = get_object_cluster(obj)
    if cluster:
        job_conf["job"]["cluster_id"] = cluster.pk

    if action.prototype.type == "service":
        if action.host_action:
            service = ClusterObject.obj.get(prototype=action.prototype, cluster=cluster)
            job_conf["job"]["hostgroup"] = service.name
            job_conf["job"]["service_id"] = service.pk
            job_conf["job"]["service_type_id"] = service.prototype.pk
        else:
            job_conf["job"]["hostgroup"] = obj.prototype.name
            job_conf["job"]["service_id"] = obj.pk
            job_conf["job"]["service_type_id"] = obj.prototype.pk
    elif action.prototype.type == "component":
        if action.host_action:
            service = ClusterObject.obj.get(prototype=action.prototype.parent, cluster=cluster)
            comp = ServiceComponent.obj.get(prototype=action.prototype, cluster=cluster, service=service)
            job_conf["job"]["hostgroup"] = f"{service.name}.{comp.name}"
            job_conf["job"]["service_id"] = service.pk
            job_conf["job"]["component_id"] = comp.pk
            job_conf["job"]["component_type_id"] = comp.prototype.pk
        else:
            job_conf["job"]["hostgroup"] = f"{obj.service.prototype.name}.{obj.prototype.name}"
            job_conf["job"]["service_id"] = obj.service.pk
            job_conf["job"]["component_id"] = obj.pk
            job_conf["job"]["component_type_id"] = obj.prototype.pk
    elif action.prototype.type == "cluster":
        job_conf["job"]["hostgroup"] = "CLUSTER"
    elif action.prototype.type == "host":
        job_conf["job"]["hostgroup"] = "HOST"
        job_conf["job"]["hostname"] = obj.fqdn
        job_conf["job"]["host_id"] = obj.pk
        job_conf["job"]["host_type_id"] = obj.prototype.pk
        job_conf["job"]["provider_id"] = obj.provider.pk
    elif action.prototype.type == "provider":
        job_conf["job"]["hostgroup"] = "PROVIDER"
        job_conf["job"]["provider_id"] = obj.pk
    elif action.prototype.type == "adcm":
        job_conf["job"]["hostgroup"] = "127.0.0.1"
    else:
        raise_adcm_ex("NOT_IMPLEMENTED", f'unknown prototype type "{action.prototype.type}"')

    if conf:
        job_conf["job"]["config"] = conf

    fd = open(Path(settings.RUN_DIR, f"{job_id}", "config.json"), "w", encoding=settings.ENCODING_UTF_8)
    json.dump(job_conf, fd, indent=3, sort_keys=True)
    fd.close()


def create_task(
    action: Action,
    obj: ADCM | Cluster | ClusterObject | ServiceComponent | HostProvider | Host,
    conf: dict,
    attr: dict,
    hc: List[HostComponent],
    hosts: List[Host],
    verbose: bool,
    post_upgrade_hc: List[dict],
) -> TaskLog:
    task = TaskLog.objects.create(
        action=action,
        task_object=obj,
        config=conf,
        attr=attr,
        hostcomponentmap=hc,
        hosts=hosts,
        post_upgrade_hc_map=post_upgrade_hc,
        verbose=verbose,
        start_date=timezone.now(),
        finish_date=timezone.now(),
        status=JobStatus.CREATED,
        selector=get_selector(obj, action),
    )
    set_task_status(task, JobStatus.CREATED, ctx.event)

    if action.type == ActionType.Job.value:
        sub_actions = [None]
    else:
        sub_actions = SubAction.objects.filter(action=action).all()

    for sub_action in sub_actions:
        job = JobLog.obj.create(
            task=task,
            action=action,
            sub_action=sub_action,
            log_files=action.log_files,
            start_date=timezone.now(),
            finish_date=timezone.now(),
            status=JobStatus.CREATED,
            selector=get_selector(obj, action),
        )
        log_type = sub_action.script_type if sub_action else action.script_type
        LogStorage.objects.create(job=job, name=log_type, type="stdout", format="txt")
        LogStorage.objects.create(job=job, name=log_type, type="stderr", format="txt")
        set_job_status(job.pk, JobStatus.CREATED, ctx.event)
        Path(settings.RUN_DIR, f"{job.pk}", "tmp").mkdir(parents=True, exist_ok=True)

    tree = Tree(obj)
    affected = (node.value for node in tree.get_all_affected(tree.built_from))
    task.lock_affected(affected)

    return task


def get_state(action: Action, job: JobLog, status: str) -> Tuple[Optional[str], List[str], List[str]]:
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
    multi_state_set: List[str] = None,
    multi_state_unset: List[str] = None,
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
        obj.set_state(state, ctx.event)

    for m_state in multi_state_set or []:
        obj.set_multi_state(m_state, ctx.event)

    for m_state in multi_state_unset or []:
        obj.unset_multi_state(m_state, ctx.event)


def restore_hc(task: TaskLog, action: Action, status: str):
    if status not in {JobStatus.FAILED, JobStatus.ABORTED}:
        return

    if not action.hostcomponentmap:
        return

    cluster = get_object_cluster(task.task_object)
    if cluster is None:
        logger.error("no cluster in task #%s", task.pk)

        return

    host_comp_list = []
    for hc in task.hostcomponentmap:
        host = Host.objects.get(id=hc["host_id"])
        service = ClusterObject.objects.get(id=hc["service_id"], cluster=cluster)
        comp = ServiceComponent.objects.get(id=hc["component_id"], cluster=cluster, service=service)
        host_comp_list.append((service, host, comp))

    logger.warning("task #%s is failed, restore old hc", task.pk)
    save_hc(cluster, host_comp_list)


def set_before_upgrade_state(action: Action, obj: Union[Cluster, HostProvider]) -> None:
    if action.upgrade is not None:
        obj.before_upgrade["state"] = obj.state
        obj.save()


def finish_task(task: TaskLog, job: Optional[JobLog], status: str):
    action = task.action
    obj = task.task_object
    state, multi_state_set, multi_state_unset = get_state(action, job, status)

    with transaction.atomic():
        DummyData.objects.filter(id=1).update(date=timezone.now())
        if hasattr(action, "upgrade"):
            set_before_upgrade_state(action, obj)

        set_action_state(action, task, obj, state, multi_state_set, multi_state_unset)
        restore_hc(task, action, status)
        task.unlock_affected()
        set_task_status(task, status, ctx.event)
        update_hierarchy_issues(obj)

    upgrade = Upgrade.objects.filter(action=action).first()
    if upgrade:
        operation_name = f"{action.display_name} upgrade completed"
    else:
        operation_name = f"{action.display_name} action completed"

    obj_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP.get(obj.__class__)
    if not obj_type:
        return

    audit_object = get_or_create_audit_obj(
        object_id=obj.pk,
        object_name=obj.name,
        object_type=obj_type,
    )
    if status == "success":
        operation_result = AuditLogOperationResult.Success
    else:
        operation_result = AuditLogOperationResult.Fail

    audit_log = AuditLog.objects.create(
        audit_object=audit_object,
        operation_name=operation_name,
        operation_type=AuditLogOperationType.Update,
        operation_result=operation_result,
        object_changes={},
    )
    cef_logger(audit_instance=audit_log, signature_id="Action completion")

    ctx.event.send_state()
    try:
        load_mm_objects()
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("Error loading mm objects on task finish")
        logger.exception(e)


def cook_log_name(tag, level, ext="txt"):
    return f"{tag}-{level}.{ext}"


def log_custom(job_id, name, log_format, body):
    job = JobLog.obj.get(id=job_id)
    l1 = LogStorage.objects.create(job=job, name=name, type="custom", format=log_format, body=body)
    post_event(
        "add_job_log",
        "job",
        job_id,
        {
            "id": l1.pk,
            "type": l1.type,
            "name": l1.name,
            "format": l1.format,
        },
    )


def run_task(task: TaskLog, event, args: str = ""):
    err_file = open(Path(settings.LOG_DIR, "task_runner.err"), "a+", encoding=settings.ENCODING_UTF_8)
    cmd = [
        "/adcm/python/job_venv_wrapper.sh",
        task.action.venv,
        str(Path(settings.CODE_DIR, "task_runner.py")),
        str(task.pk),
        args,
    ]
    logger.info("task run cmd: %s", " ".join(cmd))
    proc = subprocess.Popen(
        cmd,
        stderr=err_file,
    )
    logger.info("task run #%s, python process %s", task.pk, proc.pid)

    set_task_status(task, JobStatus.RUNNING, event)


def prepare_ansible_config(job_id: int, action: Action, sub_action: SubAction):
    config_parser = ConfigParser()
    config_parser["defaults"] = {
        "stdout_callback": "yaml",
        "callback_whitelist": "profile_tasks",
    }
    adcm_object = ADCM.objects.get(id=1)
    cl = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    adcm_conf = cl.config
    mitogen = adcm_conf["ansible_settings"]["mitogen"]

    if mitogen:
        config_parser["defaults"]["strategy"] = "mitogen_linear"
        config_parser["defaults"]["strategy_plugins"] = str(
            Path(settings.PYTHON_SITE_PACKAGES, "ansible_mitogen", "plugins", "strategy")
        )
        config_parser["defaults"]["host_key_checking"] = "False"

    forks = adcm_conf["ansible_settings"]["forks"]
    config_parser["defaults"]["forks"] = str(forks)
    params = action.params

    if sub_action:
        params = sub_action.params

    if "jinja2_native" in params:
        config_parser["defaults"]["jinja2_native"] = str(params["jinja2_native"])

    with open(Path(settings.RUN_DIR, f"{job_id}", "ansible.cfg"), "w", encoding=settings.ENCODING_UTF_8) as config_file:
        config_parser.write(config_file)


def set_task_status(task: TaskLog, status: str, event):
    task.status = status
    task.finish_date = timezone.now()
    task.save()
    event.set_task_status(task.pk, status)


def set_job_status(job_id: int, status: str, event, pid: int = 0):
    JobLog.objects.filter(id=job_id).update(status=status, pid=pid, finish_date=timezone.now())
    event.set_job_status(job_id, status)


def abort_all(event):
    for task in TaskLog.objects.filter(status=JobStatus.RUNNING):
        set_task_status(task, JobStatus.ABORTED, event)
        task.unlock_affected()
    for job in JobLog.objects.filter(status=JobStatus.RUNNING):
        set_job_status(job.pk, JobStatus.ABORTED, event)
    ctx.event.send_state()


def getattr_first(attr: str, *objects: Any, default: Any = None) -> Any:
    """Get first truthy attr from list of object or use last one or default if set"""
    result = None
    for obj in objects:
        result = getattr(obj, attr, None)
        if result:
            return result
    if default is not None:
        return default
    else:
        return result  # it could any falsy value from objects
