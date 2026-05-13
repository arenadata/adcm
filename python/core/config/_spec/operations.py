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

from typing import Iterable

from core.config._names import is_part_of_group, level_name_from_full_name
from core.config._spec.parameters import Identifier, MapParameter, StringParameter
from core.config._spec.spec import FullSpec
from core.config._types import ParameterFullName


# may it be safely united with `detect_deactivated_parameters`?
def detect_deactivated_groups(spec: FullSpec, active_groups: Iterable[ParameterFullName]) -> set[ParameterFullName]:
    deactivated_groups = spec.attributes.activatable_groups.difference(active_groups)
    if not deactivated_groups:
        return set()

    return {
        group_name
        for group_name in spec.groups
        for deactivated_name in deactivated_groups
        if is_part_of_group(group_name, group=deactivated_name)
    }


def detect_deactivated_parameters(spec: FullSpec, active_groups: Iterable[ParameterFullName]) -> set[ParameterFullName]:
    deactivated_groups = spec.attributes.activatable_groups.difference(active_groups)
    if not deactivated_groups:
        return set()

    return {
        parameter_name
        for parameter_name in spec.parameters
        for group_name in deactivated_groups
        if is_part_of_group(parameter_name, group=group_name)
    }


def build_identifier_from_name(full_name: ParameterFullName) -> Identifier:
    name = level_name_from_full_name(full_name)
    return Identifier(name=name, full=full_name)


def get_secret_parameters_names(spec: FullSpec) -> set[ParameterFullName]:
    return {
        name
        for name, param in spec.parameters.items()
        if isinstance(param, StringParameter | MapParameter) and param.is_secret
    }
