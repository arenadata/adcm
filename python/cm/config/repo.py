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

from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar
import re
import json

from core import config
from core.types import (
    ActionID,
    ADCMCoreType,
    ADCMHostGroupType,
    ConfigID,
    CoreObjectDescriptor,
    HostGroupDescriptor,
    ObjectOrGroup,
    PrototypeID,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F

from cm.converters import core_type_to_model
from cm.models import ADCM, ConfigHostGroup, ConfigLog, MainObject, ObjectConfig, Prototype, PrototypeConfig
from cm.services.config._base import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta

_SECRET_TYPES = frozenset(("password", "secrettext", "secretfile", "secretmap"))

T = TypeVar("T")


@dataclass(slots=True)
class ConfigPrototypeInfo:
    bundle_hash: str
    group_customization_flag: bool
    parameter_prototypes: tuple[PrototypeConfig, ...]


@dataclass(slots=True)
class ConfigRepo(config.ConfigRepoI):
    secrets: config.secrets.AnsibleSecrets
    # retrieve

    def get_config(self, owner: ObjectOrGroup) -> config.ConfigurationWithID:
        owner_model = _detect_owner_model(owner)

        owner_orm = owner_model.objects.select_related("config").get(pk=owner.id)

        if not owner_orm.config:
            message = f"Unexpectedly got object without configuration: {owner}"
            raise config.ObjectWithoutConfigError(message)

        current_id = owner_orm.config.current

        try:
            record = self.find_configs_by_ids(ids=(current_id,))[current_id]
        except KeyError as e:
            raise config.NoConfigError(f"configuration unexpectedly missing: id={current_id}") from e

        return config.ConfigurationWithID(id=current_id, values=record.values, attributes=record.attributes)

    def get_spec_and_defaults(
        self, owner: CoreObjectDescriptor, action_id: ActionID | None
    ) -> tuple[config.spec.FullSpec, config.Defaults]:
        config_spec_info = _get_config_prototype_info(owner=owner, action_id=action_id)
        if not config_spec_info.parameter_prototypes:
            message = f"Unexpectedly got object without configuration: {owner}"
            raise config.ObjectWithoutConfigError(message)

        bundle_root = _build_path_to_bundle_root(owner_type=owner.type, bundle_hash=config_spec_info.bundle_hash)
        spec, defaults = _build_spec(
            config_prototype=config_spec_info, secrets_service=self.secrets, bundle_root=bundle_root
        )
        return spec, defaults

    def find_configs_by_ids(self, ids: Iterable[ConfigID]) -> dict[ConfigID, config.Configuration]:
        records = _get_configs_by_ids(ids=ids)
        return {
            config_id: _to_configuration(values=record.config, attrs=record.attr)
            for config_id, record in records.items()
        }

    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID]
    ) -> dict[PrototypeID, tuple[config.spec.FullSpec, config.Defaults]]:
        ids_ = tuple(ids)

        proto_dir_mapping_query = Prototype.objects.filter(id__in=ids_).values_list("id", "type", "bundle__hash")
        proto_dir_map = {
            prototype_id: _build_path_to_bundle_root(owner_type=ADCMCoreType(type_), bundle_hash=bundle_hash)
            for prototype_id, type_, bundle_hash in proto_dir_mapping_query.all()
        }

        config_prototypes = _get_config_prototypes_info_by_ids(ids=ids_)

        return {
            prototype_id: _build_spec(
                config_prototype=info, secrets_service=self.secrets, bundle_root=proto_dir_map[prototype_id]
            )
            for prototype_id, info in config_prototypes.items()
        }

    # todo: shouldn't be here, see service for more info
    def find_host_group_configurations(
        self, owner: CoreObjectDescriptor
    ) -> dict[HostGroupDescriptor, config.Configuration]:
        if owner.type in (ADCMCoreType.HOST, ADCMCoreType.ADCM):
            return {}

        model = core_type_to_model(owner.type)
        content_type = ContentType.objects.get_for_model(model)

        group_config_id_query = ConfigHostGroup.objects.filter(
            object_id=owner.id, object_type=content_type
        ).values_list("id", "config__current")
        group_config_id_map: dict[int, int] = dict(group_config_id_query)

        configs_query = ConfigLog.objects.filter(id__in=group_config_id_map.values())
        configs = {config.pk: (config.config, config.attr) for config in configs_query}

        records = ((group_id, *configs[config_id]) for group_id, config_id in group_config_id_map.items())

        return {
            HostGroupDescriptor(id=group_id, type=ADCMHostGroupType.CONFIG): _to_configuration(
                values=values, attrs=attrs
            )
            for group_id, values, attrs in records
        }

    # change

    def set_new_config_for_object(
        self, config: config.Configuration, description: str, owner: ObjectOrGroup
    ) -> ConfigID:
        owner_model = _detect_owner_model(owner)
        owner_orm = owner_model.objects.select_related("config").get(id=owner.id)
        meta_like_attr = defaultdict(dict)
        for name, value in config.attributes.items():
            if value.activation:
                meta_like_attr[name]["isActive"] = value.is_active

            if value.synchronization:
                meta_like_attr[name]["isSynchronized"] = value.is_synced

        attr = convert_adcm_meta_to_attr(meta_like_attr)

        # maybe shouldn't be in here
        if not owner_orm.config:
            owner_orm.config = ObjectConfig.objects.create(current=0, previous=0)
            owner_orm.save(update_fields=["config"])

        config_log = ConfigLog.objects.create(
            obj_ref=owner_orm.config, config=config.values, attr=attr, description=description
        )

        owner_orm.config.previous = owner_orm.config.current
        owner_orm.config.current = config_log.pk
        owner_orm.config.save(update_fields=["previous", "current"])

        return config_log.pk


