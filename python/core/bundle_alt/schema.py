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

from contextlib import contextmanager
from typing import Annotated, Any, Literal, TypeAlias
import re

from adcm_version import compare_prototype_versions
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from typing_extensions import TypedDict

from core.bundle_alt._pattern import Pattern
from core.bundle_alt.errors import BundleParsingError

# Should be moved to consts section
ADCM_TURN_ON_MM_ACTION_NAME = "adcm_turn_on_maintenance_mode"
ADCM_TURN_OFF_MM_ACTION_NAME = "adcm_turn_off_maintenance_mode"
ADCM_HOST_TURN_ON_MM_ACTION_NAME = "adcm_host_turn_on_maintenance_mode"
ADCM_HOST_TURN_OFF_MM_ACTION_NAME = "adcm_host_turn_off_maintenance_mode"
ADCM_DELETE_SERVICE_ACTION_NAME = "adcm_delete_service"
ADCM_SERVICE_ACTION_NAMES_SET = {
    ADCM_TURN_ON_MM_ACTION_NAME,
    ADCM_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_DELETE_SERVICE_ACTION_NAME,
}
ADCM_MM_ACTION_FORBIDDEN_PROPS_SET = {"config", "hc_acl", "ui_options"}
# section end

# copied from cm.utils
NAME_REGEX = re.compile(pattern=r"[0-9a-zA-Z_\.-]+")

VERSION: TypeAlias = int | float | str
VENV: TypeAlias = Annotated[
    Literal["default", "2.8", "2.9"] | None,
    Field(default=None),
    # fixme cast is too broad, but required since round trip load
    BeforeValidator(lambda x: str(x) if x is not None else x),
]
MONITORING: TypeAlias = Annotated[Literal["active", "passive"] | None, Field(default=None)]
ACTION_SCRIPT_TYPE: TypeAlias = Literal["ansible", "internal", "python"]


def validate_name(name: str) -> str:
    if NAME_REGEX.fullmatch(name) is None:
        raise ValueError(
            "Name is incorrect. Only latin characters, digits, "
            "dots (.), dashes (-), and underscores (_) are allowed.",
        )

    return name


NAME: TypeAlias = Annotated[str, AfterValidator(validate_name)]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


########
# CONFIG
########


# COPIED from cm FOR ADCM-6350
def is_path_correct(raw_path: str) -> bool:
    """
    Return whether given path meets ADCM path description requirements

    >>> this = is_path_correct
    >>> this("relative_to_bundle/path.yaml")
    True
    >>> this("./relative/to/file.yaml")
    True
    >>> this(".secret")
    True
    >>> this("../hack/system")
    False
    >>> this("/hack/system")
    False
    >>> this(".././hack/system")
    False
    >>> this("../../hack/system")
    False
    """
    return raw_path.startswith("./") or not raw_path.startswith(("..", "/"))


def convert_config(config: list | dict) -> list:
    """Converts old-style dict config to list config"""

    if not isinstance(config, dict):
        return config

    new_config = []
    for key, value in config.items():
        subs = None
        extra = {}

        if "type" not in value or not isinstance(value["type"], str):  # it is a group
            extra = {"type": "group", "required": False}
            subs = convert_config(value)

        new_value = {"name": key, "subs": subs, **extra} if subs is not None else {"name": key, **value, **extra}
        new_config.append(new_value)

    return new_config


def license_allowed_for_type(type_: str) -> None:
    allowed_types = {"cluster", "service", "provider"}

    if type_ not in allowed_types:
        raise ValueError("License can be placed in cluster, service or provider")


def min_and_max_present(versions: "VersionsSchema"):
    if versions.min is None and versions.min_strict is None:
        raise ValueError("min or min_strict should be present in versions of upgrade")

    if versions.max is None and versions.max_strict is None:
        raise ValueError("max or max_strict should be present in versions of upgrade")

    return versions


def min_less_than_max(versions: "VersionsSchema"):
    if versions.min is None or versions.max is None:
        return versions

    if compare_prototype_versions(str(versions.min), str(versions.max)) > 0:
        raise ValueError("Min version should be less or equal max version")

    return versions


def script_is_correct_path(script: str):
    if not is_path_correct(script):
        raise ValueError(f"Action's script has unsupported path format: {script}")

    return script


def is_correct_pattern(pattern: str | None):
    if not isinstance(pattern, str):
        return pattern

    if not Pattern(pattern).is_valid:
        raise ValueError(f"Pattern is not valid regular expression: {pattern}")

    return pattern


