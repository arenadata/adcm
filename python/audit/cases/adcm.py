from audit.cases.common import obj_pk_case
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)


def adcm_case(path: list[str, ...]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (
            ["adcm", adcm_pk, "config", "history"]
            | ["adcm", adcm_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.ADCM,
                operation_type=AuditLogOperationType.Update,
                obj_pk=adcm_pk,
                operation_aux_str="configuration ",
            )

    return audit_operation, audit_object
