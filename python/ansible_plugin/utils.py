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
from copy import deepcopy
from typing import Any, NamedTuple
import json
import fcntl

# isort: off
from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.vars import merge_hash
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from ansible_plugin.messages import (
    MSG_NO_CONFIG,
    MSG_NO_CONTEXT,
    MSG_WRONG_CONTEXT,
    MSG_WRONG_CONTEXT_ID,
    MSG_NO_CLUSTER_CONTEXT,
    MSG_MANDATORY_ARGS,
    MSG_NO_ROUTE,
    MSG_NO_SERVICE_NAME,
    MSG_NO_MULTI_STATE_TO_DELETE,
)
from cm.adcm_config.ansible import ansible_decrypt
from cm.adcm_config.config import get_option_value
from cm.api import add_hc, get_hc, set_object_config_with_plugin
from cm.errors import AdcmEx
from cm.models import (
    Action,
    ADCMEntity,
    CheckLog,
    Cluster,
    ClusterObject,
    ConfigLog,
    GroupCheckLog,
    Host,
    HostProvider,
    JobLog,
    JobStatus,
    LogStorage,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
    get_model_by_type,
)
from cm.status_api import send_object_update_event, send_config_creation_event
from rbac.models import Role, Policy
from rbac.roles import assign_group_perm
# isort: on


def job_lock(job_id):
    file_descriptor = open(  # noqa: SIM115
        settings.RUN_DIR / f"{job_id}/config.json",
        encoding=settings.ENCODING_UTF_8,
    )
    try:
        fcntl.flock(file_descriptor.fileno(), fcntl.LOCK_EX)

        return file_descriptor
    except OSError as e:
        raise AdcmEx("LOCK_ERROR", e) from e


def check_context_type(task_vars: dict, context_types: tuple, err_msg: str | None = None) -> None:
    """
    Check context type. Check if inventory.json and config.json were passed
    and check if `context` exists in task variables, сheck if a context is of a given type.
    """
    if not task_vars:
        raise AnsibleError(MSG_NO_CONFIG)

    if "context" not in task_vars:
        raise AnsibleError(MSG_NO_CONTEXT)

    if not isinstance(task_vars["context"], dict):
        raise AnsibleError(MSG_NO_CONTEXT)

    context = task_vars["context"]
    if context["type"] not in context_types:
        if err_msg is None:
            err_msg = MSG_WRONG_CONTEXT.format(", ".join(context_types), context["type"])
        raise AnsibleError(err_msg)


def get_object_id_from_context(
    task_vars: dict, id_type: str, context_types: tuple, err_msg: str | None = None, raise_: bool = True
) -> tuple[int | None, None | AnsibleError]:
    """
    Get object id from context.
    """
    check_context_type(task_vars=task_vars, context_types=context_types, err_msg=err_msg)
    context = task_vars["context"]

    if id_type not in context:
        error = AnsibleError(MSG_WRONG_CONTEXT_ID.format(id_type))
        if raise_:
            raise error

        return None, error

    return context[id_type], None


def get_context_object(task_vars: dict, err_msg: str = None) -> ADCMEntity:
    obj_type = task_vars["context"]["type"]

    obj_pk, _ = get_object_id_from_context(
        task_vars=task_vars, id_type=f"{obj_type}_id", context_types=(obj_type,), err_msg=err_msg
    )
    obj = get_model_by_type(object_type=obj_type).objects.filter(pk=obj_pk).first()

    if not obj:
        raise AnsibleError(f'Object of type "{obj_type}" with PK "{obj_pk}" does not exist')

    return obj


