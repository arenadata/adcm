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
from core.types import ClusterID, HostID, ShortObjectInfo
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy

from cm.models import Cluster, ClusterObject, Host, HostComponent, ServiceComponent


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
            ClusterObject.objects.select_related("prototype")
            .prefetch_related("servicecomponent_set__prototype")
            .filter(cluster_id__in=cluster_ids)
        )

        result = defaultdict(list)
        for service in services:
            result[service.cluster_id].append(
                (
                    ShortObjectInfo(id=service.pk, name=service.name),
                    tuple(
                        ShortObjectInfo(id=component.pk, name=component.name)
                        for component in service.servicecomponent_set.all()
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
    with atomic():
        add_hosts_to_cluster(cluster_id=cluster_id, hosts=hosts, db=ClusterDB)

        re_apply_object_policy(Cluster.objects.get(id=cluster_id))

    status_service.reset_hc_map()

    return hosts


def retrieve_clusters_topology(cluster_ids: Iterable[ClusterID]) -> Generator[ClusterTopology, None, None]:
    return build_clusters_topology(cluster_ids=cluster_ids, db=ClusterDB)


def retrieve_clusters_objects_maintenance_mode(cluster_ids: Iterable[ClusterID]) -> MaintenanceModeOfObjects:
    return MaintenanceModeOfObjects(
        hosts={
            host_id: ObjectMaintenanceModeState(mm)
            for host_id, mm in Host.objects.values_list("id", "maintenance_mode").filter(cluster_id__in=cluster_ids)
        },
        services={
            service_id: ObjectMaintenanceModeState(mm)
            for service_id, mm in ClusterObject.objects.values_list("id", "_maintenance_mode").filter(
                cluster_id__in=cluster_ids
            )
        },
        components={
            component_id: ObjectMaintenanceModeState(mm)
            for component_id, mm in ServiceComponent.objects.values_list("id", "_maintenance_mode").filter(
                cluster_id__in=cluster_ids
            )
        },
    )
