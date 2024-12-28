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

from contextlib import suppress
import json

from audit.alt.api import audit_create, audit_delete, audit_update, audit_view
from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result, RetrieveAuditObjectFunc
from audit.alt.hooks import AuditHook, adjust_denied_on_404_result
from cm.models import ConfigHostGroup, Host
from rest_framework.response import Response

from api_v2.utils.audit import object_does_exist


def audit_config_host_group_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        create=audit_create(name="{group_name} configuration group created", object_=retrieve_owner).attach_hooks(
            on_collect=set_config_host_group_name_from_response
        ),
        destroy=audit_delete(name="{group_name} configuration group deleted", object_=retrieve_owner).attach_hooks(
            pre_call=set_config_host_group_name,
            on_collect=adjust_denied_on_404_result(objects_exist=config_host_group_exists),
        ),
        partial_update=audit_update(
            name="{group_name} configuration group updated", object_=retrieve_owner
        ).attach_hooks(
            on_collect=(set_config_host_group_name, adjust_denied_on_404_result(objects_exist=config_host_group_exists))
        ),
    )


def audit_host_config_host_group_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        create=audit_update(
            name="{host_name} host added to {group_name} configuration group", object_=retrieve_owner
        ).attach_hooks(
            pre_call=set_config_host_group_and_host_names_from_response,
            on_collect=adjust_denied_on_404_result(objects_exist=nested_config_host_group_exists),
        ),
        destroy=audit_update(
            name="{host_name} host removed from {group_name} configuration group", object_=retrieve_owner
        ).attach_hooks(
            on_collect=[
                set_config_host_group_and_host_names,
                adjust_denied_on_404_result(objects_exist=host_in_config_host_group_exists),
            ]
        ),
    )


def audit_config_config_host_group_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        create=audit_update(name="{group_name} configuration group updated", object_=retrieve_owner).attach_hooks(
            on_collect=(
                set_nested_config_host_group_name,
                adjust_denied_on_404_result(objects_exist=nested_config_host_group_exists),
            )
        )
    )


# hooks


def config_host_group_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=ConfigHostGroup)


def nested_config_host_group_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=ConfigHostGroup, id_field="config_host_group_pk")


def host_in_config_host_group_exists(hook: AuditHook) -> bool:
    m2m = ConfigHostGroup.hosts.through
    return m2m.objects.filter(
        host_id=hook.call_arguments.get("pk"), confighostgroup_id=hook.call_arguments.get("config_host_group_pk")
    ).exists()


def set_config_host_group_name_from_response(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,  # noqa: ARG001
    result: Result | None,
    exception: Exception | None,  # noqa: ARG001
):
    group_name = ""
    if isinstance(result, Response) and result.status_code < 300 and isinstance(result.data, dict):
        group_name = result.data.get("name", "")

    context.name = context.name.format(group_name=group_name).strip()


def set_config_host_group_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    group_name = ConfigHostGroup.objects.values_list("name", flat=True).filter(id=call_arguments.get("pk")).first()

    context.name = context.name.format(group_name=group_name or "").strip()


def set_nested_config_host_group_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    group_name = (
        ConfigHostGroup.objects.values_list("name", flat=True)
        .filter(id=call_arguments.get("config_host_group_pk"))
        .first()
    )

    context.name = context.name.format(group_name=group_name or "").strip()


def set_config_host_group_and_host_names(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    group_name = (
        ConfigHostGroup.objects.values_list("name", flat=True)
        .filter(id=call_arguments.get("config_host_group_pk"))
        .first()
    )
    host_name = Host.objects.values_list("fqdn", flat=True).filter(id=call_arguments.get("pk")).first()

    context.name = (
        context.name.format(group_name=group_name or "", host_name=host_name or "").strip().replace("  ", " ")
    )


def set_config_host_group_and_host_names_from_response(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    host_name = ""
    group_name = (
        ConfigHostGroup.objects.values_list("name", flat=True)
        .filter(id=call_arguments.get("config_host_group_pk"))
        .first()
    )

    if request := call_arguments.get("request"):
        data = None
        with suppress(AttributeError, json.JSONDecodeError):
            data = json.loads(request.body)

        if isinstance(data, dict):
            host_name = Host.objects.values_list("fqdn", flat=True).filter(id=data.get("hostId")).first() or ""

    context.name = context.name.format(group_name=group_name or "", host_name=host_name).strip().replace("  ", " ")
