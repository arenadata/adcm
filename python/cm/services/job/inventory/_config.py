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
from copy import deepcopy
from functools import reduce
from typing import Iterable, NamedTuple

from core.cluster.types import ClusterTopology
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, ObjectID, PrototypeID
from django.conf import settings
from django.db.models import F, QuerySet, Value

from cm.adcm_config.utils import build_string_path_for_file
from cm.models import (
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ServiceComponent,
)
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects
from cm.services.config.types import AttrDict, ConfigDict
from cm.services.group_config import GroupConfigInfo, GroupConfigName
from cm.services.job.inventory._types import ObjectsInInventoryMap


class _ObjectRequiredConfigInfo(NamedTuple):
    prototype_id: PrototypeID
    config_id: ConfigID


def get_objects_configurations(
    objects_in_inventory: ObjectsInInventoryMap,
) -> dict[tuple[ADCMCoreType, ObjectID], dict]:
    objects_config_info = _get_config_info(objects=objects_in_inventory)

    if not objects_config_info:
        return {(type_, object_id): {} for type_, ids in objects_in_inventory.items() for object_id in ids}

    configurations = retrieve_config_attr_pairs(
        configurations=(entry.config_id for entry in objects_config_info.values())
    )
    specifications_for_prototypes = retrieve_flat_spec_for_objects(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    objects_configurations: dict[CoreObjectDescriptor, ConfigDict] = {}

    for object_, info in objects_config_info.items():
        # what to do if one of them is absent? looks like error in storage, so I think just fail with key error
        configuration, attributes = configurations[info.config_id]
        specification = specifications_for_prototypes[info.prototype_id]

        objects_configurations[object_] = _update_configuration_for_inventory_inplace(
            configuration=configuration, attributes=attributes, specification=specification, config_owner=object_
        )

    return {
        (type_, object_id): objects_configurations.get(CoreObjectDescriptor(object_id, type_), {})
        for type_, ids in objects_in_inventory.items()
        for object_id in ids
    }


def _get_config_info(objects: ObjectsInInventoryMap) -> dict[CoreObjectDescriptor, _ObjectRequiredConfigInfo]:
    query_for_objects_config_info: QuerySet = reduce(
        lambda left_qs, right_qs: left_qs.union(right_qs),
        (
            orm_type.objects.filter(id__in=objects.get(core_type, ()), config__isnull=False).values(
                "id", "prototype_id", current_config_id=F("config__current"), type=Value(core_type.value)
            )
            for orm_type, core_type in (
                (Cluster, ADCMCoreType.CLUSTER),
                (ClusterObject, ADCMCoreType.SERVICE),
                (ServiceComponent, ADCMCoreType.COMPONENT),
                (HostProvider, ADCMCoreType.HOSTPROVIDER),
                (Host, ADCMCoreType.HOST),
            )
        ),
    )
    return {
        CoreObjectDescriptor(id=row["id"], type=ADCMCoreType(row["type"])): _ObjectRequiredConfigInfo(
            prototype_id=row["prototype_id"], config_id=row["current_config_id"]
        )
        for row in query_for_objects_config_info
    }


def _update_configuration_for_inventory_inplace(
    configuration: ConfigDict,
    attributes: AttrDict,
    specification: FlatSpec,
    config_owner: CoreObjectDescriptor,
    group_config_id: int | None = None,
) -> AttrDict:
    skip_deactivated_groups: set[str] = set()

    for composite_key, field_ in specification.items():
        key, subkey = composite_key.split("/")

        if field_.type == "group":
            is_regular_or_active_group = attributes.get(key, {}).get("active", True)
            if not is_regular_or_active_group:
                configuration[key] = None
                skip_deactivated_groups.add(key)

            continue

        if key in skip_deactivated_groups or key not in configuration:
            continue

        match field_.type, subkey:
            case ["file" | "secretfile", ""]:
                if configuration[key]:
                    configuration[key] = build_string_path_for_file(
                        object_itself=config_owner, config_key=key, group_config_id=group_config_id
                    )
            case ["file" | "secretfile", _]:
                if subkey in configuration[key] and configuration[key][subkey]:
                    configuration[key][subkey] = build_string_path_for_file(
                        object_itself=config_owner,
                        config_key=key,
                        config_subkey=subkey,
                        group_config_id=group_config_id,
                    )
            case ["password" | "secrettext", ""]:
                # check for None
                if settings.ANSIBLE_VAULT_HEADER in (configuration[key] or ""):
                    configuration[key] = {"__ansible_vault": configuration[key]}
            case ["password" | "secrettext", _]:
                if settings.ANSIBLE_VAULT_HEADER in (configuration[key][subkey] or ""):
                    configuration[key][subkey] = {"__ansible_vault": configuration[key][subkey]}
            case ["secretmap", ""]:
                if configuration[key]:
                    for map_key, map_value in configuration[key].items():
                        if settings.ANSIBLE_VAULT_HEADER in map_value:
                            configuration[key][map_key] = {"__ansible_vault": map_value}
            case ["secretmap", _]:
                if subkey in configuration[key] and configuration[key][subkey]:
                    for map_key, map_value in configuration[key][subkey].items():
                        if settings.ANSIBLE_VAULT_HEADER in map_value:
                            configuration[key][subkey][map_key] = {"__ansible_vault": map_value}
            case ["map" | "list", ""]:
                if configuration[key] is None:
                    configuration[key] = {} if field_.type == "map" else []
            case ["map" | "list", _]:
                group = configuration[key]
                if subkey in group and group[subkey] is None:
                    group[subkey] = {} if field_.type == "map" else []

    return configuration


def get_group_config_alternatives_for_hosts_in_cluster_groups(
    group_configs: Iterable[GroupConfigInfo],
    cluster_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict],
    topology: ClusterTopology,
) -> dict[str, dict]:
    groups_with_hosts = tuple(group for group in group_configs if group.hosts)

    configurations = retrieve_config_attr_pairs(configurations=(group.current_config_id for group in groups_with_hosts))

    objects_with_groups = defaultdict(set)
    for group in groups_with_hosts:
        objects_with_groups[group.owner.type].add(group.owner.id)

    objects_config_info = _get_config_info(objects=objects_with_groups)

    specifications_for_prototypes = retrieve_flat_spec_for_objects(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    result = defaultdict(lambda: deepcopy(cluster_vars))

    for group in groups_with_hosts:
        configuration, attributes = configurations[group.current_config_id]
        specification = specifications_for_prototypes[objects_config_info[group.owner].prototype_id]
        updated_config = _update_configuration_for_inventory_inplace(
            configuration=configuration,
            attributes=attributes,
            specification=specification,
            config_owner=group.owner,
            group_config_id=group.id,
        )

        group_before_upgrade = objects_before_upgrade.get((group.owner, group.name), None)

        for host_info in group.hosts:
            node = None
            match group.owner.type:
                case ADCMCoreType.CLUSTER:
                    node = result[host_info.name]["cluster"]
                case ADCMCoreType.SERVICE:
                    node = result[host_info.name]["services"][topology.services[group.owner.id].info.name]
                case ADCMCoreType.COMPONENT:
                    service = next(
                        (service_ for service_ in topology.services.values() if group.owner.id in service_.components),
                        None,
                    )
                    if service:
                        node = result[host_info.name]["services"][service.info.name][
                            service.components[group.owner.id].info.name
                        ]

            if not node:
                raise RuntimeError(f"Failed to determine node in `vars` for {group.owner}")

            if group_before_upgrade:
                node["before_upgrade"] = group_before_upgrade

            node["config"] = updated_config

    return result
