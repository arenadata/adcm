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

from operator import attrgetter
from typing import Collection

from core.cluster import (
    HostAlreadyBoundError,
    HostBelongsToAnotherClusterError,
    HostClusterPair,
    HostDoesNotExistError,
)


def check_all_hosts_exist(host_candidates: Collection[int], existing_hosts: Collection[HostClusterPair]) -> None:
    if not set(host_candidates).issubset(map(attrgetter("host_id"), existing_hosts)):
        raise HostDoesNotExistError()


def check_hosts_can_be_added_to_cluster(cluster_id: int, hosts: Collection[HostClusterPair]) -> None:
    bound_hosts = set(entry for entry in hosts if entry.cluster_id)
    if not bound_hosts:
        return

    if any(entry.cluster_id == cluster_id for entry in bound_hosts):
        raise HostAlreadyBoundError()

    raise HostBelongsToAnotherClusterError()
