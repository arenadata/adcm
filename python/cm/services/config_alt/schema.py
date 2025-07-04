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

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from functools import cache, partial
from typing import Any, Callable, Collection, Generator, Literal, Mapping, Protocol, TypeAlias, TypedDict
import json

from core.types import ObjectID
from typing_extensions import NotRequired, Self

from cm.services.config_alt import repo
from cm.services.config_alt._common import is_editable
from cm.services.config_alt._variant import resolve_variant
from cm.services.config_alt.types import (
    ConfigOwner,
    ConfigOwnerObjectInfo,
    Configuration,
    FullSpec,
    ListParameter,
    MapParameter,
    NumberParameter,
    OptionParameter,
    ParameterFullName,
    ParameterGroup,
    ParameterLevelName,
    ParameterType,
    SimpleParameter,
    SpecHierarchyLevel,
    StringParameter,
    StructureParameter,
    VariantParameter,
    level_names_to_full_name,
)

Defaults: TypeAlias = dict[ParameterFullName, Any]

_TYPE_MAPPING: dict[ParameterType, str] = {
    ParameterType.BOOLEAN: "boolean",
    ParameterType.MAP: "object",
    ParameterType.LIST: "array",
    ParameterType.JSON: "string",
    ParameterType.STRING: "string",
}


class ADCMMetaDict(TypedDict):
    isAdvanced: bool
    isInvisible: bool
    isSecret: bool
    activation: dict | None
    synchronization: dict | None
    stringExtra: NotRequired[dict | None]
    enumExtra: NotRequired[dict | None]
    nullValue: NotRequired[Any]


NoneNode: TypeAlias = dict[Literal["type"], Literal["null"]]


class JSONSchemaNodeDict(TypedDict):
    title: str
    # type and enum disallow one another
    type: NotRequired[str]
    enum: NotRequired[list]
    description: str
    default: NotRequired[Any]
    readOnly: bool
    adcmMeta: ADCMMetaDict

    required: NotRequired[list[ParameterLevelName]]

    items: NotRequired[Self]
    minItems: NotRequired[int]

    properties: NotRequired[dict[ParameterLevelName, Self | dict[Literal["oneOf"], Self | NoneNode]]]
    additionalProperties: NotRequired[bool]
    minProperties: NotRequired[int]

    minLength: NotRequired[int]
    pattern: NotRequired[str]
    format: NotRequired[str]

    maximum: NotRequired[int | float]
    minimum: NotRequired[int | float]


OptionalNode: TypeAlias = JSONSchemaNodeDict | dict[Literal["oneOf"], list[JSONSchemaNodeDict | NoneNode]]


class SchemaGenerationContext(Protocol):
    is_group_config: bool
    owner_info: ConfigOwnerObjectInfo
    defaults: Mapping[ParameterFullName, Any]
    variant_values: Mapping[ParameterFullName, Collection[str]]


@dataclass(slots=True)
class _Context:
    spec: FullSpec
    defaults: Defaults
    owner: ConfigOwner
    is_group_config: bool
    retrieve_config: Callable[[], Configuration]


def spec_to_jsonschema(
    spec: FullSpec,
    defaults: Defaults,
    owner: ConfigOwner,
    host_group_id: ObjectID | None,
) -> dict:
    if host_group_id is not None:
        is_group_config = True
        retrieve_config = partial(repo.get_host_group_configuration, group_id=host_group_id)
    else:
        is_group_config = False
        retrieve_config = partial(repo.get_object_configuration, owner=owner.descriptor)

    context = _Context(
        spec=spec,
        defaults=defaults,
        owner=owner,
        is_group_config=is_group_config,
        retrieve_config=cache(retrieve_config),
    )

    properties = OrderedDict()
    required = []
    root_schema = {
        "title": "Configuration",
        "description": "",
        "readOnly": False,
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
        "adcmMeta": {
            "isAdvanced": False,
            "isInvisible": False,
            "activation": None,
            "synchronization": None,
            "nullValue": None,
            "isSecret": False,
            "stringExtra": None,
            "enumExtra": None,
        },
        "$schema": "https://json-schema.org/draft/2020-12/schema",
    }

    for property_name, schema in _hierarchy_level_to_jsonschema(
        level=spec.hierarchy, previous_levels=(), context=context
    ):
        required.append(property_name)
        properties[property_name] = schema

    return root_schema


def _hierarchy_level_to_jsonschema(
    level: SpecHierarchyLevel, previous_levels: tuple[str, ...], context: _Context
) -> Generator[tuple[ParameterLevelName, OptionalNode], None, None]:
    for parameter_level_name in level.fields:
        levels = (*previous_levels, parameter_level_name)
        full_name = level_names_to_full_name(levels)

        if parameter_level_name in level.child_groups:
            group_spec = context.spec.groups[full_name]
            schema = _group_parameter_to_schema(group=group_spec, context=context)

            properties = OrderedDict()
            for child_name, child_schema in _hierarchy_level_to_jsonschema(
                level=level.child_groups[parameter_level_name], previous_levels=levels, context=context
            ):
                properties[child_name] = child_schema

            schema["properties"] = properties
            schema["required"] = list(properties)

        else:
            param_spec = context.spec.parameters[full_name]
            schema = _simple_parameter_to_schema(parameter=param_spec, context=context)

        yield parameter_level_name, schema


