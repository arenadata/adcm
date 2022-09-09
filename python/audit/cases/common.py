from django.db.models import Model
from rest_framework.response import Response

from audit.models import (
    AUDIT_OBJECT_TYPE_TO_MODEL_MAP,
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    PATH_STR_TO_OBJ_CLASS_MAP,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Action, ClusterObject, TaskLog, Upgrade


def _get_audit_operation(
    obj_type: AuditObjectType,
    operation_type: AuditLogOperationType,
    operation_aux_str: str | None = None,
):
    if obj_type == AuditObjectType.ADCM:
        operation_name = obj_type.upper()
    else:
        operation_name = obj_type.capitalize()

    if operation_aux_str:
        operation_name = f"{operation_name} {operation_aux_str}"
        if operation_aux_str[-1] == " ":
            operation_name = f"{operation_name}{operation_type}d"
    else:
        operation_name = f"{operation_name} {operation_type}d"

    return AuditOperation(name=operation_name, operation_type=operation_type)


def _task_case(task_pk: str, action: str) -> tuple[AuditOperation, AuditObject | None]:
    if action == "cancel":
        action = f"{action}l"

    obj = TaskLog.objects.filter(pk=task_pk).first()

    if obj and obj.action:
        action_name = obj.action.display_name
    else:
        action_name = "Task"

    audit_operation = AuditOperation(
        name=f"{action_name} {action}ed",
        operation_type=AuditLogOperationType.Update,
    )

    if obj:
        audit_object = get_or_create_audit_obj(
            object_id=task_pk,
            object_name=obj.task_object.name,
            object_type=obj.object_type.name,
        )
    else:
        audit_object = None

    return audit_operation, audit_object


def get_obj_name(obj: Model, obj_type: str) -> str:
    if obj_type == "service":
        obj_name = obj.display_name
        cluster = getattr(obj, "cluster")
        if cluster:
            obj_name = f"{cluster.name}/{obj_name}"
    elif obj_type == "component":
        obj_name = obj.display_name
        service = getattr(obj, "service")
        if service:
            obj_name = f"{service.display_name}/{obj_name}"
            cluster = getattr(service, "cluster")
            if cluster:
                obj_name = f"{cluster.name}/{obj_name}"
    else:
        obj_name = obj.name

    return obj_name


def get_or_create_audit_obj(
        object_id: str,
        object_name: str,
        object_type: str,
) -> AuditObject:
    audit_object = AuditObject.objects.filter(
        object_id=object_id,
        object_type=object_type,
    ).first()

    if not audit_object:
        audit_object = AuditObject.objects.create(
            object_id=object_id,
            object_name=object_name,
            object_type=object_type,
        )

    return audit_object


def get_audit_object_from_resp(response: Response, obj_type: str) -> AuditObject | None:
    response_has_data = response and response.data and response.data.get("id")
    if not response_has_data:
        return None

    obj = AUDIT_OBJECT_TYPE_TO_MODEL_MAP[obj_type].objects.get(pk=response.data["id"])
    object_name = get_obj_name(obj=obj, obj_type=obj_type)

    return get_or_create_audit_obj(
        object_id=response.data["id"],
        object_name=object_name,
        object_type=obj_type,
    )


def get_service_name(service: ClusterObject) -> str:
    if service.display_name:
        return service.display_name

    if service.prototype.name:
        return service.prototype.name

    return str(service)


def response_case(
    obj_type: AuditObjectType,
    operation_type: AuditLogOperationType,
    response: Response | None = None,
    operation_aux_str: str | None = None,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = _get_audit_operation(
        obj_type=obj_type,
        operation_type=operation_type,
        operation_aux_str=operation_aux_str,
    )
    audit_object = get_audit_object_from_resp(response=response, obj_type=obj_type)

    return audit_operation, audit_object


def obj_pk_case(
    obj_type: AuditObjectType,
    operation_type: AuditLogOperationType,
    obj_pk: int,
    obj_name: str | None = None,
    operation_aux_str: str | None = None,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = _get_audit_operation(
        obj_type=obj_type,
        operation_type=operation_type,
        operation_aux_str=operation_aux_str,
    )
    obj = AUDIT_OBJECT_TYPE_TO_MODEL_MAP[obj_type].objects.filter(pk=obj_pk).first()
    if obj:
        obj_name = get_obj_name(obj=obj, obj_type=obj_type) or obj.name

    audit_object = get_or_create_audit_obj(
        object_id=obj_pk,
        object_name=obj_name,
        object_type=obj_type,
    )

    return audit_operation, audit_object


def action_case(path: list[str, ...]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (
            [obj_type, obj_pk, "action", action_pk, "run"]
            | [_, _, obj_type, obj_pk, "action", action_pk, "run"]
            | [_, _, _, _, obj_type, obj_pk, "action", action_pk, "run"]
        ):
            audit_operation = AuditOperation(
                name="{action_display_name} action launched",
                operation_type=AuditLogOperationType.Update,
            )

            action = Action.objects.filter(pk=action_pk).first()
            if action:
                audit_operation.name = audit_operation.name.format(
                    action_display_name=action.display_name
                )

            obj = PATH_STR_TO_OBJ_CLASS_MAP[obj_type].objects.filter(pk=obj_pk).first()
            if obj:
                object_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP[PATH_STR_TO_OBJ_CLASS_MAP[obj_type]]
                audit_object = get_or_create_audit_obj(
                    object_id=obj_pk,
                    object_name=get_obj_name(obj=obj, obj_type=object_type),
                    object_type=object_type,
                )
            else:
                audit_object = None

    return audit_operation, audit_object


def upgrade_case(path: list[str, ...]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case [obj_type, obj_pk, "upgrade", upgrade_pk, "do"]:
            audit_operation = AuditOperation(
                name="Upgraded to",
                operation_type=AuditLogOperationType.Update,
            )

            upgrade = Upgrade.objects.filter(pk=upgrade_pk).first()
            if not upgrade:
                return audit_operation, None

            if upgrade.action:
                audit_operation.name = f"{upgrade.action.display_name} upgrade launched"
            else:
                audit_operation.name = f"{audit_operation.name} {upgrade.name}"

            obj = PATH_STR_TO_OBJ_CLASS_MAP[obj_type].objects.filter(pk=obj_pk).first()
            object_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP[PATH_STR_TO_OBJ_CLASS_MAP[obj_type]]
            if obj:
                audit_object = get_or_create_audit_obj(
                    object_id=obj_pk,
                    object_name=get_obj_name(obj=obj, obj_type=object_type),
                    object_type=object_type,
                )
            else:
                audit_object = None

    return audit_operation, audit_object


def task_case(path: list[str, ...]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["task", task_pk, action] | ["task", task_pk, action]:
            audit_operation, audit_object = _task_case(task_pk=task_pk, action=action)

    return audit_operation, audit_object
