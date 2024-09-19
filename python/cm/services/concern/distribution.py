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

from collections import defaultdict
from copy import copy
from itertools import chain
from operator import itemgetter
from typing import Iterable, TypeAlias

from core.cluster.types import ClusterTopology
from core.types import (
    ADCMCoreType,
    ClusterID,
    ComponentID,
    ConcernID,
    CoreObjectDescriptor,
    HostID,
    HostProviderID,
    ObjectID,
    ServiceID,
)
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import (
    Cluster,
    ClusterObject,
    ConcernItem,
    ConcernType,
    Host,
    HostComponent,
    HostProvider,
    ServiceComponent,
)

# PUBLIC redistribute_issues_and_flags


TopologyObjectMap: TypeAlias = dict[ADCMCoreType, tuple[ObjectID, ...]]
OwnObjectConcernMap: TypeAlias = dict[ADCMCoreType, dict[ObjectID, set[ConcernID]]]
AffectedObjectConcernMap: TypeAlias = OwnObjectConcernMap
ProviderHostMap: TypeAlias = dict[HostProviderID, set[HostID]]


def redistribute_issues_and_flags(topology: ClusterTopology) -> None:
    topology_objects: TopologyObjectMap = {
        ADCMCoreType.CLUSTER: (topology.cluster_id,),
        ADCMCoreType.SERVICE: tuple(topology.services),
        ADCMCoreType.COMPONENT: tuple(topology.component_ids),
        ADCMCoreType.HOST: tuple(topology.hosts),
    }

    provider_host_ids_mapping: ProviderHostMap = defaultdict(set)
    for host_id, provider_id in Host.objects.values_list("id", "provider_id").filter(
        id__in=topology_objects[ADCMCoreType.HOST]
    ):
        provider_host_ids_mapping[provider_id].add(host_id)

    # Step #1. Get own concerns of all related objects
    objects_concerns = _retrieve_concerns_of_objects_in_topology(
        topology_objects=topology_objects, provider_host_mapping=provider_host_ids_mapping
    )

    if not objects_concerns:
        # nothing to redistribute, expected that no links will be found too
        return

    # Step #2. Calculate new concern relations
    concern_links: AffectedObjectConcernMap = _calculate_concerns_distribution_for_topology(
        topology=topology, objects_concerns=objects_concerns
    )

    # Step #3. Link objects to concerns
    _relink_concerns_to_objects_in_db(
        concern_links=concern_links,
        topology_objects=topology_objects,
        hosts_existing_concerns=objects_concerns.get(ADCMCoreType.HOST, {}),
    )


def _retrieve_concerns_of_objects_in_topology(
    topology_objects: TopologyObjectMap, provider_host_mapping: ProviderHostMap
) -> OwnObjectConcernMap:
    objects_concerns = _get_own_concerns_of_objects(
        with_types=(ConcernType.ISSUE, ConcernType.FLAG),
        clusters=topology_objects[ADCMCoreType.CLUSTER],
        hosts=topology_objects[ADCMCoreType.HOST],
        services=topology_objects[ADCMCoreType.SERVICE],
        components=topology_objects[ADCMCoreType.COMPONENT],
        hostproviders=set(provider_host_mapping),
    )

    if not objects_concerns:
        # nothing to redistribute, expected that no links will be found too
        return objects_concerns

    if ADCMCoreType.HOSTPROVIDER in objects_concerns:
        # Merge HostProvider concerns to corresponding hosts so the passing of concerns will go smoothly
        # without need to extract provider's concerns for each host-component relation
        for provider_id, concerns in objects_concerns.pop(ADCMCoreType.HOSTPROVIDER).items():
            for host_id in provider_host_mapping[provider_id]:
                objects_concerns[ADCMCoreType.HOST][host_id] |= concerns

    return objects_concerns


def _calculate_concerns_distribution_for_topology(
    topology: ClusterTopology, objects_concerns: OwnObjectConcernMap
) -> AffectedObjectConcernMap:
    concern_links: dict[ADCMCoreType, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))

    cluster_own_concerns: set[int] = objects_concerns.get(ADCMCoreType.CLUSTER, {}).get(topology.cluster_id, set())
    concern_links[ADCMCoreType.CLUSTER][topology.cluster_id] = copy(cluster_own_concerns)

    hosts_existing_concerns = objects_concerns.get(ADCMCoreType.HOST, {})

    for service_id, service_topology in topology.services.items():
        concerns_from_service = objects_concerns.get(ADCMCoreType.SERVICE, {}).get(service_id, set())
        concern_links[ADCMCoreType.SERVICE][service_id] |= cluster_own_concerns | concerns_from_service

        for component_id, component_topology in service_topology.components.items():
            concerns_from_component = objects_concerns.get(ADCMCoreType.COMPONENT, {}).get(component_id, set())

            concerns_from_hosts = set()
            for host_id in set(component_topology.hosts):
                host_related_concerns = hosts_existing_concerns.get(host_id, set())
                concerns_from_hosts |= host_related_concerns

                concern_links[ADCMCoreType.HOST][host_id] |= (
                    cluster_own_concerns | concerns_from_service | concerns_from_component | host_related_concerns
                )

            # "push" concerns up a "tree"
            concern_links[ADCMCoreType.COMPONENT][component_id] = (
                cluster_own_concerns | concerns_from_service | concerns_from_component | concerns_from_hosts
            )
            concern_links[ADCMCoreType.SERVICE][service_id] |= concerns_from_component | concerns_from_hosts

        concern_links[ADCMCoreType.CLUSTER][topology.cluster_id] |= concern_links[ADCMCoreType.SERVICE][service_id]

    return concern_links