class ContextActionModule(ActionBase):
    TRANSFERS_FILES = False
    _VALID_ARGS = None
    _MANDATORY_ARGS = None

    def _wrap_call(self, func, *args):
        try:
            res = func(*args)
        except AdcmEx as e:
            return {"failed": True, "msg": e.msg}
        if isinstance(res, PluginResult):
            return {"changed": res.changed}
        return {"changed": True}

    def _check_mandatory(self):
        for arg in self._MANDATORY_ARGS:
            if arg not in self._task.args:
                raise AnsibleError(MSG_MANDATORY_ARGS.format(self._MANDATORY_ARGS))

    def _get_job_var(self, task_vars, name):
        try:
            return task_vars["job"][name]
        except KeyError as error:
            raise AnsibleError(MSG_NO_CLUSTER_CONTEXT) from error

    def _do_cluster(self, task_vars, context):
        raise NotImplementedError

    def _do_service_by_name(self, task_vars, context):
        raise NotImplementedError

    def _do_service(self, task_vars, context):
        raise NotImplementedError

    def _do_host(self, task_vars, context):
        raise NotImplementedError

    def _do_component(self, task_vars, context):
        raise NotImplementedError

    def _do_component_by_name(self, task_vars, context):
        raise NotImplementedError

    def _do_provider(self, task_vars, context):
        raise NotImplementedError

    def _do_host_from_provider(self, task_vars, context):
        raise NotImplementedError

    def run(self, tmp=None, task_vars=None):
        self._check_mandatory()
        obj_type = self._task.args["type"]
        job_id = task_vars["job"]["id"]
        file_descriptor = job_lock(job_id)

        if obj_type == "cluster":
            check_context_type(task_vars=task_vars, context_types=("cluster", "service", "component"))
            res = self._do_cluster(task_vars, {"cluster_id": self._get_job_var(task_vars, "cluster_id")})
        elif obj_type == "service" and "service_name" in self._task.args:
            check_context_type(task_vars=task_vars, context_types=("cluster", "service", "component"))
            res = self._do_service_by_name(task_vars, {"cluster_id": self._get_job_var(task_vars, "cluster_id")})
        elif obj_type == "service":
            check_context_type(task_vars=task_vars, context_types=("service", "component"))
            res = self._do_service(
                task_vars,
                {
                    "cluster_id": self._get_job_var(task_vars, "cluster_id"),
                    "service_id": self._get_job_var(task_vars, "service_id"),
                },
            )
        elif obj_type == "host" and "host_id" in self._task.args:
            check_context_type(task_vars=task_vars, context_types=("provider",))
            res = self._do_host_from_provider(task_vars, {})
        elif obj_type == "host":
            check_context_type(task_vars=task_vars, context_types=("host",))
            res = self._do_host(task_vars, {"host_id": self._get_job_var(task_vars, "host_id")})
        elif obj_type == "provider":
            check_context_type(task_vars=task_vars, context_types=("provider", "host"))
            res = self._do_provider(task_vars, {"provider_id": self._get_job_var(task_vars, "provider_id")})
        elif obj_type == "component" and "component_name" in self._task.args:
            if "service_name" in self._task.args:
                check_context_type(task_vars=task_vars, context_types=("cluster", "service", "component"))
                res = self._do_component_by_name(
                    task_vars,
                    {
                        "cluster_id": self._get_job_var(task_vars, "cluster_id"),
                        "service_id": None,
                    },
                )
            else:
                check_context_type(task_vars=task_vars, context_types=("cluster", "service", "component"))
                if task_vars["job"].get("service_id", None) is None:
                    raise AnsibleError(MSG_NO_SERVICE_NAME)
                res = self._do_component_by_name(
                    task_vars,
                    {
                        "cluster_id": self._get_job_var(task_vars, "cluster_id"),
                        "service_id": self._get_job_var(task_vars, "service_id"),
                    },
                )
        elif obj_type == "component":
            check_context_type(task_vars=task_vars, context_types=("component",))
            res = self._do_component(task_vars, {"component_id": self._get_job_var(task_vars, "component_id")})
        else:
            raise AnsibleError(MSG_NO_ROUTE)

        result = super().run(tmp, task_vars)
        file_descriptor.close()

        return merge_hash(result, res)


# Helper functions for ansible plugins


def get_component_by_name(cluster_id, service_id, component_name, service_name):
    if service_id is not None:
        comp = ServiceComponent.obj.get(cluster_id=cluster_id, service_id=service_id, prototype__name=component_name)
    else:
        comp = ServiceComponent.obj.get(
            cluster_id=cluster_id,
            service__prototype__name=service_name,
            prototype__name=component_name,
        )
    return comp


def get_service_by_name(cluster_id, service_name):
    cluster = Cluster.obj.get(id=cluster_id)
    proto = Prototype.obj.get(type="service", name=service_name, bundle=cluster.prototype.bundle)
    return ClusterObject.obj.get(cluster=cluster, prototype=proto)


