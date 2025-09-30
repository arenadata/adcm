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

from core.types import ClusterID, HostID
from django.db.transaction import atomic

from cm.errors import AdcmEx
from cm.models import Cluster
from cm.services import cluster
from cm.services.concern.distribution import distribute_concern_from_provider_to_host
from cm.services.host import repo
from cm.services.status import notify
from cm.status_api import notify_about_redistributed_concerns_from_maps


def create_duplicate(host_id: HostID, name: str, cluster_id: ClusterID | None = None) -> HostID:
    with atomic():
        original = repo.get_original_host(host_id=host_id)

        overrides = repo.DuplicateHostOverrides(name=name, description=f"Copied from {original.fqdn}")
        duplicate = repo.duplicate_host_record(host=original, overrides=overrides)

        if original.config:
            repo.prepare_symlinks_for_file_type(duplicate=duplicate)

        if cluster_id is not None:
            try:
                cluster.perform_host_to_cluster_map(
                    cluster_id=cluster_id,
                    hosts=[duplicate.id],
                    status_service=notify,
                )
            except Cluster.DoesNotExist as e:
                raise AdcmEx("CLUSTER_NOT_FOUND") from e

        attached_concern_map = distribute_concern_from_provider_to_host(host_id=duplicate.id)

    notify.register_host_duplicates(original=host_id, duplicates=(duplicate.id,))
    notify_about_redistributed_concerns_from_maps(added=attached_concern_map, removed={})

    return duplicate.id
