from django.db.models import Model
from rest_framework.response import Response

from audit.cases.common import obj_pk_case, response_case
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Bundle


def stack_case(
    path: list[str, ...],
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation | None, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["stack", "upload"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.Bundle,
                operation_type=AuditLogOperationType.Create,
                operation_aux_str="uploaded",
            )

        case ["stack", "load"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.Bundle,
                operation_type=AuditLogOperationType.Create,
                response=response,
                operation_aux_str="loaded",
            )

        case ["stack", "bundle", bundle_pk]:
            deleted_obj: Bundle
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Bundle,
                operation_type=AuditLogOperationType.Delete,
                obj_pk=bundle_pk,
                obj_name=deleted_obj.name,
            )

        case ["stack", "bundle", bundle_pk, "update"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Bundle,
                operation_type=AuditLogOperationType.Update,
                obj_pk=bundle_pk,
            )

        case ["stack", "bundle", bundle_pk, "license", "accept"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Bundle,
                operation_type=AuditLogOperationType.Update,
                obj_pk=bundle_pk,
                operation_aux_str="license accepted",
            )

    return audit_operation, audit_object
