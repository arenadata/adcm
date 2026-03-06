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

from core import provider
from core.types import ADCMCoreType, Descriptor, HostDesc, ProviderID

from cm.models import Host


class ProviderRepo(provider.ProviderRepoI):
    def find_hosts_by_provider(self, provider_id: ProviderID) -> tuple[HostDesc, ...]:
        query = Host.objects.filter(provider_id=provider_id).values_list("id", flat=True)
        return tuple(Descriptor(id=id_, type=ADCMCoreType.HOST) for id_ in query)
