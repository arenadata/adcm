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
from typing import Literal

from core.cluster.types import ClusterTopology
from core.types import HostID, HostName

from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.inventory._types import HostGroupName


def detect_host_groups_for_cluster_bundle_action(
    cluster_topology: ClusterTopology, hosts_in_maintenance_mode: set[int], hc_delta: dict
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

    if not hc_delta:
        return groups

    for hc_acl_action, delta_groups in hc_delta.items():
        hc_acl_action: Literal["add", "remove"]
        for host_group_prefix, hosts_in_group in delta_groups.items():
            host_group_prefix: HostGroupName
            group_full_name = f"{host_group_prefix}.{hc_acl_action}"

            hosts_not_in_mm = {
                (host.pk, host.fqdn) for host in hosts_in_group.values() if host.pk not in hosts_in_maintenance_mode
            }
            if hosts_not_in_mm:
                groups[group_full_name] = hosts_not_in_mm

            if hc_acl_action == "remove":
                hosts_in_mm = {
                    (host.pk, host.fqdn) for host in hosts_in_group.values() if host.pk in hosts_in_maintenance_mode
                }
                if hosts_in_mm:
                    groups[f"{group_full_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = hosts_in_mm

    return groups
