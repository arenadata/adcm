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
from audit.cases.common import get_or_create_audit_obj, obj_pk_case, response_case
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Bundle, Prototype
from django.db.models import Model
from rest_framework.response import Response


def stack_case(
    path: list[str],
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation | None, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["stack", "upload"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.BUNDLE,
                operation_type=AuditLogOperationType.CREATE,
                operation_aux_str="uploaded",
            )

        case ["stack", "load"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.BUNDLE,
                operation_type=AuditLogOperationType.CREATE,
                response=response,
                operation_aux_str="loaded",
            )

        case ["stack", "bundle", bundle_pk]:
            deleted_obj: Bundle
            if deleted_obj:
                audit_operation, audit_object = obj_pk_case(
                    obj_type=AuditObjectType.BUNDLE,
                    operation_type=AuditLogOperationType.DELETE,
                    obj_pk=bundle_pk,
                    obj_name=deleted_obj.name,
                )

        case ["stack", "bundle", bundle_pk, "update"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.BUNDLE,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=bundle_pk,
            )
        case ["stack", "bundle", bundle_pk, "license", "accept"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.BUNDLE,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=bundle_pk,
                operation_aux_str="license accepted",
            )
        case ["stack", "prototype", prototype_pk, "license", "accept"]:
            prototype = Prototype.objects.get(pk=prototype_pk)
            audit_object = get_or_create_audit_obj(
                object_id=prototype_pk, object_name=prototype.name, object_type=AuditObjectType.PROTOTYPE
            )
            audit_operation = AuditOperation(
                name=f"{prototype.type.capitalize()} license accepted", operation_type=AuditLogOperationType.UPDATE
            )

    return audit_operation, audit_object
