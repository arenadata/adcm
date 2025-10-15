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

from functools import partial
from typing import Annotated, Any, Literal, Optional, Sequence, TypeAlias

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    conlist,
    field_validator,
    model_validator,
)
from typing_extensions import TypedDict

from core.bundle_alt.errors import BundleParsingError, convert_validation_to_bundle_error
from core.bundle_alt.schema_validation import (
    convert_config,
    forbidden_mm_actions,
    is_correct_pattern,
    is_path_correct,
    license_allowed_for_type,
    min_and_max_present,
    min_less_than_max,
    patch_masking,
    script_is_correct_path,
    template_script_is_correct_path,
    validate_name,
)
from core.job.types import StepType
from core.templates import Template

# pyright: reportIncompatibleVariableOverride=false, reportInvalidTypeForm=false

VERSION: TypeAlias = int | float | str
VENV: TypeAlias = Annotated[
    Literal["default", "2.8", "2.9", "2.16"] | None,
    Field(default=None),
    # fixme cast is too broad, but required since round trip load
    BeforeValidator(lambda x: str(x) if x is not None else x),
]
MONITORING: TypeAlias = Annotated[Literal["active", "passive"] | None, Field(default=None)]
ACTION_SCRIPT_TYPE: TypeAlias = Literal["ansible", "internal", "python"]

NAME: TypeAlias = Annotated[str, AfterValidator(validate_name)]

WizardTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="wizard_template"))
]
ScriptsTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="scripts_template"))
]
ConfigTemplate = Annotated[
    Template, AfterValidator(partial(template_script_is_correct_path, field_name="config_template"))
]
HCTemplate = Annotated[Template, AfterValidator(partial(template_script_is_correct_path, field_name="hc_template"))]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


########
# CONFIG
########


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


class AnsibleOptionsSchema(TypedDict):
    unsafe: bool


class _WithAnsibleOptions:
    ansible_options: Annotated[AnsibleOptionsSchema | None, Field(default=None)]


class _WithPattern:
    pattern: Annotated[str | None, Field(default=None), AfterValidator(is_correct_pattern)]


class _WithStringDefault:
    default: Annotated[str | None, Field(default=None)]


class ConfigItemStringSchema(_WithStringDefault, _WithAnsibleOptions, _WithPattern, _BaseConfigItemSchema):
    type: Literal["string"]


class ConfigItemPasswordSchema(_WithStringDefault, _WithPattern, _BaseConfigItemSchema):
    type: Literal["password"]


class ConfigItemSecretTextSchema(_WithStringDefault, _WithPattern, _BaseConfigItemSchema):
    type: Literal["secrettext"]


class ConfigItemTextSchema(_WithStringDefault, _WithAnsibleOptions, _WithPattern, _BaseConfigItemSchema):
    type: Literal["text"]


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
    | ConfigItemStringSchema
    | ConfigItemPasswordSchema
    | ConfigItemTextSchema
    | ConfigItemSecretTextSchema
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


# TODO: move to schema_validation.py
def config_duplicates(parameters: Sequence[CONFIG_ITEMS | ConfigItemGroupSchema] | None):
    # at least ADS has duplicates in config
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
]
ACTION_CONFIG_TYPE: TypeAlias = Annotated[CONFIG_TYPE, AfterValidator(config_duplicates)]


#######
# STATES SCHEMAS
#######


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


MASKING_SCHEMA = Annotated[MaskingSchema | None, Field(default=None), BeforeValidator(patch_masking)]

#######
# HC_ACL SCHEMAS
#######


class HcAclSchema(TypedDict):
    component: str
    action: Literal["add", "remove"]
    service: Annotated[str | None, Field(default=None)]


class HcApplyRule(_BaseModel):
    service: str
    component: str
    action: Literal["add", "remove"]


class HcApplySchema(_BaseModel):
    rules: list[HcApplyRule]


class AdcmConfigApplyRule(_BaseModel):
    type: Literal["adcm"]


class HostConfigApplyRule(_BaseModel):
    type: Literal["host"]


class ProviderConfigApplyRule(_BaseModel):
    type: Literal["provider"]


class ClusterConfigApplyRule(_BaseModel):
    type: Literal["cluster"]


class ServiceConfigApplyRule(_BaseModel):
    type: Literal["service"]
    service_name: str


class ComponentConfigApplyRule(ServiceConfigApplyRule):
    type: Literal["component"]
    component_name: str


class ConfigApplyParameterItem(_BaseModel):
    key: str
    value: Any


