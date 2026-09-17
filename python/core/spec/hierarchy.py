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

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from typing_extensions import Self

from core.spec.types import LevelSpecKey

RuleT = TypeVar("RuleT")


@dataclass(slots=True)
class HierarchyLevel(ABC, Generic[RuleT]):
    """
    One level of a specification hierarchy: what's declared directly in it,
    which of those are groups with a level of their own, and how entries of
    this level relate to each other.

    LEGACY NOTE on attribute naming:
        `fields` and `child_groups` are named after configuration parameters,
        even thou the type is domain-agnostic. This exact naming is already
        persisted as JSON (`FullSpec` dumps stored in wizard step specs),
        so renaming requires a data migration and is deliberately postponed.

    Attributes:
        fields: keys of everything declared at this level, leaves and groups alike,
            in declaration order. Defines order, not kind.
        child_groups: subset of `fields` that are groups, mapped to their own level.
            Every key here is also present in `fields`, the reverse is not true.
        rule: how entries of this level relate to each other.
            Its meaning is domain-specific (e.g. a validation rule for configuration,
            an execution style for jobs), which is what `RuleT` parametrizes.
    """

    rule: RuleT
    fields: list[LevelSpecKey] = field(default_factory=list)
    child_groups: dict[LevelSpecKey, Self] = field(default_factory=dict)

    @classmethod
    @abstractmethod
    def build_with_defaults(cls) -> Self:
        """
        Build an empty level with the default `rule` of the concrete domain.

        Required because `rule` has no domain-agnostic default,
        yet levels have to be created implicitly during `register` / `set_rule`.
        """

    def register(self, key: Sequence[LevelSpecKey]) -> bool:
        """
        Place `key` at its level, creating levels of groups it's nested in if they're missing.

        Returns whether it was placed: `False` means the key is already present at its level
        (registered before or created implicitly as a group of previously registered key).
        It's up to the caller to decide whether that's an error.
        """

        *groups, own_key = key

        if not groups:
            if own_key in self.fields:
                return False

            self.fields.append(own_key)
            return True

        first_group, *rest_groups = groups

        if first_group not in self.child_groups:
            # This one added for convenience in cases when "groups" aren't passed in function, but only "parameters".
            # See test `test_hierarchy_register_without_groups` for example.
            if first_group not in self.fields:
                self.fields.append(first_group)

            self.child_groups[first_group] = self.build_with_defaults()

        return self.child_groups[first_group].register((*rest_groups, own_key))

    def set_rule(self, group: Sequence[LevelSpecKey], rule: RuleT) -> None:
        *groups, own_key = group

        if not groups:
            if own_key not in self.child_groups:
                # rule can be set only for groups, we trust caller on that,
                # so we create it if it's missing
                self.child_groups[own_key] = self.build_with_defaults()

            self.child_groups[own_key].rule = rule
            return

        first_group, *rest_groups = groups
        self.child_groups[first_group].set_rule(group=(*rest_groups, own_key), rule=rule)
