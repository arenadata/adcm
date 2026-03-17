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

from core.types import ClusterID, ClusterObjectDesc
from django.db.transaction import atomic
import core


@dataclass(slots=True)
class ResetBeforeUpgradeCluster:
    cluster_service: core.cluster.ClusterService
    upgrade_service: core.upgrade.UpgradeService

    @atomic
    def do(self, target: ClusterObjectDesc, cluster_id: ClusterID) -> None:
        topology = self.cluster_service.retrieve_topology(cluster_id=cluster_id)
        affected_objects = self.cluster_service.find_objects_in_hierarchy(start_from=target, topology=topology)
        self.upgrade_service.reset_before_upgrade(targets=affected_objects)
