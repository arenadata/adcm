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
from cm.models import Bundle, Prototype
from django.views import View
from rest_framework.response import Response


def license_case(
    path: list[str, ...],
    view: View,
    response: Response,
) -> tuple[AuditOperation | None, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (["bundles", bundle_pk]):
            if view.request.method == "PUT" and "accept" in path and response.status_code == 200:
                audit_operation = AuditOperation(
                    name="Bundle license accepted",
                    operation_type=AuditLogOperationType.UPDATE,
                )
                bundle = Bundle.objects.filter(pk=bundle_pk).first()
                audit_object = get_or_create_audit_obj(
                    object_id=bundle_pk,
                    object_name=bundle.name,
                    object_type=AuditObjectType.BUNDLE,
                )
        case (["prototypes", prototype_pk, "license", "accept"]):
            if view.request.method == "POST" and response and response.status_code == 200:
                prototype = Prototype.objects.filter(pk=prototype_pk).first()
                audit_operation = AuditOperation(
                    name="Bundle license accepted",
                    operation_type=AuditLogOperationType.UPDATE,
                )
                audit_object = get_or_create_audit_obj(
                    object_id=prototype.bundle.pk,
                    object_name=prototype.bundle.name,
                    object_type=AuditObjectType.BUNDLE,
                )

    return audit_operation, audit_object