def _simple_parameter_to_schema(parameter: SimpleParameter, context: _Context) -> OptionalNode:
    is_read_only = not is_editable(rule=parameter.edit_rule, owner=context.owner.info)
    schema = _get_basic_schema(parameter=parameter, read_only=is_read_only)

    type_ = _TYPE_MAPPING.get(parameter.type)
    if type_:
        schema["type"] = type_
    elif isinstance(parameter, NumberParameter):
        schema["type"] = "number" if parameter.is_float else "integer"
    schema["default"] = context.defaults.get(parameter.identifier.full)

    if context.is_group_config:
        desyncable = parameter.identifier.full in context.spec.attributes.desyncable_parameters
        schema["adcmMeta"]["synchronization"] = {"isAllowChange": desyncable}

    _fill_type_specifics_to_schema_node(
        schema=schema, parameter=parameter, owner=context.owner, retrieve_config=context.retrieve_config
    )

    # check for type is required, because "enum" based parameters' nullability is different
    if not parameter.is_required and "type" in schema:
        schema: OptionalNode = {"oneOf": [schema, {"type": "null"}]}

    return schema


def _group_parameter_to_schema(group: ParameterGroup, context: _Context) -> JSONSchemaNodeDict:
    is_read_only = bool(group.activation and not is_editable(rule=group.activation.edit_rule, owner=context.owner.info))
    schema: JSONSchemaNodeDict = _get_basic_schema(parameter=group, read_only=is_read_only)

    schema["type"] = "object"
    schema["additionalProperties"] = False
    schema["default"] = {}

    if group.is_activatable:
        schema["adcmMeta"]["activation"] = {"isAllowChange": not is_read_only}
        if context.is_group_config:
            is_allow_change = group.identifier.full in context.spec.attributes.desyncable_parameters
            schema["adcmMeta"]["synchronization"] = {"isAllowChange": is_allow_change}

    return schema


def _get_basic_schema(parameter: SimpleParameter | ParameterGroup, read_only: bool) -> JSONSchemaNodeDict:
    return JSONSchemaNodeDict(
        title=parameter.extra.display_name,
        description=parameter.extra.description,
        readOnly=read_only,
        default=None,
        adcmMeta=ADCMMetaDict(
            isAdvanced=parameter.extra.ui_options.get("advanced", False),
            isInvisible=parameter.extra.ui_options.get("invisible", False),
            isSecret=parameter.is_secret if not isinstance(parameter, ParameterGroup) else False,
            activation=None,
            synchronization=None,
            stringExtra=None,
            enumExtra=None,
        ),
    )


def _fill_type_specifics_to_schema_node(
    schema: JSONSchemaNodeDict,
    parameter: SimpleParameter,
    owner: ConfigOwner,
    retrieve_config: Callable[[], Configuration],
) -> None:
    if schema.get("type") == "string":
        if parameter.is_required:
            schema["minLength"] = 1

        if isinstance(parameter, StringParameter) and parameter.pattern is not None:
            schema["pattern"] = parameter.pattern

        is_multiline = (
            isinstance(parameter, StringParameter) and parameter.supports_multiline
        ) or parameter.type == ParameterType.JSON

        schema["adcmMeta"]["stringExtra"] = {"isMultiline": is_multiline}

        if parameter.type == ParameterType.JSON:
            schema["format"] = "json"
            if (default := schema.get("default")) is not None:
                schema["default"] = json.dumps(default)

        return

    if isinstance(parameter, NumberParameter):
        if parameter.max:
            schema["maximum"] = parameter.max

        if parameter.min:
            schema["minimum"] = parameter.min

        return

    match parameter:
        case MapParameter():
            schema["additionalProperties"] = True
            schema["properties"] = {}
            if parameter.is_required:
                schema["minProperties"] = 1

            if schema.get("default") is None:
                schema["default"] = {}

        case ListParameter():
            schema["items"] = JSONSchemaNodeDict(
                type="string",
                title="",
                description="",
                default=None,
                readOnly=schema["readOnly"],
                adcmMeta=ADCMMetaDict(
                    isAdvanced=False,
                    isInvisible=False,
                    activation=None,
                    synchronization=None,
                    nullValue=None,
                    isSecret=False,
                    stringExtra=None,
                    enumExtra=None,
                ),
            )

            if schema.get("default") is None:
                schema["default"] = []

        case VariantParameter(is_strict=is_strict):
            choices = sorted(
                resolve_variant(
                    parameter=parameter,
                    retrieve_current_config=retrieve_config,
                    owner=owner.descriptor,
                )
            )

            if is_strict:
                schema["adcmMeta"]["stringExtra"] = {"isMultiline": False}

                if not parameter.is_required and None not in choices:
                    schema["enum"] = [*choices, None]
                else:
                    schema["enum"] = choices

            else:
                schema["type"] = "string"
                schema["adcmMeta"]["stringExtra"] = {"isMultiline": False, "suggestions": choices}
                if parameter.is_required:
                    schema["minLength"] = 1

        case OptionParameter():
            enum = []
            labels = []

            for label, value in parameter.options.items():
                enum.append(value)
                labels.append(label)

            schema["enum"] = enum
            schema["adcmMeta"]["enumExtra"] = {"labels": labels}

        case StructureParameter():
            _fill_structure_parameter_node(schema=schema, parameter=parameter)

    if not schema.get("type") and schema.get("enum") is None:
        # failsafe
        message = f"Failed to prepare schema for parameter {parameter.identifier.full}"
        raise RuntimeError(message)


