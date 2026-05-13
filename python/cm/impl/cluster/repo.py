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
from typing import Collection, Generator, Iterable, cast

from core import cluster
from core.types import (
    ActionHostGroupID,
    ADCMCoreType,
    ClusterID,
    ClusterObjectDesc,
    ComponentID,
    Descriptor,
    HostDesc,
    HostID,
    MaintenanceModeOfObjects,
    ObjectMaintenanceModeState,
    ShortObjectInfo,
)

from cm.converters import model_name_to_core_type
from cm.models import ActionHostGroup, Component, Host, HostComponent, Service


class ClusterRepo(cluster.ClusterRepoI):
    def get_topology_for_cluster(self, cluster_id: ClusterID) -> cluster.ClusterTopology:
        topologies = retrieve_multiple_topologies(cluster_ids=(cluster_id,))
        return next(topologies)

    def get_related_cluster_id(self, object_: ClusterObjectDesc | HostDesc) -> ClusterID:
        match object_:
            case Descriptor(type=ADCMCoreType.CLUSTER):
                return object_.id
            case Descriptor(type=ADCMCoreType.SERVICE):
                return Service.objects.filter(id=object_.id).values_list("cluster_id", flat=True).get()
            case Descriptor(type=ADCMCoreType.COMPONENT):
                return Component.objects.filter(id=object_.id).values_list("cluster_id", flat=True).get()
            case Descriptor(type=ADCMCoreType.HOST):
                return Host.objects.filter(id=object_.id).values_list("cluster_id", flat=True).get()

    def get_clusters_objects_own_maintenance_mode(self, cluster_ids: Iterable[ClusterID]) -> MaintenanceModeOfObjects:
        # COPIED FROM cm.legacy.services.cluster.retrieve_clusters_objects_maintenance_mode

        return MaintenanceModeOfObjects(
            hosts={
                host_id: ObjectMaintenanceModeState(mm)
                for host_id, mm in Host.objects.values_list("id", "maintenance_mode").filter(cluster_id__in=cluster_ids)
            },
            services={
                service_id: ObjectMaintenanceModeState(mm)
                for service_id, mm in Service.objects.values_list("id", "_maintenance_mode").filter(
                    cluster_id__in=cluster_ids
                )
            },
            components={
                component_id: ObjectMaintenanceModeState(mm)
                for component_id, mm in Component.objects.values_list("id", "_maintenance_mode").filter(
                    cluster_id__in=cluster_ids
                )
            },
        )

    def get_ahg_owner(self, ahg_id: ActionHostGroupID) -> ClusterObjectDesc:
        object_id, model_name = (
            ActionHostGroup.objects.filter(id=ahg_id).values_list("object_id", "object_type__model").get()
        )

        # only cluster, service or component can have AHG
        return cast(ClusterObjectDesc, Descriptor(id=object_id, type=model_name_to_core_type(model_name)))


def retrieve_multiple_topologies(cluster_ids: Iterable[ClusterID]) -> Generator[cluster.ClusterTopology, None, None]:
    hosts_in_clusters = {
        cluster_id: {host.id: host for host in hosts}
        for cluster_id, hosts in get_clusters_hosts(cluster_ids=cluster_ids).items()
    }
    services_in_clusters = get_clusters_services_with_components(cluster_ids=cluster_ids)

    hosts_on_components: dict[ClusterID, dict[ComponentID, set[HostID]]] = {
        cluster_id: defaultdict(set) for cluster_id in cluster_ids
    }
    if hosts_in_clusters:
        for cluster_id, entries in get_host_component_entries(cluster_ids=cluster_ids).items():
            for host_id, component_id in entries:
                hosts_on_components[cluster_id][component_id].add(host_id)

    return (
        cluster.ClusterTopology(
            cluster_id=cluster_id,
            hosts=hosts_in_clusters.get(cluster_id, {}),
            services={
                service.id: cluster.ServiceTopology(
                    info=service,
                    components={
                        component.id: cluster.ComponentTopology(
                            info=component,
                            hosts={
                                host_id: hosts_in_clusters[cluster_id][host_id]
                                for host_id in hosts_on_components[cluster_id][component.id]
                            },
                        )
                        for component in components
                    },
                )
                for service, components in services_in_clusters.get(cluster_id, ())
            },
        )
        for cluster_id in cluster_ids
    )


# Copied from cm.legacy.services.cluster


def get_clusters_hosts(cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, list[ShortObjectInfo]]:
    query = Host.objects.filter(cluster_id__in=cluster_ids).values_list("id", "fqdn", "cluster_id")

    result = defaultdict(list)
    for host_id, name, cluster_id in query:
        result[cluster_id].append(ShortObjectInfo(id=host_id, name=name))

    return result


def get_clusters_services_with_components(
    cluster_ids: Iterable[ClusterID],
) -> dict[ClusterID, list[tuple[ShortObjectInfo, Collection[ShortObjectInfo]]]]:
    services = (
        Service.objects.select_related("prototype")
        .prefetch_related("components__prototype")
        .filter(cluster_id__in=cluster_ids)
    )

    result = defaultdict(list)
    for service in services:
        result[service.cluster_id].append(  # pyright: ignore[reportAttributeAccessIssue]
            (
                ShortObjectInfo(id=service.pk, name=service.name),
                tuple(
                    ShortObjectInfo(id=component.pk, name=component.name)
                    for component in service.components.all()  # pyright: ignore[reportAttributeAccessIssue]
                ),
            )
        )

    return result


def get_host_component_entries(cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, list[tuple[HostID, ComponentID]]]:
    query = HostComponent.objects.filter(cluster_id__in=cluster_ids).values_list(
        "host_id", "component_id", "cluster_id"
    )

    result = defaultdict(list)
    for host_id, component_id, cluster_id in query:
        result[cluster_id].append((host_id, component_id))

    return result
