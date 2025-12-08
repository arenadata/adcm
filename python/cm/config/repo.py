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
from itertools import chain
from pathlib import Path
from typing import Iterable, Literal, overload

from core import config
from core.types import (
    ActionID,
    ADCMCoreType,
    ADCMHostGroupType,
    ConfigID,
    CoreObjectDescriptor,
    Descriptor,
    HostGroupDescriptor,
    ObjectOrGroup,
    PrototypeID,
)
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F, Q

from cm.config._repo_spec import build_defaults, build_specification
from cm.config.convert import convert_adcm_meta_to_attr, convert_attr_to_adcm_meta
from cm.converters import core_type_to_model
from cm.models import ADCM, Action, ConfigHostGroup, ConfigLog, MainObject, ObjectConfig, Prototype, PrototypeConfig


@dataclass(slots=True)
class ConfigPrototypeInfo:
    bundle_hash: str
    group_customization_flag: bool
    parameter_prototypes: tuple[PrototypeConfig, ...]


@dataclass(slots=True)
class ConfigRepo(config.ConfigRepoI):
    # retrieve

    def get_config(self, owner: ObjectOrGroup) -> config.ConfigurationWithID:
        owner_model = _detect_owner_model(owner)

        owner_orm = owner_model.objects.select_related("config").get(pk=owner.id)

        if not owner_orm.config:
            message = f"Unexpectedly got object without configuration: {owner}"
            raise config.ObjectWithoutConfigError(message)

        current_id = owner_orm.config.current

        try:
            record = _get_configs_by_ids(ids=(current_id,))[current_id]
        except KeyError as e:
            raise config.NoConfigError(f"configuration unexpectedly missing: id={current_id}") from e

        configuration = _to_configuration(values=record.config, attrs=record.attr)

        return config.ConfigurationWithID(
            id=current_id,
            description=record.description,
            values=configuration.values,
            attributes=configuration.attributes,
        )

    # those overloads are required for some reason for pyright to understand it correctly,
    # see related case (not protocols, so it's different) in https://github.com/microsoft/pyright/issues/5718
    # maybe it's unexpected behavior
    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        defaults: Literal[False],
        only_for: Iterable[type[config.spec.p.SimpleParameter] | type[config.spec.p.ParameterGroup]] | None = None,
    ) -> config.spec.FullSpec:
        ...

    @overload
    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        defaults: config.EncryptFunc,
        only_for: Iterable[type[config.spec.p.SimpleParameter] | type[config.spec.p.ParameterGroup]] | None = None,
    ) -> tuple[config.spec.FullSpec, config.Defaults]:
        ...

    def get_spec(
        self,
        owner: CoreObjectDescriptor,
        action_id: ActionID | None,
        *,
        defaults: Literal[False] | config.EncryptFunc = False,
        only_for: Iterable[type[config.spec.p.SimpleParameter] | type[config.spec.p.ParameterGroup]] | None = None,
    ) -> config.spec.FullSpec | tuple[config.spec.FullSpec, config.Defaults]:
        config_spec_info = _get_config_prototype_info(owner=owner, action_id=action_id, only_for=only_for)
        if not config_spec_info.parameter_prototypes and not only_for:
            message = f"Unexpectedly got object without configuration: {owner}"
            raise config.ObjectWithoutConfigError(message)

        bundle_root = _build_path_to_bundle_root(owner_type=owner.type, bundle_hash=config_spec_info.bundle_hash)
        spec = build_specification(
            records=config_spec_info.parameter_prototypes,
            group_customization_flag=config_spec_info.group_customization_flag,
        )
        if defaults is False:
            return spec

        spec_defaults = build_defaults(
            records=config_spec_info.parameter_prototypes,
            spec=spec,
            bundle_root=bundle_root,
            encrypt=defaults,
        )
        return spec, spec_defaults

    def find_configs_by_ids(self, ids: Iterable[ConfigID]) -> dict[ConfigID, config.Configuration]:
        records = _get_configs_by_ids(ids=ids)
        return {
            config_id: _to_configuration(values=record.config, attrs=record.attr)
            for config_id, record in records.items()
        }

    def find_specs_by_prototype_ids(
        self, ids: Iterable[PrototypeID], encrypt: config.EncryptFunc
    ) -> dict[PrototypeID, tuple[config.spec.FullSpec, config.Defaults]]:
        ids_ = tuple(ids)

        proto_dir_mapping_query = Prototype.objects.filter(id__in=ids_).values_list("id", "type", "bundle__hash")
        proto_dir_map = {
            prototype_id: _build_path_to_bundle_root(owner_type=ADCMCoreType(type_), bundle_hash=bundle_hash)
            for prototype_id, type_, bundle_hash in proto_dir_mapping_query.all()
        }

        config_prototypes = _get_config_prototypes_info_by_ids(ids=ids_)

        result = {}

        for prototype_id, info in config_prototypes.items():
            # REDACTED: for now we need to return all specifications,
            #           because of some upgrade cases when configuration is removed
            #
            # don't want to return "non-existent" specifications
            # if not info.parameter_prototypes: continue

            specification = build_specification(
                records=info.parameter_prototypes, group_customization_flag=info.group_customization_flag
            )
            defaults = build_defaults(
                records=info.parameter_prototypes,
                spec=specification,
                bundle_root=proto_dir_map[prototype_id],
                encrypt=encrypt,
            )
            result[prototype_id] = (specification, defaults)

        return result

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
            # need to update to not trigger "save" for ConfigHostGroup case
            owner_model.objects.filter(id=owner_orm.pk).update(config_id=owner_orm.config.pk)

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
    specification = build_specification(records=records, group_customization_flag=group_customization_flag)
    defaults = build_defaults(
        records=records, spec=specification, bundle_root=bundle_root, encrypt=secrets_service.encrypt
    )

    return specification, defaults


