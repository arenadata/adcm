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

from core.types import (
    ADCMCoreType,
    ProviderObjectDesc,
)
from django.db.transaction import atomic
import core


@dataclass(slots=True)
class ResetBeforeUpgradeProvider:
    provider_service: core.provider.ProviderService
    upgrade_service: core.upgrade.UpgradeService

    @atomic
    def do(self, target: ProviderObjectDesc) -> None:
        affected_objects = [target]

        if target.type == ADCMCoreType.PROVIDER:
            hosts = self.provider_service.retrieve_hosts_by_provider(provider_id=target.id)
            affected_objects.extend(hosts)

        self.upgrade_service.reset_before_upgrade(targets=affected_objects)
