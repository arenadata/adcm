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

from cm.services.cluster import perform_host_to_cluster_map
from cm.services.host import repo
from cm.services.status import notify


@atomic
def create_duplicate(host_id: HostID, name: str, cluster_id: ClusterID | None = None) -> HostID:
    original = repo.get_original_host(host_id=host_id)

    overrides = repo.DuplicateHostOverrides(name=name, description=f"Copied from {original.fqdn}")
    duplicate = repo.duplicate_host_record(host=original, overrides=overrides)

    if cluster_id:
        perform_host_to_cluster_map(
            cluster_id=cluster_id,
            hosts=[duplicate.id],
            status_service=notify,
        )

    return duplicate.id
