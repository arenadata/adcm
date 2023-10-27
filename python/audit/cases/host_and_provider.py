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
from cm.models import Host, HostProvider
from django.db.models import Model
from django.views import View
from rest_framework.response import Response


def host_and_provider_case(
    path: list[str, ...],
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (
            ["host", host_pk]
            | ["host", host_pk, _]
            | ["provider", _, "host", host_pk]
            | ["provider", _, "host", host_pk, "maintenance-mode"]
        ):
            if view.request.method == "DELETE":
                operation_type = AuditLogOperationType.DELETE
            else:
                operation_type = AuditLogOperationType.UPDATE

            object_name = None
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.HOST.capitalize()} {operation_type}d",
                operation_type=operation_type,
            )
            if isinstance(deleted_obj, Host):
                object_name = deleted_obj.fqdn
            else:
                host = Host.objects.filter(pk=host_pk).first()
                if host:
                    object_name = host.fqdn

            if object_name:
                audit_object = get_or_create_audit_obj(
                    object_id=host_pk,
                    object_name=object_name,
                    object_type=AuditObjectType.HOST,
                )
            else:
                audit_object = None

        case ["host"] | ["provider", _, "host"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.HOST,
                operation_type=AuditLogOperationType.CREATE,
                response=response,
            )

        case ["provider"] | ["hostproviders"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.PROVIDER,
                operation_type=AuditLogOperationType.CREATE,
                response=response,
            )

        case ["provider" | "hostproviders", provider_pk]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.PROVIDER.capitalize()} {AuditLogOperationType.DELETE}d",
                operation_type=AuditLogOperationType.DELETE,
            )
            if isinstance(deleted_obj, HostProvider):
                audit_object = get_or_create_audit_obj(
                    object_id=provider_pk,
                    object_name=deleted_obj.name,
                    object_type=AuditObjectType.PROVIDER,
                )
            else:
                audit_object = None

        case (
            ["provider", provider_pk, "config", "history"]
            | ["provider", provider_pk, "config", "history", _, "restore"]
            | ["hostproviders", provider_pk, "configs"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.PROVIDER,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=provider_pk,
                operation_aux_str="configuration ",
            )

    return audit_operation, audit_object
