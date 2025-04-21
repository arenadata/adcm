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


from core.cluster.types import ClusterTopology
from core.types import HostID, HostName

from cm.services.job.inventory._constants import MAINTENANCE_MODE_GROUP_SUFFIX
from cm.services.job.inventory._types import HostGroupName
from cm.services.job.types import TaskMappingDelta


def detect_host_groups_for_cluster_bundle_action(
    cluster_topology: ClusterTopology, hosts_in_maintenance_mode: set[int], hc_delta: TaskMappingDelta
) -> dict[HostGroupName, set[tuple[HostID, HostName]]]:
    keep_in_mm = lambda hosts: set(hosts).intersection(hosts_in_maintenance_mode)  # noqa: E731
    keep_not_in_mm = lambda hosts: set(hosts).difference(hosts_in_maintenance_mode)  # noqa: E731

    groups = {
        "CLUSTER": keep_not_in_mm(cluster_topology.hosts),
        f"CLUSTER.{MAINTENANCE_MODE_GROUP_SUFFIX}": keep_in_mm(cluster_topology.hosts),
    }

    for service in cluster_topology.services.values():
        service_name = service.info.name
        # <service> and <service>.maintenance_mode
        groups[service_name] = keep_not_in_mm(service.host_ids)
        groups[f"{service_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = keep_in_mm(service.host_ids)

        for component in service.components.values():
            component_id = component.info.id
            component_name = component.info.name
            # <service>.<component> and <service>.<component>.maintenance_mode
            groups[f"{service_name}.{component_name}"] = keep_not_in_mm(component.hosts)
            groups[f"{service_name}.{component_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = keep_in_mm(component.hosts)
            # <service>.<component>.add and <service>.<component>.add.maintenance_mode
            groups[f"{service_name}.{component_name}.add"] = keep_not_in_mm(hc_delta.add.get(component_id, ()))
            groups[f"{service_name}.{component_name}.add.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = keep_in_mm(
                hc_delta.add.get(component_id, ())
            )
            # For backward compatibility add hosts also to
            # <service> and <service>.maintenance_mode
            groups[service_name].update(keep_not_in_mm(hc_delta.add.get(component_id, ())))
            groups[f"{service_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"].update(
                keep_in_mm(hc_delta.add.get(component_id, ()))
            )
            # <service>.<component> and <service>.<component>.maintenance_mode
            groups[f"{service_name}.{component_name}"].update(keep_not_in_mm(hc_delta.add.get(component_id, ())))
            groups[f"{service_name}.{component_name}.{MAINTENANCE_MODE_GROUP_SUFFIX}"].update(
                keep_in_mm(hc_delta.add.get(component_id, ()))
            )
            # <service>.<component>.remove and <service>.<component>.remove.maintenance_mode
            groups[f"{service_name}.{component_name}.remove"] = keep_not_in_mm(hc_delta.remove.get(component_id, ()))
            groups[f"{service_name}.{component_name}.remove.{MAINTENANCE_MODE_GROUP_SUFFIX}"] = keep_in_mm(
                hc_delta.remove.get(component_id, ())
            )

    return {
        group_name: {(hid, cluster_topology.hosts[hid].name) for hid in hosts}
        for group_name, hosts in groups.items()
        if len(hosts) > 0
    }
