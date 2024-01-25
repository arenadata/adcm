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

from typing import Collection, Iterable

from core.cluster.operations import add_hosts_to_cluster
from core.cluster.types import HostClusterPair
from core.types import ClusterID, HostID
from django.db.transaction import atomic
from rbac.models import re_apply_object_policy

from cm.api import load_service_map
from cm.models import Cluster, Host


class HostClusterDB:
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


def perform_host_to_cluster_map(cluster_id: int, hosts: Collection[int]) -> Collection[int]:
    with atomic():
        add_hosts_to_cluster(cluster_id=cluster_id, hosts=hosts, db=HostClusterDB)

        re_apply_object_policy(Cluster.objects.get(id=cluster_id))

    load_service_map()

    return hosts
