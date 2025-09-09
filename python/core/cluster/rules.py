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
from functools import partial
from operator import attrgetter
from typing import Collection, Iterable

from typing_extensions import Self

from core.cluster.errors import (
    ClusterAddHostError,
    HostAlreadyBoundError,
    HostBelongsToAnotherClusterError,
    HostDoesNotExistError,
)
from core.cluster.types import HostAddInfo
from core.result import Fail, Success, is_fail, is_success
from core.types import ClusterID, HostID, HostName


def check_all_hosts_exist(hosts_to_add: Collection[int], existing_hosts: Collection[HostAddInfo]) -> None:
    if not set(hosts_to_add).issubset(map(attrgetter("id"), existing_hosts)):
        raise HostDoesNotExistError()


def check_hosts_can_be_added_to_cluster(
    hosts_to_add: Collection[HostAddInfo], cluster_id: int, hosts_in_cluster: Collection[HostAddInfo]
) -> None:
    context = _ClusterHostsInfo.construct(cluster_id=cluster_id, hosts_in_cluster=hosts_in_cluster)

    for host in hosts_to_add:
        result = _is_host_candidate(host=host, context=context)
        if is_fail(result):
            raise result.value


def filter_host_candidates(
    unbound_hosts: Iterable[HostAddInfo], cluster_id: int, hosts_in_cluster: Iterable[HostAddInfo]
) -> Iterable[HostAddInfo]:
    context = _ClusterHostsInfo.construct(cluster_id=cluster_id, hosts_in_cluster=hosts_in_cluster)

    is_host_candidate = partial(_is_host_candidate, context=context)
    check_results = map(is_host_candidate, unbound_hosts)
    success_results = filter(is_success, check_results)

    return (result.value for result in success_results)


@dataclass(slots=True)
class _ClusterHostsInfo:
    cluster_id: ClusterID
    ids: set[HostID]
    """
    All host ids from cluster (both "really" added and originals)
    """

    names: set[HostName]

    @classmethod
    def construct(cls, cluster_id: ClusterID, hosts_in_cluster: Iterable[HostAddInfo]) -> Self:
        host_ids: set[HostID] = set()
        host_names: set[HostName] = set()

        for host in hosts_in_cluster:
            host_ids.add(host.id)
            if host.original_id is not None:
                host_ids.add(host.original_id)

            host_names.add(host.name)

        return cls(cluster_id=cluster_id, ids=host_ids, names=host_names)


def _is_host_candidate(host: HostAddInfo, context: _ClusterHostsInfo) -> Success[HostAddInfo] | Fail[Exception]:
    if host.cluster_id is not None:
        if host.cluster_id == context.cluster_id:
            return Fail(HostAlreadyBoundError())

        return Fail(HostBelongsToAnotherClusterError())

    if host.id in context.ids or host.original_id in context.ids:
        return Fail(ClusterAddHostError(message="Host with the same origin is already added to cluster"))

    if host.name in context.names:
        return Fail(ClusterAddHostError(message="Host with the same name is already added to cluster"))

    return Success(host)