def _relink_concerns_to_objects_in_db(
    concern_links: dict[ADCMCoreType, dict[ObjectID, set[int]]],
    topology_objects: TopologyObjectMap,
    hosts_existing_concerns: dict[ObjectID, set[int]],
) -> None:
    # ADCMCoreType.HOST is a special case, because we really don't want to delete host/provider-related concerns
    for core_type in (ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT):
        orm_model = core_type_to_model(core_type)
        id_field = f"{orm_model.__name__.lower()}_id"
        m2m_model = orm_model.concerns.through

        # Delete all concern relations for objects in question
        m2m_model.objects.filter(**{f"{id_field}__in": topology_objects[core_type]}).exclude(
            concernitem__type=ConcernType.LOCK
        ).delete()

        # ... and create them again
        m2m_model.objects.bulk_create(
            (
                m2m_model(concernitem_id=concern_id, **{id_field: object_id})
                for object_id, concerns in concern_links[core_type].items()
                for concern_id in concerns
            )
        )

    # handle hosts links
    m2m_model = Host.concerns.through
    hostprovider_hierarchy_concerns = set(chain.from_iterable(hosts_existing_concerns.values()))
    # Delete all cluster/service/component related concern links, but keep host/hostprovider ones:
    # thou we could recreate those concerns too, but it doesn't make much sense.
    (
        m2m_model.objects.filter(host_id__in=topology_objects[ADCMCoreType.HOST])
        .exclude(Q(concernitem_id__in=hostprovider_hierarchy_concerns) | Q(concernitem__type=ConcernType.LOCK))
        .delete()
    )

    # create only cluster/service/component related concern links
    m2m_model.objects.bulk_create(
        (
            m2m_model(concernitem_id=concern_id, host_id=host_id)
            for host_id, concerns in concern_links[ADCMCoreType.HOST].items()
            for concern_id in (concerns - hostprovider_hierarchy_concerns)
        )
    )


# PUBLIC distribute_concern_on_related_objects

ConcernRelatedObjects: TypeAlias = dict[ADCMCoreType, set[ObjectID]]


def distribute_concern_on_related_objects(owner: CoreObjectDescriptor, concern_id: ConcernID):
    distribution_targets = _find_concern_distribution_targets(owner=owner)
    _add_concern_links_to_objects_in_db(targets=distribution_targets, concern_id=concern_id)


