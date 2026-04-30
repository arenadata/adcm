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
from dataclasses import dataclass, field
from functools import reduce
from operator import or_
from typing import Final, Iterable

from core.types import (
    ADCMCoreType,
    ADCMHostGroupType,
    BundleID,
    ConfigID,
    CoreObjectDescriptor,
    HostGroupDescriptor,
    ObjectID,
    PrototypeID,
)
from django.db.models import F, JSONField, Q, Value
import core

from cm.converters import core_type_to_db_record_type, db_record_type_to_core_type
from cm.legacy.services.config_host_group import ConfigHostGroupInfo, ConfigHostGroupName
from cm.legacy.services.job.context._types import ObjectsInInventoryMap
from cm.models import (
    Cluster,
    Component,
    Host,
    Prototype,
    Provider,
    Service,
)

DEFAULT_BEFORE_UPGRADE: Final = {"state": None}


@dataclass(slots=True)
class ProcessedBeforeUpgrade:
    # raw before upgrade "as is" from database
    before_upgrade: dict

    is_default: bool

    # `prototype_name` field is required for searching related prototypes
    #
    # It is expected to be `tuple[str, str]` for Component
    # with Service's prototype name at first position and Component's prototype name at second
    prototype_name: str | tuple[str, str] | None = None
    config_id: int | None = None
    bundle_id: int | None = None
    config_host_groups_info: dict[ConfigHostGroupName, ConfigID] = field(default_factory=dict)


def extract_objects_before_upgrade(
    objects: ObjectsInInventoryMap,
) -> dict[CoreObjectDescriptor, ProcessedBeforeUpgrade]:
    empty_json_field = Value({}, output_field=JSONField())
    empty_char_field = Value("")
    query = reduce(
        lambda left_qs, right_qs: left_qs.union(right_qs),
        (
            orm_type.objects.filter(id__in=objects.get(core_type, ())).values(
                "id",
                "before_upgrade",
                prototype_name=F("prototype__name"),
                service_name=F("service__prototype__name") if core_type == ADCMCoreType.COMPONENT else empty_char_field,
                parent_before_upgrade=F("cluster__before_upgrade")
                if core_type in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT)
                else empty_json_field,
                type=Value(core_type.value),
            )
            for orm_type, core_type in (
                (Cluster, ADCMCoreType.CLUSTER),
                (Service, ADCMCoreType.SERVICE),
                (Component, ADCMCoreType.COMPONENT),
                (Host, ADCMCoreType.HOST),
                (Provider, ADCMCoreType.PROVIDER),
            )
        ),
    )

    result = {}

    for row in query:
        object_ = CoreObjectDescriptor(id=row["id"], type=ADCMCoreType(row["type"]))
        raw_before_upgrade = row["before_upgrade"]

        processed_before_upgrade = construct_processed_before_upgrade(
            raw_before_upgrade=raw_before_upgrade,
            prototype_name=row["prototype_name"]
            if not row["service_name"]
            else (row["service_name"], row["prototype_name"]),
            parent_before_upgrade=row["parent_before_upgrade"],
        )

        result[object_] = processed_before_upgrade

    return result


def construct_processed_before_upgrade(
    raw_before_upgrade: dict, prototype_name: str | tuple[str, str] | None, parent_before_upgrade: dict
):
    if raw_before_upgrade == DEFAULT_BEFORE_UPGRADE:
        return ProcessedBeforeUpgrade(before_upgrade=raw_before_upgrade, is_default=True)

    return ProcessedBeforeUpgrade(
        before_upgrade=raw_before_upgrade,
        is_default=False,
        config_id=raw_before_upgrade.get("config_id"),
        prototype_name=prototype_name,
        bundle_id=raw_before_upgrade.get("bundle_id", parent_before_upgrade.get("bundle_id")),
        config_host_groups_info={
            group_name: int(group_info["config_id"])
            for group_name, group_info in raw_before_upgrade.get("config_host_groups", {}).items()
        },
    )


