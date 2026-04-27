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
from functools import partial
import json

from audit.alt.api import audit_create, audit_delete, audit_update, audit_view
from audit.alt.core import (
    AuditedCallArguments,
    IDBasedAuditObjectCreator,
    OperationAuditContext,
    Result,
    RetrieveAuditObjectFunc,
)
from audit.alt.hooks import AuditHook, adjust_denied_on_404_result
from audit.alt.object_retrievers import GeneralAuditObjectRetriever
from audit.models import AuditObjectType
from cm.models import ActionHostGroup, Host
from rest_framework.response import Response

from api_v2.utils.audit import ExtractID, get_ahg_audit_name, object_does_exist

# hooks


class ActionHostGroupAuditObjectCreator(IDBasedAuditObjectCreator):
    model = ActionHostGroup
    name_field = "prototype__display_name"

    def get_name(self, id_: str | int) -> str | None:
        return get_ahg_audit_name(id_=id_)


_extract_action_host_group = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.ACTION_HOST_GROUP,
    create_new=ActionHostGroupAuditObjectCreator(model=ActionHostGroup),
)
action_host_group_from_lookup = _extract_action_host_group(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_action_host_group_from_lookup = _extract_action_host_group(
    extract_id=ExtractID(field="action_host_group_pk").from_lookup_kwargs
)


def audit_action_host_group_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        create=(
            audit_create(name="{group_name} action host group created", object_=retrieve_owner).attach_hooks(
                on_collect=set_group_name_from_response
            )
        ),
        partial_update=(
            audit_update(name="{group_name} action host group updated", object_=retrieve_owner).attach_hooks(
                pre_call=set_group_name,
                on_collect=adjust_denied_on_404_result(objects_exist=action_host_group_exists),
            )
        ),
        destroy=(
            audit_delete(
                name="{group_name} action host group deleted",
                object_=retrieve_owner,
            ).attach_hooks(
                pre_call=set_group_name,
                on_collect=adjust_denied_on_404_result(objects_exist=action_host_group_exists),
            )
        ),
    )


def action_host_group_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=ActionHostGroup)


def nested_action_host_group_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=ActionHostGroup, id_field="action_host_group_pk")


def host_and_action_host_group_exist(hook: AuditHook) -> bool:
    m2m = ActionHostGroup.hosts.through
    return m2m.objects.filter(
        host_id=hook.call_arguments.get("pk"), actionhostgroup_id=hook.call_arguments.get("action_host_group_pk")
    ).exists()


def set_group_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    group_name = ActionHostGroup.objects.values_list("name", flat=True).filter(id=call_arguments.get("pk")).first()

    context.name = context.name.format(group_name=group_name or "").strip().replace("  ", " ")


def set_group_name_from_response(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,  # noqa: ARG001
    result: Result | None,
    exception: Exception | None,  # noqa: ARG001
):
    group_name = ""
    if isinstance(result, Response) and result.status_code < 300 and isinstance(result.data, dict):
        group_name = result.data.get("name", "")

    context.name = context.name.format(group_name=group_name).strip()


def set_group_and_host_names(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    group_name = (
        ActionHostGroup.objects.values_list("name", flat=True)
        .filter(id=call_arguments.get("action_host_group_pk"))
        .first()
    )
    host_name = Host.objects.values_list("fqdn", flat=True).filter(id=call_arguments.get("pk")).first()

    context.name = (
        context.name.format(group_name=group_name or "", host_name=host_name or "").strip().replace("  ", " ")
    )


def set_group_and_host_names_from_response(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    # this function feels incorrect, see set_config_host_group_name_from_response for reference implementation
    host_name = ""
    group_name = (
        ActionHostGroup.objects.values_list("name", flat=True)
        .filter(id=call_arguments.get("action_host_group_pk"))
        .first()
    )

    if request := call_arguments.get("request"):
        data = None
        with suppress(AttributeError, json.JSONDecodeError):
            data = json.loads(request.body)

        if isinstance(data, dict):
            host_name = Host.objects.values_list("fqdn", flat=True).filter(id=data.get("hostId")).first() or ""

    context.name = context.name.format(group_name=group_name or "", host_name=host_name).strip().replace("  ", " ")