def _fill_structure_parameter_node(schema: JSONSchemaNodeDict, parameter: StructureParameter) -> None:
    root_type = schema["type"] = _get_schema_type(parameter.yspec["root"]["match"])
    parameter_is_invisible = schema["adcmMeta"]["isInvisible"]

    if root_type == "array":
        if schema.get("default") is None:
            schema["default"] = []

        item_node_name = parameter.yspec["root"]["item"]
        schema["items"] = _get_structure_item_schema(
            yspec_schema=parameter.yspec,
            item_yspec_node=parameter.yspec[item_node_name],
            is_parent_invisible=parameter_is_invisible,
            parent_schema=schema,
        )
        if parameter.is_required:
            schema["minItems"] = 1

    elif root_type == "object":
        if schema.get("default") is None:
            schema["default"] = {}

        schema["additionalProperties"] = False
        schema["required"] = parameter.yspec["root"].get("required_items", [])

        invisible_items = set(parameter.yspec["root"].get("invisible_items", ()))
        properties = {}
        for item_key, item_value in parameter.yspec["root"]["items"].items():
            is_invisible = parameter_is_invisible or item_key in invisible_items
            properties[item_key] = _get_structure_item_schema(
                yspec_schema=parameter.yspec,
                item_yspec_node=parameter.yspec[item_value],
                is_parent_invisible=is_invisible,
                parent_schema=schema,
                title=item_key,
            )

        schema["properties"] = properties


def _get_schema_type(type_: str) -> str:
    match type_:
        case "list":
            return "array"
        case "dict":
            return "object"
        case "bool":
            return "boolean"
        case "string":
            return "string"
        case "int":
            return "integer"
        case "float":
            return "number"
        case _:
            raise NotImplementedError


def _get_structure_item_schema(
    yspec_schema: dict,
    item_yspec_node: dict,
    is_parent_invisible: bool,
    parent_schema: JSONSchemaNodeDict,
    title: str = "",
) -> JSONSchemaNodeDict:
    node_type = _get_schema_type(item_yspec_node["match"])
    meta_ = deepcopy(parent_schema["adcmMeta"])
    meta_["isInvisible"] = is_parent_invisible
    meta_["synchronization"] = None

    schema = JSONSchemaNodeDict(
        {
            "type": node_type,
            "title": title,
            "description": "",
            "default": None,
            "readOnly": parent_schema["readOnly"],
            "adcmMeta": meta_,
        }
    )

    if node_type == "array":
        schema["default"] = []
        schema["items"] = _get_structure_item_schema(
            yspec_schema=yspec_schema,
            item_yspec_node=yspec_schema[item_yspec_node["item"]],
            is_parent_invisible=is_parent_invisible,
            parent_schema=parent_schema,
        )

    elif node_type == "object":
        schema["default"] = {}
        required_items = item_yspec_node.get("required_items", [])
        schema["additionalProperties"] = False
        schema["required"] = required_items

        properties = {}
        invisible_items = set(item_yspec_node.get("invisible_items", ()))
        for item_key, item_value in item_yspec_node["items"].items():
            is_invisible = is_parent_invisible or item_key in invisible_items
            item_schema = _get_structure_item_schema(
                yspec_schema=yspec_schema,
                item_yspec_node=yspec_schema[item_value],
                parent_schema=parent_schema,
                is_parent_invisible=is_invisible,
                title=item_key,
            )
            if item_schema["title"] not in required_items and item_schema.get("type") not in ("array", "object"):
                # Here pyright will say that default is required, but it's not for sub nodes of structure.
                # Yet it's too tricky to make it non-required totally
                # and separate type feels "a lot", so this ignore is helpful.
                item_schema.pop("default", None)

            properties[item_key] = item_schema

        schema["properties"] = properties

    return schema