class ConfigApplyObject(_BaseModel):
    object: Annotated[
        ClusterConfigApplyRule
        | ServiceConfigApplyRule
        | ComponentConfigApplyRule
        | HostConfigApplyRule
        | ProviderConfigApplyRule
        | AdcmConfigApplyRule,
        Field(discriminator="type"),
    ]
    parameters: list[ConfigApplyParameterItem]

    def __hash__(self):
        return hash(self.model_dump_json())


class ConfigApplySchema(_BaseModel):
    changes: conlist(ConfigApplyObject, min_length=1)

    @model_validator(mode="after")
    def ensure_unique_changes(self):
        seen = set()
        for change in self.changes:
            if change in seen:
                raise ValueError("Duplicate change detected in 'changes'")
            seen.add(change)
        return self


#######
# BASE SCRIPTS
#######


class _WithAllowToTerminateField(_BaseModel):
    allow_to_terminate: Annotated[bool | None, Field(default=None)]


class _InternalBundleSwitchScript(_BaseModel):
    script_type: Literal["internal"]
    script: Literal["bundle_switch"]
    params: Annotated[None, Field(default=None)]


class _InternalBundleRevertScript(_BaseModel):
    script_type: Literal["internal"]
    script: Literal["bundle_revert"]
    params: Annotated[None, Field(default=None)]


class _InternalHcApplyScript(_BaseModel):
    script_type: Literal["internal"]
    script: Literal["hc_apply"]
    params: Annotated[HcApplySchema | None, Field(default=None)]


class _AnsibleScript(_BaseModel):
    script_type: Literal["ansible"]
    script: Annotated[str, AfterValidator(script_is_correct_path)]
    params: Annotated[dict | None, Field(default=None)]


class _PythonScript(_BaseModel):
    script_type: Literal["python"]
    script: Annotated[str, AfterValidator(script_is_correct_path)]
    params: Annotated[None, Field(default=None)]


class _InternalConfigApplyScript(_BaseModel):
    script_type: Literal["internal"]
    script: Literal["config_apply"]
    params: ConfigApplySchema


class _BaseScriptSchema(_BaseModel):
    name: str
    display_name: Annotated[str | None, Field(default=None)]
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]


class InternalBundleSwitchScriptSchema(_BaseScriptSchema, _InternalBundleSwitchScript):
    ...


class InternalBundleRevertScriptSchema(_BaseScriptSchema, _InternalBundleRevertScript):
    ...


class InternalHcApplyScriptSchema(_BaseScriptSchema, _InternalHcApplyScript):
    ...


class AnsibleScriptSchema(_BaseScriptSchema, _AnsibleScript):
    ...


class PythonScriptSchema(_BaseScriptSchema, _PythonScript):
    ...


class InternalConfigApplyScriptSchema(_BaseScriptSchema, _InternalConfigApplyScript):
    ...


##########
# UPGRADES
##########


INTERNAL_UPGRADE_SCRIPTS_SCHEMA = Annotated[
    InternalBundleSwitchScriptSchema | InternalBundleRevertScriptSchema, Field(discriminator="script")
]


UPGRADE_SCRIPTS_SCHEMA = Annotated[
    INTERNAL_UPGRADE_SCRIPTS_SCHEMA | AnsibleScriptSchema, Field(discriminator="script_type")
]


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


##########################
# ACTION PROCESS (WIZARD)
##########################


class _Names(_BaseModel):
    name: str
    display_name: str


# Step Schemas


class _StepOperationUIOptions(_BaseModel):
    button_name: str


class OperationStep(_Names):
    scripts_template: ScriptsTemplate
    ui_options: _StepOperationUIOptions | None = None

    @property
    def type(self) -> StepType:
        return StepType.OPERATION

    @property
    def template(self) -> Template:
        return self.scripts_template


class ConfigurationStep(_Names):
    config_template: ConfigTemplate

    @property
    def type(self) -> StepType:
        return StepType.CONFIGURATION

    @property
    def template(self) -> Template:
        return self.config_template


class MappingStep(_Names):
    hc_template: HCTemplate

    @property
    def type(self) -> StepType:
        return StepType.MAPPING

    @property
    def template(self) -> Template:
        return self.hc_template


ActionProcessStep = OperationStep | ConfigurationStep | MappingStep


# Stage & Action Process Schema


class ActionProcessStage(_Names):
    steps: list[ActionProcessStep] = Field(..., min_length=1, description="At least one step is required in a stage")

    @model_validator(mode="after")
    def steps_names_are_unique(self):
        step_names = set()
        for step in self.steps:
            if step.name in step_names:
                raise ValueError(f"Duplicate step name: {step.name}")

            step_names.add(step.name)

        return self


