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

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from core.types import ADCMCoreType, CoreObjectDescriptor, ObjectID


class ConcernType(str, Enum):
    LOCK = "lock"
    ISSUE = "issue"
    FLAG = "flag"


class ConcernCause(str, Enum):
    CONFIG = "config"
    JOB = "job"
    HOSTCOMPONENT = "host-component"
    IMPORT = "import"
    SERVICE = "service"
    REQUIREMENT = "requirement"
    CONFIGURING_PROCESS = "configuring_process"


# objects a concern is linked to, grouped by core type
ConcernRelatedObjects: TypeAlias = dict[ADCMCoreType, set[ObjectID]]


@dataclass(slots=True)
class ConcernTarget:
    """
    Owner/target of a concern, carrying enough info to both store the concern (via
    `as_descriptor`) and render it in message placeholders (`name`, `id_chain`).
    """

    id: ObjectID
    type: ADCMCoreType
    name: str
    id_chain: dict

    @property
    def as_descriptor(self) -> CoreObjectDescriptor:
        return CoreObjectDescriptor(id=self.id, type=self.type)


@dataclass(slots=True)
class ConcernDraft:
    type: ConcernType
    cause: ConcernCause
    name: str
    reason: dict
    blocking: bool
    owner: CoreObjectDescriptor
