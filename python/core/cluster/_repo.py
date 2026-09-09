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
from typing import Protocol

from core.cluster._types import ClusterTopology, ExportData
from core.types import (
    ActionHostGroupID,
    ClusterBindSchema,
    ClusterHierarchyBeforeUpgradeBinds,
    ClusterID,
    ClusterObjectDesc,
    ComponentDesc,
    HostDesc,
    MaintenanceModeOfObjects,
    MaintenanceModeState,
    ServiceDesc,
    ServiceID,
)


class ClusterRepoI(Protocol):
    def get_topology_for_cluster(self, cluster_id: ClusterID) -> ClusterTopology:
        ...

    def get_clusters_topologies(self, cluster_ids: Iterable[ClusterID]) -> dict[ClusterID, ClusterTopology]:
        ...

    def get_related_cluster_id(self, object_: ClusterObjectDesc) -> ClusterID:
        # use carefully, this info is already available in many scenarios
        ...

    def get_clusters_objects_own_maintenance_mode(self, cluster_ids: Iterable[ClusterID]) -> MaintenanceModeOfObjects:
        ...

    def get_ahg_owner(self, ahg_id: ActionHostGroupID) -> ClusterObjectDesc:
        ...

    def set_maintenance_mode(self, target: ServiceDesc | ComponentDesc | HostDesc, value: MaintenanceModeState) -> bool:
        ...

    def retrieve_export_data(self, clusters: Iterable[ClusterID], services: Iterable[ServiceID]) -> ExportData:
        """
        Collects specified Clusters' and Services' data.
        Returns this data in exports format to import them to some other objects.
        """
        ...

    def create_binds(self, binds: Iterable[ClusterBindSchema], ignore_conflicts: bool) -> None:
        ...

    def delete_hierarchy_binds(self, cluster_id: ClusterID) -> None:
        ...

    def retrieve_hierarchy_before_upgrade_binds(self, cluster_id: ClusterID) -> ClusterHierarchyBeforeUpgradeBinds:
        ...
