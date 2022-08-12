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
# pylint: disable=too-many-lines


# pylint: disable=too-many-lines
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
from cm.models import (
    ADCM,
    Bundle,
    Cluster,
    ClusterBind,
    ClusterObject,
    GroupConfig,
    Host,
    HostProvider,
    ServiceComponent,
    TaskLog,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import Model
from django.http.response import Http404
from django.views.generic.base import View
from rbac.models import Group, Policy, Role, User
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.status import HTTP_403_FORBIDDEN, is_success


def _get_audit_object_from_resp(res: Response, obj_type: str) -> Optional[AuditObject]:
    if res and res.data and res.data.get("id") and res.data.get("name"):
        audit_object = _get_or_create_audit_obj(
            object_id=res.data["id"],
            object_name=res.data["name"],
            object_type=obj_type,
        )
    else:
        audit_object = None

    return audit_object


def _get_object_type_from_resp(audit_operation: AuditOperation, resp: Response) -> str:
    if audit_operation.object_type == "config log":
        object_type: str = ContentType.objects.get_for_model(
            resp.data.serializer.instance.obj_ref.object
        ).name
    else:
        object_type: str = resp.data.serializer.instance.object_type.name

    return object_type


def _task_case(task_pk: str, action: str) -> Tuple[AuditOperation, AuditObject]:
    if action == "cancel":
        action = f"{action}l"

    obj = TaskLog.objects.get(pk=task_pk)
    obj_type = obj.object_type.name

    if obj_type == "adcm":
        obj_type = obj_type.upper()
    else:
        obj_type = obj_type.capitalize()

    if obj.action:
        action_name = obj.action.display_name
    else:
        action_name = "task"

    audit_operation = AuditOperation(
        name=f"{obj_type} {action_name} {action}ed",
        operation_type=AuditLogOperationType.Update,
    )
    audit_object = _get_or_create_audit_obj(
        object_id=task_pk,
        object_name=obj.task_object.name,
        object_type=obj.object_type.name,
    )

    return audit_operation, audit_object


def _get_service_name(service: ClusterObject) -> str:
    if service.display_name:
        return service.display_name

    if service.prototype.name:
        return service.prototype.name

    return str(service)


def _get_obj_type(obj_type: str) -> str:
    if obj_type == "cluster object":
        return "service"
    elif obj_type == "service component":
        return "component"

    return obj_type


def _get_or_create_audit_obj(object_id: int, object_name: str, object_type: str) -> AuditObject:
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


# pylint: disable-next=too-many-statements,too-many-branches,too-many-locals
def _get_audit_operation_and_object(
        view: View, res: Response, deleted_obj: Model
) -> Tuple[Optional[AuditOperation], Optional[AuditObject], Optional[str]]:
    operation_name = None
    path = view.request.path.replace("/api/v1/", "")[:-1].split("/")

    match path:
        case ["stack", "upload"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.capitalize()} uploaded",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = None

        case ["stack", "load"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.capitalize()} loaded",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = _get_audit_object_from_resp(res, AuditObjectType.Bundle)

        case ["stack", "bundle", bundle_pk]:
            deleted_obj: Bundle
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.capitalize()} {AuditLogOperationType.Delete}d",
                operation_type=AuditLogOperationType.Delete,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=bundle_pk,
                object_name=deleted_obj.name,
                object_type=AuditObjectType.Bundle,
            )

        case ["stack", "bundle", bundle_pk, "update"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.capitalize()} {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Bundle.objects.get(pk=bundle_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=bundle_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Bundle,
            )

        case ["stack", "bundle", bundle_pk, "license", "accept"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Bundle.capitalize()} license accepted",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Bundle.objects.get(pk=bundle_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=bundle_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Bundle,
            )

        case ["cluster"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} "
                f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = _get_audit_object_from_resp(res, AuditObjectType.Cluster)

        case ["cluster", cluster_pk]:
            if view.request.method == "DELETE":
                deleted_obj: Cluster
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = Cluster.objects.get(pk=cluster_pk)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} {operation_type}d",
                operation_type=operation_type,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "host"]:
            audit_operation = AuditOperation(
                name="{host_fqdn} added",
                operation_type=AuditLogOperationType.Update,
            )

            host_fqdn = None
            if res and res.data:
                host_fqdn = res.data["fqdn"]

            if "host_id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["host_id"]).first()
                if host:
                    host_fqdn = host.fqdn

            if host_fqdn:
                audit_operation.name = audit_operation.name.format(host_fqdn=host_fqdn)

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "hostcomponent"]:
            audit_operation = AuditOperation(
                name="Host-Component map updated",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "import"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} "
                     f"import {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "service"]:
            audit_operation = AuditOperation(
                name="{service_display_name} service added",
                operation_type=AuditLogOperationType.Update,
            )

            service_display_name = None
            if res and res.data:
                service_display_name = res.data["display_name"]

            if "service_id" in view.request.data:
                service = ClusterObject.objects.filter(pk=view.request.data["service_id"]).first()
                if service:
                    service_display_name = _get_service_name(service)

            if service_display_name:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=service_display_name,
                )

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "service", service_pk]:
            audit_operation = AuditOperation(
                name="{service_display_name} service removed",
                operation_type=AuditLogOperationType.Update,
            )

            service_display_name = None
            if deleted_obj:
                if isinstance(deleted_obj, ClusterObject):
                    deleted_obj: ClusterObject
                    service_display_name = deleted_obj.display_name
                else:
                    service = ClusterObject.objects.filter(pk=service_pk).first()
                    if service:
                        service_display_name = _get_service_name(service)

            if service_display_name:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=service_display_name,
                )

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "service", service_pk, "bind"]:
            cluster = Cluster.objects.get(pk=cluster_pk)
            service = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} bound to "
                     f"{cluster.name}/{_get_service_name(service)}",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=service.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", cluster_pk, "service", service_pk, "bind", _]:
            cluster = Cluster.objects.get(pk=cluster_pk)
            service = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{cluster.name}/{_get_service_name(service)} unbound",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=service.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", _, "service", service_pk, "config", "history"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", _, "service", service_pk, "import"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"import {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", _, "service", _, "component", component_pk, "config", "history"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Component.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ServiceComponent.objects.get(pk=component_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=component_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Component,
            )

        case ["cluster", cluster_pk, "bind"]:
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} bound to "
                     f"{obj.name}/{{service_display_name}}",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

            service = None
            if res and res.data and res.data.get("export_service_id"):
                service = ClusterObject.objects.filter(pk=res.data["export_service_id"]).first()

            if "export_service_id" in view.request.data:
                service = ClusterObject.objects.filter(
                    pk=view.request.data["export_service_id"],
                ).first()

            if service:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=_get_service_name(service),
                )

        case ["cluster", cluster_pk, "bind", bind_pk]:
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_operation = AuditOperation(
                name=f"{obj.name}/{{service_display_name}} unbound",
                operation_type=AuditLogOperationType.Update,
            )

            service_display_name = None
            if deleted_obj:
                if isinstance(deleted_obj, ClusterObject):
                    deleted_obj: ClusterObject
                    service_display_name = _get_service_name(deleted_obj)
                else:
                    bind = ClusterBind.objects.filter(pk=bind_pk).first()
                    if bind and bind.source_service:
                        service_display_name = _get_service_name(bind.source_service)

            if service_display_name:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=service_display_name,
                )

            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case (
            ["cluster", cluster_pk, "config", "history"]
            | ["cluster", cluster_pk, "config", "history", _, "restore"]
        ):
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", _, "host", host_pk, "config", "history", _, "restore"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Host.objects.get(pk=host_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=host_pk,
                object_name=obj.fqdn,
                object_type=AuditObjectType.Host,
            )

        case [
            "cluster",
            _,
            "service",
            _,
            "component",
            component_pk,
            "config",
            "history",
            _,
            "restore",
        ]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Component.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ServiceComponent.objects.get(pk=component_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=component_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Component,
            )

        case ["cluster", _, "service", service_pk, "config", "history", _, "restore"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", _, "host", host_pk, "config", "history"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Host.objects.get(pk=host_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=host_pk,
                object_name=obj.fqdn,
                object_type=AuditObjectType.Host,
            )

        case ["config-log"] | ["group-config", _, "config", _, "config-log"]:
            audit_operation = AuditOperation(
                name=f"config log {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )

            if res:
                object_type = ContentType.objects.get_for_model(
                    res.data.serializer.instance.obj_ref.object
                ).name
                object_type = _get_obj_type(object_type)
                audit_object = _get_or_create_audit_obj(
                    object_id=res.data.serializer.instance.id,
                    object_name=str(res.data.serializer.instance),
                    object_type=object_type,
                )
                operation_name = f"{object_type.capitalize()} {audit_operation.name}"
            else:
                audit_object = None
                operation_name = audit_operation.name

        case ["group-config"]:
            if view.action == "create":
                operation_type = AuditLogOperationType.Create
            elif view.action in {"update", "partial_update"}:
                operation_type = AuditLogOperationType.Update
            else:
                operation_type = AuditLogOperationType.Delete

            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            if res:
                if view.action == "destroy":
                    deleted_obj: GroupConfig
                    obj = deleted_obj
                else:
                    obj = res.data.serializer.instance

                object_type = _get_obj_type(obj.object_type.name)
                audit_object = _get_or_create_audit_obj(
                    object_id=obj.object.id,
                    object_name=obj.object.name,
                    object_type=object_type,
                )
                operation_name = f"{obj.name} {audit_operation.name}"
            else:
                audit_object = None
                operation_name = audit_operation.name

        case ["group-config", group_config_pk]:
            if view.action in {"update", "partial_update"}:
                operation_type = AuditLogOperationType.Update
            else:
                operation_type = AuditLogOperationType.Delete

            audit_operation = AuditOperation(
                name=f"configuration group {operation_type}d",
                operation_type=operation_type,
            )
            if res:
                if view.action == "destroy":
                    deleted_obj: GroupConfig
                    obj = deleted_obj
                else:
                    obj = res.data.serializer.instance
            else:
                obj = GroupConfig.objects.filter(pk=group_config_pk).first()

            if obj:
                object_type = _get_obj_type(obj.object_type.name)
                audit_object = _get_or_create_audit_obj(
                    object_id=obj.object.id,
                    object_name=obj.object.name,
                    object_type=object_type,
                )
                operation_name = f"{obj.name} {audit_operation.name}"
            else:
                audit_object = None
                operation_name = audit_operation.name

        case ["group-config", config_group_pk, "host"]:
            config_group = GroupConfig.objects.get(pk=config_group_pk)
            audit_operation = AuditOperation(
                name=f"{{fqdn}} host added to {config_group.name} configuration group",
                operation_type=AuditLogOperationType.Update,
            )
            object_type = _get_obj_type(config_group.object_type.name)
            audit_object = _get_or_create_audit_obj(
                object_id=config_group.pk,
                object_name=config_group.object.name,
                object_type=object_type,
            )
            if res:
                audit_operation.name = audit_operation.name.format(fqdn=res.data["fqdn"])
            elif "id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["id"]).first()
                if host:
                    audit_operation.name = audit_operation.name.format(fqdn=host.fqdn)

            operation_name = audit_operation.name

        case ["group-config", config_group_pk, "host", host_pk]:
            config_group = GroupConfig.objects.get(pk=config_group_pk)
            obj = Host.objects.get(pk=host_pk)
            audit_operation = AuditOperation(
                name=f"{obj.fqdn} host removed from {config_group.name} configuration group",
                operation_type=AuditLogOperationType.Update,
            )
            object_type = _get_obj_type(config_group.object_type.name)
            audit_object = _get_or_create_audit_obj(
                object_id=config_group.pk,
                object_name=config_group.object.name,
                object_type=object_type,
            )

        case ["rbac", "group"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Group.capitalize()} "
                f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = _get_audit_object_from_resp(res, AuditObjectType.Group)

        case ["rbac", "group", group_pk]:
            if view.action == "destroy":
                deleted_obj: Group
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = Group.objects.get(pk=group_pk)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Group.capitalize()} "
                     f"{operation_type}d",
                operation_type=operation_type,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=group_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Group,
            )

        case ["rbac", "policy"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Policy.capitalize()} "
                f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = _get_audit_object_from_resp(res, AuditObjectType.Policy)

        case ["rbac", "policy", policy_pk]:
            if view.action == "destroy":
                deleted_obj: Policy
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = Policy.objects.get(pk=policy_pk)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Policy.capitalize()} "
                     f"{operation_type}d",
                operation_type=operation_type,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=policy_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Policy,
            )

        case ["rbac", "role"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Role.capitalize()} "
                     f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            audit_object = _get_audit_object_from_resp(res, AuditObjectType.Role)

        case ["rbac", "role", role_pk]:
            if view.action == "destroy":
                deleted_obj: Role
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = Role.objects.get(pk=role_pk)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Role.capitalize()} "
                     f"{operation_type}d",
                operation_type=operation_type,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=role_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Role,
            )

        case ["rbac", "user"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.User.capitalize()} "
                     f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            if res:
                audit_object = _get_or_create_audit_obj(
                    object_id=res.data["id"],
                    object_name=res.data["username"],
                    object_type=AuditObjectType.User,
                )
            else:
                audit_object = None

        case ["rbac", "user", user_pk]:
            if view.action == "destroy":
                deleted_obj: User
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = User.objects.get(pk=user_pk)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.User.capitalize()} "
                     f"{operation_type}d",
                operation_type=operation_type,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=user_pk,
                object_name=obj.username,
                object_type=AuditObjectType.User,
            )

        case ["host", host_pk] | ["provider", _, "host", host_pk]:
            deleted_obj: Host
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"{AuditLogOperationType.Delete}d",
                operation_type=AuditLogOperationType.Delete,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=host_pk,
                object_name=deleted_obj.fqdn,
                object_type=AuditObjectType.Host,
            )

        case ["host"] | ["provider", _, "host"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            if res:
                audit_object = _get_or_create_audit_obj(
                    object_id=res.data["id"],
                    object_name=res.data["fqdn"],
                    object_type=AuditObjectType.Host,
                )
            else:
                audit_object = None

        case ["provider", _, "host", host_pk, "config", "history"]:
            obj = Host.objects.get(pk=host_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=obj.pk,
                object_name=obj.fqdn,
                object_type=AuditObjectType.Host,
            )

        case ["provider"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Provider.capitalize()} "
                f"{AuditLogOperationType.Create}d",
                operation_type=AuditLogOperationType.Create,
            )
            if res:
                audit_object = _get_audit_object_from_resp(res, AuditObjectType.Provider)
            else:
                audit_object = None

        case ["provider", provider_pk]:
            deleted_obj: HostProvider
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Provider.capitalize()} "
                     f"{AuditLogOperationType.Delete}d",
                operation_type=AuditLogOperationType.Delete,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=provider_pk,
                object_name=deleted_obj.name,
                object_type=AuditObjectType.Provider,
            )

        case ["provider", provider_pk, "config", "history"]:
            obj = HostProvider.objects.get(pk=provider_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Provider.capitalize()} "
                f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                    object_id=provider_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.Provider,
                )

        case (
            ["host", host_pk, "config", "history"]
            | ["host", host_pk, "config", "history", _, "restore"]
        ):
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Host.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Host.objects.get(pk=host_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=host_pk,
                object_name=obj.fqdn,
                object_type=AuditObjectType.Host,
            )

        case ["service", _]:
            deleted_obj: ClusterObject
            audit_operation = AuditOperation(
                name=f"{deleted_obj.display_name} service removed",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = _get_or_create_audit_obj(
                object_id=deleted_obj.cluster.pk,
                object_name=deleted_obj.cluster.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["service", service_pk, "import"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"import {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["service", service_pk, "bind"]:
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"bound to {{export_cluster_name}}/{_get_service_name(obj)}",
                operation_type=AuditLogOperationType.Update,
            )

            export_cluster_name = None
            if res and res.data:
                export_cluster_name=res.data["export_cluster_name"]
            elif "export_cluster_id" in view.request.data:
                cluster = Cluster.objects.filter(pk=view.request.data["export_cluster_id"]).first()
                if cluster:
                    export_cluster_name = cluster.name

            if export_cluster_name:
                audit_operation.name = audit_operation.name.format(
                    export_cluster_name=export_cluster_name,
                )

            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["service", service_pk, "bind", _]:
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{{export_cluster_name}}/{_get_service_name(obj)} unbound",
                operation_type=AuditLogOperationType.Update,
            )

            if deleted_obj:
                if isinstance(deleted_obj, tuple):
                    export_cluster_name = deleted_obj[0].cluster.name
                else:
                    deleted_obj: ClusterObject
                    export_cluster_name = deleted_obj.cluster.name

                if export_cluster_name:
                    audit_operation.name = audit_operation.name.format(
                        export_cluster_name=export_cluster_name,
                    )

            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case (
            ["service", _, "component", component_pk, "config", "history"]
            | ["service", _, "component", component_pk, "config", "history", _, "restore"]
        ):
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Component.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ServiceComponent.objects.get(pk=component_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=component_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Component,
            )

        case (
            ["service", service_pk, "config", "history"]
            | ["service", service_pk, "config", "history", _, "restore"]
        ):
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["component", component_pk, "config", "history", _, "restore"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Component.capitalize()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ServiceComponent.objects.get(pk=component_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=component_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Component,
            )

        case ["adcm", adcm_pk, "config", "history"]:
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.ADCM.upper()} "
                     f"configuration {AuditLogOperationType.Update}d",
                operation_type=AuditLogOperationType.Update,
            )
            obj = ADCM.objects.get(pk=adcm_pk)
            audit_object = _get_or_create_audit_obj(
                object_id=adcm_pk,
                object_name=obj.name,
                object_type=AuditObjectType.ADCM,
            )

        case ["task", task_pk, action] | ["task", task_pk, action]:
            audit_operation, audit_object = _task_case(task_pk, action)

        case _:
            return None, None, None

    if not operation_name and audit_operation:
        operation_name = audit_operation.name

    return audit_operation, audit_object, operation_name


