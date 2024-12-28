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
from typing import Collection, Generator, Iterable, Protocol

from core.cluster.operations import add_hosts_to_cluster, build_clusters_topology
from core.cluster.types import (
    ClusterTopology,
    HostClusterPair,
    HostComponentEntry,
    MaintenanceModeOfObjects,
    ObjectMaintenanceModeState,
)
from core.types import ADCMCoreType, ClusterID, CoreObjectDescriptor, HostID, ShortObjectInfo
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy

from cm.models import Cluster, Component, ConcernCause, Host, HostComponent, Service
from cm.services.concern import create_issue, delete_issue
from cm.status_api import notify_about_new_concern


class ClusterDB:
    __slots__ = ()

    @staticmethod
    def get_host_cluster_pairs_for_hosts(hosts: Iterable[HostID]) -> Iterable[HostClusterPair]:
        return (
            HostClusterPair(host_id=host, cluster_id=cluster_)
            for host, cluster_ in Host.objects.filter(pk__in=hosts).values_list("id", "cluster_id").all()
        )

    @staticmethod
    def set_cluster_id_for_hosts(cluster_id: ClusterID, hosts: Iterable[HostID]) -> None:
        Host.objects.filter(pk__in=hosts).update(cluster_id=cluster_id)

    @staticmethod
    def get_clusters_hosts(cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, list[ShortObjectInfo]]:
        query = Host.objects.filter(cluster_id__in=cluster_ids).values_list("id", "fqdn", "cluster_id")

        result = defaultdict(list)
        for host_id, name, cluster_id in query:
            result[cluster_id].append(ShortObjectInfo(id=host_id, name=name))

        return result

    @staticmethod
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
            result[service.cluster_id].append(
                (
                    ShortObjectInfo(id=service.pk, name=service.name),
                    tuple(
                        ShortObjectInfo(id=component.pk, name=component.name) for component in service.components.all()
                    ),
                )
            )

        return result

    @staticmethod
    def get_host_component_entries(cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, list[HostComponentEntry]]:
        query = HostComponent.objects.filter(cluster_id__in=cluster_ids).values_list(
            "host_id", "component_id", "cluster_id"
        )

        result = defaultdict(list)
        for host_id, component_id, cluster_id in query:
            result[cluster_id].append(HostComponentEntry(host_id=host_id, component_id=component_id))

        return result


class _StatusServerService(Protocol):
    def reset_hc_map(self) -> None:
        ...


def perform_host_to_cluster_map(
    cluster_id: int, hosts: Collection[int], status_service: _StatusServerService
) -> Collection[int]:
    # this import should be resolved later:
    # concerns management should be passed in here the same way as `status_service`,
    # because it's a dependency that shouldn't be directly set
    from cm.services.concern.checks import cluster_mapping_has_issue_orm_version
    from cm.services.concern.distribution import distribute_concern_on_related_objects

    with atomic():
        add_hosts_to_cluster(cluster_id=cluster_id, hosts=hosts, db=ClusterDB)
        cluster = Cluster.objects.get(id=cluster_id)
        cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)

        concern_id = None
        related_objects = {}
        if not cluster_mapping_has_issue_orm_version(cluster=cluster):
            delete_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
        elif not cluster.get_own_issue(cause=ConcernCause.HOSTCOMPONENT):
            concern = create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
            concern_id = concern.id
            related_objects = distribute_concern_on_related_objects(owner=cluster_cod, concern_id=concern.id)

        re_apply_object_policy(apply_object=cluster)

    status_service.reset_hc_map()
    if concern_id:
        notify_about_new_concern(concern_id=concern_id, related_objects=related_objects)

    return hosts


def retrieve_host_component_entries(cluster_id: ClusterID) -> set[HostComponentEntry]:
    return {
        HostComponentEntry(**db_entry)
        for db_entry in HostComponent.objects.values("host_id", "component_id").filter(cluster_id=cluster_id)
    }


def retrieve_cluster_topology(cluster_id: ClusterID) -> ClusterTopology:
    return next(retrieve_multiple_clusters_topology(cluster_ids=(cluster_id,)))


def retrieve_multiple_clusters_topology(cluster_ids: Iterable[ClusterID]) -> Generator[ClusterTopology, None, None]:
    return build_clusters_topology(cluster_ids=cluster_ids, db=ClusterDB)


def retrieve_related_cluster_topology(orm_object: Cluster | Service | Component | Host) -> ClusterTopology:
    if isinstance(orm_object, Cluster):
        cluster_id = orm_object.id
    elif isinstance(orm_object, (Service, Component, Host)) and orm_object.cluster_id:
        cluster_id = orm_object.cluster_id
    else:
        message = f"Can't detect cluster variables for {orm_object}"
        raise RuntimeError(message)

    return next(retrieve_multiple_clusters_topology([cluster_id]))


def retrieve_clusters_objects_maintenance_mode(cluster_ids: Iterable[ClusterID]) -> MaintenanceModeOfObjects:
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
