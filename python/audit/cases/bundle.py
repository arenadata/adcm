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

from audit.cases.common import get_or_create_audit_obj
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Bundle
from django.db.models import Model
from django.views import View
from rest_framework.response import Response


def bundle_case(
    path: list[str],
    view: View,
    response: Response | None,
    deleted_obj: Model,
) -> tuple[AuditOperation | None, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (["bundles", bundle_pk]):
            if view.request.method != "DELETE":
                return audit_operation, audit_object
            operation_type = AuditLogOperationType.DELETE
            operation_name = f"{AuditObjectType.BUNDLE.capitalize()} {operation_type}d"

            object_name = None
            audit_operation = AuditOperation(
                name=operation_name,
                operation_type=operation_type,
            )

            if isinstance(deleted_obj, Bundle):
                object_name = deleted_obj.name
            else:
                bundle = Bundle.objects.filter(pk=bundle_pk).first()
                if bundle:
                    object_name = bundle.name

            if object_name:
                audit_object = get_or_create_audit_obj(
                    object_id=bundle_pk,
                    object_name=object_name,
                    object_type=AuditObjectType.BUNDLE,
                )
                audit_object.is_deleted = True
                audit_object.save()
            else:
                audit_object = None

        case (["bundles"]):
            if view.request.method == "POST" and response and response.status_code == 201:
                audit_operation = AuditOperation(
                    name="Bundle uploaded",
                    operation_type=AuditLogOperationType.CREATE,
                )

    return audit_operation, audit_object
