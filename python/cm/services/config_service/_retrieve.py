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
import re
import json

from core import config
from core.types import ADCMCoreType, ADCMHostGroupType, CoreObjectDescriptor, HostGroupDescriptor
from django.conf import settings

from cm.models import ADCM, ConfigHostGroup, ConfigLog, MainObject, PrototypeConfig
from cm.services.config._base import convert_attr_to_adcm_meta
from cm.services.config_service import _repo as repo
from cm.services.config_service._secrets import AnsibleSecrets, encrypt_if_possible

_SECRET_TYPES = frozenset(("password", "secrettext", "secretfile", "secretmap"))


Defaults: TypeAlias = dict[config.ParameterFullName, Any]

T = TypeVar("T")


def get_current_configuration(owner: MainObject | ADCM | ConfigHostGroup) -> config.Configuration:
    if not owner.config:
        message = f"Unexpectedly got object without configuration: {owner.__class__.__name__} #{owner.pk}"
        raise ValueError(message)

    current_id = owner.config.current
    record = ConfigLog.objects.get(id=current_id)

    return _to_configuration(values=record.config, attrs=record.attr)


def get_configurations_of_host_groups(owner: CoreObjectDescriptor) -> dict[HostGroupDescriptor, config.Configuration]:
    if owner.type in (ADCMCoreType.HOST, ADCMCoreType.ADCM):
        return {}

    records = repo.get_configurations_of_host_groups(owner)

    return {
        HostGroupDescriptor(id=rec.group_id, type=ADCMHostGroupType.CONFIG): _to_configuration(
            values=rec.values, attrs=rec.attrs
        )
        for rec in records
    }


def get_specification(owner: CoreObjectDescriptor) -> tuple[config.spec.FullSpec, Defaults]:
    config_spec_info = repo.get_config_prototype_info(owner=owner)
    bundle_root = _build_path_to_bundle_root(owner=owner, bundle_hash=config_spec_info.bundle_hash)
    spec, defaults = _build_spec(
        config_prototype=config_spec_info, secrets_service=AnsibleSecrets(), bundle_root=bundle_root
    )
    return spec, defaults


def build_specification_from_prototype_config_records(
    records: tuple[PrototypeConfig, ...],
    group_customization_flag: bool,
    secrets_service: AnsibleSecrets,
    bundle_root: Path,
) -> tuple[config.spec.FullSpec, Defaults]:
    return _build_spec(
        config_prototype=repo.ConfigPrototypeInfo(
            bundle_hash="", group_customization_flag=group_customization_flag, parameter_prototypes=records
        ),
        bundle_root=bundle_root,
        secrets_service=secrets_service,
    )


def _build_path_to_bundle_root(owner: CoreObjectDescriptor, bundle_hash: str) -> Path:
    if owner.type == ADCMCoreType.ADCM:
        return Path(settings.BASE_DIR, "conf", "adcm")

    return Path(settings.BUNDLE_DIR, bundle_hash)


