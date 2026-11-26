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

from collections.abc import Collection, Iterable
from typing import Protocol

from core.object.types import Selector, SelectorOwnerDescriptor, SelectorTargetDescriptor
from core.types import ADCMCoreType, Descriptor


class ObjectRepoI(Protocol):
    def set_state(self, object_: Descriptor[ADCMCoreType], state: str) -> None: ...

    def update_multi_state(
        self, object_: Descriptor[ADCMCoreType], add: Collection[str], remove: Collection[str]
    ) -> list[str]: ...

    def retrieve_multi_state(self, object_: Descriptor[ADCMCoreType]) -> list[str]: ...

    def build_selector(
        self,
        targets: Iterable[SelectorTargetDescriptor],
        owner: SelectorOwnerDescriptor | None = None,
    ) -> dict[SelectorTargetDescriptor, Selector]: ...
