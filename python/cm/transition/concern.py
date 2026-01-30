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

from core.types import ADCMCoreType, ConcernID, CoreObjectDescriptor

from cm.legacy.services.concern import create_issue
from cm.legacy.services.concern.checks import cluster_mapping_has_issue_orm_version
from cm.legacy.services.concern.distribution import ConcernRelatedObjects, distribute_concern_on_related_objects
from cm.models import Cluster, ConcernCause


def create_and_distribute_hostcomponent_concern_on_add_host_to_cluster(
    cluster: Cluster,
) -> tuple[ConcernID | None, ConcernRelatedObjects]:
    cluster_cod = CoreObjectDescriptor(id=cluster.pk, type=ADCMCoreType.CLUSTER)
    concern = cluster.get_own_issue(cause=ConcernCause.HOSTCOMPONENT)

    if concern is None:
        if cluster_mapping_has_issue_orm_version(cluster=cluster):
            concern = create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
        else:
            return None, {}

    return concern.pk, distribute_concern_on_related_objects(owner=cluster_cod, concern_id=concern.pk)
