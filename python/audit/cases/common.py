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
from audit.models import (
    AUDIT_OBJECT_TYPE_TO_MODEL_MAP,
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    PATH_STR_TO_OBJ_CLASS_MAP,
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    ClusterObject,
    JobLog,
    ServiceComponent,
    TaskLog,
    Upgrade,
)
from rest_framework.response import Response


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
    if action in ("terminate", "cancel"):
        action = "cancell"

    task = TaskLog.objects.filter(pk=task_pk).first()

    if task and task.action:
        action_name = task.action.display_name
    else:
        action_name = "Task"

    audit_operation = AuditOperation(
        name=f"{action_name} {action}ed",
        operation_type=AuditLogOperationType.UPDATE,
    )

    if task and task.task_object:
        audit_object = get_or_create_audit_obj(
            object_id=task.task_object.pk,
            object_name=task.task_object.name,
            object_type=task.object_type.name,
        )
    else:
        audit_object = None

    return audit_operation, audit_object


def _job_case(job_pk: str, version=1) -> tuple[AuditOperation, AuditObject | None]:
    job = JobLog.objects.filter(pk=job_pk).first()
    operation_name = ""

    if job:
        if job.sub_action:
            if version == 1:
                operation_name = f'Job "{job.sub_action.display_name}"'
                if job.action:
                    operation_name += f' of action "{job.action.display_name}"'
            else:
                operation_name = job.sub_action.display_name
        elif job.action:
            operation_name = job.action.display_name

    if not operation_name:
        operation_name = "Job"
    operation_name += " terminated"

    audit_operation = AuditOperation(
        name=operation_name,
        operation_type=AuditLogOperationType.UPDATE,
    )

    if job and job.task and job.task.task_object:
        audit_object = get_or_create_audit_obj(
            object_id=job.task.task_object.pk,
            object_name=job.task.task_object.name,
            object_type=job.task.object_type.name,
        )
    else:
        audit_object = None

    return audit_operation, audit_object


def get_obj_name(obj: ClusterObject | ServiceComponent | ADCMEntity, obj_type: str) -> str:
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

    if not audit_object and object_name is not None:
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
        object_id=str(obj_pk),
        object_name=obj_name,
        object_type=obj_type,
    )

    return audit_operation, audit_object


def action_case(path: list[str], api_version: int) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case (
            [obj_type, obj_pk, "action" | "actions", action_pk, "run"]
            | [_, _, obj_type, obj_pk, "action" | "actions", action_pk, "run"]
            | [_, _, _, _, obj_type, obj_pk, "action" | "actions", action_pk, "run"]
        ):
            audit_operation = AuditOperation(
                name="{action_display_name} action launched",
                operation_type=AuditLogOperationType.UPDATE,
            )

            action = Action.objects.filter(pk=action_pk).first()
            if action:
                audit_operation.name = audit_operation.name.format(action_display_name=action.display_name)
            elif api_version != 1:
                audit_operation.name = "action launched"

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

        case ["adcm", "actions", action_pk, "run"]:
            audit_operation = AuditOperation(
                name="{action_display_name} action launched",
                operation_type=AuditLogOperationType.UPDATE,
            )

            action = Action.objects.filter(pk=action_pk).first()
            if action:
                audit_operation.name = audit_operation.name.format(action_display_name=action.display_name)
            elif api_version != 1:
                audit_operation.name = "action launched"

            obj, object_type = ADCM.objects.first(), AuditObjectType.ADCM
            audit_object = get_or_create_audit_obj(
                object_id=obj.pk,
                object_name=get_obj_name(obj=obj, obj_type=object_type),
                object_type=object_type,
            )

    return audit_operation, audit_object


def upgrade_case(path: list[str]) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case [obj_type, obj_pk, "upgrade" | "upgrades", upgrade_pk, "do" | "run"]:
            upgrade = Upgrade.objects.filter(pk=upgrade_pk).first()
            if upgrade and upgrade.action:
                audit_operation_name = f"{upgrade.action.display_name} upgrade launched"
            elif upgrade:
                audit_operation_name = f"Upgraded to {upgrade.name}"
            else:
                audit_operation_name = "Upgraded to"

            audit_operation = AuditOperation(
                name=audit_operation_name,
                operation_type=AuditLogOperationType.UPDATE,
            )
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


def task_job_case(path: list[str], version=1) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["task", task_pk, action] | ["tasks", task_pk, action]:
            audit_operation, audit_object = _task_case(task_pk=task_pk, action=action)
        case ["jobs", job_pk, action]:
            audit_operation, audit_object = _job_case(job_pk=job_pk, version=version)

    return audit_operation, audit_object
