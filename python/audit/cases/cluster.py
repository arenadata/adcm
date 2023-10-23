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

from audit.cases.common import (
    get_obj_name,
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
from cm.models import Cluster, ClusterBind, ClusterObject, Host, Prototype
from django.db.models import Model
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

CONFIGURATION_STR = "configuration "


def get_export_cluster_and_service_names(response: Response, view: GenericAPIView) -> tuple[str, str]:
    cluster, service = None, None
    cluster_name, service_name = "", ""
    if response and response.data and isinstance(response.data.get("export_cluster_id"), int):
        cluster = Cluster.objects.filter(
            pk=response.data["export_cluster_id"],
        ).first()
    elif isinstance(view.request.data.get("export_cluster_id"), int):
        cluster = Cluster.objects.filter(
            pk=view.request.data["export_cluster_id"],
        ).first()

    if response and response.data and isinstance(response.data.get("export_service_id"), int):
        service = ClusterObject.objects.filter(
            pk=response.data["export_service_id"],
        ).first()
    elif isinstance(view.request.data.get("export_service_id"), int):
        service = ClusterObject.objects.filter(
            pk=view.request.data["export_service_id"],
        ).first()

    if cluster is not None:
        cluster_name = cluster.name
    if service is not None:
        service_name = get_service_name(service)

    return cluster_name, service_name


def make_export_name(cluster_name: str, service_name: str) -> str:
    export_name = ""
    if cluster_name and service_name:
        export_name = f"{cluster_name}/{service_name}"
    elif cluster_name:
        export_name = f"{cluster_name}"
    return export_name


# pylint: disable-next=too-many-locals,too-many-branches,too-many-statements
def cluster_case(
    path: list[str, ...],
    view: GenericAPIView,
    response: Response,
    deleted_obj: Model,
    api_version: int = 1,
) -> tuple[AuditOperation, AuditObject | None]:
    audit_operation = None
    audit_object = None

    match path:
        case ["cluster"] | ["clusters"]:
            audit_operation, audit_object = response_case(
                obj_type=AuditObjectType.CLUSTER,
                operation_type=AuditLogOperationType.CREATE,
                response=response,
            )

        case ["cluster", cluster_pk] | ["clusters", cluster_pk]:
            if view.request.method == "DELETE":
                deleted_obj: Cluster
                operation_type = AuditLogOperationType.DELETE
                obj = deleted_obj
            else:
                operation_type = AuditLogOperationType.UPDATE
                obj = Cluster.objects.filter(pk=cluster_pk).first()

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.CLUSTER.capitalize()} {operation_type}d",
                operation_type=operation_type,
            )
            if obj:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.CLUSTER,
                )
            else:
                audit_object = None

        case ["cluster", cluster_pk, "host"] | ["clusters", cluster_pk, "hosts"]:
            host_fqdn = ""

            if response and response.data:
                if api_version == 1:
                    host_fqdn = response.data["fqdn"]
                else:
                    host_fqdn = response.data["name"]

            if "host_id" in view.request.data:
                host = Host.objects.filter(pk=view.request.data["host_id"]).first()
                if host:
                    host_fqdn = host.fqdn

            operation_name = f"{host_fqdn} host added".strip()

            audit_operation = AuditOperation(
                name=operation_name,
                operation_type=AuditLogOperationType.UPDATE,
            )
            obj = Cluster.objects.filter(pk=cluster_pk).first()
            if obj is not None:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.CLUSTER,
                )

        case ["cluster", cluster_pk, "host", host_pk] | ["clusters", cluster_pk, "hosts", host_pk] | [
            "cluster",
            cluster_pk,
            "host",
            host_pk,
            "maintenance-mode",
        ] | ["clusters", cluster_pk, "hosts", host_pk, "maintenance-mode"]:
            if view.request.method == "DELETE":
                name = "host removed"
                if not isinstance(deleted_obj, Host):
                    deleted_obj = Host.objects.filter(pk=host_pk).first()

                if deleted_obj:
                    name = f"{deleted_obj.fqdn} host removed"

                obj = Cluster.objects.filter(pk=cluster_pk).first()
                if obj:
                    audit_object = get_or_create_audit_obj(
                        object_id=cluster_pk,
                        object_name=obj.name,
                        object_type=AuditObjectType.CLUSTER,
                    )
                else:
                    audit_object = None
            else:
                obj = Host.objects.filter(pk=host_pk).first()
                name = f"{AuditObjectType.HOST.capitalize()} updated"
                if obj:
                    audit_object = get_or_create_audit_obj(
                        object_id=host_pk,
                        object_name=obj.name,
                        object_type=AuditObjectType.HOST,
                    )

            audit_operation = AuditOperation(
                name=name,
                operation_type=AuditLogOperationType.UPDATE,
            )

        case ["cluster", cluster_pk, "hostcomponent"] | ["clusters", cluster_pk, "mapping"]:
            audit_operation = AuditOperation(
                name="Host-Component map updated",
                operation_type=AuditLogOperationType.UPDATE,
            )
            obj = Cluster.objects.filter(pk=cluster_pk).first()
            if obj is not None:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.CLUSTER,
                )

        case ["cluster", cluster_pk, "import"] | ["clusters", cluster_pk, "imports"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.CLUSTER,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=cluster_pk,
                operation_aux_str="import ",
            )

        case ["cluster", cluster_pk, "service"] | ["clusters", cluster_pk, "services"]:
            service_display_name = ""

            if api_version == 1:
                if response and response.data and response.data.get("display_name"):
                    service_display_name = response.data["display_name"]

                if "service_id" in view.request.data:
                    service = ClusterObject.objects.filter(pk=view.request.data["service_id"]).first()
                    if service:
                        service_display_name = get_service_name(service)

                operation_name = f"{service_display_name} service added".strip()

            elif api_version == 2:
                if response and response.data:
                    service_display_name = [data["display_name"] for data in response.data]
                else:
                    service_display_name = (
                        Prototype.objects.filter(
                            pk__in=[data["prototype_id"] for data in view.request.data if "prototype_id" in data]
                        )
                        .order_by("pk")
                        .values_list("display_name", flat=True)
                    )

                service_display_name = f"[{', '.join(service_display_name)}]"
                operation_name = f"{service_display_name} service(s) added"

            else:
                raise ValueError("Unexpected api version")

            audit_operation = AuditOperation(
                name=operation_name,
                operation_type=AuditLogOperationType.UPDATE,
            )

            obj = Cluster.objects.filter(pk=cluster_pk).first()
            if obj is not None:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.CLUSTER,
                )

        case ["cluster", cluster_pk, "service", service_pk] | ["clusters", cluster_pk, "services", service_pk]:
            audit_operation = AuditOperation(
                name="service removed",
                operation_type=AuditLogOperationType.UPDATE,
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
                audit_operation.name = f"{service_display_name} {audit_operation.name}"

            obj = Cluster.objects.filter(pk=cluster_pk).first()
            if obj is not None:
                audit_object = get_or_create_audit_obj(
                    object_id=cluster_pk,
                    object_name=obj.name,
                    object_type=AuditObjectType.CLUSTER,
                )

        case ["cluster", _, "service", service_pk, "bind"]:
            service = ClusterObject.objects.get(pk=service_pk)
            cluster_name, service_name = get_export_cluster_and_service_names(response, view)
            audit_operation = AuditOperation(
                name=f"{AuditObjectType.SERVICE.capitalize()} bound to "
                f"{make_export_name(cluster_name, service_name)}".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=get_obj_name(obj=service, obj_type=AuditObjectType.SERVICE),
                object_type=AuditObjectType.SERVICE,
            )

        case ["cluster", _, "service", service_pk, "bind", _]:
            service = ClusterObject.objects.get(pk=service_pk)
            cluster_name, service_name = "", ""
            if deleted_obj and isinstance(deleted_obj, ClusterBind):
                cluster_name = deleted_obj.source_cluster.name
                if deleted_obj.source_service:
                    deleted_obj: ClusterBind
                    service_name = get_service_name(deleted_obj.source_service)

            audit_operation = AuditOperation(
                name=f"{make_export_name(cluster_name, service_name)} unbound".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_or_create_audit_obj(
                object_id=service_pk,
                object_name=get_obj_name(obj=service, obj_type=AuditObjectType.SERVICE),
                object_type=AuditObjectType.SERVICE,
            )

        case (
            ["cluster", _, "service", service_pk, "config", "history"]
            | ["cluster", _, "service", service_pk, "config", "history", _, "restore"]
            | ["service", service_pk, "config", "history"]
            | ["service", service_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.SERVICE,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=service_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case (["cluster", _, "service", service_pk, "import"] | ["service", service_pk, "import"]):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.SERVICE,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=service_pk,
                operation_aux_str="import ",
            )

        case ["cluster", _, "service", service_pk, "maintenance-mode"]:
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.SERVICE,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=service_pk,
            )

        case (
            ["cluster", _, "service", _, "component", component_pk, "config", "history"]
            | [
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
            ]
            | ["service", _, "component", component_pk, "config", "history"]
            | ["service", _, "component", component_pk, "config", "history", _, "restore"]
            | ["component", component_pk, "config", "history"]
            | ["component", component_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.COMPONENT,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=component_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case ["cluster", cluster_pk, "bind"]:
            obj = Cluster.objects.get(pk=cluster_pk)
            cluster_name, service_name = get_export_cluster_and_service_names(response, view)

            audit_operation = AuditOperation(
                name=f"{AuditObjectType.CLUSTER.capitalize()} bound to "
                f"{make_export_name(cluster_name, service_name)}".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )
            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.CLUSTER,
            )

        case ["cluster", cluster_pk, "bind", _]:
            obj = Cluster.objects.get(pk=cluster_pk)

            cluster_name, service_name = "", ""
            if deleted_obj and isinstance(deleted_obj, ClusterBind):
                cluster_name = deleted_obj.source_cluster.name
                if deleted_obj.source_service:
                    deleted_obj: ClusterBind
                    service_name = get_service_name(deleted_obj.source_service)

            audit_operation = AuditOperation(
                name=f"{make_export_name(cluster_name, service_name)} unbound".strip(),
                operation_type=AuditLogOperationType.UPDATE,
            )

            audit_object = get_or_create_audit_obj(
                object_id=cluster_pk,
                object_name=obj.name,
                object_type=AuditObjectType.CLUSTER,
            )

        case (
            ["cluster", cluster_pk, "config", "history"]
            | ["cluster", cluster_pk, "config", "history", _, "restore"]
            | ["clusters", cluster_pk, "configs"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.CLUSTER,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=cluster_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case (
            ["cluster", _, "host", host_pk, "config", "history"]
            | ["cluster", _, "host", host_pk, "config", "history", _, "restore"]
            | ["provider", _, "host", host_pk, "config", "history"]
            | ["provider", _, "host", host_pk, "config", "history", _, "restore"]
            | ["host", host_pk, "config", "history"]
            | ["host", host_pk, "config", "history", _, "restore"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.HOST,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=host_pk,
                operation_aux_str=CONFIGURATION_STR,
            )

        case (
            ["component", component_pk]
            | ["component", component_pk, _]
            | ["cluster", _, "service", _, "component", component_pk, "maintenance-mode"]
            | ["service", _, "component", component_pk, "maintenance-mode"]
        ):
            audit_operation, audit_object = obj_pk_case(
                obj_type=AuditObjectType.COMPONENT,
                operation_type=AuditLogOperationType.UPDATE,
                obj_pk=component_pk,
            )

    return audit_operation, audit_object
