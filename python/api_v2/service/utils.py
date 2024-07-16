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

from typing import Literal

from cm.adcm_config.config import get_prototype_config, process_file_type
from cm.errors import AdcmEx
from cm.models import (
    ADCMEntity,
    Cluster,
    ClusterObject,
    ConfigLog,
    ObjectConfig,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from cm.services.cluster import retrieve_clusters_topology
from cm.services.concern.cases import recalculate_own_concerns_on_add_services
from cm.services.concern.distribution import redistribute_issues_and_flags
from cm.services.status.notify import reset_hc_map
from django.db import connection, transaction
from django.db.models import QuerySet
from rbac.models import re_apply_object_policy


@transaction.atomic
def bulk_add_services_to_cluster(cluster: Cluster, prototypes: QuerySet[Prototype]) -> QuerySet[ClusterObject]:
    ClusterObject.objects.bulk_create(objs=[ClusterObject(cluster=cluster, prototype=proto) for proto in prototypes])
    services = ClusterObject.objects.filter(cluster=cluster, prototype__in=prototypes).select_related("prototype")
    bulk_init_config(objects=services)

    service_proto_service_map = {service.prototype.pk: service for service in services}
    ServiceComponent.objects.bulk_create(
        objs=[
            ServiceComponent(
                cluster=cluster, service=service_proto_service_map[prototype.parent.pk], prototype=prototype
            )
            for prototype in Prototype.objects.filter(type=ObjectType.COMPONENT, parent__in=prototypes).select_related(
                "parent"
            )
        ]
    )
    components = ServiceComponent.objects.filter(cluster=cluster, service__in=services).select_related("prototype")
    bulk_init_config(objects=components)

    recalculate_own_concerns_on_add_services(
        cluster=cluster,
        services=services.prefetch_related(
            "servicecomponent_set"
        ).all(),  # refresh values from db to update `config` field
    )
    redistribute_issues_and_flags(topology=next(retrieve_clusters_topology((cluster.pk,))))

    re_apply_object_policy(apply_object=cluster)
    reset_hc_map()

    return services


def bulk_init_config(objects: QuerySet[ADCMEntity]) -> None:
    if not objects.exists():
        return

    # SQLite support. We need ids of created objects, bulk_create on SQLite does not return ids
    cursor = connection.cursor()
    cursor.execute(
        f"""INSERT INTO "cm_objectconfig" ("current", "previous") VALUES
        {', '.join(['(0, 0)'] * objects.count())} RETURNING id;"""
    )
    object_config_ids = [item[0] for item in cursor.fetchall()]
    object_configs: QuerySet[ObjectConfig] = ObjectConfig.objects.filter(pk__in=object_config_ids)

    obj_proto_conf_map = {}
    objects_to_update = []
    for obj, obj_config in zip(objects, object_configs):
        obj_proto_conf_map.setdefault(obj.pk, get_prototype_config(prototype=obj.prototype))
        obj.config = obj_config
        objects_to_update.append(obj)
    objects.model.objects.bulk_update(objs=objects_to_update, fields=["config"])

    config_logs: list[ConfigLog] = []
    for obj_conf in object_configs:
        obj = obj_conf.object
        spec, _, config, attr = obj_proto_conf_map[obj.pk]
        config_logs.append(ConfigLog(obj_ref=obj_conf, config=config, attr=attr, description="init"))
        process_file_type(obj=obj, spec=spec, conf=config)

    ConfigLog.objects.bulk_create(objs=config_logs)
    config_logs: QuerySet[ConfigLog] = (
        ConfigLog.objects.filter(obj_ref__in=object_configs)
        .order_by("-pk")
        .select_related("obj_ref")[: len(config_logs)]
    )

    object_configs: list[ObjectConfig] = []
    for config_log in config_logs:
        obj_conf = config_log.obj_ref
        obj_conf.current = config_log.pk
        object_configs.append(obj_conf)
    ObjectConfig.objects.bulk_update(objs=object_configs, fields=["current"])


def validate_service_prototypes(
    cluster: Cluster, data: list[dict[Literal["prototype_id"], int]]
) -> tuple[QuerySet[Prototype] | None, AdcmEx | None]:
    prototypes = Prototype.objects.filter(
        pk__in=[single_proto_data["prototype_id"] for single_proto_data in data]
    ).select_related("bundle")

    if not prototypes.exists():
        return None, AdcmEx(code="PROTOTYPE_NOT_FOUND")

    if {proto.type for proto in prototypes}.difference({ObjectType.SERVICE.value}):
        return None, AdcmEx(code="OBJ_TYPE_ERROR", msg=f"All prototypes must be `{ObjectType.SERVICE}` type")

    if "unaccepted" in {proto.license for proto in prototypes}:
        return None, AdcmEx(code="LICENSE_ERROR", msg="All licenses must be accepted")

    if ClusterObject.objects.filter(prototype__in=prototypes, cluster=cluster).exists():
        return None, AdcmEx(code="SERVICE_CONFLICT")

    if {proto.bundle.pk for proto in prototypes if not proto.shared}.difference({cluster.prototype.bundle.pk}):
        return None, AdcmEx(
            code="SERVICE_CONFLICT",
            msg=f"Some service prototype does not belong to bundle "
            f'"{cluster.prototype.bundle.name}" {cluster.prototype.version}',
        )

    return prototypes, None
