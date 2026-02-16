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

from typing import Annotated, Any, Literal, Sequence, TypeAlias, Union

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, field_validator, model_validator
from typing_extensions import Self, TypedDict

from core.bundle._parsing.shared.model import BundleModel
from core.bundle._parsing.shared.validation import convert_config, is_correct_pattern, validate_name

Name: TypeAlias = Annotated[str, AfterValidator(validate_name)]


class _BaseConfigItemSchema(BundleModel):
    name: Name
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


class _BaseVariantSourceSchema(BaseModel):
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
    subs: list[Annotated[Union[CONFIG_ITEMS, Self, "ConfigItemSelectionGroupSchema"], Field(discriminator="type")]]
    activatable: Annotated[bool | None, Field(default=None)]
    active: Annotated[bool | None, Field(default=None)]

    @field_validator("name", mode="after")
    @classmethod
    def name_is_allowed(cls, value: str) -> str:
        if value == "_selection":
            message = 'Group is not allowed to be named "_selection"'
            raise ValueError(message)

        return value


class ConfigItemSelectionGroupSchema(_BaseConfigItemSchema):
    type: Literal["selection_group"]
    subs: Annotated[list[ConfigItemGroupSchema], Field(min_length=1)]
    default: Annotated[str | None, Field(default=None)]

    @field_validator("subs", mode="after")
    @classmethod
    def child_groups_are_regular(cls, groups: list[ConfigItemGroupSchema]) -> list[ConfigItemGroupSchema]:
        activatable_group_names = {group.name for group in groups if group.activatable}
        if activatable_group_names:
            message = (
                "Activatable groups aren't allowed as children "
                f"of selection groups: {', '.join(sorted(activatable_group_names))}"
            )
            raise ValueError(message)

        return groups

    @model_validator(mode="after")
    def default_is_one_of_subs(self) -> Self:
        if self.default is None:
            return self

        sub_group_names = {group.name for group in self.subs}
        if self.default not in sub_group_names:
            allowed_values_repr = ", ".join(sorted(sub_group_names))
            message = (
                f'Default (value="{self.default}") for selection group '
                f"must be name of one of it's subgroups: {allowed_values_repr}"
            )
            raise ValueError(message)

        return self

    @model_validator(mode="after")
    def default_not_none_if_set(self) -> Self:
        if "default" in self.model_fields_set and self.default is None:
            message = "Default must be string, even for non-required selectable groups"
            raise ValueError(message)

        return self


def config_duplicates(
    parameters: Sequence[CONFIG_ITEMS | ConfigItemGroupSchema | ConfigItemSelectionGroupSchema] | None,
):
    # at least ADS has duplicates in config
    if not parameters:
        return None

    names = set()

    for param in parameters:
        if param.name in names:
            raise ValueError(f"Duplicate config for key {param.name}")

        names.add(param.name)

        if isinstance(param, ConfigItemGroupSchema | ConfigItemSelectionGroupSchema):
            config_duplicates(param.subs)

    return parameters


ConfigAsList: TypeAlias = list[
    Annotated[CONFIG_ITEMS | ConfigItemGroupSchema | ConfigItemSelectionGroupSchema, Field(discriminator="type")]
]

ConfigAsListDictOrNone: TypeAlias = Annotated[
    ConfigAsList | None,
    Field(default=None),
    BeforeValidator(convert_config),
]
ConfigAsListDictOrNoneNoDuplicates: TypeAlias = Annotated[ConfigAsListDictOrNone, AfterValidator(config_duplicates)]
