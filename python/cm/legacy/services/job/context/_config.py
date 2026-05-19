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
from dataclasses import dataclass
from functools import reduce
from typing import Any, Iterable, NamedTuple

from core.cluster import ClusterTopology
from core.config import ConfigDict
from core.types import (
    ADCMCoreType,
    ADCMHostGroupType,
    ConfigHostGroupID,
    ConfigID,
    CoreObjectDescriptor,
    HostGroupDescriptor,
    ObjectID,
    PrototypeID,
)
from django.db.models import F, Q, QuerySet, Value
from django.db.models.functions import Coalesce
import core

from cm.legacy.services.config_host_group import ConfigHostGroupInfo, ConfigHostGroupName
from cm.legacy.services.job.context._types import ObjectsInInventoryMap
from cm.models import ADCM, Cluster, Component, Host, Provider, Service


class _ObjectRequiredConfigInfo(NamedTuple):
    prototype_id: PrototypeID
    config_id: ConfigID


@dataclass(slots=True)
class _ConfigRetrievalData:
    configurations: dict[ConfigID, core.config.Configuration]
    objects_config_info: dict[CoreObjectDescriptor, _ObjectRequiredConfigInfo]
    specifications_for_prototypes: dict[PrototypeID, core.config.spec.FullSpec]


def prepare_groups_for_config_host_group(
    config_host_groups: Iterable[ConfigHostGroupInfo],
    cluster_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, ConfigHostGroupName], dict],
    topology: ClusterTopology,
    config_service: core.config.ConfigService,
) -> dict[str, dict]:
    groups_with_hosts = tuple(group for group in config_host_groups if group.hosts)

    if not groups_with_hosts:
        return {}

    config_data = _retrieve_config_dependencies(groups_with_hosts=groups_with_hosts, config_service=config_service)
    updated_configurations_by_group_id = _prepare_updated_configurations_by_group_id(
        groups_with_hosts=groups_with_hosts,
        config_data=config_data,
        config_service=config_service,
    )
    return core.action.context.operations.prepare_groups_for_host_groups(
        groups_with_hosts=groups_with_hosts,
        updated_configurations_by_group_id=updated_configurations_by_group_id,
        cluster_vars=cluster_vars,
        objects_before_upgrade=objects_before_upgrade,
        topology=topology,
    )


