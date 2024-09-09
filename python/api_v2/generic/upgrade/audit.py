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

from audit.alt.api import audit_update, audit_view
from audit.alt.core import AuditedCallArguments, OperationAuditContext, Result, RetrieveAuditObjectFunc
from audit.alt.hooks import AuditHook, adjust_denied_on_404_result
from cm.models import Upgrade

from api_v2.utils.audit import object_does_exist


def audit_upgrade_viewset(retrieve_owner: RetrieveAuditObjectFunc):
    return audit_view(
        run=audit_update(name="upgrade launched", object_=retrieve_owner).attach_hooks(
            on_collect=[set_name, adjust_denied_on_404_result(objects_exist=action_exists)]
        )
    )


# hooks


def action_exists(hook: AuditHook) -> bool:
    return object_does_exist(hook=hook, model=Upgrade)


def set_name(
    context: OperationAuditContext,
    call_arguments: AuditedCallArguments,
    result: Result | None,  # noqa: ARG001
    exception: Exception | None,  # noqa: ARG001
):
    upgrade_name, action_name = Upgrade.objects.values_list("display_name", "action__display_name").filter(
        id=call_arguments.get("pk")
    ).first() or (None, None)

    if action_name is not None:
        context.name = f"{action_name} upgrade launched".strip()
    else:
        context.name = f"Upgraded to {upgrade_name or ''}".strip()
