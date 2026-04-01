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

from typing import TypeAlias, cast

from cm.errors import AdcmEx
from cm.legacy.services import cluster
from cm.legacy.services.concern.distribution import distribute_concern_from_provider_to_host
from cm.legacy.services.host import repo
from cm.legacy.services.status import notify
from cm.legacy.status_api import notify_about_redistributed_concerns_from_maps
from cm.models import Cluster, Host
from core.config import ConfigService
from core.types import ADCMCoreType, ClusterID, Descriptor, HostDesc, HostID, HostName
from django.db.transaction import atomic
from rbac.scenarios import RBACScenarios

HostDuplicateID: TypeAlias = HostID


def create_duplicate(
    config_service: ConfigService,
    host_id: HostID,
    name: HostName,
    rbac_scenarios: RBACScenarios,
    cluster_id: ClusterID | None = None,
) -> HostDuplicateID:
    with atomic():
        try:
            original = repo.get_original_host(host_id=host_id)
        except Host.DoesNotExist as e:
            raise AdcmEx(code="INVALID_CREATE_DUPLICATE_HOST", msg=f"There is not a #{host_id} original host") from e

        overrides = repo.DuplicateHostOverrides(name=name, description=f"Copied from {original.fqdn}")
        duplicate = repo.duplicate_host_record(host=original, overrides=overrides)

        if original.config:
            original_desc = cast(HostDesc, Descriptor(id=original.pk, type=ADCMCoreType.HOST))
            duplicate_desc = cast(HostDesc, Descriptor(id=duplicate.pk, type=ADCMCoreType.HOST))
            config_service.prepare_symlinks_for_file_type(original=original_desc, duplicate=duplicate_desc)

        if cluster_id is not None:
            try:
                cluster.perform_host_to_cluster_map(
                    cluster_id=cluster_id,
                    hosts=[duplicate.pk],
                    status_service=notify,
                    rbac_scenarios=rbac_scenarios,
                )
            except Cluster.DoesNotExist as e:
                raise AdcmEx("CLUSTER_NOT_FOUND") from e

        attached_concern_map = distribute_concern_from_provider_to_host(host_id=duplicate.pk)

    notify.register_host_duplicates(original=host_id, duplicates=(duplicate.pk,))
    notify_about_redistributed_concerns_from_maps(added=attached_concern_map, removed={})

    return duplicate.pk
