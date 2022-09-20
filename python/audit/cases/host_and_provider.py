from django.db.models import Model
from django.views import View
from rest_framework.response import Response

from audit.cases.common import get_or_create_audit_obj, obj_pk_case, response_case
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Host, HostProvider


def host_and_provider_case(
    path: list[str, ...],
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["host", host_pk] | ["provider", _, "host", host_pk]:
            if view.request.method == "DELETE":
                operation_type = AuditLogOperationType.Delete
            else:
                operation_type = AuditLogOperationType.Update
            object_name = None
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} {operation_type}d",
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
                    object_type=AuditObjectType.Host,
                )
            else:
                audit_object = None

        case ["host"] | ["provider", _, "host"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.Host,
                operation_type=AuditLogOperationType.Create,
                response=response,
            )

        case ["provider"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.Provider,
                operation_type=AuditLogOperationType.Create,
                response=response,
            )

        case ["provider", provider_pk]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Provider.capitalize()} {AuditLogOperationType.Delete}d",
                operation_type=AuditLogOperationType.Delete,
            )
            if isinstance(deleted_obj, HostProvider):
                audit_object = get_or_create_audit_obj(
                    object_id=provider_pk,
                    object_name=deleted_obj.name,
                    object_type=AuditObjectType.Provider,
                )
            else:
                audit_object = None

        case (
            ["provider", provider_pk, "config", "history"]
            | ["provider", provider_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Provider,
                operation_type=AuditLogOperationType.Update,
                obj_pk=provider_pk,
                operation_aux_str="configuration ",
            )

    return audit_operation, audit_object
