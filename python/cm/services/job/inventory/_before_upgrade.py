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
from typing import Iterable

from core.types import ADCMCoreType, BundleID, ConfigID, CoreObjectDescriptor, ObjectID, PrototypeID
from django.db.models import F, JSONField, Q, Value

from cm.converters import core_type_to_db_record_type, db_record_type_to_core_type
from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    Prototype,
    ServiceComponent,
    get_default_before_upgrade,
)
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import retrieve_flat_spec_for_objects
from cm.services.group_config import GroupConfigInfo, GroupConfigName
from cm.services.job.inventory._config import _update_configuration_for_inventory_inplace
from cm.services.job.inventory._types import ObjectsInInventoryMap


@dataclass(slots=True)
class ProcessedBeforeUpgrade:  # todo think about naming of this and "extract" function
    # raw before upgrade "as is" from database
    before_upgrade: dict

    is_default: bool

    # is required for searching related prototypes
    prototype_name: str | None = None
    config_id: int | None = None
    bundle_id: int | None = None
    group_configs_info: dict[GroupConfigName, ConfigID] = field(default_factory=dict)


def extract_objects_before_upgrade(
    objects: ObjectsInInventoryMap,
) -> dict[CoreObjectDescriptor, ProcessedBeforeUpgrade]:
    empty_json_field = Value({}, output_field=JSONField())
    query = reduce(
        lambda left_qs, right_qs: left_qs.union(right_qs),
        (
            orm_type.objects.filter(id__in=objects.get(core_type, ())).values(
                "id",
                "before_upgrade",
                prototype_name=F("prototype__name"),
                parent_before_upgrade=F("cluster__before_upgrade")
                if core_type in (ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT)
                else empty_json_field,
                type=Value(core_type.value),
            )
            for orm_type, core_type in (
                (Cluster, ADCMCoreType.CLUSTER),
                (ClusterObject, ADCMCoreType.SERVICE),
                (ServiceComponent, ADCMCoreType.COMPONENT),
                (Host, ADCMCoreType.HOST),
                (HostProvider, ADCMCoreType.HOSTPROVIDER),
            )
        ),
    )

    default_before_upgrade = get_default_before_upgrade()

    result = {}

    for row in query:
        object_ = CoreObjectDescriptor(id=row["id"], type=ADCMCoreType(row["type"]))
        raw_before_upgrade = row["before_upgrade"]

        if raw_before_upgrade == default_before_upgrade:
            result[object_] = ProcessedBeforeUpgrade(before_upgrade=raw_before_upgrade, is_default=True)
            continue

        result[object_] = ProcessedBeforeUpgrade(
            before_upgrade=raw_before_upgrade,
            is_default=False,
            config_id=raw_before_upgrade.get("config_id"),
            prototype_name=row["prototype_name"],
            bundle_id=raw_before_upgrade.get("bundle_id", row["parent_before_upgrade"].get("bundle_id")),
            group_configs_info={
                # todo can here be something non-convertable to `int`?
                group_name: int(group_info["group_config_id"])
                for group_name, group_info in raw_before_upgrade.get("groups", {}).items()
            },
        )

    return result


def get_before_upgrades(
    before_upgrades: dict[CoreObjectDescriptor, ProcessedBeforeUpgrade], group_configs: Iterable[GroupConfigInfo] = ()
) -> dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict]:
    required_prototypes: dict[BundleID, set[tuple[CoreObjectDescriptor, str]]] = defaultdict(set)
    required_configs: dict[[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName]], ConfigID] = {}

    result: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict] = {}

    for object_, before_upgrade_info in before_upgrades.items():
        if before_upgrade_info.is_default:
            result[object_] = before_upgrade_info.before_upgrade
            continue

        if not before_upgrade_info.bundle_id:
            # then we can't get the config prototype to convert the config
            result[object_] = {"state": before_upgrade_info.before_upgrade.get("state"), "config": None}
            continue

        required_prototypes[before_upgrade_info.bundle_id].add((object_, before_upgrade_info.prototype_name))
        if before_upgrade_info.config_id:
            required_configs[object_] = before_upgrade_info.config_id

        for group_config_name, config_id in before_upgrade_info.group_configs_info.items():
            required_configs[object_, group_config_name] = config_id

    if not (required_configs and required_configs):
        return result

    configurations = retrieve_config_attr_pairs(required_configs.values())

    required_prototypes: dict[tuple[ADCMCoreType, str], PrototypeID] = {
        (db_record_type_to_core_type(proto["type"]), proto["name"]): proto["id"]
        for proto in Prototype.objects.values("id", "type", "name").filter(
            reduce(
                or_,
                (
                    Q(bundle_id=bundle_id, type=core_type_to_db_record_type(object_.type), name=name)
                    for bundle_id, requested in required_prototypes.items()
                    for object_, name in requested
                ),
            )
        )
    }
    specifications_for_prototypes = retrieve_flat_spec_for_objects(prototypes=required_prototypes.values())

    group_config_name_id_map: dict[GroupConfigName, ObjectID] = {
        group_info.name: group_info.id for group_info in group_configs
    }

    for unprocessed_object, before_upgrade_info in (
        (key, value) for key, value in before_upgrades.items() if key not in result
    ):
        # config either will be overriden or kept None
        result[unprocessed_object] = {"state": before_upgrade_info.before_upgrade.get("state"), "config": None}

        try:
            prototype_id = required_prototypes[unprocessed_object.type, before_upgrade_info.prototype_name]
            specification = specifications_for_prototypes[prototype_id]
        except KeyError:
            continue

        try:
            configuration, attributes = configurations[before_upgrade_info.config_id]
        except KeyError:
            continue

        result[unprocessed_object]["config"] = _update_configuration_for_inventory_inplace(
            configuration=configuration,
            attributes=attributes,
            specification=specification,
            config_owner=unprocessed_object,
        )

        for group_config_name, config_id in before_upgrade_info.group_configs_info:
            if group_config_name not in group_config_name_id_map:
                # if group for some reason doesn't exist in "inventory scope" it's of no interest to us
                continue

            try:
                configuration, attributes = configurations[config_id]
            except KeyError:
                # here nothing should be added to result dict
                continue

            result[unprocessed_object, group_config_name] = {
                "state": before_upgrade_info.before_upgrade.get("state"),
                "config": _update_configuration_for_inventory_inplace(
                    configuration=configuration,
                    attributes=attributes,
                    specification=specification,
                    config_owner=unprocessed_object,
                    group_config_id=group_config_name_id_map[group_config_name],
                ),
            }

    return result