def _set_object_state(obj: ADCMEntity, state: str) -> ADCMEntity:
    obj.set_state(state)
    send_object_update_event(object_=obj, changes={"state": state})
    return obj


def set_cluster_state(cluster_id, state):
    obj = Cluster.obj.get(id=cluster_id)
    return _set_object_state(obj, state)


def set_host_state(host_id, state):
    obj = Host.obj.get(id=host_id)
    return _set_object_state(obj, state)


def set_component_state(component_id, state):
    obj = ServiceComponent.obj.get(id=component_id)
    return _set_object_state(obj, state)


def set_component_state_by_name(cluster_id, service_id, component_name, service_name, state):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _set_object_state(obj, state)


def set_provider_state(provider_id, state):
    obj = HostProvider.obj.get(id=provider_id)
    return _set_object_state(obj, state)


def set_service_state_by_name(cluster_id, service_name, state):
    obj = get_service_by_name(cluster_id, service_name)
    return _set_object_state(obj, state)


def set_service_state(cluster_id, service_id, state):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")
    return _set_object_state(obj, state)


def _set_object_multi_state(obj: ADCMEntity, multi_state: str) -> ADCMEntity:
    obj.set_multi_state(multi_state)
    return obj


def set_cluster_multi_state(cluster_id, multi_state):
    obj = Cluster.obj.get(id=cluster_id)
    return _set_object_multi_state(obj, multi_state)


def set_service_multi_state_by_name(cluster_id, service_name, multi_state):
    obj = get_service_by_name(cluster_id, service_name)
    return _set_object_multi_state(obj, multi_state)


def set_service_multi_state(cluster_id, service_id, multi_state):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")
    return _set_object_multi_state(obj, multi_state)


def set_component_multi_state_by_name(cluster_id, service_id, component_name, service_name, multi_state):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _set_object_multi_state(obj, multi_state)


def set_component_multi_state(component_id, multi_state):
    obj = ServiceComponent.obj.get(id=component_id)
    return _set_object_multi_state(obj, multi_state)


def set_provider_multi_state(provider_id, multi_state):
    obj = HostProvider.obj.get(id=provider_id)
    return _set_object_multi_state(obj, multi_state)


def set_host_multi_state(host_id, multi_state):
    obj = Host.obj.get(id=host_id)
    return _set_object_multi_state(obj, multi_state)


def change_hc(job_id, cluster_id, operations):
    """
    For use in ansible plugin adcm_hc
    """
    file_descriptor = job_lock(job_id)
    action_id = JobLog.objects.values_list("task__action_id", flat=True).get(id=job_id)
    action = Action.objects.get(id=action_id)
    if action.hostcomponentmap:
        raise AdcmEx("ACTION_ERROR", "You can not change hc in plugin for action with hc_acl")

    cluster = Cluster.obj.get(id=cluster_id)
    hostcomponent = get_hc(cluster)
    for operation in operations:
        service = ClusterObject.obj.get(cluster=cluster, prototype__name=operation["service"])
        component = ServiceComponent.obj.get(cluster=cluster, service=service, prototype__name=operation["component"])
        host = Host.obj.get(cluster=cluster, fqdn=operation["host"])
        item = {
            "host_id": host.id,
            "service_id": service.id,
            "component_id": component.id,
        }
        if operation["action"] == "add":
            if item not in hostcomponent:
                hostcomponent.append(item)
            else:
                msg = 'There is already component "{}" on host "{}"'
                raise AdcmEx("COMPONENT_CONFLICT", msg.format(component.prototype.name, host.fqdn))
        elif operation["action"] == "remove":
            if item in hostcomponent:
                hostcomponent.remove(item)
            else:
                msg = 'There is no component "{}" on host "{}"'
                raise AdcmEx("COMPONENT_CONFLICT", msg.format(component.prototype.name, host.fqdn))
        else:
            raise AdcmEx("INVALID_INPUT", f'unknown hc action "{operation["action"]}"')

    add_hc(cluster, hostcomponent)
    file_descriptor.close()


def cast_to_type(field_type: str, value: Any, limits: dict) -> Any:
    try:
        match field_type:
            case "float":
                return float(value)
            case "integer":
                return int(value)
            case "option":
                return get_option_value(value=value, limits=limits)
            case _:
                return value
    except ValueError as error:
        raise AnsibleError(f"Could not convert '{value}' to '{field_type}'") from error