# todo temporal, should be moved in repo or service
def build_specification_from_prototype_config_records(
    records: tuple[PrototypeConfig, ...],
    group_customization_flag: bool,
    secrets_service: config.secrets.AnsibleSecrets,
    bundle_root: Path,
) -> tuple[config.spec.FullSpec, config.Defaults]:
    return _build_spec(
        config_prototype=ConfigPrototypeInfo(
            bundle_hash="", group_customization_flag=group_customization_flag, parameter_prototypes=records
        ),
        bundle_root=bundle_root,
        secrets_service=secrets_service,
    )


def _detect_owner_model(owner: ObjectOrGroup) -> type[MainObject | ADCM | ConfigHostGroup]:
    match owner:
        case CoreObjectDescriptor(type=type_):
            return core_type_to_model(type_)
        case HostGroupDescriptor():
            return ConfigHostGroup


def _get_config_prototype_info(owner: CoreObjectDescriptor, action_id: int | None) -> ConfigPrototypeInfo:
    model = core_type_to_model(owner.type)
    response = model.objects.values(
        "prototype_id",
        customization=F("prototype__config_group_customization"),
        bundle_hash=F("prototype__bundle__hash"),
    ).get(id=owner.id)
    parameter_prototypes = tuple(
        PrototypeConfig.objects.filter(prototype_id=response["prototype_id"], action_id=action_id).order_by("pk")
    )

    return ConfigPrototypeInfo(
        bundle_hash=response["bundle_hash"],
        group_customization_flag=response["customization"],
        parameter_prototypes=parameter_prototypes,
    )


def _get_configs_by_ids(ids: Iterable[ConfigID]) -> dict[ConfigID, ConfigLog]:
    query = ConfigLog.objects.filter(id__in=ids)
    return {record.pk: record for record in query}


def _get_config_prototypes_info_by_ids(ids: Iterable[PrototypeID]) -> dict[PrototypeID, ConfigPrototypeInfo]:
    prototypes_query = Prototype.objects.filter(id__in=ids).values(
        "id", customization=F("config_group_customization"), bundle_hash=F("bundle__hash")
    )
    records = {p["id"]: p for p in prototypes_query}

    prototype_configs_query = PrototypeConfig.objects.filter(prototype_id__in=records.keys(), action_id=None).order_by(
        "pk"
    )
    parameter_prototypes = defaultdict(deque)
    for prototype_config in prototype_configs_query:
        parameter_prototypes[prototype_config.prototype_id].append(prototype_config)  # pyright: ignore [reportAttributeAccessIssue]

    return {
        prototype_id: ConfigPrototypeInfo(
            bundle_hash=info["bundle_hash"],
            group_customization_flag=info["customization"],
            parameter_prototypes=tuple(parameter_prototypes.get(prototype_id, ())),
        )
        for prototype_id, info in records.items()
    }


# todo put to repo dependencies
def _build_path_to_bundle_root(owner_type: ADCMCoreType, bundle_hash: str) -> Path:
    if owner_type == ADCMCoreType.ADCM:
        return Path(settings.BASE_DIR, "conf", "adcm")

    return Path(settings.BUNDLE_DIR, bundle_hash)


def _build_spec(
    config_prototype: ConfigPrototypeInfo,
    # most likely it's correct to put encrypt in here instead of service,
    # because not in all cases encryption is required
    secrets_service: config.secrets.AnsibleSecrets,
    bundle_root: Path,
    # adjustment for times when defaults are ignored, so bundle root may be a dummy => files can't be read
    ignore_missing_files: bool = False,
) -> tuple[config.spec.FullSpec, config.Defaults]:
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
                ignore_missing_files=ignore_missing_files,
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
    # adjustment for times when defaults are ignored, so bundle root may be a dummy => files can't be read
    ignore_missing_files: bool = False,
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
            # Temporal patch, because defaults for files are paths, but we want content
            if parameter.as_file and default is not None:
                path = bundle_root / str(default)
                if path.is_file():
                    default = path.read_text(encoding="utf-8")
                elif ignore_missing_files:
                    default = ""
                else:
                    message = f"Missing file for {parameter.identifier.full} at {path}"
                    raise RuntimeError(message)

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
            # todo: ternary required here,
            #  because sometimes values are plain (after parsing), not string (from database);
            #  most likely should be solved after spec-defaults separation or something
            default = (
                _parse_default_if_not_none(default, lambda x: x.lower() in {"true", "yes"})
                if isinstance(default, str)
                else default
            )

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
            payload = {**config_proto_entry.limits["source"]}
            source_type = payload["type"]
            is_strict = payload.get("strict", False)
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
        default = config.secrets.encrypt_if_possible(value=default, encryptor=encrypt)

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
