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

from core.bundle._parsing.v_2_0.targets import ADCMSchema as ADCMSchemaV2
from core.bundle._parsing.v_2_0.targets import Cluster as ClusterV2
from core.bundle._parsing.v_2_0.targets import Component as ComponentV2
from core.bundle._parsing.v_2_0.targets import DynamicActionScripts as DynamicActionScriptsV2
from core.bundle._parsing.v_2_0.targets import DynamicUpgradeScripts as DynamicUpgradeScriptsV2
from core.bundle._parsing.v_2_0.targets import DynamicWizardScripts as DynamicWizardScriptsV2
from core.bundle._parsing.v_2_0.targets import Host as HostV2
from core.bundle._parsing.v_2_0.targets import Provider as ProviderV2
from core.bundle._parsing.v_2_0.targets import Service as ServiceV2
from core.bundle._parsing.v_2_1.scripts import (
    ADCMEntry,
    ClusterEntry,
    DynamicActionEntry,
    DynamicUpgradeEntry,
    DynamicWizardEntry,
    ProviderEntry,
    UpgradeEntry,
)

MainVenv: TypeAlias = Literal["2.16", "2.21"]
ChildVenv: TypeAlias = Annotated[MainVenv | None, Field(default=None)]


class Cluster(ClusterV2[ClusterEntry, UpgradeEntry]):
    contract_version: Literal["2.1"]  # pyright: ignore[reportIncompatibleVariableOverride]
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Service(ServiceV2[ClusterEntry]):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Component(ComponentV2[ClusterEntry]):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Provider(ProviderV2[ProviderEntry, UpgradeEntry]):
    contract_version: Literal["2.1"]  # pyright: ignore[reportIncompatibleVariableOverride]
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class Host(HostV2[ProviderEntry]):
    venv: ChildVenv  # pyright: ignore[reportIncompatibleVariableOverride]


class ADCMSchema(ADCMSchemaV2[ADCMEntry, UpgradeEntry]):
    contract_version: Literal["2.1"]  # pyright: ignore[reportIncompatibleVariableOverride]
    venv: MainVenv  # pyright: ignore[reportIncompatibleVariableOverride]


DynamicActionScripts = DynamicActionScriptsV2[DynamicActionEntry]
DynamicUpgradeScripts = DynamicUpgradeScriptsV2[DynamicUpgradeEntry]
DynamicWizardScripts = DynamicWizardScriptsV2[DynamicWizardEntry]

RootTarget = ADCMSchema | Provider | Host | Cluster | Service