class PluginResult(NamedTuple):
    value: dict | int | str
    changed: bool


def update_config(obj: ADCMEntity, conf: dict, attr: dict) -> PluginResult:
    config_log = ConfigLog.objects.get(id=obj.config.current)

    new_config = deepcopy(config_log.config)
    new_attr = deepcopy(config_log.attr) if config_log.attr is not None else {}

    for keys, value in conf.items():
        keys_list = keys.split("/")
        key = keys_list[0]
        subkey = None
        if len(keys_list) > 1:
            subkey = keys_list[1]

        if subkey:
            try:
                prototype_conf = PrototypeConfig.objects.get(
                    name=key, subname=subkey, prototype=obj.prototype, action=None
                )
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}/{subkey}' does not exist") from error
            new_config[key][subkey] = cast_to_type(
                field_type=prototype_conf.type, value=value, limits=prototype_conf.limits
            )
        else:
            try:
                prototype_conf = PrototypeConfig.objects.get(name=key, subname="", prototype=obj.prototype, action=None)
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}' does not exist") from error
            new_config[key] = cast_to_type(field_type=prototype_conf.type, value=value, limits=prototype_conf.limits)

        if key in attr:
            prototype_conf = PrototypeConfig.objects.filter(
                name=key, prototype=obj.prototype, type="group", action=None
            )

            if not prototype_conf or "activatable" not in prototype_conf.first().limits:
                raise AnsibleError("'active' key should be used only with activatable group")

            new_attr.update(attr)

    for key in attr:
        for subkey, value in config_log.config[key].items():
            if not new_config[key] or subkey not in new_config[key]:
                new_config[key][subkey] = value

    if _does_contain(base_dict=config_log.config, part=new_config) and _does_contain(
        base_dict=config_log.attr, part=new_attr
    ):
        return PluginResult(conf, False)

    set_object_config_with_plugin(obj=obj, config=new_config, attr=new_attr)
    send_config_creation_event(object_=obj)

    if len(conf) == 1:
        return PluginResult(list(conf.values())[0], True)

    return PluginResult(conf, True)


def set_cluster_config(cluster_id: int, config: dict, attr: dict) -> PluginResult:
    obj = Cluster.obj.get(id=cluster_id)

    return update_config(obj=obj, conf=config, attr=attr)


def set_host_config(host_id: int, config: dict, attr: dict) -> PluginResult:
    obj = Host.obj.get(id=host_id)

    return update_config(obj=obj, conf=config, attr=attr)


def set_provider_config(provider_id: int, config: dict, attr: dict) -> PluginResult:
    obj = HostProvider.obj.get(id=provider_id)

    return update_config(obj=obj, conf=config, attr=attr)


def set_service_config_by_name(cluster_id: int, service_name: str, config: dict, attr: dict) -> PluginResult:
    obj = get_service_by_name(cluster_id, service_name)

    return update_config(obj=obj, conf=config, attr=attr)


def set_service_config(cluster_id: int, service_id: int, config: dict, attr: dict) -> PluginResult:
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")

    return update_config(obj=obj, conf=config, attr=attr)


def _does_contain(base_dict: dict, part: dict) -> bool:
    """
    Check fields in `part` have the same value in `base_dict`
    """

    for key, val2 in part.items():
        if key not in base_dict:
            return False

        val1 = base_dict[key]

        if isinstance(val1, dict) and isinstance(val2, dict):
            if not _does_contain(val1, val2):
                return False
        else:
            val1 = ansible_decrypt(val1)
            val2 = ansible_decrypt(val2)
            if val1 != val2:
                return False

    return True


def set_component_config_by_name(
    cluster_id: int,
    service_id: int,
    component_name: str,
    service_name: str,
    config: dict,
    attr: dict,
):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)

    return update_config(obj=obj, conf=config, attr=attr)


def set_component_config(component_id: int, config: dict, attr: dict):
    obj = ServiceComponent.obj.get(id=component_id)

    return update_config(obj=obj, conf=config, attr=attr)


def check_missing_ok(obj: ADCMEntity, multi_state: str, missing_ok):
    if missing_ok is False and multi_state not in obj.multi_state:
        raise AnsibleError(MSG_NO_MULTI_STATE_TO_DELETE)


