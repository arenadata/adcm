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

from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field
from typing_extensions import TypedDict
import yaml

VERSION: TypeAlias = int | float | str
VENV: TypeAlias = Annotated[Literal["default", "2.9"] | None, Field(default=None)]
MONITORING: TypeAlias = Annotated[Literal["active", "passive"] | None, Field(default=None)]
ACTION_SCRIPT_TYPE: TypeAlias = Literal["ansible", "internal", "python"]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


########
# CONFIG
########


def convert_config(config: list | dict) -> list:
    """Converts old-style dict config to list config"""

    if not isinstance(config, dict):
        return config

    new_config = []
    for key, value in config.items():
        subs = None
        extra = {}

        if "type" not in value or not isinstance(value["type"], str):  # it is a group
            extra = {"type": "group"}
            subs = convert_config(value)

        new_value = {"name": key, "subs": subs, **extra} if subs is not None else {"name": key, **value, **extra}
        new_config.append(new_value)

    return new_config


class _BaseConfigItemSchema(_BaseModel):
    type: str
    name: str
    read_only: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    writable: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    required: Annotated[bool | None, Field(default=None)]
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]
    group_customization: Annotated[bool | None, Field(default=None)]


class ConfigItemBooleanSchema(_BaseConfigItemSchema):
    type: Literal["boolean"]
    default: Annotated[bool | None, Field(default=None)]


class ConfigItemIntegerSchema(_BaseConfigItemSchema):
    type: Literal["integer"]
    min: Annotated[int | None, Field(default=None)]
    max: Annotated[int | None, Field(default=None)]
    default: Annotated[int | None, Field(default=None)]


class ConfigItemFloatSchema(_BaseConfigItemSchema):
    type: Literal["float"]
    min: Annotated[float | int | None, Field(default=None)]
    max: Annotated[float | int | None, Field(default=None)]
    default: Annotated[float | int | None, Field(default=None)]


class ConfigItemFileSchema(_BaseConfigItemSchema):
    type: Literal["file", "secretfile"]
    default: Annotated[str | None, Field(default=None)]


class ConfigItemStringWithPatternSchema(_BaseConfigItemSchema):
    type: Literal["string", "password", "secrettext", "text"]
    default: Annotated[str | None, Field(default=None)]
    pattern: Annotated[str | None, Field(default=None)]


class ConfigItemListSchema(_BaseConfigItemSchema):
    type: Literal["list"]
    default: Annotated[list[str] | None, Field(default=None)]


class ConfigItemMapSchema(_BaseConfigItemSchema):
    type: Literal["map", "secretmap"]
    default: Annotated[dict[str, str] | None, Field(default=None)]


class ConfigItemStructureSchema(_BaseConfigItemSchema):
    type: Literal["structure"]
    yspec: str
    default: Annotated[Any, Field(default=None)]


class ConfigItemJsonSchema(_BaseConfigItemSchema):
    type: Literal["json"]
    default: Annotated[Any, Field(default=None)]


class ConfigItemOptionSchema(_BaseConfigItemSchema):
    type: Literal["option"]
    option: dict[Any, str | int | float]
    default: Annotated[str | int | float | None, Field(default=None)]


class _BaseVariantSourceSchema(_BaseModel):
    type: str
    strict: Annotated[bool | None, Field(default=None)]


class VariantInlineSchema(_BaseVariantSourceSchema):
    type: Literal["inline"]
    value: list[str]


class VariantConfigSchema(_BaseVariantSourceSchema):
    type: Literal["config"]
    name: str


class _BaseVariantBuiltinSchema(_BaseVariantSourceSchema):
    type: Literal["builtin"]


class PredicateAndOrSchema(TypedDict):
    predicate: Literal["and", "or"]
    # recursive forward annotation. See https://docs.pydantic.dev/latest/concepts/forward_annotations/
    args: 'list[Annotated[_VariantBuiltinHostArgsSchema, Field(discriminator="predicate")]]'


