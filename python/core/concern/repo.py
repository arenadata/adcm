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

from collections.abc import Collection
from typing import Protocol, TypeAlias

from core.concern.types import ConcernDraft, ConcernRelatedObjects
from core.types import ADCMCoreType, ClusterDesc, ConcernID, HostDesc, ObjectID

# concerns of an owner grouped by objects those concerns are shown on
ConcernDistribution: TypeAlias = dict[ADCMCoreType, dict[ObjectID, set[ConcernID]]]


class ConcernRepoI(Protocol):
    def create(self, draft: ConcernDraft) -> ConcernID:
        ...

    def link(self, *, concern_id: ConcernID, targets: ConcernRelatedObjects) -> None:
        """
        Link an existing concern to `targets`.

        NOTE: computing which objects a concern should be distributed to (cluster/provider
        hierarchy, MM, etc.) is not part of this method and is not yet reworked to be
        core-safe — callers must supply `targets` themselves for now.
        """
        ...

    def update_object_name_in_concerns(
        self, object_: ClusterDesc | HostDesc, previous_name: str, new_name: str
    ) -> tuple[ConcernID, ...]:
        """
        Rename given object from `previous_name` to `new_name`
        in placeholders of all concerns that point at it.

        Returns ids of changed concerns.
        """
        ...

    def get_concerns_distribution(self, concern_ids: Collection[ConcernID]) -> ConcernDistribution:
        """
        Find objects given concerns are currently distributed on.
        """
        ...
