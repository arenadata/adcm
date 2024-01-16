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

from typing import Any, Collection, Iterable, Protocol

from core.cluster.rules import (
    check_all_hosts_exist,
    check_hosts_can_be_added_to_cluster,
)
from core.cluster.types import HostClusterPair
from core.types import ClusterID, HostID


class HostClusterDBProtocol(Protocol):
    def get_host_cluster_pairs_for_hosts(self, hosts: Iterable[HostID]) -> Iterable[HostClusterPair]:
        """Extract pairs of ids host-component for given hosts"""

    def set_cluster_id_for_hosts(self, cluster_id: ClusterID, hosts: Iterable[HostID]) -> Any:
        """Set `cluster_id` to all given hosts"""


def add_hosts_to_cluster(cluster_id: int, hosts: Collection[int], db: HostClusterDBProtocol) -> Collection[int]:
    existing_hosts: tuple[HostClusterPair, ...] = tuple(db.get_host_cluster_pairs_for_hosts(hosts))

    check_all_hosts_exist(host_candidates=hosts, existing_hosts=existing_hosts)
    check_hosts_can_be_added_to_cluster(cluster_id=cluster_id, hosts=existing_hosts)

    db.set_cluster_id_for_hosts(cluster_id, hosts)

    return hosts
