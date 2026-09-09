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

from core.action._context import groups
from core.action._context.types import ConfigHostGroupInfo
from core.cluster import ClusterTopology
from core.config import Configuration
from core.types import ConfigHostGroupID, CoreObjectDescriptor


def prepare_groups_for_host_groups(
    groups_with_hosts: tuple[ConfigHostGroupInfo, ...],
    updated_configurations_by_group_id: dict[ConfigHostGroupID, Configuration],
    cluster_vars: dict,
    objects_before_upgrade: dict[CoreObjectDescriptor | tuple[CoreObjectDescriptor, str], dict],
    topology: ClusterTopology,
) -> dict[str, dict]:
    grouped_hosts_by_common_groups = groups.group_hosts_by_common_host_groups(
        hosts_in_groups={group.id: [host_info.id for host_info in group.hosts] for group in groups_with_hosts}
    )
    owner_to_node_path = groups.build_node_paths(topology=topology)

    groups_data_by_id: dict[ConfigHostGroupID, groups.GroupOverrides] = {}
    for group in groups_with_hosts:
        groups_data_by_id[group.id] = groups.GroupOverrides(
            node_path=owner_to_node_path[group.owner],
            before_upgrade=objects_before_upgrade.get((group.owner, group.name)),
            prepared_config_values=updated_configurations_by_group_id[group.id].values,
        )

    vars_by_key = groups.prepare_vars_by_key(
        grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
        cluster_vars=cluster_vars,
        groups_data_by_id=groups_data_by_id,
    )
    hosts_by_key = groups.prepare_hosts_by_key(
        grouped_hosts_by_common_groups=grouped_hosts_by_common_groups,
        host_name_by_id={host_id: host_info.name for host_id, host_info in topology.hosts.items()},
    )

    return {key: {"vars": vars_by_key[key], "hosts": hosts_by_key[key]} for key in vars_by_key}
