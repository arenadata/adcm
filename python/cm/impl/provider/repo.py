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
from core.types import (
    ADCMCoreType,
    Descriptor,
    HostID,
    MaintenanceModeState,
    ObjectMM,
    ProviderID,
    ProviderObjectDesc,
)

from cm.models import Host


class ProviderRepo(provider.ProviderRepoI):
    def find_hosts_by_provider(self, provider_id: ProviderID) -> tuple[provider.HostInfo, ...]:
        query = Host.objects.filter(provider_id=provider_id).values_list("id", "cluster_id", "maintenance_mode")
        return tuple(
            provider.HostInfo(
                id=id_,
                type=ADCMCoreType.HOST,
                cluster_id=cluster_id,
                maintenance_mode=ObjectMM(MaintenanceModeState(mm.lower())),
            )
            for id_, cluster_id, mm in query
        )

    def get_hosts_own_maintenance_mode(self, object_: ProviderObjectDesc) -> dict[HostID, ObjectMM]:
        match object_:
            case Descriptor(type=ADCMCoreType.HOST):
                host_ids = (object_.id,)
            case Descriptor(type=ADCMCoreType.PROVIDER):
                host_ids = (host.id for host in self.find_hosts_by_provider(provider_id=object_.id))

        hosts_qs = Host.objects.filter(id__in=host_ids).values_list("id", "maintenance_mode")

        return {id_: ObjectMM(MaintenanceModeState(mm.lower())) for id_, mm in hosts_qs}