def get_config_host_group_alternatives_for_hosts_in_provider_groups(
    config_host_groups: Iterable[ConfigHostGroupInfo],
    provider_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, ConfigHostGroupName], dict],
    config_service: core.config.ConfigService,
) -> dict[str, dict]:
    groups_of_provider_with_hosts = tuple(
        group for group in config_host_groups if group.hosts and group.owner.type == ADCMCoreType.PROVIDER
    )

    if not groups_of_provider_with_hosts:
        return {}

    configurations = config_service.retrieve_configurations_by_id(
        configurations=(group.current_config_id for group in groups_of_provider_with_hosts)
    )

    objects_with_groups = defaultdict(set)
    for group in groups_of_provider_with_hosts:
        objects_with_groups[group.owner.type].add(group.owner.id)

    objects_config_info = get_config_info(objects=objects_with_groups)

    specifications_for_prototypes = config_service.retrieve_specifications_by_prototypes(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    result = defaultdict(lambda: deepcopy(provider_vars))

    for group in groups_of_provider_with_hosts:
        updated_configuration = config_service.prepare_configuration_for_ansible(
            configuration=configurations[group.current_config_id],
            specification=specifications_for_prototypes[objects_config_info[group.owner].prototype_id],
            file_owner=(group.owner, HostGroupDescriptor(id=group.id, type=ADCMHostGroupType.CONFIG)),
            inplace=True,
        )

        group_before_upgrade = objects_before_upgrade.get((group.owner, group.name), None)

        for host_info in group.hosts:
            node = result[host_info.name]["provider"]

            if group_before_upgrade:
                node["before_upgrade"] = group_before_upgrade

            node["config"] = updated_configuration.values

    return result


def get_objects_configurations(
    objects: ObjectsInInventoryMap, config_service: core.config.ConfigService
) -> dict[tuple[ADCMCoreType, ObjectID], dict]:
    objects_config_info = get_config_info(objects=objects)

    if not objects_config_info:
        return {(type_, object_id): {} for type_, ids in objects.items() for object_id in ids}

    configurations = config_service.retrieve_configurations_by_id(
        configurations=(entry.config_id for entry in objects_config_info.values())
    )
    specifications_for_prototypes = config_service.retrieve_specifications_by_prototypes(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    objects_configurations: dict[CoreObjectDescriptor, ConfigDict] = {}

    for object_, info in objects_config_info.items():
        # what to do if one of them is absent? looks like error in storage, so I think just fail with key error
        updated_configuration = config_service.prepare_configuration_for_ansible(
            configuration=configurations[info.config_id],
            specification=specifications_for_prototypes[info.prototype_id],
            file_owner=object_,
            inplace=True,
        )
        objects_configurations[object_] = updated_configuration.values

    return {
        (type_, object_id): objects_configurations.get(CoreObjectDescriptor(object_id, type_), {})
        for type_, ids in objects.items()
        for object_id in ids
    }


def get_adcm_configuration(adcm: ADCM, config_service: core.config.ConfigService) -> dict[str, Any]:
    configuration = config_service.retrieve_configurations_by_id(configurations=(adcm.config.current,))[
        adcm.config.current
    ]
    specification = config_service.retrieve_specifications_by_prototypes(prototypes=(adcm.prototype_id,))[
        adcm.prototype_id
    ]

    return config_service.prepare_configuration_for_ansible(
        configuration=configuration,
        specification=specification,
        file_owner=CoreObjectDescriptor(id=adcm.pk, type=ADCMCoreType.ADCM),
        inplace=True,
    ).values


def get_config_info(objects: ObjectsInInventoryMap) -> dict[CoreObjectDescriptor, _ObjectRequiredConfigInfo]:
    # Refactoring is necessary.
    # The current implementation is difficult to understand. Since the copies of the host
    # do not have their own configuration, the original configuration must be used when generating
    # the inventory file. 2 conditions have been added for this.
    query_for_objects_config_info: QuerySet = reduce(
        lambda left_qs, right_qs: left_qs.union(right_qs),
        (
            (
                orm_type.objects.filter(
                    Q(config__isnull=False)
                    | Q(config__isnull=True, original__isnull=False, original__config__isnull=False),
                    id__in=objects.get(core_type, ()),
                )
                if core_type == ADCMCoreType.HOST
                else orm_type.objects.filter(id__in=objects.get(core_type, ()), config__isnull=False)
            ).values(
                "id",
                "prototype_id",
                current_config_id=Coalesce("original__config__current", "config__current")
                if core_type == ADCMCoreType.HOST
                else F("config__current"),
                type=Value(core_type.value if isinstance(core_type, ADCMCoreType) else core_type),
            )
            for orm_type, core_type in (
                (Cluster, ADCMCoreType.CLUSTER),
                (Service, ADCMCoreType.SERVICE),
                (Component, ADCMCoreType.COMPONENT),
                (Provider, ADCMCoreType.PROVIDER),
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


def _retrieve_config_dependencies(
    groups_with_hosts: tuple[ConfigHostGroupInfo, ...], config_service: core.config.ConfigService
) -> _ConfigRetrievalData:
    configurations = config_service.retrieve_configurations_by_id(
        configurations=(group.current_config_id for group in groups_with_hosts)
    )

    objects_with_groups = defaultdict(set)
    for group in groups_with_hosts:
        objects_with_groups[group.owner.type].add(group.owner.id)

    objects_config_info = get_config_info(objects=objects_with_groups)

    specifications_for_prototypes = config_service.retrieve_specifications_by_prototypes(
        prototypes=(entry.prototype_id for entry in objects_config_info.values())
    )

    return _ConfigRetrievalData(
        configurations=configurations,
        objects_config_info=objects_config_info,
        specifications_for_prototypes=specifications_for_prototypes,
    )


def _prepare_updated_configurations_by_group_id(
    groups_with_hosts: tuple[ConfigHostGroupInfo, ...],
    config_data: _ConfigRetrievalData,
    config_service: core.config.ConfigService,
) -> dict[ConfigHostGroupID, core.config.Configuration]:
    updated_configurations_by_group_id: dict[ConfigHostGroupID, core.config.Configuration] = {}

    for group in groups_with_hosts:
        file_owner = (group.owner, HostGroupDescriptor(id=group.id, type=ADCMHostGroupType.CONFIG))
        updated_configurations_by_group_id[group.id] = config_service.prepare_configuration_for_ansible(
            configuration=config_data.configurations[group.current_config_id],
            specification=config_data.specifications_for_prototypes[
                config_data.objects_config_info[group.owner].prototype_id
            ],
            file_owner=file_owner,
        )

    return updated_configurations_by_group_id
