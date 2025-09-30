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

from audit.alt.api import audit_create, audit_update, audit_view
from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result, RetrieveAuditObjectFunc
from audit.alt.hooks import AuditHook, adjust_denied_on_404_result
from cm.models import Action

from api_v2.utils.audit import _retrieve_request_body, object_does_exist


def audit_action_process_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        create=audit_create(name="Process of action {action_name} created", object_=retrieve_owner).attach_hooks(
            on_collect=[set_name, adjust_denied_on_404_result(objects_exist=parent_action_exists)]
        ),
        operation=audit_update(
            name="Operation {operation_name} for process {process_id} of action {action_name}",
            object_=retrieve_owner,
        ).attach_hooks(
            pre_call=retrieve_operation_name,
            on_collect=[set_names, adjust_denied_on_404_result(objects_exist=parent_action_exists)],
        ),
    )


def parent_action_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Action, id_field="action_pk")


def set_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    action_name = (
        Action.objects.values_list("display_name", flat=True).filter(id=call_arguments.get("action_pk")).first()
    )

    context.name = context.name.format(action_name=action_name or "").strip().replace("  ", " ")


def set_names(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    action_name = (
        Action.objects.values_list("display_name", flat=True).filter(id=call_arguments.get("action_pk")).first()
    )
    process_id = call_arguments.get("pk")
    operation_name = call_arguments.data.get("method", "")

    context.name = (
        context.name.format(operation_name=operation_name, process_id=process_id, action_name=action_name or "")
        .strip()
        .replace("  ", " ")
    )


class retrieve_operation_name(AuditHook):  # noqa: N801
    def __call__(self):
        request = self.call_arguments.get("request")
        if request is None:
            return ()

        if (data := _retrieve_request_body(request=request)) is None:
            return ()

        self.call_arguments.data["method"] = data.get("method").strip()