def forbidden_mm_actions(actions: Any):
    if not isinstance(actions, dict):
        return None

    for name, data in actions.items():
        if name in ADCM_SERVICE_ACTION_NAMES_SET and ADCM_MM_ACTION_FORBIDDEN_PROPS_SET.intersection(data.keys()):
            raise ValueError(
                "Maintenance mode actions shouldn't have " f'"{ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )

    return actions


class AnsibleOptionsSchema(_BaseModel):
    unsafe: bool = False


class _BaseConfigItemSchema(_BaseModel):
    type: str
    name: NAME
    read_only: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    writable: Annotated[Literal["any"] | list[str] | None, Field(default=None)]
    required: Annotated[bool | None, Field(default=None)]
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    ui_options: Annotated[dict | None, Field(default=None)]
    group_customization: Annotated[bool | None, Field(default=None)]
    ansible_options: Annotated[AnsibleOptionsSchema | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_editable_options(self):
        read_only_specified = self.read_only is not None
        writable_specified = self.writable is not None

        if read_only_specified and writable_specified:
            raise ValueError(
                'Config entry can not have "read_only" and "writable" simultaneously',
            )

        return self


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
    pattern: Annotated[str | None, Field(default=None), AfterValidator(is_correct_pattern)]


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


def config_duplicates(parameters: list[CONFIG_ITEMS | ConfigItemGroupSchema] | None):
    # at least ADS has duplicates in config
    return parameters
    if not parameters:
        return None

    names = set()

    for param in parameters:
        if param.name in names:
            raise ValueError(f"Duplicate config for key {param.name}")

        names.add(param.name)

        if isinstance(param, ConfigItemGroupSchema):
            config_duplicates(param.subs)

    return parameters


CONFIG_LIST: TypeAlias = list[Annotated[CONFIG_ITEMS | ConfigItemGroupSchema, Field(discriminator="type")]]
CONFIG_TYPE: TypeAlias = Annotated[
    CONFIG_LIST | None,
    Field(default=None),
    BeforeValidator(convert_config),
    AfterValidator(config_duplicates),
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


class VersionsSchema(_BaseModel):
    min: Annotated[VERSION | None, Field(default=None)]
    max: Annotated[VERSION | None, Field(default=None)]
    min_strict: Annotated[VERSION | None, Field(default=None)]
    max_strict: Annotated[VERSION | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_min_max_stricts(self):
        if self.min is not None and self.min_strict is not None:
            raise ValueError("min and min_strict can not be used simultaneously in versions")

        if self.max is not None and self.max_strict is not None:
            raise ValueError("max and max_strict can not be used simultaneously in versions")

        return self


class UpgradeScriptSchema(TypedDict):
    name: str
    script: str
    script_type: Literal["internal", "ansible"]
    display_name: Annotated[str | None, Field(default=None)]
    params: Annotated[dict | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]


class _BaseUpgradeSchema(_BaseModel):
    name: VERSION
    versions: Annotated[VersionsSchema, AfterValidator(min_and_max_present)]
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

    @model_validator(mode="after")
    def exclusive_masking_and_scripts(self):
        if self.scripts is not None:
            return self

        any_masking_field_set = any(x is not None for x in (self.masking, self.on_success, self.on_fail))

        if any_masking_field_set:
            raise ValueError(
                "Upgrade couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
            )

        return self


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

    @model_validator(mode="before")
    @classmethod
    def exclusive_jinja_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data

        scripts_jinja_specified = "scripts_jinja" in data
        scripts_specified = "scripts" in data
        if scripts_jinja_specified and scripts_specified:
            raise ValueError('"scripts" and "scripts_jinja" are mutually exclusive')

        config_jinja_specified = "config_jinja" in data
        config_specified = "config" in data
        if config_jinja_specified and config_specified:
            raise ValueError('"config" and "config_jinja" are mutually exclusive')

        return data

    @model_validator(mode="after")
    def exclusive_visibility_fields(self):
        states_specified = self.states is not None
        masking_specified = self.masking is not None

        if states_specified and masking_specified:
            raise ValueError('Action uses both mutual excluding states "states" and "masking"')

        on_fail_success_specified = self.on_fail is not None or self.on_success is not None
        if states_specified and on_fail_success_specified:
            raise ValueError('Action uses "on_success/on_fail" states without "masking"')

        return self

    @model_validator(mode="after")
    def exclusive_host_action_and_action_host_group(self):
        is_host_action = bool(self.host_action)
        is_allowed_in_host_group = bool(self.allow_for_action_host_group)

        if is_host_action and is_allowed_in_host_group:
            raise ValueError(
                "The allow_for_action_host_group and host_action attributes are mutually exclusive.",
            )

        return self

    @model_validator(mode="after")
    def config_jinja_path_format(self):
        if not isinstance(self.config_jinja, str):
            return self

        if not is_path_correct(self.config_jinja):
            raise ValueError('"config_jinja" has unsupported path format')

        return self


class JobSchema(_BaseActionSchema):
    type: Literal["job"]
    script_type: ACTION_SCRIPT_TYPE
    script: Annotated[str, AfterValidator(script_is_correct_path)]


class _BaseTaskSchema(_BaseActionSchema):
    type: Literal["task"]


class ScriptSchema(TypedDict):
    name: str
    script: Annotated[str, AfterValidator(script_is_correct_path)]
    script_type: ACTION_SCRIPT_TYPE
    display_name: Annotated[str | None, Field(default=None)]
    params: Annotated[dict | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]
    allow_to_terminate: Annotated[bool | None, Field(default=None)]


class TaskPlainSchema(_BaseTaskSchema):
    scripts: list[ScriptSchema]


class TaskJinjaSchema(_BaseTaskSchema):
    scripts_jinja: str

    @field_validator("scripts_jinja")
    @classmethod
    def scripts_jinja_path_format(cls, v: str):
        if not is_path_correct(v):
            raise ValueError('"scripts_jinja" has unsupported path format')

        return v


ACTIONS_TYPE: TypeAlias = Annotated[
    dict[NAME, JobSchema | TaskPlainSchema | TaskJinjaSchema] | None,
    Field(default=None),
    BeforeValidator(forbidden_mm_actions),
]


#########
# OBJECTS
#########


def init_not_defined_components(components: dict[str, Any] | Any) -> dict[str, dict] | Any:
    if not isinstance(components, dict):
        return components

    return {k: v or {} for k, v in components.items()}


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


class ImportSchema(_BaseModel):
    versions: Annotated[VersionsSchema | None, Field(default=None), AfterValidator(min_less_than_max)]
    required: Annotated[bool | None, Field(default=None)]
    multibind: Annotated[bool | None, Field(default=None)]
    default: Annotated[list[str] | None, Field(default=None)]

    @model_validator(mode="after")
    def exclusive_default_and_required(self):
        if self.required and self.default:
            raise ValueError("Import can't have default and be required in the same time")

        return self


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

    @model_validator(mode="after")
    def check_license_allowed(self):
        if self.license is not None:
            license_allowed_for_type(self.type)

        return self

    @field_validator("license")
    @classmethod
    def check_license_path_is_correct(cls, v: str | None):
        if isinstance(v, str) and not is_path_correct(v):
            raise ValueError(f"Unsupported path format for license: {v}")

        return v


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

    @model_validator(mode="before")
    @classmethod
    def check_license_allowed(cls, data: Any):
        if not isinstance(data, dict):
            return data

        if "license" in data:
            license_allowed_for_type("component")

        return data


class ServiceSchema(_BaseObjectSchema):
    type: Literal["service"]
    imports: Annotated[dict[str, ImportSchema] | None, Field(alias="import", default=None)]
    export: Annotated[str | list[str] | None, Field(default=None)]
    shared: Annotated[bool | None, Field(default=None, deprecated=True)]
    components: Annotated[
        dict[NAME, ComponentSchema] | None, Field(default=None), BeforeValidator(init_not_defined_components)
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


################
# Bundle parsing
################


TYPE_SCHEMA_MAP = {
    "cluster": ClusterSchema,
    "service": ServiceSchema,
    "provider": ProviderSchema,
    "host": HostSchema,
    "adcm": ADCMSchema,
}


@contextmanager
def _validation_to_bundle_error():
    try:
        yield
    except ValidationError as e:
        message = "Errors found in definition of bundle entity:"
        # implement
        details = str(e)

        message = f"{message}\n{details}"

        raise BundleParsingError(message) from e


def parse(
    definition: dict,
) -> ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema:
    try:
        def_type = definition["type"]
    except KeyError as e:
        raise BundleParsingError("Field `type` is missing: can't parse definition") from e

    with _validation_to_bundle_error():
        return TYPE_SCHEMA_MAP[def_type].model_validate(definition, strict=True)


###############
# scripts_jinja
###############


class ScriptsJinjaSchema(_BaseModel):
    scripts: Annotated[list[ScriptSchema], Field(min_length=1)]


##############
# config_jinja
##############


class ConfigJinjaSchema(_BaseModel):
    config: Annotated[CONFIG_LIST, BeforeValidator(convert_config), AfterValidator(config_duplicates)]
