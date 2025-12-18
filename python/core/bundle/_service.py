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
from itertools import chain
from pathlib import Path
from typing import Collection

from core import config
from core.bundle import parsing
from core.bundle._definitions import DefinitionsMap
from core.bundle._files import get_config_files
from core.bundle._reader import read_root_entries_from_yaml_file
from core.bundle._repo import BundleRepoI
from core.bundle._types import BundleUnpackingInfo
from core.bundle._validate import (
    ConvertConfigDefinition,
    ValidationContext,
    check_definitions_are_valid,
    check_has_valid_definitions_set,
)
from core.types import BundleID


@dataclass(slots=True)
class BundleService:
    adcm_version: str
    parsers: list[tuple[parsing.VersionInfo, parsing.BundleParser]]
    definition_to_spec_converter: ConvertConfigDefinition

    repo: BundleRepoI

    config_service: config.ConfigService

    def create_bundle_from_definitions(
        self, definitions: DefinitionsMap, unpacking_info: BundleUnpackingInfo
    ) -> BundleID:
        bundle_id = self.repo.save_definitions(
            definitions=definitions,
            bundle_root=unpacking_info.root,
            bundle_hash=unpacking_info.hash,
            verification_status=unpacking_info.signature,
        )
        self.repo.update_prototype_licenses(bundle_id=bundle_id)
        self.repo.recollect_categories()
        return bundle_id

    def read_root_bundle_entries_from_fs(self, bundle_root: Path) -> list[parsing.RootEntry]:
        config_files = get_config_files(bundle_root)
        root_entries = map(read_root_entries_from_yaml_file, config_files)
        return list(chain.from_iterable(root_entries))

    def parse_to_definitions(self, entries: Collection[parsing.RootEntry], bundle_root: Path) -> DefinitionsMap:
        meta = parsing.extract_parsing_meta(entries)
        parsing.check_adcm_min_version(current=self.adcm_version, required=meta.adcm_min_version)
        parser = parsing.pick_suitable_parser(version=meta.contract_version, parsers=self.parsers)
        definitions = parser.parse_root_entries(entries=entries, bundle_root=bundle_root)
        check_has_valid_definitions_set(definitions)
        context = ValidationContext(bundle_root=bundle_root, to_spec_and_defaults=self.definition_to_spec_converter)
        check_definitions_are_valid(definitions=definitions, context=context, config_service=self.config_service)
        return definitions
