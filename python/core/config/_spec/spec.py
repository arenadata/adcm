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
from enum import Enum
from functools import cached_property

from pydantic import BaseModel, Field
from typing_extensions import Self

from core.config._names import full_name_to_level_names, level_names_to_full_name
from core.config._spec.parameters import ParameterGroup, SimpleParameter
from core.config._types import FullDisplayName, ParameterFullName
from core.spec.hierarchy import HierarchyLevel


@dataclass(slots=True)
class SpecAttributes:
    """
    "Special" properties of parameters that's worth storing separately
    and may affect certain scenarios.
    """

    activatable_groups: set[ParameterFullName] = field(default_factory=set)
    """
    Names of parameter groups that can be (de)activated
    """

    desyncable_parameters: set[ParameterFullName] = field(default_factory=set)
    """
    Names of parameters (including groups) that can be desynced from main configuration
    when working with configuration host groups
    """


class HierarchyValidationRule(str, Enum):
    ALL = "all"
    AT_MOST_ONE = "at-most-one"
    EXACTLY_ONE = "exactly-one"


@dataclass(slots=True)
class SpecHierarchyLevel(HierarchyLevel[HierarchyValidationRule]):
    @classmethod
    def build_with_defaults(cls) -> Self:
        return cls(rule=HierarchyValidationRule.ALL)


class FullSpec(BaseModel):
    """
    Configuration Specification in ADCM-oriented format (as opposed to "raw bundle DSL format").

    Original format can be restored from this one thou (except defaults).

    Note that "defaults" information isn't part of Specification.
    Reasons for that:
        - in most cases defaults aren't required
        - they can be great in size => no reason to take them everywhere the spec goes
    """

    hierarchy: SpecHierarchyLevel = Field(default_factory=SpecHierarchyLevel.build_with_defaults)
    groups: dict[ParameterFullName, ParameterGroup] = Field(default_factory=dict)
    parameters: dict[ParameterFullName, SimpleParameter] = Field(default_factory=dict)

    @cached_property
    def attributes(self) -> SpecAttributes:
        groups_activation = {name: group.activation for name, group in self.groups.items() if group.activation}
        with_desync_property = groups_activation | self.parameters
        desyncable_params = {name for name, param in with_desync_property.items() if param.is_desyncable}

        return SpecAttributes(activatable_groups=set(groups_activation.keys()), desyncable_parameters=desyncable_params)

    @classmethod
    def from_parameters(cls, *parameters: SimpleParameter | ParameterGroup) -> Self:
        instance = cls()

        for param in parameters:
            names = full_name_to_level_names(param.identifier.full)
            instance.hierarchy.register(names)

            if isinstance(param, ParameterGroup):
                instance.groups[param.identifier.full] = param
                if param.selection:
                    rule = (
                        HierarchyValidationRule.EXACTLY_ONE
                        if param.selection.is_required
                        else HierarchyValidationRule.AT_MOST_ONE
                    )
                    instance.hierarchy.set_rule(group=names, rule=rule)
            else:
                instance.parameters[param.identifier.full] = param

        return instance

    @property
    def is_empty(self) -> bool:
        return not self.parameters and not self.groups

    @cached_property
    def full_display_names(self) -> dict[ParameterFullName, FullDisplayName]:
        spec_items = self.groups | self.parameters
        return {name: _build_full_display_name(param=item, spec=self) for name, item in spec_items.items()}

    def get_full_display_name(self, param_full_name: ParameterFullName) -> ParameterFullName | FullDisplayName:
        """
        Return the full display name for parameters or groups by its full name.
        """

        return self.full_display_names.get(param_full_name, param_full_name)


def _build_full_display_name(param: SimpleParameter | ParameterGroup, spec: FullSpec) -> FullDisplayName:
    display_names = []

    levels = full_name_to_level_names(param.identifier.full)
    for i, level_name in enumerate(levels, start=1):
        full_name = level_names_to_full_name(levels[:i])
        spec_item = spec.parameters.get(full_name) or spec.groups.get(full_name)
        display_name = spec_item.extra.display_name if spec_item is not None else ""
        display_names.append(display_name or level_name)

    return level_names_to_full_name(display_names)
