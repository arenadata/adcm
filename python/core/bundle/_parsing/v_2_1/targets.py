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

from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from core.bundle._parsing.v_2_0.targets import (
    ADCMSchema as ADCMSchemaV2,
)
from core.bundle._parsing.v_2_0.targets import (
    Cluster as ClusterV2,
)
from core.bundle._parsing.v_2_0.targets import (
    Component as ComponentV2,
)
from core.bundle._parsing.v_2_0.targets import (
    Host as HostV2,
)
from core.bundle._parsing.v_2_0.targets import (
    Provider as ProviderV2,
)
from core.bundle._parsing.v_2_0.targets import (
    Service as ServiceV2,
)

MainVenv: TypeAlias = Literal["2.16"]
ChildVenv: TypeAlias = Annotated[MainVenv | None, Field(default=None)]


class Cluster(ClusterV2):
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Service(ServiceV2):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Component(ComponentV2):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Provider(ProviderV2):
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Host(HostV2):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class ADCMSchema(ADCMSchemaV2):
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


RootTarget = ADCMSchema | Provider | Host | Cluster | Service
