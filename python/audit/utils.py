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
from typing import Optional, Tuple

from adwp_base.errors import AdwpEx
from audit.models import (
    AuditLog,
    AuditLogOperationResult,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.errors import AdcmEx
from cm.models import Host
from django.contrib.contenttypes.models import ContentType
from django.views.generic.base import View
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, is_success


def _get_audit_object_from_resp(resp: Response, obj_type: str) -> Optional[AuditObject]:
    if resp:
        audit_object = AuditObject.objects.create(
            object_id=resp.data["id"],
            object_name=resp.data["name"],
            object_type=obj_type,
        )
    else:
        audit_object = None

    return audit_object



def _get_audit_operation_and_object(  # pylint: disable=too-many-statements
        view: View, resp: Response
) -> Tuple[Optional[AuditOperation], Optional[AuditObject], Optional[str]]:
    operation_name = None
    audit_object = None
    path = view.request.stream.path.replace("/api/v1/", "")[:-1].split("/")

    match path:
        case ["stack", "upload"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.label.capitalize()} uploaded",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = None

        case ["stack", "load"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.label.capitalize()} loaded",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Bundle.label)

        case ["cluster"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.label.capitalize()} "
                f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Cluster.label)

        case ["config-log"] | ["group-config", _, "config", _, "config-log"]:
            audit_operation = AuditOperation(
                name=f"config log {AuditLogOperationType.Update.label}d",
                operation_type=AuditLogOperationType.Update.label,
            )

            if resp:
                object_type = ContentType.objects.get_for_model(
                    resp.data.serializer.instance.obj_ref.object
                ).name
                audit_object = AuditObject.objects.create(
                    object_id=resp.data.serializer.instance.id,
                    object_name=str(resp.data.serializer.instance),
                    object_type=object_type,
                )
                operation_name = f"{object_type.capitalize()} {audit_operation.name}"
            else:
                audit_object = None
                operation_name = audit_operation.name

        case ["group-config"]| ["group-config", _]:
            if view.action == "create":
                operation_type = AuditLogOperationType.Create.label
            elif view.action in {"update", "partial_update"}:
                operation_type = AuditLogOperationType.Update.label
            else:
                operation_type = AuditLogOperationType.Delete.label

            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            if resp:
                object_type = resp.data.serializer.instance.object_type.name
                audit_object = AuditObject.objects.create(
                    object_id=resp.data.serializer.instance.object.id,
                    object_name=resp.data.serializer.instance.object.name,
                    object_type=object_type,
                )
                operation_name = f"{resp.data.serializer.instance.name} {audit_operation.name}"
            else:
                audit_object = None
                operation_name = audit_operation.name

        case ["rbac", "group"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Group.label.capitalize()} "
                f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Group.label)

        case ["rbac", "policy"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Policy.label.capitalize()} "
                f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Policy.label)

        case ["rbac", "role"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Role.label.capitalize()} "
                     f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Role.label)

        case ["rbac", "user"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.User.label.capitalize()} "
                     f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            if resp:
                audit_object = AuditObject.objects.create(
                    object_id=resp.data["id"],
                    object_name=resp.data["username"],
                    object_type=AuditObjectType.User.label,
                )
            else:
                audit_object = None

        case ["host"] | ["provider", _, "host"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.label.capitalize()} "
                     f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            if resp:
                audit_object = AuditObject.objects.create(
                    object_id=resp.data["id"],
                    object_name=resp.data["fqdn"],
                    object_type=AuditObjectType.Host.label,
                )
            else:
                audit_object = None

        case ["provider"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Provider.label.capitalize()} "
                f"{AuditLogOperationType.Create.label}d",
                operation_type=AuditLogOperationType.Create.label,
            )
            audit_object = _get_audit_object_from_resp(resp, AuditObjectType.Provider.label)

        case ["host", host_pk, "config", "history"]:
            object_type = "host"
            operation_type = AuditLogOperationType.Update.label
            audit_operation = AuditOperation(
                name=f"{object_type.capitalize()} configuration {operation_type}d",
                operation_type=operation_type,
            )
            obj = Host.objects.get(pk=host_pk)
            audit_object = AuditObject.objects.create(
                object_id=host_pk,
                object_name=obj.fqdn,
                object_type=object_type,
            )

        case _:
            return None, None, None

    if not operation_name and audit_operation:
        operation_name = audit_operation.name

    return audit_operation, audit_object, operation_name


def audit(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        # pylint: disable=too-many-branches

        audit_operation: AuditOperation
        audit_object: AuditObject
        operation_name: str

        error = None

        try:
            resp = func(*args, **kwargs)
            status_code = resp.status_code
        except (AdcmEx, AdwpEx) as exc:
            error = exc
            resp = None
            status_code = exc.status_code

        view: View = args[0]
        audit_operation, audit_object, operation_name = _get_audit_operation_and_object(view, resp)
        if audit_operation:
            object_changes: dict = {}

            if is_success(status_code):
                operation_result = AuditLogOperationResult.Success
            elif status_code == HTTP_403_FORBIDDEN:
                operation_result = AuditLogOperationResult.Denied
            else:
                operation_result = AuditLogOperationResult.Fail

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
