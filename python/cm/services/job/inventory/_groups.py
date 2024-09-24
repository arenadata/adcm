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

from core.cluster.types import ClusterTopology
from core.types import HostID, HostName

from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.inventory._types import HostGroupName
from cm.services.job.types import TaskMappingDelta


def detect_host_groups_for_cluster_bundle_action(
    cluster_topology: ClusterTopology, hosts_in_maintenance_mode: set[int], hc_delta: TaskMappingDelta
) -> dict[HostGroupName, set[tuple[HostID, HostName]]]:
    groups = defaultdict(set)

    for host in cluster_topology.hosts.values():
        group = "CLUSTER" if host.id not in hosts_in_maintenance_mode else f"CLUSTER.{MAINTENANCE_MODE_GROUP_SUFFIX}"
        groups[group].add((host.id, host.name))

    for service in cluster_topology.services.values():
        service_name = service.info.name
        for component in service.components.values():
            hosts_in_mm = {
                (host_id, component.hosts[host_id].name)
                for host_id in set(component.hosts).intersection(hosts_in_maintenance_mode)
            }
            hosts_not_in_mm = {
                (host_id, component.hosts[host_id].name)
                for host_id in set(component.hosts).difference(hosts_in_maintenance_mode)
            }

            component_name = component.info.name

            if hosts_not_in_mm:  # we don't need empty groups
                groups[f"{service_name}.{component_name}"] = hosts_not_in_mm
                groups[service_name] |= hosts_not_in_mm

            if hosts_in_mm:
                groups[f"{service_name}.{component_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = hosts_in_mm
                groups[f"{service_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] |= hosts_in_mm

    if hc_delta.is_empty:
        return groups

    for component_key, hosts in hc_delta.add.items():
        group_full_name = f"{component_key}.add"
        hosts_not_in_mm = {(host.id, host.name) for host in hosts if host.id not in hosts_in_maintenance_mode}
        if hosts_not_in_mm:
            groups[group_full_name] = hosts_not_in_mm

    for component_key, hosts in hc_delta.remove.items():
        group_full_name = f"{component_key}.remove"
        hosts_not_in_mm = {(host.id, host.name) for host in hosts if host.id not in hosts_in_maintenance_mode}
        if hosts_not_in_mm:
            groups[group_full_name] = hosts_not_in_mm

        hosts_in_mm = {(host.id, host.name) for host in hosts if host.id in hosts_in_maintenance_mode}
        if hosts_in_mm:
            groups[f"{group_full_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = hosts_in_mm

    return groups
