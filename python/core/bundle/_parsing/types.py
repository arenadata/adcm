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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Protocol, TypeAlias

from core.bundle._definitions import DefinitionsMap

VersionTag: TypeAlias = str
VersionSupportStatus: TypeAlias = Literal["supported", "deprecated"]


@dataclass(slots=True)
class VersionInfo:
    tag: VersionTag
    status: VersionSupportStatus


@dataclass(slots=True)
class ParsingMeta:
    adcm_min_version: str | None = None
    contract_version: VersionTag = "1.0"


@dataclass(slots=True)
class RootEntry:
    data: dict[str, Any]
    full_path_to_file: Path


class BundleParser(Protocol):
    def parse_root_entries(self, entries: Iterable[RootEntry], bundle_root: Path) -> DefinitionsMap:
        # parsed_definitions_map, definition_path_map = _parse_bundle_definitions(
        #     definition_path_pairs, bundle_root=bundle_dir, adcm_version=adcm_version
        # )
        # _propagate_attributes(parsed_definitions_map)
        # normalized_definitions = _normalize_definitions(
        #    definitions=parsed_definitions_map, relative_definition_paths=definition_path_map, bundle_root=bundle_dir
        # )

        ...
