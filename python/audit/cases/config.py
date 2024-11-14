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

from contextlib import suppress

from cm.models import ConfigHostGroup, Host, ObjectConfig
from cm.utils import get_obj_type
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from audit.cases.common import get_audit_cm_object_from_path_info, get_obj_name, get_or_create_audit_obj
from audit.models import (
    MODEL_TO_AUDIT_OBJECT_TYPE_MAP,
    PATH_STR_TO_OBJ_CLASS_MAP,
    AuditLogOperationType,
    AuditObject,
    AuditOperation,
)


def config_case(
    path: list[str],
    view: ViewSet,
    response: Response,
    deleted_obj: ConfigHostGroup,
) -> tuple[AuditOperation, AuditObject | None, str | None]:
    audit_operation = None
    audit_object = None
    operation_name = None

    match path:
        case ["config-log"]:
            audit_operation = AuditOperation(
                name=f"configuration {AuditLogOperationType.UPDATE}d",
                operation_type=AuditLogOperationType.UPDATE,
            )

            config = None
            if response:
                config = response.data.serializer.instance.obj_ref
            elif view.request.data.get("obj_ref"):
                config = ObjectConfig.objects.filter(pk=view.request.data["obj_ref"]).first()

            if config:
                object_type = ContentType.objects.get_for_model(config.object).name
                object_type = get_obj_type(obj_type=object_type)
                object_name = get_obj_name(obj=config.object, obj_type=object_type)

                audit_object = get_or_create_audit_obj(
                    object_id=config.object.pk,
                    object_name=object_name,
                    object_type=object_type,
                )
                object_type = "ADCM" if object_type == "adcm" else object_type.capitalize()

                operation_name = f"{object_type} {audit_operation.name}"
            else:
                audit_object = None

        case ["group-config", host_group_pk, "config", _, "config-log"]:
            audit_operation = AuditOperation(
                name=f"configuration group {AuditLogOperationType.UPDATE}d",
                operation_type=AuditLogOperationType.UPDATE,
            )

            config = None
            if response:
                config = response.data.serializer.instance.obj_ref
                if getattr(config, "config_host_group", None):
                    config = config.config_host_group
            elif view.request.data.get("obj_ref"):
                config = ObjectConfig.objects.filter(pk=view.request.data["obj_ref"]).first()

            if not config:
                config = ConfigHostGroup.objects.filter(pk=host_group_pk).first()

            if config:
                object_type = ContentType.objects.get_for_model(config.object).name
                object_type = get_obj_type(object_type)
                object_name = get_obj_name(obj=config.object, obj_type=object_type)

                audit_object = get_or_create_audit_obj(
                    object_id=config.object.pk,
                    object_name=object_name,
                    object_type=object_type,
                )
                object_type = object_type.capitalize()
                if isinstance(config, ConfigHostGroup):
                    object_type = config.name

                operation_name = f"{object_type} {audit_operation.name}"
            else:
                audit_object = None

        case [*_, owner_type, owner_pk, "config-groups"]:
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )
            audit_operation = AuditOperation(
                name="configuration group created",
                operation_type=AuditLogOperationType.CREATE,
            )

            if response and (new_object_pk := response.data.get("id", None)):
                name = ConfigHostGroup.objects.values("name").get(pk=new_object_pk)["name"]
                audit_operation.name = f"{name} configuration group created"

        case [*_, owner_type, owner_pk, "config-groups", host_group_pk]:
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )
            if deleted_obj:
                group_name = deleted_obj.name
            else:
                host_group = ConfigHostGroup.objects.values("name").filter(pk=host_group_pk).first()
                group_name = host_group["name"] if host_group else ""

            if view.action in {"update", "partial_update"}:
                audit_operation = AuditOperation(
                    name=f"{group_name} configuration group updated".strip(),
                    operation_type=AuditLogOperationType.UPDATE,
                )
            else:
                audit_operation = AuditOperation(
                    name=f"{group_name} configuration group deleted".strip(),
                    operation_type=AuditLogOperationType.DELETE,
                )

        case [*_, "group-config"]:
            if view.action == "create":
                operation_type = AuditLogOperationType.CREATE
            elif view.action in {"update", "partial_update"}:
                operation_type = AuditLogOperationType.UPDATE
            else:
                operation_type = AuditLogOperationType.DELETE

            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            if response:
                if view.action == "destroy":
                    deleted_obj: ConfigHostGroup
                    obj = deleted_obj
                else:
                    obj = response.data.serializer.instance

                object_type = get_obj_type(obj.object_type.name)
                object_name = get_obj_name(obj=obj.object, obj_type=object_type)
                audit_object = get_or_create_audit_obj(
                    object_id=obj.object.id,
                    object_name=object_name,
                    object_type=object_type,
                )
                operation_name = f"{obj.name} {audit_operation.name}"
            else:
                audit_object = None

        case ["group-config", host_group_pk]:
            if view.action in {"update", "partial_update"}:
                operation_type = AuditLogOperationType.UPDATE
            else:
                operation_type = AuditLogOperationType.DELETE

            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            if response:
                if view.action == "destroy":
                    deleted_obj: ConfigHostGroup
                    obj = deleted_obj
                else:
                    obj = response.data.serializer.instance
            else:
                obj = ConfigHostGroup.objects.filter(pk=host_group_pk).first()

            if obj:
                object_type = get_obj_type(obj.object_type.name)
                object_name = get_obj_name(obj=obj.object, obj_type=object_type)
                audit_object = get_or_create_audit_obj(
                    object_id=obj.object.id,
                    object_name=object_name,
                    object_type=object_type,
                )
                operation_name = f"{obj.name} {audit_operation.name}"
            else:
                audit_object = None

        case ["group-config", config_group_pk, "host"]:
            config_group = ConfigHostGroup.objects.get(pk=config_group_pk)
            audit_operation = AuditOperation(
                name=f"host added to {config_group.name} configuration group",
                operation_type=AuditLogOperationType.UPDATE,
            )
            object_type = get_obj_type(config_group.object_type.name)
            object_name = get_obj_name(obj=config_group.object, obj_type=object_type)
            audit_object = get_or_create_audit_obj(
                object_id=config_group.object.pk,
                object_name=object_name,
                object_type=object_type,
            )

            fqdn = None
            if response:
                fqdn = response.data["fqdn"]
            elif "id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["id"]).first()
                if host:
                    fqdn = host.fqdn

            if fqdn:
                audit_operation.name = f"{fqdn} {audit_operation.name}"

        case [*_, owner_type, owner_pk, "config-groups", config_group_pk, "hosts"]:
            config_group = ConfigHostGroup.objects.filter(pk=config_group_pk).first()
            name_suffix = f"{config_group.name if config_group else ''} configuration group".strip()
            audit_operation = AuditOperation(
                name=f"host added to {name_suffix}",
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )

            if "host_id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["host_id"]).values("fqdn").first()
                if host:
                    audit_operation.name = f"{host['fqdn']} {audit_operation.name}"

        case [*_, owner_type, owner_pk, "config-groups", config_group_pk, "hosts", host_pk]:
            config_group = ConfigHostGroup.objects.filter(pk=config_group_pk).first()
            name_suffix = f"{config_group.name if config_group else ''} configuration group".strip()
            audit_operation = AuditOperation(
                name=f"host removed from {name_suffix}",
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_audit_cm_object_from_path_info(
                object_type_from_path=owner_type, object_pk_from_path=owner_pk
            )

            with suppress(ValueError):
                host = Host.objects.filter(pk=int(host_pk)).values("fqdn").first()
                if host:
                    audit_operation.name = f"{host['fqdn']} {audit_operation.name}"

        case ["group-config", config_group_pk, "host", host_pk]:
            config_group = ConfigHostGroup.objects.get(pk=config_group_pk)
            obj = Host.objects.get(pk=host_pk)
            audit_operation = AuditOperation(
                name=f"{obj.fqdn} host removed from {config_group.name} configuration group",
                operation_type=AuditLogOperationType.UPDATE,
            )
            object_type = get_obj_type(config_group.object_type.name)
            object_name = get_obj_name(obj=config_group.object, obj_type=object_type)
            audit_object = get_or_create_audit_obj(
                object_id=config_group.object.pk,
                object_name=object_name,
                object_type=object_type,
            )
        case [*_, obj_type, obj_pk, "config-groups", pk, "configs"]:
            operation_type = AuditLogOperationType.UPDATE
            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            host_group = ConfigHostGroup.objects.filter(pk=pk).first()
            operation_name = f"{host_group.name} {audit_operation.name}" if host_group else audit_operation.name
            obj = PATH_STR_TO_OBJ_CLASS_MAP[obj_type].objects.filter(pk=obj_pk).first()
            if obj:
                object_type = MODEL_TO_AUDIT_OBJECT_TYPE_MAP[PATH_STR_TO_OBJ_CLASS_MAP[obj_type]]
                audit_object = get_or_create_audit_obj(
                    object_id=obj_pk,
                    object_name=get_obj_name(obj=obj, obj_type=object_type),
                    object_type=object_type,
                )

    return audit_operation, audit_object, operation_name