def _retrieve_existing_prototypes(
    required_prototypes: dict[BundleID, set[tuple[CoreObjectDescriptor, str | tuple[str, str]]]],
) -> dict[tuple[ADCMCoreType, str, str | None], PrototypeID]:
    return {
        (db_record_type_to_core_type(proto["type"]), proto["name"], proto["parent__name"]): proto["id"]
        for proto in Prototype.objects.values("id", "type", "name", "parent__name").filter(
            reduce(
                or_,
                (
                    Q(bundle_id=bundle_id, type=core_type_to_db_record_type(object_.type), name=name)
                    # it will be tuple for component, because component names are unique only within service,
                    # not within cluster, so to uniquely detect component's prototype,
                    # we have to use both names from service and component
                    if not isinstance(name, tuple)
                    else Q(
                        bundle_id=bundle_id,
                        type=core_type_to_db_record_type(object_.type),
                        name=name[1],
                        parent__name=name[0],
                    )
                    for bundle_id, requested in required_prototypes.items()
                    for object_, name in requested
                ),
            )
        )
    }


def get_before_upgrades(
    before_upgrades: dict[CoreObjectDescriptor, ProcessedBeforeUpgrade],
    config_service: core.config.ConfigService,
    config_host_groups: Iterable[ConfigHostGroupInfo] = (),
    retrieve_existing_prototypes=_retrieve_existing_prototypes,
) -> dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, ConfigHostGroupName], dict]:
    required_prototypes: dict[BundleID, set[tuple[CoreObjectDescriptor, str | tuple[str, str]]]] = defaultdict(set)
    required_configs: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, ConfigHostGroupName], ConfigID] = {}
    with_config = set()

    result: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, ConfigHostGroupName], dict] = {}

    for object_, before_upgrade_info in before_upgrades.items():
        if before_upgrade_info.is_default:
            # we rely on ProcessedBeforeUpgrade consistency here, avoiding binding to before upgrade default state
            result[object_] = before_upgrade_info.before_upgrade
            continue

        result[object_] = {
            "state": before_upgrade_info.before_upgrade.get("state"),
            "config": None,
        }
        if "imports" in before_upgrade_info.before_upgrade:
            result[object_]["imports"] = before_upgrade_info.before_upgrade["imports"]["config"]

        if not before_upgrade_info.bundle_id:
            # then we can't get the config prototype to convert the config
            continue

        with_config.add(object_)

        required_prototypes[before_upgrade_info.bundle_id].add((object_, before_upgrade_info.prototype_name))
        if before_upgrade_info.config_id:
            required_configs[object_] = before_upgrade_info.config_id

        for host_group_name, config_id in before_upgrade_info.config_host_groups_info.items():
            required_configs[object_, host_group_name] = config_id

    if not (required_configs and required_prototypes):
        return result

    configurations = config_service.retrieve_configurations_by_id(required_configs.values())

    existing_prototypes = retrieve_existing_prototypes(required_prototypes)
    specifications_for_prototypes = config_service.retrieve_specifications_by_prototypes(
        prototypes=existing_prototypes.values()
    )

    host_group_name_id_map: dict[ConfigHostGroupName, ObjectID] = {
        group_info.name: group_info.id for group_info in config_host_groups
    }

    for unprocessed_object in with_config:
        before_upgrade_info = before_upgrades[unprocessed_object]

        try:
            if isinstance(before_upgrade_info.prototype_name, tuple):
                parent_name, own_name = before_upgrade_info.prototype_name
            else:
                parent_name, own_name = None, before_upgrade_info.prototype_name

            prototype_id = existing_prototypes[unprocessed_object.type, own_name, parent_name]
            specification = specifications_for_prototypes[prototype_id]
        except KeyError:
            continue

        try:
            configuration = configurations[before_upgrade_info.config_id]
        except KeyError:
            continue

        result[unprocessed_object]["config"] = config_service.prepare_configuration_for_ansible(
            configuration=configuration,
            specification=specification,
            file_owner=unprocessed_object,
        ).values

        for host_group_name, config_id in before_upgrade_info.config_host_groups_info.items():
            if host_group_name not in host_group_name_id_map:
                # if group for some reason doesn't exist in "inventory scope" it's of no interest to us
                continue

            try:
                configuration = configurations[config_id]
            except KeyError:
                # here nothing should be added to result dict
                continue

            updated_configuration = config_service.prepare_configuration_for_ansible(
                configuration=configuration,
                specification=specification,
                file_owner=(
                    unprocessed_object,
                    HostGroupDescriptor(id=host_group_name_id_map[host_group_name], type=ADCMHostGroupType.CONFIG),
                ),
            )

            result[unprocessed_object, host_group_name] = result[unprocessed_object] | {
                "config": updated_configuration.values
            }

    return result
