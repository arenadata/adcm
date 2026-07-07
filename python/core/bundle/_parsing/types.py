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

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, TypeAlias

from core import action, mapping
from core.bundle._definitions import ConfigDefinition, DefinitionsMap
from core.bundle._types import ComponentKey, ContractVersion, VersionSupportStatus

VersionTag: TypeAlias = str


@dataclass(slots=True)
class VersionInfo:
    tag: ContractVersion
    status: VersionSupportStatus


@dataclass(slots=True)
class ParsingMeta:
    adcm_min_version: str | None = None
    contract_version: ContractVersion = "1.0"


@dataclass(slots=True)
class RootEntry:
    data: dict[str, Any]
    full_path_to_file: Path


class BundleParser(Protocol):
    def parse_root_entries(self, entries: Iterable[RootEntry], bundle_root: Path) -> DefinitionsMap:
        ...

    def parse_config(
        self,
        config: list[dict],
        bundle_root: Path,
        template_path: Path,
    ) -> ConfigDefinition:
        ...

    def parse_scripts(
        self,
        scripts: list[dict],
        template_path: Path,
        action_allow_to_terminate: bool,
        mode: Literal["action", "upgrade", "wizard"],
    ) -> list[action.JobSpec]:
        ...

    def parse_wizard_stages(
        self,
        stages: list[dict],
        template_path: Path,
    ) -> list[action.wizard.Stage]:
        ...

    def parse_mapping_rules(
        self, rules: list[dict], component_keys: Collection[ComponentKey]
    ) -> list[mapping.MappingRule]:
        ...