class PredicateInClusterInHcNotInHcSchema(TypedDict):
    predicate: Literal["in_cluster", "in_hc", "not_in_hc"]
    args: None


class PredicateInNotInServiceSchema(TypedDict):
    predicate: Literal["in_service", "not_in_service"]
    args: dict[Literal["service"], str]


class PredicateInNotInComponentSchema(TypedDict):
    predicate: Literal["in_component", "not_in_component"]
    args: dict[Literal["service", "component"], str]


_VariantBuiltinHostArgsSchema = (
    PredicateAndOrSchema
    | PredicateInClusterInHcNotInHcSchema
    | PredicateInNotInServiceSchema
    | PredicateInNotInComponentSchema
)


class VariantBuiltinHostSchema(_BaseVariantBuiltinSchema):
    name: Literal["host"]
    args: Annotated[_VariantBuiltinHostArgsSchema, Field(discriminator="predicate")]


class HostInClusterArgsSchema(TypedDict):
    service: str
    component: Annotated[str | None, Field(default=None)]


class VariantBuiltinHostInClusterSchema(_BaseVariantBuiltinSchema):
    name: Literal["host_in_cluster"]
    args: Annotated[HostInClusterArgsSchema | None, Field(default=None)]


class VariantBuiltinOthersSchema(_BaseVariantBuiltinSchema):
    name: Literal["host_not_in_clusters", "service_in_cluster", "service_to_add"]


_VariantBuiltinSchema: TypeAlias = (
    VariantBuiltinHostSchema | VariantBuiltinHostInClusterSchema | VariantBuiltinOthersSchema
)


class ConfigItemVariantSchema(_BaseConfigItemSchema):
    type: Literal["variant"]
    source: Annotated[
        VariantInlineSchema | VariantConfigSchema | Annotated[_VariantBuiltinSchema, Field(discriminator="name")],
        Field(discriminator="type"),
    ]
    default: Annotated[str | None, Field(default=None)]


CONFIG_ITEMS: TypeAlias = (
    ConfigItemBooleanSchema
    | ConfigItemIntegerSchema
    | ConfigItemFloatSchema
    | ConfigItemFileSchema
    | ConfigItemStringWithPatternSchema
    | ConfigItemListSchema
    | ConfigItemMapSchema
    | ConfigItemStructureSchema
    | ConfigItemJsonSchema
    | ConfigItemOptionSchema
    | ConfigItemVariantSchema
)


class ConfigItemGroupSchema(_BaseConfigItemSchema):
    type: Literal["group"]
    subs: list[Annotated[CONFIG_ITEMS, Field(discriminator="type")]]
    activatable: Annotated[bool | None, Field(default=None)]
    active: Annotated[bool | None, Field(default=None)]


CONFIG_TYPE: TypeAlias = Annotated[
    list[Annotated[CONFIG_ITEMS | ConfigItemGroupSchema, Field(discriminator="type")]] | None,
    Field(default=None),
    BeforeValidator(convert_config),
]


##########
# UPGRADES
##########


class StatesSchema(TypedDict):
    available: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    on_success: Annotated[str | None, Field(default=None)]
    on_fail: Annotated[str | None, Field(default=None)]


class MultiStateSchema(TypedDict):
    set: Annotated[list[str] | None, Field(default=None)]
    unset: Annotated[list[str] | None, Field(default=None)]


class StateActionResultSchema(TypedDict):
    state: Annotated[str | None, Field(default=None)]
    multi_state: Annotated[MultiStateSchema | None, Field(default=None)]


class AvailabilitySchema(TypedDict):
    available: Literal["any"] | list[str]


class UnAvailabilitySchema(TypedDict):
    unavailable: Literal["any"] | list[str]


class MaskingSchema(TypedDict):
    state: Annotated[AvailabilitySchema | UnAvailabilitySchema | None, Field(default=None)]
    multi_state: Annotated[AvailabilitySchema | UnAvailabilitySchema | None, Field(default=None)]


