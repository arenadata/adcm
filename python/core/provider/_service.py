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

from core.provider._repo import ProviderRepoI
from core.types import (
    HostDesc,
    MaintenanceModeOfObjects,
    ProviderID,
    ProviderObjectDesc,
)


@dataclass(slots=True)
class ProviderService:
    repo: ProviderRepoI

    def retrieve_hosts_by_provider(self, provider_id: ProviderID) -> tuple[HostDesc, ...]:
        return self.repo.find_hosts_by_provider(provider_id=provider_id)

    def retrieve_own_maintenance_mode(self, target: ProviderObjectDesc) -> MaintenanceModeOfObjects:
        return MaintenanceModeOfObjects(
            services={},
            components={},
            hosts=self.repo.get_hosts_own_maintenance_mode(object_=target),
        )