def _find_concern_distribution_targets(owner: CoreObjectDescriptor) -> ConcernRelatedObjects:
    """
    Find objects that should be affected by appeared concern on given objects considering HC.
    """
    targets: ConcernRelatedObjects = defaultdict(set)

    targets[owner.type].add(owner.id)

    match owner.type:
        case ADCMCoreType.CLUSTER:
            targets[ADCMCoreType.SERVICE] |= set(
                ClusterObject.objects.values_list("id", flat=True).filter(cluster_id=owner.id)
            )
            targets[ADCMCoreType.COMPONENT] |= set(
                ServiceComponent.objects.values_list("id", flat=True).filter(cluster_id=owner.id)
            )
            targets[ADCMCoreType.HOST] |= set(
                HostComponent.objects.values_list("host_id", flat=True).filter(cluster_id=owner.id)
            )

        case ADCMCoreType.SERVICE:
            targets[ADCMCoreType.HOST] |= set(
                HostComponent.objects.values_list("host_id", flat=True).filter(service_id=owner.id)
            )
            targets[ADCMCoreType.COMPONENT] |= set(
                ServiceComponent.objects.values_list("id", flat=True).filter(service_id=owner.id)
            )
            targets[ADCMCoreType.CLUSTER].add(
                ClusterObject.objects.values_list("cluster_id", flat=True).get(id=owner.id)
            )

        case ADCMCoreType.COMPONENT:
            cluster_id, service_id = ServiceComponent.objects.values_list("cluster_id", "service_id").get(id=owner.id)

            targets[ADCMCoreType.CLUSTER].add(cluster_id)
            targets[ADCMCoreType.SERVICE].add(service_id)
            targets[ADCMCoreType.HOST] |= set(
                HostComponent.objects.values_list("host_id", flat=True).filter(component_id=owner.id)
            )

        case ADCMCoreType.HOST:
            hc_records = tuple(
                HostComponent.objects.values("cluster_id", "service_id", "component_id").filter(host_id=owner.id)
            )
            if hc_records:
                targets[ADCMCoreType.CLUSTER].add(hc_records[0]["cluster_id"])
                targets[ADCMCoreType.SERVICE].update(map(itemgetter("service_id"), hc_records))
                targets[ADCMCoreType.COMPONENT].update(map(itemgetter("component_id"), hc_records))

        case ADCMCoreType.HOSTPROVIDER:
            targets[ADCMCoreType.HOST] |= set(Host.objects.values_list("id", flat=True).filter(provider_id=owner.id))

            hc_records = tuple(
                HostComponent.objects.values("cluster_id", "service_id", "component_id").filter(
                    host_id__in=targets.get(ADCMCoreType.HOST, ())
                )
            )
            if hc_records:
                targets[ADCMCoreType.CLUSTER].add(hc_records[0]["cluster_id"])
                targets[ADCMCoreType.SERVICE].update(map(itemgetter("service_id"), hc_records))
                targets[ADCMCoreType.COMPONENT].update(map(itemgetter("component_id"), hc_records))

        case _:
            message = f"Direct concerns distribution isn't implemented for {owner.type}"
            raise NotImplementedError(message)

    return targets


# PUBLIC lock/unlock multiple objects


def lock_objects(targets: Iterable[CoreObjectDescriptor], lock_id: ConcernID) -> None:
    grouped_by_type = defaultdict(set)
    for target in targets:
        grouped_by_type[target.type].add(target.id)

    _add_concern_links_to_objects_in_db(targets=grouped_by_type, concern_id=lock_id)


def unlock_objects(targets: Iterable[CoreObjectDescriptor], lock_id: ConcernID) -> None:
    grouped_by_type = defaultdict(set)
    for target in targets:
        grouped_by_type[target.type].add(target.id)

    _remove_concern_links_from_objects_in_db(targets=grouped_by_type, concern_id=lock_id)


# PROTECTED generic-purpose methods


def _add_concern_links_to_objects_in_db(targets: ConcernRelatedObjects, concern_id: ConcernID) -> None:
    for core_type, ids in targets.items():
        orm_model = core_type_to_model(core_type)
        id_field = f"{orm_model.__name__.lower()}_id"
        m2m_model = orm_model.concerns.through

        m2m_model.objects.bulk_create(
            objs=(m2m_model(concernitem_id=concern_id, **{id_field: object_id}) for object_id in ids),
            ignore_conflicts=True,
        )


def _remove_concern_links_from_objects_in_db(targets: ConcernRelatedObjects, concern_id: ConcernID) -> None:
    for core_type, ids in targets.items():
        orm_model = core_type_to_model(core_type)
        id_field = f"{orm_model.__name__.lower()}_id"
        m2m_model = orm_model.concerns.through

        m2m_model.objects.filter(concernitem_id=concern_id, **{f"{id_field}__in": ids}).delete()


def _get_own_concerns_of_objects(
    with_types: Iterable[ConcernType],
    *,
    clusters: Iterable[ClusterID] = (),
    services: Iterable[ServiceID] = (),
    components: Iterable[ComponentID] = (),
    hosts: Iterable[HostID] = (),
    hostproviders: Iterable[HostProviderID] = (),
) -> dict[ADCMCoreType, dict[ObjectID, set[int]]]:
    existing_concerns_qs = (
        ConcernItem.objects.select_related("owner_type")
        .filter(type__in=with_types)
        .filter(
            Q(owner_id__in=clusters, owner_type=ContentType.objects.get_for_model(Cluster))
            | Q(owner_id__in=hosts, owner_type=ContentType.objects.get_for_model(Host))
            | Q(owner_id__in=services, owner_type=ContentType.objects.get_for_model(ClusterObject))
            | Q(owner_id__in=components, owner_type=ContentType.objects.get_for_model(ServiceComponent))
            | Q(owner_id__in=hostproviders, owner_type=ContentType.objects.get_for_model(HostProvider))
        )
    )

    # Those are own concerns of objects defined by type and ID
    # except Host which set of concerns will also contain HostProvider concerns
    objects_concerns: dict[ADCMCoreType, dict[int, set[int]]] = defaultdict(lambda: defaultdict(set))
    for concern in existing_concerns_qs.all():
        concern: ConcernItem
        objects_concerns[model_name_to_core_type(concern.owner_type.model)][concern.owner_id].add(concern.id)

    return objects_concerns
