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

from typing import Iterable

from cm import errors, models
from cm.converters import orm_object_to_core_descriptor
from cm.legacy.api import check_license
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern.cases import (
    recalculate_own_concerns_on_add_clusters,
    recalculate_own_concerns_on_add_services,
)
from cm.legacy.services.concern.distribution import redistribute_issues_and_flags
from cm.legacy.services.status.notify import reset_hc_map
from cm.legacy.status_api import notify_about_redistributed_concerns_from_maps
from core import result as r
from core import types
from django.db import transaction
from django.db.models import Count, QuerySet
from rbac.models import re_apply_object_policy
import core


def create_cluster(
    prototype: models.Prototype, name: str, description: str, config_service: core.config.ConfigService
) -> models.Cluster:
    if prototype.type != types.ADCMCoreType.CLUSTER:
        raise errors.AdcmEx("OBJ_TYPE_ERROR", f"Prototype type should be cluster, not {prototype.type}")

    check_license(prototype)

    with transaction.atomic():
        cluster = _create_cluster(
            prototype=prototype, name=name, description=description, config_service=config_service
        )
        _create_ansible_config(cluster_id=cluster.pk)

        added, removed = {}, {}
        if recalculate_own_concerns_on_add_clusters(cluster):
            added, removed = redistribute_issues_and_flags(topology=retrieve_cluster_topology(cluster.pk))

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

    return cluster


def create_services_from_prototypes(
    cluster: models.Cluster, prototype_ids: Iterable[types.PrototypeID], config_service: core.config.ConfigService
) -> tuple[models.Service, ...]:
    result = _validate_service_prototypes(cluster=cluster, ids=prototype_ids)
    match result:
        case r.Fail(err):
            raise err

    prototypes = result.value

    with transaction.atomic():
        services = _bulk_add_services_to_cluster(cluster=cluster, prototypes=prototypes, config_service=config_service)

        recalculate_own_concerns_on_add_services(
            cluster=cluster,
            services=services.prefetch_related("components").all(),  # refresh values from db to update `config` field
        )
        added, removed = redistribute_issues_and_flags(topology=retrieve_cluster_topology(cluster.pk))

        re_apply_object_policy(apply_object=cluster)

    reset_hc_map()
    notify_about_redistributed_concerns_from_maps(added=added, removed=removed)

    return tuple(services)


# COPIED FROM api_v2.service.utils WITHIN ADCM-7090 (minor changes applied)
def _validate_service_prototypes(
    cluster: models.Cluster, ids: Iterable[types.PrototypeID]
) -> r.Success[tuple[models.Prototype, ...]] | r.Fail[errors.AdcmEx]:
    prototypes = tuple(models.Prototype.objects.filter(pk__in=ids).select_related("bundle"))

    if not prototypes:
        return r.Fail(errors.AdcmEx(code="PROTOTYPE_NOT_FOUND"))

    if {proto.type for proto in prototypes}.difference({models.ObjectType.SERVICE.value}):
        return r.Fail(
            errors.AdcmEx(code="OBJ_TYPE_ERROR", msg=f"All prototypes must be `{models.ObjectType.SERVICE.value}` type")
        )

    if "unaccepted" in {proto.license for proto in prototypes}:
        return r.Fail(errors.AdcmEx(code="LICENSE_ERROR", msg="All licenses must be accepted"))

    if models.Service.objects.filter(prototype__in=prototypes, cluster=cluster).exists():
        return r.Fail(errors.AdcmEx(code="SERVICE_CONFLICT"))

    if {proto.bundle.pk for proto in prototypes if not proto.shared}.difference({cluster.prototype.bundle.pk}):
        return r.Fail(
            errors.AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f"Some service prototype does not belong to bundle "
                f'"{cluster.prototype.bundle.name}" {cluster.prototype.version}',
            )
        )

    return r.Success(prototypes)


# COPIED FROM api_v2.service.utils WITHIN ADCM-7090 (minor changes applied)
#
# This function is not truly bulk add due to sequential config init,
# but for now it's too costly to implement bulk config init
def _bulk_add_services_to_cluster(
    cluster: models.Cluster, prototypes: tuple[models.Prototype, ...], config_service: core.config.ConfigService
) -> QuerySet[models.Service]:
    models.Service.objects.bulk_create(objs=[models.Service(cluster=cluster, prototype=proto) for proto in prototypes])
    services = (
        models.Service.objects.annotate(config_count=Count("prototype__prototypeconfig"))
        .filter(cluster=cluster, prototype__in=prototypes)
        .select_related("prototype")
    )

    for target in services:
        descriptor = orm_object_to_core_descriptor(target)
        config_service.create_initial_configuration_if_required(owner=descriptor)

    service_proto_service_map = {service.prototype.pk: service for service in services}
    models.Component.objects.bulk_create(
        objs=[
            models.Component(
                cluster=cluster, service=service_proto_service_map[prototype.parent.pk], prototype=prototype
            )
            for prototype in models.Prototype.objects.filter(
                type=models.ObjectType.COMPONENT, parent__in=prototypes
            ).select_related("parent")
        ]
    )
    components = (
        models.Component.objects.annotate(config_count=Count("prototype__prototypeconfig"))
        .filter(cluster=cluster, service__in=services, config_count__gt=0)
        .select_related("prototype")
    )
    for target in components:
        descriptor = orm_object_to_core_descriptor(target)
        config_service.create_initial_configuration_if_required(owner=descriptor)

    return services


# TRANSITIONED FROM cm.api WITHIN ADCM-7090,
# must be moved to services level

# There's no good place to place it for now.
# Since it's more about API than `cm.legacy.services.job`, it'll live here.
# But don't stick to it.
DEFAULT_FORKS_AMOUNT: str = "5"


def _create_cluster(
    prototype: models.Prototype, name: str, description: str, config_service: core.config.ConfigService
):
    cluster = models.Cluster.objects.create(prototype=prototype, name=name, description=description)
    descriptor = types.CoreObjectDescriptor(id=cluster.pk, type=types.ADCMCoreType.CLUSTER)
    config_service.create_initial_configuration_if_required(owner=descriptor)
    return cluster


def _create_ansible_config(cluster_id: types.ClusterID):
    models.AnsibleConfig.objects.create(
        value={"defaults": {"forks": DEFAULT_FORKS_AMOUNT}},
        object_id=cluster_id,
        object_type=models.ContentType.objects.get_for_model(models.Cluster),
    )


# TRANSITIONED END
