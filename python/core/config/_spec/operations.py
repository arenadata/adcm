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

from dataclasses import dataclass, field
from itertools import chain
from typing import Iterable

from core.config._names import is_part_of_group
from core.config._spec.parameters import ReadOnlyRule, WritableRule
from core.config._spec.spec import FullSpec
from core.config._types import ParameterFullName


@dataclass(slots=True)
class StatefulParameters:
    read_only: set[ParameterFullName] = field(default_factory=set)
    """
    Names for parameters and activatable groups
    """

    desync_allowed: set[ParameterFullName] = field(default_factory=set)
    """
    Names for parameters and activatable groups
    """

    deactivated: set[ParameterFullName] = field(default_factory=set)
    """
    Names for parameters in activatable groups, group names excluded
    """


def detect_stateful_parameters(
    spec: FullSpec, owner_state: str, active_groups: Iterable[ParameterFullName]
) -> StatefulParameters:
    """
    Gather information about "state" of parameters.
    State means that parameters have properties dependable on things like owner state or user input.
    Desync info also included for convenience reasons.
    Prefer using this function instead of figuring out what is allowed or not manually.
    """
    groups_activation = {param.identifier.full: param.activation for param in spec.groups.values() if param.activation}
    with_edit_rule = chain(spec.parameters.items(), groups_activation.items())
    read_only_parameters = {
        name for name, param in with_edit_rule if _is_read_only(rule=param.edit_rule, owner_state=owner_state)
    }

    deactivated_groups = spec.attributes.activatable_groups.difference(active_groups)
    deactivated_parameters = {
        parameter_name
        for parameter_name in spec.parameters
        for group_name in deactivated_groups
        if is_part_of_group(parameter=parameter_name, group=group_name)
    }

    return StatefulParameters(
        read_only=read_only_parameters,
        desync_allowed=spec.attributes.desyncable_parameters,
        deactivated=deactivated_parameters,
    )


# May be it should be placed in "rules" module if split will be required
def _is_read_only(rule: ReadOnlyRule | WritableRule, owner_state: str) -> bool:
    match rule:
        case ReadOnlyRule(read_only="any"):
            return True

        case ReadOnlyRule(read_only=states):
            return owner_state in states

        case WritableRule(writable="any"):
            return False

        case WritableRule(writable=states):
            return owner_state not in states
