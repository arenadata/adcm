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
from typing import Literal, Protocol

from core.types import ADCMCoreType, ClusterID, Descriptor, HostID, ObjectMM, ProviderID, ProviderObjectDesc


@dataclass(slots=True, frozen=True)
class HostInfo(Descriptor[Literal[ADCMCoreType.HOST]]):
    """
    A `HostDesc` (usable anywhere a plain host descriptor is expected) enriched with what's
    commonly needed alongside it — its cluster (if any) and own maintenance mode.
    """

    cluster_id: ClusterID | None
    maintenance_mode: ObjectMM


class ProviderRepoI(Protocol):
    def find_hosts_by_provider(self, provider_id: ProviderID) -> tuple[HostInfo, ...]:
        ...

    def get_hosts_own_maintenance_mode(self, object_: ProviderObjectDesc) -> dict[HostID, ObjectMM]:
        ...
