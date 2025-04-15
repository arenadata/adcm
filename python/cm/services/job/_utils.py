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

from core.cluster.types import TopologyHostDiff

from cm.errors import AdcmEx
from cm.models import Component
from cm.services.job.types import ActionHCRule, TaskMappingDelta


def construct_delta_for_task(host_difference: TopologyHostDiff) -> TaskMappingDelta:
    delta = TaskMappingDelta()
    delta.add = dict(host_difference.mapped.components)
    delta.remove = dict(host_difference.unmapped.components)

    return delta


def check_delta_is_allowed(delta: TaskMappingDelta, rules: list[ActionHCRule]) -> None:
    if not rules:
        return

    allowed = {"add": set(), "remove": set()}
    components_lookup = {
        f"{service_name}.{component_name}": pk
        for service_name, component_name, pk in Component.objects.values_list(
            "service__prototype__name", "prototype__name", "pk"
        )
    }

    for rule in rules:
        component_key = f"{rule['service']}.{rule['component']}"  # Create the service.component key
        component_id = components_lookup.get(component_key)
        if component_id:
            allowed[rule["action"]].add(component_id)

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
