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
from django.db.models import Model
from django.views import View
from rest_framework.response import Response

from audit.cases.cluster import get_export_cluster_and_service_names, make_export_name
from audit.cases.common import get_obj_name, get_or_create_audit_obj, get_service_name
from audit.models import (
    AuditLogOperationType,
    AuditObject,
    AuditObjectType,
    AuditOperation,
)
from cm.models import Cluster, ClusterBind, ClusterObject


def service_case(  # pylint: disable=too-many-branches
    path: list[str, ...],
    view: View,
    response: Response,
    deleted_obj: Model,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["service"]:
            audit_operation = AuditOperation(
                name="service added",
                operation_type=AuditLogOperationType.Update,
            )

            cluster_pk = None
            if response and response.data:
                if response.data.get("cluster_id"):
                    cluster_pk = response.data["cluster_id"]

                if response.data.get("display_name"):
                    audit_operation.name = f"{response.data['display_name']} {audit_operation.name}"
            elif view.request.data.get("cluster_id"):
                cluster_pk = view.request.data["cluster_id"]

            if cluster_pk:
                cluster = Cluster.objects.filter(pk=cluster_pk).first()
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=cluster.name,
                    object_type=AuditObjectType.Cluster,
                )
            else:
                audit_object = None

        case ["service", service_pk] | ["service", service_pk, "maintenance-mode"]:
            deleted_obj: ClusterObject
            if view.request.method == "DELETE":
                audit_operation = AuditOperation(
                    name="service removed",
                    operation_type=AuditLogOperationType.Update,
                )
            else:
                audit_operation = AuditOperation(
                    name=f"{AuditObjectType.Service.capitalize()} {AuditLogOperationType.Update}d",
                    operation_type=AuditLogOperationType.Update,
                )

            if deleted_obj and "maintenance-mode" not in path:
                audit_operation.name = f"{deleted_obj.display_name} {audit_operation.name}"
                audit_object = get_or_create_audit_obj(
                    object_id=deleted_obj.cluster.pk,
                    object_name=deleted_obj.cluster.name,
                    object_type=AuditObjectType.Cluster,
                )
            else:
                obj = ClusterObject.objects.filter(pk=service_pk).first()
                if obj:
                    audit_object = get_or_create_audit_obj(
                        object_id=service_pk,
                        object_name=get_obj_name(obj=obj, obj_type=AuditObjectType.Service),
                        object_type=AuditObjectType.Service,
                    )
                else:
                    audit_object = None

        case ["service", service_pk, "bind"]:
            obj = ClusterObject.objects.get(pk=service_pk)
            cluster_name, service_name = get_export_cluster_and_service_names(response, view)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.Service.capitalize()} "
                f"bound to {make_export_name(cluster_name, service_name)}".strip(),
                operation_type=AuditLogOperationType.Update,
            )

            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=get_obj_name(obj=obj, obj_type=AuditObjectType.Service),
                object_type=AuditObjectType.Service,
            )

        case ["service", service_pk, "bind", _]:
            obj = ClusterObject.objects.get(pk=service_pk)

            cluster_name, service_name = "", ""
            if deleted_obj and isinstance(deleted_obj, ClusterBind):
                cluster_name = deleted_obj.source_cluster.name
                if deleted_obj.source_service:
                    deleted_obj: ClusterBind
                    service_name = get_service_name(deleted_obj.source_service)

            audit_operation = AuditOperation(
                name=f"{make_export_name(cluster_name, service_name)} unbound".strip(),
                operation_type=AuditLogOperationType.Update,
            )

            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=get_obj_name(obj=obj, obj_type=AuditObjectType.Service),
                object_type=AuditObjectType.Service,
            )

    return audit_operation, audit_object