def _unset_object_multi_state(obj: ADCMEntity, multi_state: str, missing_ok) -> ADCMEntity:
    check_missing_ok(obj, multi_state, missing_ok)
    obj.unset_multi_state(multi_state)
    send_object_update_event(object_=obj, changes={"state": multi_state})
    return obj


def unset_cluster_multi_state(cluster_id, multi_state, missing_ok):
    obj = Cluster.obj.get(id=cluster_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_service_multi_state_by_name(cluster_id, service_name, multi_state, missing_ok):
    obj = get_service_by_name(cluster_id, service_name)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_service_multi_state(cluster_id, service_id, multi_state, missing_ok):
    obj = ClusterObject.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_component_multi_state_by_name(cluster_id, service_id, component_name, service_name, multi_state, missing_ok):
    obj = get_component_by_name(cluster_id, service_id, component_name, service_name)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_component_multi_state(component_id, multi_state, missing_ok):
    obj = ServiceComponent.obj.get(id=component_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_provider_multi_state(provider_id, multi_state, missing_ok):
    obj = HostProvider.obj.get(id=provider_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def unset_host_multi_state(host_id, multi_state, missing_ok):
    obj = Host.obj.get(id=host_id)
    return _unset_object_multi_state(obj, multi_state, missing_ok)


def log_group_check(group: GroupCheckLog, fail_msg: str, success_msg: str):
    logs = CheckLog.objects.filter(group=group).values("result")
    result = all(log["result"] for log in logs)

    msg = success_msg if result else fail_msg

    group.message = msg
    group.result = result
    group.save()


def assign_view_logstorage_permissions_by_job(log_storage: LogStorage) -> None:
    task_role = Role.objects.filter(name=f"View role for task {log_storage.job.task_id}", built_in=True).first()
    view_logstorage_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=LogStorage),
        codename=f"view_{LogStorage.__name__.lower()}",
    )

    for policy in (policy for policy in Policy.objects.all() if task_role in policy.role.child.all()):
        assign_group_perm(policy=policy, permission=view_logstorage_permission, obj=log_storage)


def create_custom_log(job_id: int, name: str, log_format: str, body: str) -> LogStorage:
    log = LogStorage.objects.create(job_id=job_id, name=name, type="custom", format=log_format, body=body)
    assign_view_logstorage_permissions_by_job(log_storage=log)
    return log


def create_checklog_object(job_id: int, group_data: dict, check_data: dict) -> CheckLog:
    file_descriptor = job_lock(job_id)
    job = JobLog.obj.get(id=job_id)
    if job.status != JobStatus.RUNNING:
        raise AdcmEx("JOB_NOT_FOUND", f'job #{job.pk} has status "{job.status}", not "running"')

    group_title = group_data.pop("title")

    if group_title:
        group, _ = GroupCheckLog.objects.get_or_create(job=job, title=group_title)
    else:
        group = None

    check_data.update({"job": job, "group": group})
    check_log = CheckLog.objects.create(**check_data)

    if group is not None:
        group_data.update({"group": group})
        log_group_check(**group_data)

    log_storage, _ = LogStorage.objects.get_or_create(job=job, name="ansible", type="check", format="json")

    assign_view_logstorage_permissions_by_job(log_storage)

    file_descriptor.close()

    return check_log


def get_checklogs_data_by_job_id(job_id: int) -> list[dict[str, Any]]:
    data = []
    group_subs = defaultdict(list)

    for check_log in CheckLog.objects.filter(job_id=job_id).order_by("id"):
        group = check_log.group
        if group is None:
            data.append(
                {"title": check_log.title, "type": "check", "message": check_log.message, "result": check_log.result},
            )
        else:
            if group not in group_subs:
                data.append(
                    {
                        "title": group.title,
                        "type": "group",
                        "message": group.message,
                        "result": group.result,
                        "content": group_subs[group],
                    },
                )
            group_subs[group].append(
                {"title": check_log.title, "type": "check", "message": check_log.message, "result": check_log.result},
            )
    return data


def finish_check(job_id: int):
    data = get_checklogs_data_by_job_id(job_id)
    if not data:
        return

    job = JobLog.objects.get(id=job_id)
    LogStorage.objects.filter(job=job, name="ansible", type="check", format="json").update(body=json.dumps(data))

    GroupCheckLog.objects.filter(job=job).delete()
    CheckLog.objects.filter(job=job).delete()
