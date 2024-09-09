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

from audit.alt.core import AuditSignature, Hooks, OperationAuditContext
from audit.alt.object_retrievers import ignore_object_search
from audit.models import AuditLogOperationResult, AuditLogOperationType, AuditObject, AuditObjectType
from core.job.types import ExecutionStatus, Task
from core.types import ADCMCoreType


def audit_task_finish(task: Task, task_result: ExecutionStatus) -> None:
    audit_context = OperationAuditContext(
        signature=AuditSignature(id="Action completion", type=AuditLogOperationType.UPDATE),
        default_name=f"{task.action.display_name} {'upgrade' if task.action.is_upgrade else 'action'} completed",
        retrieve_object=ignore_object_search,
        custom_hooks=Hooks(),
    )
    audit_context.result = (
        AuditLogOperationResult.SUCCESS if task_result == ExecutionStatus.SUCCESS else AuditLogOperationResult.FAIL
    )

    # If object doesn't exist for some reason, we don't create it.
    # Now action can't be launched avoiding audit.
    # In case it will change, don't use `target.name`,
    # use retrievers that create audit objects based on type and name
    # in order to build correct audit names for service/component/action host group.
    audit_context.object = AuditObject.objects.filter(
        object_id=str(task.target.id),
        object_type=AuditObjectType(task.target.type.value)
        if task.target.type != ADCMCoreType.HOSTPROVIDER
        else AuditObjectType.PROVIDER,
    ).first()
    audit_context.save()
