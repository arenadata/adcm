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
from core.job.types import HcAclRule, TaskMappingDelta
from core.types import ComponentID, ComponentNameKey

from cm.errors import AdcmEx
from cm.services.job.types import ActionHCRule


def construct_delta_for_task(host_difference: TopologyHostDiff) -> TaskMappingDelta:
    delta = TaskMappingDelta()
    delta.add = dict(host_difference.mapped.components)
    delta.remove = dict(host_difference.unmapped.components)

    return delta


def check_delta_is_allowed(
    delta: TaskMappingDelta,
    rules: list[ActionHCRule | HcAclRule],
    full_name_mapping: dict[ComponentNameKey, ComponentID],
) -> None:
    if not rules:
        return

    allowed = {"add": set(), "remove": set()}

    for rule in rules:
        component_key = ComponentNameKey(service=rule["service"], component=rule["component"])
        component_id = full_name_mapping.get(component_key)
        if component_id:
            allowed[rule["action"]].add(component_id)

    disallowed_add = set(delta.add.keys()).difference(allowed["add"])
    if disallowed_add:
        disallowed_id = next(iter(disallowed_add))
        reversed_mapping = {val: key for key, val in full_name_mapping.items()}
        disallowed_name = reversed_mapping[disallowed_id]
        message = f'no permission to "add" component {disallowed_name} to cluster mapping'
        raise AdcmEx(code="WRONG_ACTION_HC", msg=message)

    disallowed_remove = set(delta.remove.keys()).difference(allowed["remove"])
    if disallowed_remove:
        disallowed_id = next(iter(disallowed_remove))
        reversed_mapping = {val: key for key, val in full_name_mapping.items()}
        disallowed_name = reversed_mapping[disallowed_id]
        message = f'no permission to "remove" component {disallowed_name} from cluster mapping'
        raise AdcmEx(code="WRONG_ACTION_HC", msg=message)
