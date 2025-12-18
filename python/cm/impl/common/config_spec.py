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
from pathlib import Path
from typing import Callable, Final, Iterable, TypeVar
import re
import json

from core import config

from cm.models import PrototypeConfig

_SECRET_TYPES = frozenset(("password", "secrettext", "secretfile", "secretmap"))

T = TypeVar("T")
V = TypeVar("V")


def build_specification(records: Iterable[PrototypeConfig], group_customization_flag: bool) -> config.spec.FullSpec:
    convert = partial(_convert_parameter, parent_group_customization_flag=group_customization_flag)

    parameters = tuple(map(convert, records))

    specification = config.spec.FullSpec.from_parameters(*parameters)

    if main_info := specification.parameters.get("/__main_info"):
        main_info.extra.ui_options["invisible"] = True

    return specification


def build_defaults(
    records: Iterable[PrototypeConfig],
    spec: config.spec.FullSpec,
    bundle_root: Path,
    encrypt: Callable[[str], str],
) -> config.Defaults:
    flat_values = {}
    activation = {}
    selection = {}

    for record in records:
        full_name = _get_record_full_name(record)

        try:
            parameter = spec.parameters[full_name]
        except KeyError:
            # it's a group
            group = spec.groups[full_name]
            if group.selection:
                selection[full_name] = record.default if record.default else None
            elif group.activation:
                activation[full_name] = record.limits.get("active", False)

            continue

        default = record.default
        if not isinstance(default, str):
            flat_values[full_name] = default
            continue

        if default == "":
            flat_values[full_name] = None
            continue

        match parameter:
            case config.spec.p.StringParameter(as_file=as_file, is_secret=is_secret):
                if as_file:
                    path = bundle_root / str(default)
                    if path.is_file():
                        default = path.read_text(encoding="utf-8")
                    else:
                        message = f"Missing file for {parameter.identifier.full} at {path}"
                        raise config.DefaultFileMissingError(message=message, parameter=parameter.identifier.full)

                if is_secret:
                    default = config.secrets.encrypt_if_possible(value=default, encryptor=encrypt)

            case config.spec.p.BooleanParameter():
                default = default.lower() in {"true", "yes"}

            case config.spec.p.NumberParameter(is_float=is_float):
                default = (float if is_float else int)(default)

            case config.spec.p.MapParameter(is_secret=is_secret):
                default = json.loads(default)

                if is_secret:
                    default = config.secrets.encrypt_if_possible(value=default, encryptor=encrypt)

            case (
                config.spec.p.ListParameter()
                | config.spec.p.JSONParameter()
                | config.spec.p.StructureParameter()
            ) if default:
                default = json.loads(default)

            case config.spec.p.OptionParameter():
                # patch due to default type (string) possible incompatibility with options
                #
                # todo see similar typecase in ansible config plugin:
                #  maybe it's worth moving this case to core.config.spec somewhere
                if default in parameter.options.values():
                    default = default
                elif re.match(r"^\d+$", default):
                    default = int(default)
                elif re.match(r"^\d+\.\d+$", default):
                    default = float(default)

        flat_values[full_name] = default

    return config.Defaults(values=flat_values, activation=activation, selection=selection)


def _convert_parameter(
    record: PrototypeConfig, parent_group_customization_flag: bool
) -> config.spec.p.SimpleParameter | config.spec.p.ParameterGroup:
    type_ = record.type

    full_name = _get_record_full_name(record)

    is_desyncable = record.group_customization
    if is_desyncable is None:
        is_desyncable = parent_group_customization_flag

    # some of these defaults aren't applied to all types, but since extra values are allowed
    # by parameter models, we can just put bit "extra" (for now)
    default_kwargs: Final = {
        "identifier": config.spec.build_identifier_from_name(full_name),
        "extra": config.spec.p.ExtraProperties(
            display_name=record.display_name,
            description=record.description,
            ui_options=record.ui_options,
            edit_rule=_detect_read_only_rule(record.limits),
        ),
        "is_required": record.required,
        "is_secret": type_ in _SECRET_TYPES,
        "is_desyncable": is_desyncable,
    }

    match type_:
        case "string" | "password" | "text" | "secrettext" | "file" | "secretfile":
            as_file = "file" in type_
            unsafe = (record.ansible_options or {}).get("unsafe", False)
            return config.spec.p.StringParameter(
                pattern=record.limits.get("pattern"),
                as_file=as_file,
                supports_multiline=as_file or ("text" in type_),
                ansible=config.spec.p.AnsibleOptions(unsafe=unsafe),
                **default_kwargs,
            )

        case "integer" | "float":
            return config.spec.p.NumberParameter(
                is_float=type_ == "float",
                min=record.limits.get("min"),
                max=record.limits.get("max"),
                **default_kwargs,
            )

        case "boolean":
            return config.spec.p.BooleanParameter(**default_kwargs)

        case "map" | "secretmap":
            return config.spec.p.MapParameter(**default_kwargs)
        case "list":
            return config.spec.p.ListParameter(**default_kwargs)
        case "json":
            return config.spec.p.JSONParameter(**default_kwargs)
        case "option":
            return config.spec.p.OptionParameter(options=record.limits["option"], **default_kwargs)
        case "variant":
            payload = {**record.limits["source"]}
            source_type = payload["type"]
            is_strict = payload.get("strict", False)
            return config.spec.p.VariantParameter(
                source=source_type, is_strict=is_strict, payload=payload, **default_kwargs
            )

        case "structure":
            return config.spec.p.StructureParameter(yspec=record.limits["yspec"], **default_kwargs)

        case "group":
            activation = None
            if record.limits.get("activatable"):
                activation = config.spec.p.Activation(
                    is_desyncable=is_desyncable,
                )

            return config.spec.p.ParameterGroup(
                identifier=default_kwargs["identifier"], extra=default_kwargs["extra"], activation=activation
            )

        case "selection_group":
            return config.spec.p.ParameterGroup(
                identifier=default_kwargs["identifier"],
                extra=default_kwargs["extra"],
                selection=config.spec.p.Selection(is_required=record.required),
            )

        case _:
            message = f"Unsupported type for conversion: {type_}"
            raise TypeError(message)


def _get_record_full_name(record: PrototypeConfig) -> config.ParameterFullName:
    return config.names.level_names_to_full_name((record.name, *record.subname.split("/")))


def _detect_read_only_rule(limits: dict) -> config.spec.p.WritableRule | config.spec.p.ReadOnlyRule:
    if read_only := limits.get("read_only"):
        return config.spec.p.ReadOnlyRule(read_only=read_only)

    if (writable := limits.get("writable")) and writable != "any":
        return config.spec.p.WritableRule(writable=writable)

    return config.spec.p.WritableRule(writable="any")
