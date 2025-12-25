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

from typing import Generic, Protocol, TypeVar

from core import config

AT = TypeVar("AT", contravariant=True)
TT = TypeVar("TT", contravariant=True)


class ContextGathererI(Protocol, Generic[AT, TT]):
    def prepare_context_for_action(self, args: AT) -> dict:
        ...

    def prepare_context_for_task(self, args: TT) -> dict:
        ...


class JinjaRendererI(Protocol):
    def render_config(self) -> tuple[config.spec.FullSpec, config.Defaults]:
        ...
