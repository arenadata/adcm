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

from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result
from audit.alt.hooks import AuditHook
from audit.alt.object_retrievers import GeneralAuditObjectRetriever
from audit.models import AuditObjectType
from cm.models import ActionHostGroup, Cluster, ClusterObject, Host, ServiceComponent

from api_v2.utils.audit import CMAuditObjectCreator, ExtractID, object_does_exist

# hooks


class ActionHostGroupAuditObjectCreator(CMAuditObjectCreator):
    cm_model = ActionHostGroup
    name_field = "prototype__display_name"

    def get_name(self, id_: str | int) -> str | None:
        # retrieval of child names is not optimal, can be improved
        # by avoiding prefetching object and just routing based on type
        group = ActionHostGroup.objects.prefetch_related("object").filter(id=id_).first()
        if not group:
            return None

        parent = group.object

        # Also naming extraction can be unified maybe, but then no easy optimization probably
        if isinstance(parent, Cluster):
            names = (parent.name,)
        elif isinstance(parent, ClusterObject):
            names = (
                ClusterObject.objects.values_list("cluster__name", "prototype__display_name")
                .filter(id=parent.id)
                .first()
                or ()
            )
        elif isinstance(parent, ServiceComponent):
            names = (
                ServiceComponent.objects.values_list(
                    "cluster__name", "service__prototype__display_name", "prototype__display_name"
                )
                .filter(id=parent.id)
                .first()
                or ()
            )
        else:
            names = ()

        return "/".join((*names, group.name))


_extract_action_host_group = partial(
    GeneralAuditObjectRetriever,
    audit_object_type=AuditObjectType.ACTION_HOST_GROUP,
    create_new=ActionHostGroupAuditObjectCreator(cm_model=ActionHostGroup),
)
action_host_group_from_lookup = _extract_action_host_group(extract_id=ExtractID(field="pk").from_lookup_kwargs)
parent_action_host_group_from_lookup = _extract_action_host_group(
    extract_id=ExtractID(field="action_host_group_pk").from_lookup_kwargs
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
