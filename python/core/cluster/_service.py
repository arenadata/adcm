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

from dataclasses import dataclass

from core.cluster._maintenance_mode import calculate_maintenance_mode_for_cluster_objects
from core.cluster._operations import find_children_excluding_hosts
from core.cluster._repo import ClusterRepoI
from core.cluster._types import ClusterTopology
from core.types import (
    ClusterID,
    ClusterObjectDesc,
    MaintenanceModeOfObjects,
    MaintenanceModeOfObjectsWithReason,
)


@dataclass(slots=True)
class ClusterService:
    repo: ClusterRepoI

    def retrieve_topology(self, cluster_id: ClusterID) -> ClusterTopology:
        return self.repo.get_topology_for_cluster(cluster_id=cluster_id)

    def find_objects_in_hierarchy(
        self, start_from: ClusterObjectDesc, topology: ClusterTopology
    ) -> tuple[ClusterObjectDesc, ...]:
        children = find_children_excluding_hosts(target=start_from, topology=topology)
        return (start_from, *children)

    def retrieve_own_maintenance_mode(self, cluster_id: ClusterID) -> MaintenanceModeOfObjects:
        return self.repo.get_clusters_objects_own_maintenance_mode(cluster_ids=(cluster_id,))

    def calculate_maintenance_mode(
        self, topology: ClusterTopology, objects_own_mm: MaintenanceModeOfObjects
    ) -> MaintenanceModeOfObjectsWithReason:
        return calculate_maintenance_mode_for_cluster_objects(topology=topology, own_maintenance_mode=objects_own_mm)
