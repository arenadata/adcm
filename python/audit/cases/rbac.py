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

from dataclasses import dataclass

from audit.cases.common import get_audit_object_from_resp, get_or_create_audit_obj
from audit.models import (
    AUDIT_OBJECT_TYPE_TO_MODEL_MAP,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.views import View
from rest_framework.response import Response


@dataclass
class RbacCaseData:
    view: View
    deleted_obj: Model
    obj_pk: int


def _rbac_case(
    obj_type: AuditObjectType,
    response: Response | None,
    data: RbacCaseData | None = None,
) -> tuple[AuditOperation, AuditObject | None]:
    if data:
        if data.view.action == "destroy":
            operation_type = AuditLogOperationType.DELETE
            obj = data.deleted_obj
        else:
            operation_type = AuditLogOperationType.UPDATE
            try:
                obj = AUDIT_OBJECT_TYPE_TO_MODEL_MAP[obj_type].objects.get(pk=data.obj_pk)
            except ObjectDoesNotExist:
                obj = None

        if obj:
            audit_object = get_or_create_audit_obj(
                object_id=str(data.obj_pk),
                object_name=obj.name if obj_type != AuditObjectType.USER else obj.username,
                object_type=obj_type,
            )
        else:
            audit_object = None

    else:
        operation_type = AuditLogOperationType.CREATE
        audit_object = get_audit_object_from_resp(
            response=response,
            obj_type=obj_type,
        )

    audit_operation = AuditOperation(
        name=f"{obj_type.capitalize()} {operation_type}d",
        operation_type=operation_type,
    )

    return audit_operation, audit_object


def rbac_case(
    path: list[str, ...],
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["rbac", "group"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.GROUP,
                response=response,
            )

        case ["rbac", "group", group_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=group_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.GROUP,
                response=response,
                data=data,
            )

        case ["rbac", "policy"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.POLICY,
                response=response,
            )

        case ["rbac", "policy", policy_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=policy_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.POLICY,
                response=response,
                data=data,
            )

        case ["rbac", "role"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.ROLE,
                response=response,
            )

        case ["rbac", "role", role_pk]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=role_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.ROLE,
                response=response,
                data=data,
            )

        case ["rbac", "user"]:
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.USER,
                response=response,
            )

        case ["rbac", "user", user_pk] | ["rbac", "user", user_pk, "reset_failed_login_attempts"]:
            data = RbacCaseData(view=view, deleted_obj=deleted_obj, obj_pk=user_pk)
            audit_operation, audit_object = _rbac_case(
                obj_type=AuditObjectType.USER,
                response=response,
                data=data,
            )

            if view.action == "reset_failed_login_attempts":
                audit_operation.name = "User login attempts reset"

    return audit_operation, audit_object
