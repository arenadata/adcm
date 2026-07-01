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
from typing import NamedTuple


class CapacityUnit(str, Enum):
    BYTES = "B"
    KIB = "KiB"
    MIB = "MiB"
    GIB = "GiB"
    TIB = "TiB"
    PIB = "PiB"


class ResourceValue(NamedTuple):
    value: float
    unit: CapacityUnit


@dataclass(frozen=True, slots=True)
class ClusterResources:
    cpu_vcores: int
    ram: ResourceValue
    disk: ResourceValue


@dataclass(frozen=True, slots=True)
class ClusterMetrics:
    id: int
    resources: ClusterResources
