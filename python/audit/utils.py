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

from functools import wraps
from typing import Tuple

from adwp_base.errors import AdwpEx
from audit.models import (
    AUDIT_OPERATION_MAP,
    AuditLog,
    AuditLogOperationResult,
    AuditObject,
    AuditOperation,
    AuditLogOperationType,
    AuditObjectType,
)
from cm.errors import AdcmEx
from cm.models import ADCM
from django.contrib.contenttypes.models import ContentType
from django.views.generic.base import View
from rbac.models import User
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, is_success


def _get_object_name_from_resp(resp: Response) -> str:
    if hasattr(resp.data.serializer.instance, "name"):
        object_name = resp.data.serializer.instance.name
    elif hasattr(resp.data.serializer.instance, "fqdn"):
        object_name = resp.data.serializer.instance.fqdn
    else:
        object_name = str(resp.data.serializer.instance)

    return object_name


def make_audit_log(operation_type, result, operation_status):
    operation_type_map = {
        "task_db": {
            "type": AuditLogOperationType.Delete,
            "name": '"Task log cleanup in database on schedule" job',
        },
        "task_fs": {
            "type": AuditLogOperationType.Delete,
            "name": '"Task log cleanup in filesystem on schedule" job',
        },
        "config": {
            "type": AuditLogOperationType.Delete,
            "name": '"Objects configurations cleanup on schedule" job',
        },
        "sync": {"type": AuditLogOperationType.Update, "name": '"User sync on schedule" job'},
        "audit": {
            "type": AuditLogOperationType.Delete,
            "name": '"Audit log cleanup/archiving on schedule" job',
        },
    }
    result = (
        AuditLogOperationResult.Success if result == 'success' else AuditLogOperationResult.Fail
    )
    operation_name = operation_type_map[operation_type]["name"] + ' ' + operation_status
    audit_object, _ = AuditObject.objects.get_or_create(
        object_id=ADCM.objects.get().id,
        object_name='ADCM',
        object_type=AuditObjectType.ADCM,
    )
    system_user = User.objects.get(username='system')
    AuditLog.objects.create(
        audit_object=audit_object,
        operation_name=operation_name,
        operation_type=operation_type_map[operation_type]['type'],
        operation_result=result,
        user=system_user,
    )


def _get_object_type_from_resp(audit_operation: AuditOperation, resp: Response) -> str:
    if audit_operation.object_type == "config log":
        object_type: str = ContentType.objects.get_for_model(
            resp.data.serializer.instance.obj_ref.object
        ).name
    else:
        object_type: str = resp.data.serializer.instance.object_type.name

    return object_type


def _get_audit_object_and_operation_name(
    audit_operation: AuditOperation, resp: Response
) -> Tuple[AuditObject, str]:
    operation_name: str = audit_operation.name
    object_name = _get_object_name_from_resp(resp)

    if audit_operation.object_type in {"group config", "config log"}:
        object_type = _get_object_type_from_resp(audit_operation, resp)
        operation_name = f"{object_type.capitalize()} {operation_name}"
    else:
        object_type: str = audit_operation.object_type

    return (
        AuditObject.objects.create(
            object_id=resp.data.serializer.instance.id,
            object_name=object_name,
            object_type=object_type,
        ),
        operation_name,
    )


def audit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        # pylint: disable=too-many-branches

        error = None

        try:
            resp = func(*args, **kwargs)
            status_code = resp.status_code
        except (AdcmEx, AdwpEx) as exc:
            error = exc
            resp = None
            status_code = exc.status_code

        view: View = args[0]
        audit_operation: AuditOperation = AUDIT_OPERATION_MAP[view.__class__.__name__][
            view.request.method
        ]
        operation_name: str = audit_operation.name
        object_changes: dict = {}

        if is_success(status_code):
            operation_result = AuditLogOperationResult.Success
            if resp.data:
                audit_object, operation_name = _get_audit_object_and_operation_name(
                    audit_operation, resp
                )
            else:
                audit_object = None
        elif status_code == HTTP_403_FORBIDDEN:
            operation_result = AuditLogOperationResult.Denied
            audit_object = None
        else:
            operation_result = AuditLogOperationResult.Fail
            audit_object = None

        AuditLog.objects.create(
            audit_object=audit_object,
            operation_name=operation_name,
            operation_type=audit_operation.operation_type,
            operation_result=operation_result,
            user=view.request.user,
            object_changes=object_changes,
        )

        if error:
            raise error

        return resp

    return wrapped


def mark_deleted_audit_object(instance):
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(object_id=instance.pk):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])
