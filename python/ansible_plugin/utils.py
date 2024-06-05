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
from typing import Any
import json

# isort: off
from ansible.errors import AnsibleError
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from ansible_plugin.messages import (
    MSG_NO_CONFIG,
    MSG_NO_CONTEXT,
    MSG_WRONG_CONTEXT,
    MSG_WRONG_CONTEXT_ID,
)
from cm.adcm_config.config import get_option_value
from cm.models import (
    CheckLog,
    Cluster,
    ClusterObject,
    GroupCheckLog,
    JobLog,
    LogStorage,
    Prototype,
)
from rbac.models import Role, Policy
from rbac.roles import assign_group_perm
# isort: on


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


# Helper functions for ansible plugins


def get_service_by_name(cluster_id, service_name):
    cluster = Cluster.obj.get(id=cluster_id)
    proto = Prototype.obj.get(type="service", name=service_name, bundle=cluster.prototype.bundle)
    return ClusterObject.obj.get(cluster=cluster, prototype=proto)


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


def assign_view_logstorage_permissions_by_job(log_storage: LogStorage) -> None:
    task_role = Role.objects.filter(name=f"View role for task {log_storage.job.task_id}", built_in=True).first()
    view_logstorage_permission, _ = Permission.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(model=LogStorage),
        codename=f"view_{LogStorage.__name__.lower()}",
    )

    for policy in (policy for policy in Policy.objects.all() if task_role in policy.role.child.all()):
        assign_group_perm(policy=policy, permission=view_logstorage_permission, obj=log_storage)


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