def _build_spec(
    config_prototype: repo.ConfigPrototypeInfo,
    # most likely it's correct to put encrypt in here instead of service,
    # because not in all cases encryption is required
    secrets_service: AnsibleSecrets,
    bundle_root: Path,
) -> tuple[config.spec.FullSpec, Defaults]:
    result_spec = config.spec.FullSpec()

    group_members: dict[str, list[str]] = defaultdict(list)
    prototype_group_customization = config_prototype.group_customization_flag
    defaults = {}

    for orm_spec in config_prototype.parameter_prototypes:
        if orm_spec.type != "group":
            param, default = _register_simple_parameter_in_spec(
                config_proto_entry=orm_spec,
                spec=result_spec,
                prototype_group_customization=prototype_group_customization,
                encrypt=secrets_service.encrypt,
                bundle_root=bundle_root,
            )

            level_name = param.identifier.name

            if orm_spec.subname:
                group_members[orm_spec.name].append(level_name)
            else:
                result_spec.hierarchy.fields.append(level_name)

            defaults[param.identifier.full] = default

            continue

        identifier = config.spec.p.Identifier(
            name=orm_spec.subname or orm_spec.name,
            full=config.names.level_names_to_full_name_safe((orm_spec.name, orm_spec.subname)),
        )
        extra = config.spec.p.ExtraProperties(
            display_name=orm_spec.display_name, description=orm_spec.description, ui_options=orm_spec.ui_options
        )

        activation = None
        if orm_spec.limits.get("activatable"):
            is_desyncable = orm_spec.group_customization
            if is_desyncable is None:
                is_desyncable = prototype_group_customization

            activation = config.spec.p.Activation(
                edit_rule=_detect_read_only_rule(orm_spec.limits),
                is_desyncable=is_desyncable,
                is_active_by_default=orm_spec.limits.get("active", False),
            )

        group = config.spec.p.ParameterGroup(identifier=identifier, extra=extra, activation=activation)

        result_spec.groups[group.identifier.full] = group
        result_spec.hierarchy.child_groups[group.identifier.name] = config.spec.SpecHierarchyLevel()
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
    spec: config.spec.FullSpec,
    prototype_group_customization: bool,
    encrypt: Callable[[str], str],
    bundle_root: Path,
) -> tuple[config.spec.p.SimpleParameter, Any]:
    is_desyncable = config_proto_entry.group_customization
    if is_desyncable is None:
        is_desyncable = prototype_group_customization

    type_ = config_proto_entry.type
    default_kwargs = {
        "identifier": config.spec.p.Identifier(
            name=config_proto_entry.subname or config_proto_entry.name,
            full=config.names.level_names_to_full_name_safe((config_proto_entry.name, config_proto_entry.subname)),
        ),
        "extra": config.spec.p.ExtraProperties(
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
            parameter = config.spec.p.StringParameter(
                pattern=config_proto_entry.limits.get("pattern"),
                as_file=as_file,
                supports_multiline=as_file or ("text" in type_),
                **default_kwargs,
            )
            if parameter.as_file:
                # Temporal patch, because defaults for files are paths, but we want content
                default = (bundle_root / str(default)).read_text(encoding="utf-8") if default is not None else default

        case "integer" | "float":
            is_float = type_ == "float"

            parameter = config.spec.p.NumberParameter(
                is_float=type_ == "float",
                min=config_proto_entry.limits.get("min"),
                max=config_proto_entry.limits.get("max"),
                **default_kwargs,
            )

            default = _parse_default_if_not_none(default, float if is_float else int)

        case "boolean":
            parameter = config.spec.p.BooleanParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, lambda x: x.lower() in {"true", "yes"})

        case "map" | "secretmap":
            parameter = config.spec.p.MapParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "list":
            parameter = config.spec.p.ListParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "json":
            parameter = config.spec.p.JSONParameter(**default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case "option":
            parameter = config.spec.p.OptionParameter(options=config_proto_entry.limits["option"], **default_kwargs)
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
            parameter = config.spec.p.VariantParameter(
                source=source_type, is_strict=is_strict, payload=payload, **default_kwargs
            )

            # temporarily disabled; maybe not required
            # if source_type == "config":
            #    source_param_name = config.names.ensure_full_name(payload["name"])
            #    spec.dependencies.internal.setdefault(source_param_name, set()).add(parameter.identifier.full)
            # elif source_type == "builtin":
            #    spec.dependencies.external.add(parameter.identifier.full)

        case "structure":
            parameter = config.spec.p.StructureParameter(yspec=config_proto_entry.limits["yspec"], **default_kwargs)
            default = _parse_default_if_not_none(default, json.loads)
        case _:
            message = f"Unsupported type for conversion: {type_.value}"
            raise TypeError(message)

    if parameter.is_desyncable:
        spec.attributes.desyncable_parameters.add(parameter.identifier.full)

    # improve when possible, is_secret is no more part of base parameter,
    # probably should just use `encrypt_secrets`
    if getattr(parameter, "is_secret", False) and default:
        default = encrypt_if_possible(value=default, encryptor=encrypt)

    if parameter.identifier.name == "__main_info":
        parameter.extra.ui_options["invisible"] = True

    spec.parameters[parameter.identifier.full] = parameter

    return parameter, default


def _detect_read_only_rule(limits: dict) -> config.spec.p.WritableRule | config.spec.p.ReadOnlyRule:
    if read_only := limits.get("read_only"):
        return config.spec.p.ReadOnlyRule(read_only=read_only)

    if (writable := limits.get("writable")) and writable != "any":
        return config.spec.p.WritableRule(writable=writable)

    return config.spec.p.WritableRule(writable="any")


def _parse_default_if_not_none(default: str | None, convert: Callable[[str], T]) -> T | None:
    if default is None:
        return None

    return convert(default)


def _to_configuration(values: dict, attrs: dict) -> config.Configuration:
    attributes_raw = convert_attr_to_adcm_meta(attrs)

    attributes = {
        name: config.Attributes(is_active=entry.get("isActive"), is_synced=entry.get("isSynchronized"))
        for name, entry in attributes_raw.items()
    }

    return config.Configuration(values=values, attributes=attributes)
