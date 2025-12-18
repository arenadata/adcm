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

from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field

from core.bundle._parsing.shared.config import ConfigAsListDictOrNone
from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.v_2_0.actions import ClusterActions, HostOrADCMActions, ProviderActions
from core.bundle._parsing.v_2_0.schema import (
    ComponentRequiresSchema,
    Export,
    FlagAutogeneration,
    FlagAutogenerationSchema,
    Imports,
    License,
    Monitoring,
    Name,
    ServiceRequiresSchema,
    Venv,
    Version,
)
from core.bundle._parsing.v_2_0.upgrades import Upgrades

# Cluster Objects


def init_not_defined_components(components: dict[str, Any] | Any) -> dict[str, dict] | Any:
    if not isinstance(components, dict):
        return components

    return {k: v or {} for k, v in components.items()}


class Component(BundleModel):
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    actions: ClusterActions
    venv: Venv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[bool | None, Field(default=None)]

    flag_autogeneration: FlagAutogeneration

    monitoring: Monitoring
    constraint: Annotated[list[int | Literal["+", "odd"]] | None, Field(default=None, min_length=1, max_length=2)]
    requires: Annotated[list[ComponentRequiresSchema] | None, Field(default=None)]


class Service(BundleModel):
    type: Literal["service"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ClusterActions
    venv: Venv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[bool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    imports: Imports
    export: Export
    monitoring: Monitoring
    required: Annotated[bool | None, Field(default=None)]
    requires: Annotated[list[ServiceRequiresSchema] | None, Field(default=None)]

    components: Annotated[
        dict[Name, Component] | None, Field(default=None), BeforeValidator(init_not_defined_components)
    ]


class Cluster(BundleModel):
    type: Literal["cluster"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ClusterActions
    venv: Venv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[bool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    imports: Imports
    export: Export
    upgrade: Upgrades
    allow_maintenance_mode: Annotated[bool | None, Field(default=None)]


# Provider Objects


class Host(BundleModel):
    type: Literal["host"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: HostOrADCMActions
    venv: Venv

    config: ConfigAsListDictOrNone

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]


class Provider(BundleModel):
    type: Literal["provider"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: ProviderActions
    venv: Venv

    config: ConfigAsListDictOrNone
    config_group_customization: Annotated[bool | None, Field(default=None)]

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    license: License
    upgrade: Upgrades


# ADCM


class ADCMSchema(BundleModel):
    type: Literal["adcm"]
    contract_version: Literal["2.0"]

    name: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]

    adcm_min_version: Annotated[Version | None, Field(default=None)]
    version: Version
    edition: Annotated[str | None, Field(default=None)]

    actions: HostOrADCMActions
    venv: Venv

    config: ConfigAsListDictOrNone

    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]

    upgrade: Upgrades


# Dynamic Blocks


# class DynamicActionScripts(BundleModel):
#    scripts: Annotated[list[TASK_SCRIPTS_JINJA_SCHEMA], Field(min_length=1)]
#
#
# class DynamicWizardScripts(BundleModel):
#    scripts: Annotated[list[TASK_WIZARD_SCRIPTS_TEMPLATE_SCHEMA], Field(min_length=1)]
#
#
# class DynamicConfig(BundleModel):
#    config: ConfigAsListDictOrNoneNoDuplicates


# Unions

RootTarget = ADCMSchema | Provider | Host | Cluster | Service
ObjectTarget = RootTarget | Component
