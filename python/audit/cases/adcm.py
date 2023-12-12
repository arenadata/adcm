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
from audit.cases.common import (
    _get_audit_operation,
    get_or_create_audit_obj,
    obj_pk_case,
)
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import ADCM
from django.views import View
from requests import Response


def adcm_case(
    path: list[str], view: View, response: Response, api_version: int = 1
) -> tuple[AuditOperation | None, AuditObject | None]:
    audit_operation = None
    audit_object = None

    if api_version == 1:
        match path:
            case (["adcm", adcm_pk, "config", "history"] | ["adcm", adcm_pk, "config", "history", _, "restore"]):
                audit_operation, audit_object = obj_pk_case(
                    obj_type=AuditObjectType.ADCM,
                    operation_type=AuditLogOperationType.UPDATE,
                    obj_pk=adcm_pk,
                    operation_aux_str="configuration ",
                )
    else:
        match path:
            case ["adcm", "configs"]:
                if not response:
                    return (
                        _get_audit_operation(
                            obj_type=AuditObjectType.ADCM,
                            operation_type=AuditLogOperationType.UPDATE,
                            operation_aux_str="configuration ",
                        ),
                        audit_object,
                    )

                audit_operation, audit_object = obj_pk_case(
                    obj_type=AuditObjectType.ADCM,
                    operation_type=AuditLogOperationType.UPDATE,
                    obj_pk=ADCM.objects.first().pk,
                    operation_aux_str="configuration ",
                )
            case ["profile"]:
                current_user = view.request.user
                audit_operation = AuditOperation(
                    name="Profile updated",
                    operation_type=AuditLogOperationType.UPDATE,
                )
                audit_object = get_or_create_audit_obj(
                    object_id=current_user.pk,
                    object_name=current_user.username,
                    object_type=AuditObjectType.USER,
                )

    return audit_operation, audit_object
