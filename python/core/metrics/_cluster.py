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

from collections.abc import Iterable
from itertools import chain

from core.cluster import ClusterService
from core.metrics._repo import ClusterMetricsRepoI
from core.metrics._types import ClusterCountsDict, ClusterMetrics, MetricsCounts
from core.status import EntityStatus, FullStatusMap, convert_to_entity_status, convert_to_service_status
from core.types import ClusterID, MaintenanceModeState


class RetrieveClusterMetrics:
    def __init__(self, repo: ClusterMetricsRepoI, cluster_service: ClusterService):
        self._repo = repo
        self._cluster_service = cluster_service

    def retrieve_metrics_many(
        self, cluster_ids: Iterable[ClusterID], status_map: FullStatusMap
    ) -> tuple[ClusterMetrics, ...]:
        resources_dict = self._repo.get_resources(cluster_ids=cluster_ids)
        counts_dict = self._retrieve_counts(cluster_ids=cluster_ids, status_map=status_map)

        return tuple(
            ClusterMetrics(**resources_dict[cluster_id], **counts_dict[cluster_id]) for cluster_id in cluster_ids
        )

    def retrieve_metrics(self, cluster_id: int, status_map: FullStatusMap) -> ClusterMetrics:
        resources_dict = self._repo.get_resources(cluster_ids=(cluster_id,))
        counts_dict = self._retrieve_counts(cluster_ids=(cluster_id,), status_map=status_map)

        return ClusterMetrics(**resources_dict[cluster_id], **counts_dict[cluster_id])

    def _retrieve_counts(
        self, cluster_ids: Iterable[ClusterID], status_map: FullStatusMap
    ) -> dict[ClusterID, ClusterCountsDict]:
        topologies = self._cluster_service.retrieve_topologies(cluster_ids=cluster_ids)
        own_mms = self._cluster_service.retrieve_own_maintenance_mode(cluster_ids=cluster_ids)
        monitorings = self._repo.get_monitorings(
            services=(s_id for s_id in chain.from_iterable(top.services for top in topologies.values()))
        )

        result = {}
        for cluster_id in cluster_ids:
            cluster_topology = topologies[cluster_id]
            service_ids = set(cluster_topology.services)
            host_ids = set(cluster_topology.hosts)

            cluster_mm = self._cluster_service.calculate_maintenance_mode(
                topology=cluster_topology, objects_own_mm=own_mms
            )
            services_mm = sum(1 for s_mm in cluster_mm.services.values() if s_mm == MaintenanceModeState.ON)
            hosts_mm = sum(1 for s_mm in cluster_mm.hosts.values() if s_mm == MaintenanceModeState.ON)

            services_statuses = [
                convert_to_service_status(
                    raw_status=status_map.get_for_service(cluster_id=cluster_id, service_id=service_id),
                    monitoring=monitorings.services[service_id],
                )
                for service_id in service_ids
            ]
            host_statuses = [
                convert_to_entity_status(raw_status=status_map.get_for_host(host_id=host_id)) for host_id in host_ids
            ]

            services_up = sum(1 for s in services_statuses if s == EntityStatus.UP)
            services_down = sum(1 for s in services_statuses if s == EntityStatus.DOWN)
            hosts_up = sum(1 for s in host_statuses if s == EntityStatus.UP)
            hosts_down = sum(1 for s in host_statuses if s == EntityStatus.DOWN)

            result[cluster_id] = ClusterCountsDict(
                services=MetricsCounts(
                    count=len(service_ids), up=services_up, down=services_down, maintenance_mode=services_mm
                ),
                hosts=MetricsCounts(count=len(host_ids), up=hosts_up, down=hosts_down, maintenance_mode=hosts_mm),
            )

        return result