class HcAclSchema(TypedDict):
    component: str
    action: Literal["add", "remove"]
    service: Annotated[str | None, Field(default=None)]


class VersionsSchema(TypedDict):
    min: Annotated[VERSION | None, Field(default=None)]
    max: Annotated[VERSION | None, Field(default=None)]
    min_strict: Annotated[VERSION | None, Field(default=None)]
    max_strict: Annotated[VERSION | None, Field(default=None)]


class UpgradeScriptSchema(TypedDict):
    name: str
    script: str
    script_type: Literal["internal", "ansible"]
    display_name: Annotated[str | None, Field(default=None)]
    params: Annotated[dict | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]


class _BaseUpgradeSchema(_BaseModel):
    name: str
    versions: VersionsSchema
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    states: Annotated[StatesSchema, Field(default=None)]
    from_edition: Annotated[str | list[str] | None, Field(default=None)]
    scripts: Annotated[list[UpgradeScriptSchema] | None, Field(default=None)]
    masking: Annotated[MaskingSchema | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]
    venv: VENV
    ui_options: Annotated[dict | None, Field(default=None)]
    config: CONFIG_TYPE


class ClusterUpgradeSchema(_BaseUpgradeSchema):
    hc_acl: Annotated[list[HcAclSchema] | None, Field(default=None)]


class ProviderUpgradeSchema(_BaseUpgradeSchema):
    pass


#########
# ACTIONS
#########


class ActionStatesSchema(TypedDict):
    available: list[str] | Literal["any"]
    on_success: Annotated[str | None, Field(default=None)]
    on_fail: Annotated[str | None, Field(default=None)]


class _BaseActionSchema(_BaseModel):
    type: str
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    params: Annotated[dict | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]
    allow_to_terminate: Annotated[bool | None, Field(default=None)]
    partial_execution: Annotated[bool | None, Field(default=None, deprecated=True)]
    host_action: Annotated[bool, Field(default=None)]
    allow_for_action_host_group: Annotated[bool, Field(default=None)]
    log_files: Annotated[list[str] | None, Field(default=None, deprecated=True)]
    states: Annotated[ActionStatesSchema | None, Field(default=None)]
    masking: Annotated[MaskingSchema | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]
    hc_acl: Annotated[list[HcAclSchema] | None, Field(default=None)]
    venv: VENV
    allow_in_maintenance_mode: Annotated[bool | None, Field(default=None)]
    config: CONFIG_TYPE
    config_jinja: Annotated[str | None, Field(default=None)]


class JobSchema(_BaseActionSchema):
    type: Literal["job"]
    script_type: ACTION_SCRIPT_TYPE
    script: str


class _BaseTaskSchema(_BaseActionSchema):
    type: Literal["task"]


class ScriptsSchema(TypedDict):
    name: str
    script: str
    script_type: ACTION_SCRIPT_TYPE
    display_name: Annotated[str | None, Field(default=None)]
    params: Annotated[dict | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]
    allow_to_terminate: Annotated[bool | None, Field(default=None)]


class TaskPlainSchema(_BaseTaskSchema):
    scripts: list[ScriptsSchema]


class TaskJinjaSchema(_BaseTaskSchema):
    scripts_jinja: str


ACTIONS_TYPE: TypeAlias = Annotated[
    dict[str, JobSchema | TaskPlainSchema | TaskJinjaSchema] | None, Field(default=None)
]


#########
# OBJECTS
#########


def init_not_defined_components(components: dict[str, Any]) -> dict[str, "ComponentSchema"]:
    if not isinstance(components, dict):
        return components

    for component_name in filter(lambda comp_key: components[comp_key] is None, components):
        components[component_name] = ComponentSchema()

    return components


class FlagAutogenerationSchema(TypedDict):
    enable_outdated_config: bool


class ServiceRequiresSchema(TypedDict):
    service: str
    component: Annotated[str | None, Field(default=None)]


