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

from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BeforeValidator, Field, StrictBool, StrictInt

from core.bundle._parsing.shared.config import ConfigAsList, ConfigAsListDictOrNone
from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.v_2_0.actions import (
    ADCMActions,
    ClusterActions,
    HostActions,
    ProviderActions,
)
from core.bundle._parsing.v_2_0.schema import (
    ChildVenv,
    ComponentRequiresSchema,
    Export,
    FlagAutogeneration,
    FlagAutogenerationSchema,
    Imports,
    License,
    MainVenv,
    Monitoring,
    Name,
    ServiceRequiresSchema,
    Version,
)
from core.bundle._parsing.v_2_0.upgrades import (
    DynamicUpgradeScriptList,
    SimpleUpgrade,
    UpgradeWithScripts,
    UpgradeWithScriptsTemplate,
)

# Targets are parametrized by entries of `scripts` they allow,
# concrete contract versions decide on them
ActionScriptT = TypeVar("ActionScriptT")
UpgradeScriptT = TypeVar("UpgradeScriptT")
ScriptT = TypeVar("ScriptT")

# Cluster Objects


def init_not_defined_components(components: dict[str, Any] | Any) -> dict[str, dict] | Any:
    if not isinstance(components, dict):
        return components

    return {k: v or {} for k, v in components.items()}


class Component(BundleModel, Generic[ActionScriptT]):
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    actions: ClusterActions[ActionScriptT]
    venv: ChildVenv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[StrictBool | None, Field(default=None)]

    flag_autogeneration: FlagAutogeneration

    monitoring: Monitoring
    constraint: Annotated[list[StrictInt | Literal["+", "odd"]] | None, Field(default=None, min_length=1, max_length=2)]
    requires: Annotated[list[ComponentRequiresSchema] | None, Field(default=None)]


class Service(BundleModel, Generic[ActionScriptT]):
    type: Literal["service"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ClusterActions[ActionScriptT]
    venv: ChildVenv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[StrictBool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    imports: Imports
    export: Export
    monitoring: Monitoring
    required: Annotated[StrictBool | None, Field(default=None)]
    requires: Annotated[list[ServiceRequiresSchema] | None, Field(default=None)]

    components: Annotated[
        dict[Name, Component[ActionScriptT]] | None, Field(default=None), BeforeValidator(init_not_defined_components)
    ]


class Cluster(BundleModel, Generic[ActionScriptT, UpgradeScriptT]):
    type: Literal["cluster"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ClusterActions[ActionScriptT]
    venv: MainVenv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[StrictBool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    imports: Imports
    export: Export
    upgrade: Annotated[
        list[UpgradeWithScriptsTemplate | UpgradeWithScripts[UpgradeScriptT] | SimpleUpgrade] | None,
        Field(default=None),
    ]
    allow_maintenance_mode: Annotated[StrictBool | None, Field(default=None)]


# Provider Objects


class Host(BundleModel, Generic[ActionScriptT]):
    type: Literal["host"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: HostActions[ActionScriptT]
    venv: ChildVenv

    config: ConfigAsListDictOrNone

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]


class Provider(BundleModel, Generic[ActionScriptT, UpgradeScriptT]):
    type: Literal["provider"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ProviderActions[ActionScriptT]
    venv: MainVenv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[StrictBool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    upgrade: Annotated[list[UpgradeWithScripts[UpgradeScriptT] | SimpleUpgrade] | None, Field(default=None)]


# ADCM


class ADCMSchema(BundleModel, Generic[ActionScriptT, UpgradeScriptT]):
    type: Literal["adcm"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ADCMActions[ActionScriptT]
    venv: MainVenv

    config: ConfigAsListDictOrNone

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    upgrade: Annotated[list[UpgradeWithScripts[UpgradeScriptT] | SimpleUpgrade] | None, Field(default=None)]


# Dynamic Blocks


class DynamicActionScripts(BundleModel, Generic[ScriptT]):
    scripts: Annotated[list[ScriptT], Field(min_length=1)]


class DynamicUpgradeScripts(BundleModel, Generic[ScriptT]):
    scripts: Annotated[DynamicUpgradeScriptList[ScriptT], Field(min_length=1)]


class DynamicWizardScripts(BundleModel, Generic[ScriptT]):
    scripts: Annotated[list[ScriptT], Field(min_length=1)]


class DynamicConfig(BundleModel):
    config: Annotated[ConfigAsList, Field(min_length=1)]


# Unions

RootTarget = ADCMSchema | Provider | Host | Cluster | Service
ObjectTarget = RootTarget | Component
