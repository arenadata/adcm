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

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, TypeAlias, TypeVar
import json

from ansible.errors import re
from core.types import PrototypeID

from cm.services.config_alt import repo
from cm.services.config_alt._common import encrypt_if_possible
from cm.services.config_alt.types import (
    Activation,
    BooleanParameter,
    ExtraProperties,
    FullSpec,
    Identifier,
    JSONParameter,
    ListParameter,
    MapParameter,
    NumberParameter,
    OptionParameter,
    ParameterFullName,
    ParameterGroup,
    ReadOnlyRule,
    SimpleParameter,
    SpecHierarchyLevel,
    StringParameter,
    StructureParameter,
    VariantParameter,
    WritableRule,
    ensure_full_name,
    level_names_to_full_name_safe,
)

_SECRET_TYPES = frozenset(("password", "secrettext", "secretfile", "secretmap"))


Defaults: TypeAlias = dict[ParameterFullName, Any]

T = TypeVar("T")


def retrieve_object_full_spec(
    prototype: PrototypeID, encrypt: Callable[[str], str], bundle_root: Path
) -> tuple[FullSpec, Defaults]:
    result_spec = FullSpec()

    group_members: dict[str, list[str]] = defaultdict(list)
    prototype_group_customization = repo.get_prototype_group_customization_flag(prototype)
    defaults = {}

    for orm_spec in repo.retrieve_object_config_prototypes(prototype_id=prototype):
        if orm_spec.type != "group":
            param, default = _register_simple_parameter_in_spec(
                config_proto_entry=orm_spec,
                spec=result_spec,
                prototype_group_customization=prototype_group_customization,
                encrypt=encrypt,
                bundle_root=bundle_root,
            )

            level_name = param.identifier.name

            if orm_spec.subname:
                group_members[orm_spec.name].append(level_name)
            else:
                result_spec.hierarchy.fields.append(level_name)

            defaults[param.identifier.full] = default

            continue

        identifier = Identifier(
            name=orm_spec.subname or orm_spec.name,
            full=level_names_to_full_name_safe((orm_spec.name, orm_spec.subname)),
        )
        extra = ExtraProperties(
            display_name=orm_spec.display_name, description=orm_spec.description, ui_options=orm_spec.ui_options
        )

        activation = None
        if orm_spec.limits.get("activatable"):
            is_desyncable = orm_spec.group_customization
            if is_desyncable is None:
                is_desyncable = prototype_group_customization

            activation = Activation(
                edit_rule=_detect_read_only_rule(orm_spec.limits),
                is_desyncable=is_desyncable,
                is_active_by_default=orm_spec.limits.get("active", False),
            )

        group = ParameterGroup(identifier=identifier, extra=extra, activation=activation)

        result_spec.groups[group.identifier.full] = group
        result_spec.hierarchy.child_groups[group.identifier.name] = SpecHierarchyLevel()
        result_spec.hierarchy.fields.append(group.identifier.name)

        if group.is_activatable:
            result_spec.attributes.activatable_groups.add(group.identifier.full)
            if group.activation and group.activation.is_desyncable:
                result_spec.attributes.desyncable_parameters.add(group.identifier.full)

    for group_name, children_names in group_members.items():
        result_spec.hierarchy.child_groups[group_name].fields = children_names

    return result_spec, defaults


def _register_simple_parameter_in_spec(
    config_proto_entry,
    spec: FullSpec,
    prototype_group_customization: bool,
    encrypt: Callable[[str], str],
    bundle_root: Path,
) -> tuple[SimpleParameter, Any]:
    is_desyncable = config_proto_entry.group_customization
    if is_desyncable is None:
        is_desyncable = prototype_group_customization

    type_ = config_proto_entry.type
    default_kwargs = {
        "identifier": Identifier(
            name=config_proto_entry.subname or config_proto_entry.name,
            full=level_names_to_full_name_safe((config_proto_entry.name, config_proto_entry.subname)),
        ),
        "extra": ExtraProperties(
            display_name=config_proto_entry.display_name,
            description=config_proto_entry.description,
            ui_options=config_proto_entry.ui_options,
        ),
        "edit_rule": _detect_read_only_rule(config_proto_entry.limits),
        "is_required": config_proto_entry.required,
        "is_desyncable": is_desyncable,
        "is_secret": type_ in _SECRET_TYPES,
    }

    # In orm spec default is always a string, so empty string is None
    #
    # Note: during bundle parsing condider even specified default="" as default=None
    default = config_proto_entry.default if config_proto_entry.default else None

    match type_:
        case "string" | "password" | "text" | "secrettext" | "file" | "secretfile":
            as_file = "file" in type_
            parameter = StringParameter(
                pattern=config_proto_entry.limits.get("pattern"),
                as_file=as_file,
                supports_multiline=as_file or ("text" in type_),
                **default_kwargs,
            )
            if parameter.as_file:
                # Temporal patch, because defaults for files are paths, but we want content
                default = (bundle_root / str(default)).read_text(encoding="utf-8")

        case "integer" | "float":
            is_float = type_ == "float"

            parameter = NumberParameter(
                is_float=type_ == "float",
                min=config_proto_entry.limits.get("min"),
                max=config_proto_entry.limits.get("max"),
                **default_kwargs,
            )

            default = _parse_default_if_not_none(default, float if is_float else int)

        case "boolean":
            parameter = BooleanParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, lambda x: x.lower() in {"true", "yes"})

        case "map" | "secretmap":
            parameter = MapParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "list":
            parameter = ListParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "json":
            parameter = JSONParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "option":
            parameter = OptionParameter(options=config_proto_entry.limits["option"], **default_kwargs)
            if default is not None:
                # patch due to default type (string) possible incompatibility with options
                if default in parameter.options.values():
                    default = default
                elif re.match(r"^\d+$", default):
                    default = int(default)
                elif re.match(r"^\d+\.\d+$", default):
                    default = float(default)
        case "variant":
            payload = config_proto_entry.limits["source"]
            source_type = payload.pop("type")
            is_strict = payload.pop("strict", False)
            parameter = VariantParameter(source=source_type, is_strict=is_strict, payload=payload, **default_kwargs)

            if source_type == "config":
                source_param_name = ensure_full_name(payload["name"])
                spec.dependencies.internal.setdefault(source_param_name, set()).add(parameter.identifier.full)
            elif source_type == "builtin":
                spec.dependencies.external.add(parameter.identifier.full)

        case "structure":
            parameter = StructureParameter(yspec=config_proto_entry.limits["yspec"], **default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case _:
            message = f"Unsupported type for conversion: {type_.value}"
            raise TypeError(message)

    if parameter.is_desyncable:
        spec.attributes.desyncable_parameters.add(parameter.identifier.full)

    if parameter.is_secret and default:
        default = encrypt_if_possible(value=default, encryptor=encrypt)

    if parameter.identifier.name == "__main_info":
        parameter.extra.ui_options["invisible"] = True

    spec.parameters[parameter.identifier.full] = parameter

    return parameter, default


def _detect_read_only_rule(limits: dict) -> WritableRule | ReadOnlyRule:
    if read_only := limits.get("read_only"):
        return ReadOnlyRule(read_only=read_only)

    if (writable := limits.get("writable")) and writable != "any":
        return WritableRule(writable=writable)

    return WritableRule(writable="any")


def _parse_default_if_not_none(default: str | None, convert: Callable[[str], T]) -> T | None:
    if default is None:
        return None

    return convert(default)
