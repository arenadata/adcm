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
from typing import Collection, Iterable, NamedTuple, TypeAlias

from core.cluster.operations import create_topology_with_new_mapping
from core.cluster.types import ClusterTopology, HostComponentEntry
from core.types import ADCMCoreType, CoreObjectDescriptor, HostID, ObjectID, ShortObjectInfo
from django.db.models import F

from cm.converters import core_type_to_model, model_name_to_core_type
from cm.models import ConfigHostGroup
from cm.services.cluster import retrieve_cluster_topology
from cm.services.host_group_common import HostGroupRepoMixin
from cm.services.job.types import TaskMappingDelta

ConfigHostGroupName: TypeAlias = str


class ConfigHostGroupInfo(NamedTuple):
    id: ObjectID
    name: str

    hosts: set[ShortObjectInfo]

    current_config_id: int
    owner: CoreObjectDescriptor


def retrieve_config_host_groups_for_hosts(
    hosts: Iterable[HostID], restrict_by_owner_type: Collection[ADCMCoreType] = ()
) -> dict[ObjectID, ConfigHostGroupInfo]:
    query = ConfigHostGroup.objects.filter(hosts__in=hosts).values(
        "id",
        "name",
        current_config_id=F("config__current"),
        owner_id=F("object_id"),
        owner_model_type=F("object_type__model"),
        host_id=F("hosts__id"),
        host_name=F("hosts__fqdn"),
    )
    if restrict_by_owner_type:
        query = query.filter(
            object_type__model__in=(
                core_type_to_model(owner_type).__name__.lower() for owner_type in restrict_by_owner_type
            )
        )

    result: dict[ObjectID, ConfigHostGroupInfo] = {}

    for record in query:
        group = result.setdefault(
            record["id"],
            ConfigHostGroupInfo(
                id=record["id"],
                name=record["name"],
                current_config_id=record["current_config_id"],
                owner=CoreObjectDescriptor(
                    id=record["owner_id"], type=model_name_to_core_type(record["owner_model_type"])
                ),
                hosts=set(),
            ),
        )
        group.hosts.add(ShortObjectInfo(id=record["host_id"], name=record["host_name"]))

    return result


class ConfigHostGroupRepo(HostGroupRepoMixin):
    group_hosts_model = ConfigHostGroup.hosts.through
    group_hosts_field_name = "confighostgroup"


# This function is a copy of `cm.services.mapping._base._construct_mapping_from_delta`.
# It was copied to avoid solving the problem of cyclic imports, because of `ConfigHostGroupRepo`.
# TODO: Fix it by packing modules `config_host_group` and `action_host_group` to one package
def _construct_mapping_from_delta(
    topology: ClusterTopology, mapping_delta: TaskMappingDelta | None
) -> Iterable[HostComponentEntry]:
    current_entries = {
        HostComponentEntry(host_id=host_id, component_id=component.info.id)
        for service in topology.services.values()
        for component in service.components.values()
        for host_id in component.hosts
    }

    to_add, to_remove = set(), set()
    if mapping_delta is not None:
        to_add = {
            HostComponentEntry(host_id=host_id, component_id=component_id)
            for component_id, host_ids in mapping_delta.add.items()
            for host_id in host_ids
        }
        to_remove = {
            HostComponentEntry(host_id=host_id, component_id=component_id)
            for component_id, host_ids in mapping_delta.remove.items()
            for host_id in host_ids
        }

    return (current_entries - to_remove) | to_add


def patch_for_hc_apply_clear_host_config_after_remove_from_config_host_groups(
    cluster_id: int, delta: TaskMappingDelta, config_host_groups: dict[ObjectID, ConfigHostGroupInfo]
) -> dict[ObjectID, ConfigHostGroupInfo]:
    # The function updates `config_host_groups` on the fly.
    # You must delete the unmapped hosts from the existing config host groups.

    topology = retrieve_cluster_topology(cluster_id=cluster_id)
    new_mapping = _construct_mapping_from_delta(topology=topology, mapping_delta=delta)
    new_topology = create_topology_with_new_mapping(topology=topology, new_mapping=new_mapping)

    hosts_map = defaultdict(set)

    for service in new_topology.services.values():
        for component in service.components.values():
            hosts = set(component.hosts.values())
            hosts_map[(component.info.id, ADCMCoreType.COMPONENT)] |= hosts
            hosts_map[(service.info.id, ADCMCoreType.SERVICE)] |= hosts

    new_config_host_groups = {}

    for chg_id, chg_info in config_host_groups.items():
        hosts = chg_info.hosts

        key = (chg_info.owner.id, chg_info.owner.type)
        if key in hosts_map:
            hosts = chg_info.hosts & hosts_map[key]

        new_config_host_groups[chg_id] = ConfigHostGroupInfo(
            id=chg_id,
            name=chg_info.name,
            current_config_id=chg_info.current_config_id,
            owner=chg_info.owner,
            hosts=hosts,
        )

    return new_config_host_groups
