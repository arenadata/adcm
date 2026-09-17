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

"""
Entries of `scripts`: scripts themselves and groups of them.

Every place scripts are declared at has its own set of allowed scripts, groups inside of it allow the same set.
Restrictions on what groups may contain (e.g. no `bundle_switch` in them)
are checked on execution plan built out of entries, not in here.

Entries are recursive (groups contain groups), so they are declared via `TypeAliasType` to be resolved lazily.
"""

from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import Discriminator, Field, Tag
from typing_extensions import TypeAliasType

from core.action.types import ExecutionStyle
from core.bundle._parsing.v_2_0.actions import (
    ADCMScript,
    ClusterScript,
    DynamicActionScript,
    DynamicWizardScript,
    ProviderScript,
)
from core.bundle._parsing.v_2_0.schema import Name
from core.bundle._parsing.v_2_0.upgrades import DynamicUpgradeScript, UpgradeScript

EntryT = TypeVar("EntryT")


@dataclass(slots=True)
class ScriptGroupBody(Generic[EntryT]):
    type: ExecutionStyle
    name: Name
    display_name: Annotated[str | None, Field(default=None)]
    scripts: Annotated[list[EntryT], Field(min_length=1)]


@dataclass(slots=True)
class ScriptGroup(Generic[EntryT]):
    group: ScriptGroupBody[EntryT]


def detect_entry_kind(value: Any) -> Literal["group", "script"]:
    # called with raw data on validation and with parsed objects on dump
    if isinstance(value, dict):
        return "group" if "group" in value else "script"

    return "group" if isinstance(value, ScriptGroup) else "script"


ClusterEntry = TypeAliasType(
    "ClusterEntry",
    Annotated[
        Annotated[ClusterScript, Tag("script")] | Annotated["ScriptGroup[ClusterEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
ProviderEntry = TypeAliasType(
    "ProviderEntry",
    Annotated[
        Annotated[ProviderScript, Tag("script")] | Annotated["ScriptGroup[ProviderEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
ADCMEntry = TypeAliasType(
    "ADCMEntry",
    Annotated[
        Annotated[ADCMScript, Tag("script")] | Annotated["ScriptGroup[ADCMEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
DynamicActionEntry = TypeAliasType(
    "DynamicActionEntry",
    Annotated[
        Annotated[DynamicActionScript, Tag("script")] | Annotated["ScriptGroup[DynamicActionEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
DynamicWizardEntry = TypeAliasType(
    "DynamicWizardEntry",
    Annotated[
        Annotated[DynamicWizardScript, Tag("script")] | Annotated["ScriptGroup[DynamicWizardEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
UpgradeEntry = TypeAliasType(
    "UpgradeEntry",
    Annotated[
        Annotated[UpgradeScript, Tag("script")] | Annotated["ScriptGroup[UpgradeEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
DynamicUpgradeEntry = TypeAliasType(
    "DynamicUpgradeEntry",
    Annotated[
        Annotated[DynamicUpgradeScript, Tag("script")] | Annotated["ScriptGroup[DynamicUpgradeEntry]", Tag("group")],
        Discriminator(detect_entry_kind),
    ],
)
