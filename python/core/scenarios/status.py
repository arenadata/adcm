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

from typing import Protocol

from core.concern.types import ConcernRelatedObjects
from core.types import ConcernID


class StatusScenariosI(Protocol):
    """
    Interface for `cm.transition.status.StatusScenarios`.

    Only covers what's used from core-level scenarios so far; extend as more
    of `StatusScenarios` gets called from core.
    """

    def notify_about_new_concern(self, concern_id: ConcernID, related_objects: ConcernRelatedObjects) -> None:
        ...
