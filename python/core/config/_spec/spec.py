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

from core.config._names import full_name_to_level_names
from core.config._spec.parameters import ParameterGroup, SimpleParameter
from core.config._types import ParameterFullName, ParameterLevelName


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
class SpecHierarchyLevel:
    fields: list[ParameterLevelName] = field(default_factory=list)
    child_groups: dict[ParameterLevelName, Self] = field(default_factory=dict)
    rule: HierarchyValidationRule = HierarchyValidationRule.ALL

    def register(self, name: list[ParameterLevelName] | tuple[ParameterLevelName, ...]) -> None:
        *groups, own_name = name

        if not groups:
            self.fields.append(own_name)
            return

        first_group, *rest_groups = groups

        if first_group not in self.child_groups:
            # This one added for convenience in cases when "groups" aren't passed in function, but only "parameters".
            # See test `test_hierarchy_register_without_groups` for example.
            if first_group not in self.fields:
                self.fields.append(first_group)

            self.child_groups[first_group] = self.__class__()

        self.child_groups[first_group].register((*rest_groups, own_name))

    def set_rule(
        self, group: list[ParameterLevelName] | tuple[ParameterLevelName, ...], rule: HierarchyValidationRule
    ) -> None:
        *groups, own_name = group

        if not groups:
            if own_name not in self.child_groups:
                # rule can be set only for groups, we trust caller on that,
                # so we create it if it's missing
                self.child_groups[own_name] = self.__class__()

            self.child_groups[own_name].rule = rule
            return

        first_group, *rest_groups = groups
        self.child_groups[first_group].set_rule(group=(*rest_groups, own_name), rule=rule)


class FullSpec(BaseModel):
    """
    Configuration Specification in ADCM-oriented format (as opposed to "raw bundle DSL format").

    Original format can be restored from this one thou (except defaults).

    Note that "defaults" information isn't part of Specification.
    Reasons for that:
        - in most cases defaults aren't required
        - they can be great in size => no reason to take them everywhere the spec goes
    """

    hierarchy: SpecHierarchyLevel = Field(default_factory=SpecHierarchyLevel)
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