class ComponentRequiresSchema(TypedDict):
    service: Annotated[str | None, Field(default=None)]
    component: Annotated[str | None, Field(default=None)]


class BoundSchema(TypedDict):
    service: str
    component: str


class ImportSchema(TypedDict):
    versions: Annotated[VersionsSchema | None, Field(default=None)]
    required: Annotated[bool | None, Field(default=None)]
    multibind: Annotated[bool | None, Field(default=None)]
    default: Annotated[list[str] | None, Field(default=None)]


class _BaseObjectSchema(_BaseModel):
    type: Literal["cluster", "service", "provider", "host", "adcm"]
    name: str
    version: VERSION
    adcm_min_version: Annotated[VERSION | None, Field(default=None)]
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    edition: Annotated[str | None, Field(default=None)]
    license: Annotated[str | None, Field(default=None)]
    config: CONFIG_TYPE
    actions: ACTIONS_TYPE
    venv: VENV
    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]


class ADCMSchema(_BaseObjectSchema):
    upgrade: Annotated[list[ProviderUpgradeSchema] | None, Field(default=None)]


class ClusterSchema(_BaseObjectSchema):
    type: Literal["cluster"]
    upgrade: Annotated[list[ClusterUpgradeSchema] | None, Field(default=None)]
    imports: Annotated[dict[str, ImportSchema] | None, Field(alias="import", default=None)]
    export: Annotated[str | list[str] | None, Field(default=None)]
    config_group_customization: Annotated[bool | None, Field(default=None)]
    allow_maintenance_mode: Annotated[bool | None, Field(default=None)]


class ComponentSchema(_BaseModel):
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    monitoring: MONITORING
    constraint: Annotated[list[int | Literal["+", "odd"]] | None, Field(default=None, min_length=1, max_length=2)]
    bound_to: Annotated[BoundSchema | None, Field(default=None)]
    params: Annotated[Any, Field(default=None, deprecated=True)]
    requires: Annotated[list[ComponentRequiresSchema] | None, Field(default=None)]
    config: CONFIG_TYPE
    actions: ACTIONS_TYPE
    config_group_customization: Annotated[bool | None, Field(default=None)]
    flag_autogeneration: Annotated[FlagAutogenerationSchema | None, Field(default=None)]
    venv: VENV


class ServiceSchema(_BaseObjectSchema):
    type: Literal["service"]
    imports: Annotated[dict[str, ImportSchema] | None, Field(alias="import", default=None)]
    export: Annotated[str | list[str] | None, Field(default=None)]
    shared: Annotated[bool | None, Field(default=None, deprecated=True)]
    components: Annotated[
        dict[str, ComponentSchema | None] | None, Field(default=None), AfterValidator(init_not_defined_components)
    ]
    required: Annotated[bool | None, Field(default=None)]
    requires: Annotated[list[ServiceRequiresSchema] | None, Field(default=None)]
    monitoring: MONITORING
    config_group_customization: Annotated[bool | None, Field(default=None)]


class HostSchema(_BaseObjectSchema):
    type: Literal["host"]


class ProviderSchema(_BaseObjectSchema):
    type: Literal["provider"]
    upgrade: Annotated[list[ProviderUpgradeSchema] | None, Field(default=None)]
    config_group_customization: Annotated[bool | None, Field(default=None)]


TYPE_SCHEMA_MAP = {
    "cluster": ClusterSchema,
    "service": ServiceSchema,
    "provider": ProviderSchema,
    "host": HostSchema,
    "adcm": ADCMSchema,
}


def retrieve_bundle_schema(
    *paths: Path,
) -> list[ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema]:
    schemas = []

    for path in paths:
        with path.open(encoding="utf-8") as config_yaml:
            definitions = yaml.safe_load(stream=config_yaml)

        if isinstance(definitions, dict):
            definitions = [definitions]

        for definition in definitions:
            schemas.append(TYPE_SCHEMA_MAP[definition["type"]].model_validate(definition, strict=True))

    return schemas