def _detect_owner_model(owner: ObjectOrGroup) -> type[MainObject | ADCM | ConfigHostGroup]:
    match owner:
        case CoreObjectDescriptor(type=type_):
            return core_type_to_model(type_)
        case HostGroupDescriptor() | Descriptor(type=ADCMHostGroupType.CONFIG):
            return ConfigHostGroup


def _get_config_prototype_info(
    owner: CoreObjectDescriptor,
    action_id: int | None,
    only_for: Iterable[type[config.spec.p.SimpleParameter] | type[config.spec.p.ParameterGroup]] | None = None,
) -> ConfigPrototypeInfo:
    if not action_id:
        model = core_type_to_model(owner.type)
        prototype_id, prototype_type_literal, group_customization, bundle_hash = model.objects.values_list(
            "prototype_id",
            "prototype__type",
            "prototype__config_group_customization",
            "prototype__bundle__hash",
        ).get(id=owner.id)

        query_filter = Q(prototype_id=prototype_id, action_id=None)
    else:
        prototype_id, prototype_type_literal, bundle_hash = Action.objects.values_list(
            "prototype_id", "prototype__type", "prototype__bundle__hash"
        ).get(id=action_id)
        group_customization = False

        query_filter = Q(action_id=action_id)

    # now implemented for two only, since others aren't required yet
    if only_for:
        type_map: dict = {
            config.spec.p.JSONParameter: ("json",),
            config.spec.p.ParameterGroup: ("group", "selection_group"),
        }
        types = set(chain.from_iterable(type_map.get(entry, ()) for entry in only_for))
        if types:
            query_filter &= Q(type__in=types)

    parameter_prototypes = tuple(PrototypeConfig.objects.filter(query_filter).order_by("pk"))

    return ConfigPrototypeInfo(
        bundle_hash=bundle_hash,
        group_customization_flag=group_customization,
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


def _to_configuration(values: dict, attrs: dict) -> config.Configuration:
    attributes_raw = convert_attr_to_adcm_meta(attrs)

    attributes = {
        name: config.Attributes(is_active=entry.get("isActive"), is_synced=entry.get("isSynchronized"))
        for name, entry in attributes_raw.items()
    }

    return config.Configuration(values=values, attributes=attributes)
