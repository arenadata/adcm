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
from typing import Any, Iterable, NamedTuple

from core.cluster.types import ClusterTopology
from core.types import ADCMCoreType, ConfigID, CoreObjectDescriptor, GeneralEntityDescriptor, ObjectID, PrototypeID
from django.conf import settings
from django.db.models import F, QuerySet, Value

from cm.models import ADCM, Cluster, Component, Host, HostProvider, Service
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects
from cm.services.config.types import AttrDict, ConfigDict
from cm.services.group_config import GroupConfigInfo, GroupConfigName
from cm.services.job.inventory._types import ObjectsInInventoryMap


class _ObjectRequiredConfigInfo(NamedTuple):
    prototype_id: PrototypeID
    config_id: ConfigID


def get_group_config_alternatives_for_hosts_in_cluster_groups(
    group_configs: Iterable[GroupConfigInfo],
    cluster_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict],
    topology: ClusterTopology,
) -> dict[str, dict]:
    groups_with_hosts = tuple(group for group in group_configs if group.hosts)

    if not groups_with_hosts:
        return {}

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
        updated_config = update_configuration_for_inventory_inplace(
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


def get_group_config_alternatives_for_hosts_in_hostprovider_groups(
    group_configs: Iterable[GroupConfigInfo],
    hostprovider_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, GroupConfigName], dict],
) -> dict[str, dict]:
    groups_of_hostprovider_with_hosts = tuple(
        group for group in group_configs if group.hosts and group.owner.type == ADCMCoreType.HOSTPROVIDER
    )

    if not groups_of_hostprovider_with_hosts:
        return {}

    configurations = retrieve_config_attr_pairs(
        configurations=(group.current_config_id for group in groups_of_hostprovider_with_hosts)
    )

    objects_with_groups = defaultdict(set)
    for group in groups_of_hostprovider_with_hosts:
        objects_with_groups[group.owner.type].add(group.owner.id)

    objects_config_info = _get_config_info(objects=objects_with_groups)

    specifications_for_prototypes = retrieve_flat_spec_for_objects(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    result = defaultdict(lambda: deepcopy(hostprovider_vars))

    for group in groups_of_hostprovider_with_hosts:
        configuration, attributes = configurations[group.current_config_id]
        specification = specifications_for_prototypes[objects_config_info[group.owner].prototype_id]
        updated_config = update_configuration_for_inventory_inplace(
            configuration=configuration,
            attributes=attributes,
            specification=specification,
            config_owner=group.owner,
            group_config_id=group.id,
        )

        group_before_upgrade = objects_before_upgrade.get((group.owner, group.name), None)

        for host_info in group.hosts:
            node = result[host_info.name]["provider"]

            if group_before_upgrade:
                node["before_upgrade"] = group_before_upgrade

            node["config"] = updated_config

    return result


def get_objects_configurations(
    objects: ObjectsInInventoryMap,
) -> dict[tuple[ADCMCoreType, ObjectID], dict]:
    objects_config_info = _get_config_info(objects=objects)

    if not objects_config_info:
        return {(type_, object_id): {} for type_, ids in objects.items() for object_id in ids}

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

        objects_configurations[object_] = update_configuration_for_inventory_inplace(
            configuration=configuration, attributes=attributes, specification=specification, config_owner=object_
        )

    return {
        (type_, object_id): objects_configurations.get(CoreObjectDescriptor(object_id, type_), {})
        for type_, ids in objects.items()
        for object_id in ids
    }


def get_adcm_configuration() -> dict[str, Any]:
    adcm = ADCM.objects.select_related("config").get()
    config_attr_pair = retrieve_config_attr_pairs(configurations=(adcm.config.current,))[adcm.config.current]
    flat_spec = retrieve_flat_spec_for_objects(prototypes=(adcm.prototype_id,))[adcm.prototype_id]

    return update_configuration_for_inventory_inplace(
        configuration=config_attr_pair.config,
        attributes=config_attr_pair.attr,
        specification=flat_spec,
        config_owner=GeneralEntityDescriptor(id=adcm.pk, type="adcm"),
    )


def _get_config_info(objects: ObjectsInInventoryMap) -> dict[CoreObjectDescriptor, _ObjectRequiredConfigInfo]:
    query_for_objects_config_info: QuerySet = reduce(
        lambda left_qs, right_qs: left_qs.union(right_qs),
        (
            orm_type.objects.filter(id__in=objects.get(core_type, ()), config__isnull=False).values(
                "id",
                "prototype_id",
                current_config_id=F("config__current"),
                type=Value(core_type.value if isinstance(core_type, ADCMCoreType) else core_type),
            )
            for orm_type, core_type in (
                (Cluster, ADCMCoreType.CLUSTER),
                (Service, ADCMCoreType.SERVICE),
                (Component, ADCMCoreType.COMPONENT),
                (HostProvider, ADCMCoreType.HOSTPROVIDER),
                (Host, ADCMCoreType.HOST),
            )
        ),
    )

    return {
        CoreObjectDescriptor(
            id=row["id"],
            type=ADCMCoreType(row["type"]),
        ): _ObjectRequiredConfigInfo(prototype_id=row["prototype_id"], config_id=row["current_config_id"])
        for row in query_for_objects_config_info
    }


def update_configuration_for_inventory_inplace(
    configuration: ConfigDict,
    attributes: AttrDict,
    specification: FlatSpec,
    config_owner: CoreObjectDescriptor | GeneralEntityDescriptor,
    group_config_id: int | None = None,
) -> AttrDict:
    skip_deactivated_groups: set[str] = set()

    for composite_key, field_ in specification.items():
        key, subkey = composite_key.split("/")

        if field_.type == "group":
            is_regular_or_active_group = attributes.get(key, {}).get("active", True)
            if not is_regular_or_active_group and key in configuration:
                configuration[key] = None
                skip_deactivated_groups.add(key)

            continue

        if key in skip_deactivated_groups or key not in configuration:
            continue

        match field_.type, subkey:
            case ["file" | "secretfile", ""]:
                if configuration[key]:
                    configuration[key] = _build_string_path_for_file(
                        object_itself=config_owner, config_key=key, group_config_id=group_config_id
                    )
            case ["file" | "secretfile", _]:
                if subkey in configuration[key] and configuration[key][subkey]:
                    configuration[key][subkey] = _build_string_path_for_file(
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


def _build_string_path_for_file(
    object_itself: CoreObjectDescriptor | GeneralEntityDescriptor,
    config_key: str,
    config_subkey: str = "",
    group_config_id: int | None = None,
) -> str:
    """
    In most cases you want to pass CoreObjectDescriptor.
    When it's about group config, pass its id alongside CoreObjectDescription (from owner of the group).
    When it's task, pass GeneralEntryDescriptor(id=task_id, type="task"),
    """
    if not isinstance(object_itself, CoreObjectDescriptor):
        type_as_string = object_itself.type
    elif object_itself.type == ADCMCoreType.HOSTPROVIDER:
        type_as_string = "provider"
    else:
        type_as_string = object_itself.type.value

    if group_config_id is not None:
        filename = [
            type_as_string,
            str(object_itself.id),
            "group",
            str(group_config_id),
            config_key,
            config_subkey,
        ]
    else:
        filename = [type_as_string, str(object_itself.id), config_key, config_subkey]

    return str(settings.FILE_DIR / ".".join(filename))
