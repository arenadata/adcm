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

from cm.api import version_in
from cm.errors import raise_adcm_ex
from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    PrototypeExport,
    PrototypeImport,
)
from cm.status_api import get_obj_status


def get_cluster_export_dict(cluster: Cluster, export_cluster: Cluster, prototype_import: PrototypeImport | None = None):
    bind_list = []
    for bind in ClusterBind.objects.filter(cluster=cluster, source_cluster=export_cluster):
        bind_list.append(get_bind_dict(bind=bind, cluster=bind.source_cluster, service=bind.source_service))

    import_cluster_dict = None
    if prototype_import:
        import_cluster_dict = {
            "prototype_id": cluster.prototype.id,
            "is_multibind": prototype_import.multibind if prototype_import else False,
            "is_required": prototype_import.required if prototype_import else False,
        }

    return {
        "id": cluster.id,
        "cluster_name": cluster.name,
        "cluster_status": get_obj_status(obj=cluster),
        "cluster_state": cluster.state,
        "import_cluster": import_cluster_dict,
        "import_services": None,
        "binds": bind_list,
    }


def get_bind_dict(bind: ClusterBind, cluster: Cluster, service: ClusterObject | None = None) -> dict:
    return {
        "id": bind.pk,
        "cluster_id": cluster.pk,
        "service_id": service.pk if service else None,
        "prototype_id": service.prototype.pk if service else cluster.prototype.pk,
    }


def get_imports(obj: Cluster | ClusterObject) -> dict:
    objects = {}
    checked_export_proto = {}
    cluster = obj
    if isinstance(obj, ClusterObject):
        cluster = obj.cluster

    for proto_import in PrototypeImport.objects.filter(prototype=obj.prototype):
        for export in PrototypeExport.objects.filter(prototype__name=proto_import.name):
            if checked_export_proto.get(export.prototype.pk):
                continue
            checked_export_proto[export.prototype.pk] = True

            if not version_in(version=export.prototype.version, ver=proto_import):
                continue

            if export.prototype.type == "cluster":
                for export_cluster in Cluster.objects.filter(prototype=export.prototype):
                    objects[cluster.id] = get_cluster_export_dict(
                        cluster=cluster, export_cluster=export_cluster, prototype_import=proto_import
                    )

            if export.prototype.type == "service":
                for service in ClusterObject.objects.filter(prototype=export.prototype):
                    service_list = (
                        objects[service.cluster.id]["import_services"] if objects.get(service.cluster.id) else []
                    )

                    service_list.append(
                        {
                            "prototype_id": service.prototype.id,
                            "name": service.name,
                            "display_name": service.display_name,
                            "version": service.version,
                            "is_required": proto_import.required,
                            "is_multibind": proto_import.multibind,
                        }
                    )

                    if not objects.get(service.cluster.id):
                        objects[service.cluster.id] = get_cluster_export_dict(
                            cluster=cluster, export_cluster=service.cluster
                        )

                    objects[service.cluster.id]["import_services"] = service_list

    return objects.values()


def cook_data_for_multibind(validated_data: list, obj: Cluster | ClusterObject) -> list:
    bind_data = []

    for item in validated_data["bind"]:
        if item.get("service_id"):
            export_obj = ClusterObject.obj.get(pk=item["service_id"])
        else:
            export_obj = Cluster.obj.get(pk=item["cluster_id"])

        proto_import = PrototypeImport.objects.filter(name=export_obj.name, prototype=obj.prototype).first()

        if not proto_import:
            raise_adcm_ex(code="INVALID_INPUT", msg="Needed import doesn't exist")

        bind_data.append(
            {
                "import_id": proto_import.pk,
                "export_id": {"cluster_id": item["cluster_id"], "service_id": item.get("service_id")},
            }
        )

        return bind_data
