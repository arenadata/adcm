from django.db.models import Model
from django.views import View
from rest_framework.response import Response

from audit.cases.common import get_or_create_audit_obj, get_service_name
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Cluster, ClusterObject


def service_case(
        path: list[str, ...],
        view: View,
        response: Response,
        deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["service"]:
            cluster = None
            audit_operation = AuditOperation(
                name="service added",
                operation_type=AuditLogOperationType.Update,
            )

            if response and response.data:
                if response.data.get("cluster_id"):
                    cluster = Cluster.objects.filter(pk=response.data["cluster_id"]).first()

                if response.data.get("display_name"):
                    audit_operation.name = f"{response.data['display_name']} {audit_operation.name}"

            if cluster:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster.pk,
                    object_name=cluster.name,
                    object_type=AuditObjectType.Cluster,
                )
            else:
                audit_object = None

        case ["service", _]:
            deleted_obj: ClusterObject
            audit_operation = AuditOperation(
                name=f"{deleted_obj.display_name} service removed",
                operation_type=AuditLogOperationType.Update,
            )
            audit_object = get_or_create_audit_obj(
                object_id=deleted_obj.cluster.pk,
                object_name=deleted_obj.cluster.name,
                object_type=AuditObjectType.Cluster,
            )

        case ["service", service_pk, "bind"]:
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                     f"bound to {{export_cluster_name}}/{get_service_name(obj)}",
                operation_type=AuditLogOperationType.Update,
            )

            export_cluster_name = None
            if response and response.data:
                export_cluster_name = response.data["export_cluster_name"]
            elif "export_cluster_id" in view.request.data:
                cluster = Cluster.objects.filter(pk=view.request.data["export_cluster_id"]).first()
                if cluster:
                    export_cluster_name = cluster.name

            if export_cluster_name:
                audit_operation.name = audit_operation.name.format(
                    export_cluster_name=export_cluster_name,
                )

            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

        case ["service", service_pk, "bind", _]:
            obj = ClusterObject.objects.get(pk=service_pk)
            audit_operation = AuditOperation(
                name=f"{{export_cluster_name}}/{get_service_name(obj)} unbound",
                operation_type=AuditLogOperationType.Update,
            )

            export_cluster_name = ""
            if deleted_obj:
                if isinstance(deleted_obj, tuple):
                    export_cluster_name = deleted_obj[0].cluster.name
                else:
                    deleted_obj: ClusterObject
                    export_cluster_name = deleted_obj.cluster.name

            audit_operation.name = audit_operation.name.format(
                export_cluster_name=export_cluster_name,
            )

            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=obj.name,
                object_type=AuditObjectType.Service,
            )

    return audit_operation, audit_object
