from django.db.models import Model
from django.views import View
from rest_framework.response import Response

from audit.cases.common import (
    get_or_create_audit_obj,
    get_service_name,
    obj_pk_case,
    response_case,
)
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Cluster, ClusterBind, ClusterObject, Host

CONFIGURATION_STR = "configuration "


# pylint: disable-next=too-many-locals,too-many-branches,too-many-statements
def cluster_case(
        path: list[str, ...],
        view: View,
        response: Response,
        deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["cluster"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.Cluster,
                operation_type=AuditLogOperationType.Create,
                response=response,
            )

        case ["cluster", cluster_pk]:
            if view.request.method == "DELETE":
                deleted_obj: Cluster
                operation_type = AuditLogOperationType.Delete
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.Update
                obj = Cluster.objects.filter(pk=cluster_pk).first()

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} {operation_type}d",
                operation_type=operation_type,
            )
            if obj:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.Cluster,
                )
            else:
                audit_object = None

        case ["cluster", cluster_pk, "host"]:
            audit_operation = AuditOperation(
                name="{host_fqdn} host added",
                operation_type=AuditLogOperationType.Update,
            )

            host_fqdn = None
            if response and response.data:
                host_fqdn = response.data["fqdn"]

            if "host_id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["host_id"]).first()
                if host:
                    host_fqdn = host.fqdn

            if host_fqdn:
                audit_operation.name = audit_operation.name.format(host_fqdn=host_fqdn)

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "host", host_pk]:
            deleted_obj: Host
            audit_operation = AuditOperation(
                name="host removed",
                operation_type=AuditLogOperationType.Update,
            )
            if not isinstance(deleted_obj, Host):
                deleted_obj = Host.objects.filter(pk=host_pk).first()

            if deleted_obj:
                audit_operation.name = f"{deleted_obj.fqdn} {audit_operation.name}"

            obj = Cluster.objects.filter(pk=cluster_pk).first()
            if obj:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.Cluster,
                )
            else:
                audit_object = None

        case ["cluster", cluster_pk, "hostcomponent"]:
            audit_operation = AuditOperation(
                name="Host-Component map updated",
                operation_type=AuditLogOperationType.Update,
            )
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "import"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Cluster,
                operation_type=AuditLogOperationType.Update,
                obj_pk=cluster_pk,
                operation_aux_str="import "
            )

        case ["cluster", cluster_pk, "service"]:
            audit_operation = AuditOperation(
                name="{service_display_name} service added",
                operation_type=AuditLogOperationType.Update,
            )

            service_display_name = None
            if response and response.data and response.data.get("display_name"):
                service_display_name = response.data["display_name"]

            if "service_id" in view.request.data:
                service = ClusterObject.objects.filter(pk=view.request.data["service_id"]).first()
                if service:
                    service_display_name = get_service_name(service)

            if service_display_name:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=service_display_name,
                )

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = get_or_create_audit_obj(
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
                        service_display_name = get_service_name(service)

            if service_display_name:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=service_display_name,
                )

            obj = Cluster.objects.get(pk=cluster_pk)
            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["cluster", cluster_pk, "service", service_pk, "bind"]:
            cluster = Cluster.objects.get(pk=cluster_pk)
            service = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} bound to "
                     f"{cluster.name}/{get_service_name(service)}",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=service.name,
                object_type=AuditObjectType.Service,
            )

        case ["cluster", cluster_pk, "service", service_pk, "bind", _]:
            cluster = Cluster.objects.get(pk=cluster_pk)
            service = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{cluster.name}/{get_service_name(service)} unbound",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=service.name,
                object_type=AuditObjectType.Service,
            )

        case (
            ["cluster", _, "service", service_pk, "config", "history"]
            | ["cluster", _, "service", service_pk, "config", "history", _, "restore"]
            | ["service", service_pk, "config", "history"]
            | ["service", service_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Service,
                operation_type=AuditLogOperationType.Update,
                obj_pk=service_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case (
            ["cluster", _, "service", service_pk, "import"]
            | ["service", service_pk, "import"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Service,
                operation_type=AuditLogOperationType.Update,
                obj_pk=service_pk,
                operation_aux_str="import "
            )

        case (
            ["cluster", _, "service", _, "component", component_pk, "config", "history"]
            | ["cluster", _, "service", _, "component", component_pk, "config", "history",
               _, "restore"]
            | ["service", _, "component", component_pk, "config", "history"]
            | ["service", _, "component", component_pk, "config", "history", _, "restore"]
            | ["component", component_pk, "config", "history"]
            | ["component", component_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Component,
                operation_type=AuditLogOperationType.Update,
                obj_pk=component_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case ["cluster", cluster_pk, "bind"]:
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Cluster.capitalize()} bound to "
                     f"{obj.name}/{{service_display_name}}",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

            service = None
            if response and response.data and response.data.get("export_service_id"):
                service = ClusterObject.objects.filter(
                    pk=response.data["export_service_id"],
                ).first()

            if "export_service_id" in view.request.data:
                service = ClusterObject.objects.filter(
                    pk=view.request.data["export_service_id"],
                ).first()

            if service:
                audit_operation.name = audit_operation.name.format(
                    service_display_name=get_service_name(service),
                )

        case ["cluster", cluster_pk, "bind", bind_pk]:
            obj = Cluster.objects.get(pk=cluster_pk)
            audit_operation = AuditOperation(
                name=f"{obj.name}/{{service_display_name}} unbound",
                operation_type=AuditLogOperationType.Update,
            )

            service_display_name = ""
            if deleted_obj:
                if isinstance(deleted_obj, ClusterObject):
                    deleted_obj: ClusterObject
                    service_display_name = get_service_name(deleted_obj)
                else:
                    bind = ClusterBind.objects.filter(pk=bind_pk).first()
                    if bind and bind.source_service:
                        service_display_name = get_service_name(bind.source_service)

            audit_operation.name = audit_operation.name.format(
                service_display_name=service_display_name,
            )

            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Cluster,
            )

        case (
            ["cluster", cluster_pk, "config", "history"]
            | ["cluster", cluster_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Cluster,
                operation_type=AuditLogOperationType.Update,
                obj_pk=cluster_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case (
            ["cluster", _, "host", host_pk, "config", "history"]
            | ["cluster", _, "host", host_pk, "config", "history", _, "restore"]
            | ["provider", _, "host", host_pk, "config", "history"]
            | ["host", host_pk, "config", "history"]
            | ["host", host_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.Host,
                operation_type=AuditLogOperationType.Update,
                obj_pk=host_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

    return audit_operation, audit_object
