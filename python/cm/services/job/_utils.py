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


from core.cluster.types import ClusterTopology, TopologyHostDiff

from cm.errors import AdcmEx
from cm.services.job.types import ActionHCRule, TaskMappingDelta


def construct_delta_for_task(topology: ClusterTopology, host_difference: TopologyHostDiff) -> TaskMappingDelta:
    delta = TaskMappingDelta()

    if not (host_difference.mapped or host_difference.unmapped):
        return delta

    component_keys = {
        component_id: f"{service_topology.info.name}.{component_topology.info.name}"
        for service_id, service_topology in topology.services.items()
        for component_id, component_topology in service_topology.components.items()
    }

    for component_id, added_hosts in host_difference.mapped.components.items():
        key = component_keys[component_id]
        delta.add[key] = {topology.hosts[host_id] for host_id in added_hosts}

    for component_id, removed_hosts in host_difference.unmapped.components.items():
        key = component_keys[component_id]
        delta.remove[key] = {topology.hosts[host_id] for host_id in removed_hosts}

    return delta


def check_delta_is_allowed(delta: TaskMappingDelta, rules: list[ActionHCRule]) -> None:
    if not rules:
        return

    allowed = {"add": set(), "remove": set()}
    for rule in rules:
        component_key = f"{rule['service']}.{rule['component']}"
        allowed[rule["action"]].add(component_key)

    disallowed_add = set(delta.add.keys()).difference(allowed["add"])
    if disallowed_add:
        disallowed = next(iter(disallowed_add))
        message = f'no permission to "add" component {disallowed} to cluster mapping'
        raise AdcmEx(code="WRONG_ACTION_HC", msg=message)

    disallowed_remove = set(delta.remove.keys()).difference(allowed["remove"])
    if disallowed_remove:
        disallowed = next(iter(disallowed_remove))
        message = f'no permission to "remove" component {disallowed} from cluster mapping'
        raise AdcmEx(code="WRONG_ACTION_HC", msg=message)