def audit(func):
    # pylint: disable=too-many-statements
    @wraps(func)
    def wrapped(*args, **kwargs):
        # pylint: disable=too-many-branches,too-many-statements

        audit_operation: AuditOperation
        audit_object: AuditObject
        operation_name: str

        error = None
        if len(args) == 2:  # for audit view methods
            view: View = args[0]
            request: Request = args[1]
        else:  # for audit has_permissions method
            view: View = args[2]
            request: Request = args[1]

        if request.method == "DELETE":
            try:
                deleted_obj = view.get_object()
            except AssertionError:
                try:
                    deleted_obj = view.get_obj(kwargs, kwargs["bind_id"])
                except AdcmEx:
                    deleted_obj = view.queryset[0]
            except (AdcmEx, Http404):  # when denied returns 404 from PermissionListMixin
                try:
                    deleted_obj = view.queryset[0]
                except TypeError:
                    if "role" in request.path:
                        deleted_obj = Role.objects.filter(pk=view.kwargs["pk"]).first()
                    else:
                        deleted_obj = None
        else:
            deleted_obj = None

        try:
            res = func(*args, **kwargs)
            if res is True:
                return res

            if res:
                status_code = res.status_code
            else:
                status_code = HTTP_403_FORBIDDEN
        except (AdcmEx, AdwpEx) as exc:
            error = exc
            res = None

            if (
                    getattr(exc, "msg", None)
                    and (
                        "doesn't exist" in exc.msg
                        or "service is not installed in specified cluster" in exc.msg
                    )
            ):
                _kwargs = None
                if "cluster_id" in kwargs:
                    _kwargs = kwargs
                elif "cluster_id" in view.kwargs:
                    _kwargs = view.kwargs

                if _kwargs:
                    deleted_obj = Cluster.objects.filter(pk=_kwargs["cluster_id"]).first()

                if "provider_id" in kwargs and "host_id" in kwargs:
                    deleted_obj = Host.objects.filter(pk=kwargs["host_id"]).first()
                elif "provider_id" in view.kwargs:
                    deleted_obj = HostProvider.objects.filter(pk=view.kwargs["provider_id"]).first()

                if "service_id" in kwargs:
                    deleted_obj = ClusterObject.objects.filter(pk=kwargs["service_id"]).first()

            if (
                    getattr(exc, "msg", None)
                    and "django model doesn't has __error_code__ attribute" in exc.msg
                    and "task_id" in kwargs
            ):
                deleted_obj = TaskLog.objects.filter(pk=kwargs["task_id"]).first()

            if not deleted_obj:
                status_code = exc.status_code
            else:  # when denied returns 404 from PermissionListMixin
                status_code = HTTP_403_FORBIDDEN
        except PermissionDenied as exc:
            status_code = HTTP_403_FORBIDDEN
            error = exc
            res = None

        audit_operation, audit_object, operation_name = _get_audit_operation_and_object(
            view,
            res,
            deleted_obj,
        )
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

        return res

    return wrapped


def mark_deleted_audit_object(instance, object_type: str):
    audit_objs = []
    for audit_obj in AuditObject.objects.filter(object_id=instance.pk, object_type=object_type):
        audit_obj.is_deleted = True
        audit_objs.append(audit_obj)

    AuditObject.objects.bulk_update(objs=audit_objs, fields=["is_deleted"])


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
    audit_object = _get_or_create_audit_obj(
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
