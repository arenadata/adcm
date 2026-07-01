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

from typing import Iterable

from core.metrics._repo import ClusterMetricsRepoI
from core.metrics._types import ClusterMetrics
from core.types import ClusterID


class RetrieveClusterMetrics:
    def __init__(self, repo: ClusterMetricsRepoI):
        self._repo = repo

    def retrieve_metrics_many(self, cluster_ids: Iterable[ClusterID]) -> tuple[ClusterMetrics, ...]:
        return tuple(self._repo.get_latest_many(cluster_ids=cluster_ids))

    def retrieve_metrics(self, cluster_id: int) -> ClusterMetrics:
        return self._repo.get_latest(cluster_id=cluster_id)
