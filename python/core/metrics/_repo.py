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
from typing import Generator, Protocol

from core.metrics._types import ClusterMetrics
from core.types import ClusterID


class ClusterMetricsRepoI(Protocol):
    def get_latest(self, cluster_id: ClusterID) -> ClusterMetrics:
        ...

    def get_latest_many(self, cluster_ids: Iterable[ClusterID]) -> Generator[ClusterMetrics, None, None]:
        ...
