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
        _assign_host_to_group(host, "CLUSTER", groups, hosts_in_maintenance_mode)

    delta_by_comp = {}
    for op, op_dict in (("add", hc_delta.add), ("remove", hc_delta.remove)):
        for c_id, host_ids in op_dict.items():
            delta_by_comp.setdefault(c_id, {}).setdefault(op, set()).update(host_ids)

    for service in cluster_topology.services.values():
        s_name = service.info.name
        for component in service.components.values():
            c_name = component.info.name
            c_id = component.info.id
            comp_base = f"{s_name}.{c_name}"

            comp_host_ids = set(component.hosts)
            hosts_mm, hosts_not_mm = _partition_by_maintenance(comp_host_ids, hosts_in_maintenance_mode)
            hosts_mm_set = _host_id_name_set(hosts_mm, component.hosts)
            hosts_not_mm_set = _host_id_name_set(hosts_not_mm, component.hosts)

            comp_delta = delta_by_comp.get(c_id, {})
            delta_add = _host_id_name_set(comp_delta.get("add", ()), cluster_topology.hosts)
            delta_remove = _host_id_name_set(comp_delta.get("remove", ()), cluster_topology.hosts)

            add_mm = {entry for entry in delta_add if entry[0] in hosts_in_maintenance_mode}
            add_not_mm = delta_add - add_mm
            remove_mm = {entry for entry in delta_remove if entry[0] in hosts_in_maintenance_mode}
            remove_not_mm = delta_remove - remove_mm

            hosts_not_mm_set = (hosts_not_mm_set | add_not_mm) - remove_not_mm
            hosts_mm_set = (hosts_mm_set | add_mm) - remove_mm

            if hosts_not_mm_set:
                groups[comp_base] = hosts_not_mm_set
                groups[s_name] |= hosts_not_mm_set
            if hosts_mm_set:
                comp_mm_group = f"{comp_base}.{MAINTENANCE_MODE_GROUP_SUFFIX}"
                groups[comp_mm_group] = hosts_mm_set
                groups[f"{s_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] |= hosts_mm_set

            if delta_add:
                delta_add_mm = {entry for entry in delta_add if entry[0] in hosts_in_maintenance_mode}
                delta_add_not_mm = delta_add - delta_add_mm
                group_base = f"{comp_base}.add"
                if delta_add_not_mm:
                    groups[group_base] = delta_add_not_mm
            if delta_remove:
                delta_remove_mm = {entry for entry in delta_remove if entry[0] in hosts_in_maintenance_mode}
                delta_remove_not_mm = delta_remove - delta_remove_mm
                group_base = f"{comp_base}.remove"
                if delta_remove_not_mm:
                    groups[group_base] = delta_remove_not_mm
                if delta_remove_mm:
                    groups[f"{group_base}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = delta_remove_mm

    return groups


def _partition_by_maintenance(host_ids, hosts_in_maintenance_mode):
    in_mm = set()
    not_in_mm = set()
    for hid in host_ids:
        (in_mm if hid in hosts_in_maintenance_mode else not_in_mm).add(hid)
    return in_mm, not_in_mm


def _host_id_name_set(host_ids, host_map):
    return {(hid, host_map[hid].name) for hid in host_ids}


def _assign_host_to_group(host, group_base, groups, hosts_in_maintenance_mode):
    group = group_base if host.id not in hosts_in_maintenance_mode else f"{group_base}.{MAINTENANCE_MODE_GROUP_SUFFIX}"
    groups[group].add((host.id, host.name))