class ActionProcessSpec(_BaseModel):
    stages: list[ActionProcessStage]

    @model_validator(mode="after")
    def stage_names_are_unique(self):
        stage_names = set()
        for stage in self.stages:
            if stage.name in stage_names:
                raise ValueError(f"Duplicate stage name: {stage.name}")

            stage_names.add(stage.name)

        return self


###########
# Upgrades
###########


class _BaseUpgradeSchema(_BaseModel):
    name: VERSION
    versions: Annotated[VersionsSchema, AfterValidator(min_and_max_present)]
    display_name: Annotated[str | None, Field(default=None)]
    description: Annotated[str | None, Field(default=None)]
    states: Annotated[StatesSchema, Field(default=None)]
    from_edition: Annotated[str | list[str] | None, Field(default=None)]
    scripts: Annotated[list[UPGRADE_SCRIPTS_SCHEMA] | None, Field(default=None)]
    masking: MASKING_SCHEMA
    on_fail: Annotated[StateActionResultSchema | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]
    venv: VENV
    ui_options: Annotated[dict | None, Field(default=None)]
    config: ACTION_CONFIG_TYPE

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
    # As part of the ADCM-6563 task, it was decided to drop support for upgrades with `hc_acl`.
    # hc_acl: Annotated[list[HcAclSchema] | None, Field(default=None)]
    pass


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
    masking: MASKING_SCHEMA
    on_fail: Annotated[StateActionResultSchema | str | None, Field(default=None)]
    on_success: Annotated[StateActionResultSchema | None, Field(default=None)]
    hc_acl: Annotated[list[HcAclSchema] | None, Field(default=None)]
    venv: VENV
    allow_in_maintenance_mode: Annotated[bool | None, Field(default=None)]
    config: ACTION_CONFIG_TYPE
    config_jinja: Annotated[str | None, Field(default=None)]
    wizard_template: Annotated[WizardTemplate | None, Field(default=None)]

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
        wizard_specified = "wizard_template" in data
        hc_acl_specified = "hc_acl" in data
        if config_jinja_specified and config_specified:
            raise ValueError('"config" and "config_jinja" are mutually exclusive')

        if wizard_specified and (config_specified or config_jinja_specified):
            raise ValueError('"wizard_template" and "config" or  "config_jinja" are mutually exclusive')

        if wizard_specified and hc_acl_specified:
            raise ValueError('"wizard_template" and "hc_acl" are mutually exclusive')

        return data

    # Has to check it as before mode and key presense,
    # because lots of cases (e.g. in integration tests specify "masking:" without value)
    # has `None` value when key is specified.
    # Surely there's a way to check it with pydantic mechanics, yet this one is easier.
    @model_validator(mode="before")
    @classmethod
    def exclusive_visibility_fields(cls, data: Any):
        if not isinstance(data, dict):
            return data

        states_specified = "states" in data
        masking_specified = "masking" in data

        if states_specified and masking_specified:
            raise ValueError('Action uses both mutual excluding states "states" and "masking"')

        on_fail_success_specified = "on_fail" in data or "on_success" in data
        if not masking_specified and on_fail_success_specified:
            raise ValueError('Action uses "on_success/on_fail" states without "masking"')

        return data

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

    @field_validator("config_jinja", mode="before")
    @classmethod
    def config_jinja_definition(cls, value: Any):
        if value is None:
            raise ValueError("the value cannot be empty")

        return value


class _BaseJobSchema(_BaseActionSchema):
    type: Literal["job"]


class InternalBundleSwitchJobSchema(_BaseJobSchema, _InternalBundleSwitchScript):
    ...


class InternalBundleRevertJobSchema(_BaseJobSchema, _InternalBundleRevertScript):
    ...


class InternalHcApplyJobShema(_BaseJobSchema, _InternalHcApplyScript):
    @model_validator(mode="after")
    def validate_hc_apply_together_hc_acl(self):
        if self.hc_acl is None:
            raise ValueError('"hc_apply" requires "hc_acl" declaration')

        return self


INTERNAL_JOB_SCHEMA = Annotated[
    InternalBundleSwitchJobSchema | InternalBundleRevertJobSchema | InternalHcApplyJobShema,
    Field(discriminator="script"),
]


class AnsibleJobSchema(_BaseJobSchema, _AnsibleScript):
    ...


class PythonJobSchema(_BaseJobSchema, _PythonScript):
    ...


JOB_SCHEMA = Annotated[INTERNAL_JOB_SCHEMA | AnsibleJobSchema | PythonJobSchema, Field(discriminator="script_type")]


