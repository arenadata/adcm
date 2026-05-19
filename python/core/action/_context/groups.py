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

from core.cluster import ClusterTopology
from core.tools import get_nested
from core.types import ADCMCoreType, ConfigHostGroupID, CoreObjectDescriptor, HostID


@dataclass(slots=True)
class GroupOverrides:
    node_path: tuple[str, ...]
    before_upgrade: dict | None
    prepared_config_values: dict


def group_hosts_by_common_host_groups(
    hosts_in_groups: dict[ConfigHostGroupID, list[HostID]],
) -> dict[tuple[ConfigHostGroupID, ...], set[HostID]]:
    groups_of_hosts: defaultdict[HostID, set[ConfigHostGroupID]] = defaultdict(set)

    for chg_id, hosts_ids in hosts_in_groups.items():
        for host_id in hosts_ids:
            groups_of_hosts[host_id].add(chg_id)

    result = defaultdict(set)

    for host_id, group_ids in groups_of_hosts.items():
        group_ids_tuple = tuple(sorted(group_ids))
        result[group_ids_tuple].add(host_id)

    return result


def build_node_paths(topology: ClusterTopology) -> dict[CoreObjectDescriptor, tuple[str, ...]]:
    """
    Build paths for "vars" format for cluster, each service and component in topology
    """
    owner_to_node_path: dict[CoreObjectDescriptor, tuple[str, ...]] = {
        CoreObjectDescriptor(id=topology.cluster_id, type=ADCMCoreType.CLUSTER): ("cluster",)
    }

    for service in topology.services.values():
        owner_to_node_path[CoreObjectDescriptor(id=service.info.id, type=ADCMCoreType.SERVICE)] = (
            "services",
            service.info.name,
        )
        for component in service.components.values():
            owner_to_node_path[CoreObjectDescriptor(id=component.info.id, type=ADCMCoreType.COMPONENT)] = (
                "services",
                service.info.name,
                component.info.name,
            )

    return owner_to_node_path


def prepare_vars_by_key(
    grouped_hosts_by_common_groups: dict[tuple[ConfigHostGroupID, ...], set[HostID]],
    cluster_vars: dict,
    groups_data_by_id: dict[ConfigHostGroupID, GroupOverrides],
) -> dict[str, dict]:
    vars_by_key: dict[str, dict] = {}

    for group_ids in grouped_hosts_by_common_groups:
        alternative_vars = deepcopy(cluster_vars)

        for group_id in group_ids:
            group_data = groups_data_by_id[group_id]
            node = get_nested(source=alternative_vars, path=group_data.node_path)
            node["config"] = group_data.prepared_config_values

            if group_data.before_upgrade:
                node["before_upgrade"] = group_data.before_upgrade

        vars_by_key[_generate_chg_key(group_ids=group_ids)] = alternative_vars

    return vars_by_key


def prepare_hosts_by_key(
    grouped_hosts_by_common_groups: dict[tuple[ConfigHostGroupID, ...], set[HostID]],
    host_name_by_id: dict[HostID, str],
) -> dict[str, dict[str, dict]]:
    hosts_by_key: dict[str, dict[str, dict]] = {}

    for group_ids, host_ids in grouped_hosts_by_common_groups.items():
        names = (host_name_by_id[host_id] for host_id in host_ids)
        hosts_by_key[_generate_chg_key(group_ids=group_ids)] = {name: {} for name in sorted(names)}

    return hosts_by_key


def _generate_chg_key(group_ids: tuple[ConfigHostGroupID, ...]) -> str:
    return f"chg_{'_'.join(map(str, group_ids))}"
