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

from cm.models import ActionHostGroup, Host
from rest_framework.response import Response

from audit.cases.common import get_audit_cm_object_from_path_info
from audit.models import AuditLogOperationType, AuditOperation


def action_host_group_case(path: list[str], response: Response | None, deleted_obj: ActionHostGroup | None):
    audit_operation = None
    audit_object = None

    match path:
        case [*_, owner_type, owner_pk, "action-host-groups"]:
            audit_operation = AuditOperation(
                name=f"{'' if not response else response.data.get('name', '')} action host group created".strip(),
                operation_type=AuditLogOperationType.CREATE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )
        case [*_, owner_type, owner_pk, "action-host-groups", _group_pk]:
            audit_operation = AuditOperation(
                name=f"{'' if not deleted_obj else deleted_obj.name} action host group deleted".strip(),
                operation_type=AuditLogOperationType.DELETE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )
        case [*_, _owner_type, _owner_pk, "action-host-groups", group_pk, "hosts"]:
            group_name = ActionHostGroup.objects.values_list("name", flat=True).filter(pk=group_pk).first() or ""
            host_info = "Host"
            if response:
                host_info = f"Host {response.data.get('name', '')}".strip()

            audit_operation = AuditOperation(
                name=f"{host_info} added to action host group {group_name}".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path="action-host-groups", object_pk_from_path=group_pk
            )
        case [*_, _owner_type, _owner_pk, "action-host-groups", group_pk, "hosts", host_pk]:
            group_name = ActionHostGroup.objects.values_list("name", flat=True).filter(pk=group_pk).first() or ""
            host_info = f"Host {Host.objects.values_list('fqdn', flat=True).filter(pk=host_pk).first() or ''}"

            audit_operation = AuditOperation(
                name=f"{host_info} removed from action host group {group_name}".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path="action-host-groups", object_pk_from_path=group_pk
            )

    return audit_operation, audit_object