class InternalBundleSwitchTaskScriptSchema(InternalBundleSwitchScriptSchema, _WithAllowToTerminateField):
    ...


class InternalBundleRevertTaskScriptSchema(InternalBundleRevertScriptSchema, _WithAllowToTerminateField):
    ...


class InternalHcApplyTaskScriptSchema(InternalHcApplyScriptSchema, _WithAllowToTerminateField):
    ...


class AnsibleTaskScriptSchema(AnsibleScriptSchema, _WithAllowToTerminateField):
    ...


class PythonTaskScriptSchema(PythonScriptSchema, _WithAllowToTerminateField):
    ...


class InternalConfigApplyTaskScriptSchema(InternalConfigApplyScriptSchema, _WithAllowToTerminateField):
    ...


class _BaseTaskSchema(_BaseActionSchema):
    type: Literal["task"]


INTERNAL_TASK_SCRIPTS_SCHEMA = Annotated[
    InternalBundleSwitchTaskScriptSchema | InternalBundleRevertTaskScriptSchema | InternalHcApplyTaskScriptSchema,
    Field(discriminator="script"),
]

INTERNAL_TASK_SCRIPTS_JINJA_SCHEMA = Annotated[
    InternalBundleSwitchTaskScriptSchema
    | InternalBundleRevertTaskScriptSchema
    | InternalHcApplyTaskScriptSchema
    | InternalConfigApplyTaskScriptSchema,
    Field(discriminator="script"),
]


TASK_SCRIPTS_SCHEMA = Annotated[
    INTERNAL_TASK_SCRIPTS_SCHEMA | AnsibleTaskScriptSchema | PythonTaskScriptSchema, Field(discriminator="script_type")
]


TASK_SCRIPTS_JINJA_SCHEMA = Annotated[
    INTERNAL_TASK_SCRIPTS_JINJA_SCHEMA | AnsibleTaskScriptSchema | PythonTaskScriptSchema,
    Field(discriminator="script_type"),
]


class TaskSchema(_BaseTaskSchema):
    scripts: Optional[list[TASK_SCRIPTS_SCHEMA]] = None
    scripts_jinja: str | None = None
    scripts_template: ScriptsTemplate | None = None

    config_template: ConfigTemplate | None = None

    @field_validator("scripts_jinja")
    @classmethod
    def scripts_jinja_path_format(cls, v: str):
        if not is_path_correct(v):
            raise ValueError('"scripts_jinja" has unsupported path format')
        return v

    @model_validator(mode="after")
    def validate_only_one_set_for_scripts(self):
        specified = tuple(filter(None, (self.scripts, self.scripts_jinja, self.scripts_template)))
        if len(specified) != 1:
            raise ValueError(
                'Exactly one of "scripts", "scripts_jinja" or "scripts_template" must be provided, '
                "not multiple nor neither."
            )

        return self

    @model_validator(mode="after")
    def validate_only_one_set_for_config(self):
        # thou this one semi duplicates check in Action schema, I put it here,
        # because `config_template` should be applicable only for Task until decided otherwise
        specified = tuple(filter(None, (self.config, self.config_jinja, self.config_template)))
        if len(specified) > 1:
            raise ValueError('At most one of "config", "config_jinja" or "config_template" must be provided.')

        return self

    @model_validator(mode="after")
    def validate_hc_apply_together_hc_acl(self):
        if self.scripts is None:
            return self

        for script in self.scripts:
            if script.script_type == "internal" and script.script == "hc_apply" and self.hc_acl is None:
                raise ValueError('"hc_apply" requires "hc_acl" declaration')

        return self


ACTIONS_TYPE: TypeAlias = Annotated[
    dict[NAME, Annotated[JOB_SCHEMA | TaskSchema, Field(discriminator="type")]] | None,
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


@convert_validation_to_bundle_error
def parse(
    definition: dict,
) -> ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema:
    try:
        def_type = definition["type"]
    except KeyError as e:
        raise BundleParsingError("Field `type` is missing: can't parse definition") from e

    try:
        core_model = TYPE_SCHEMA_MAP[def_type]
    except KeyError as e:
        raise BundleParsingError(f'Value "{def_type}" is not allowed') from e

    return core_model.model_validate(definition, strict=True)


###############
# scripts_jinja
###############


class DynamicScriptsSchema(_BaseModel):
    scripts: Annotated[list[TASK_SCRIPTS_JINJA_SCHEMA], Field(min_length=1)]


##############
# config_jinja
##############


class ConfigJinjaSchema(_BaseModel):
    config: Annotated[CONFIG_LIST, BeforeValidator(convert_config), AfterValidator(config_duplicates)]
