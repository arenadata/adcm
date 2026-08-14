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

from collections.abc import Collection
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from core import action, config, mapping
from core.bundle import parsing
from core.bundle._definitions import DefinitionsMap
from core.bundle._files import get_config_files
from core.bundle._reader import read_root_entries_from_yaml_file
from core.bundle._repo import BundleRepoI
from core.bundle._types import (
    BundleCompatibilityReport,
    BundleContext,
    BundleInfo,
    VersionSupportStatus,
)
from core.bundle._validate import (
    ConvertConfigDefinition,
    ValidationContext,
    check_config_defaults,
    check_definitions_are_valid,
    check_dynamic_config_definition,
    check_has_valid_definitions_set,
)
from core.types import BundleID, CoreObjectDescriptor, CurrentADCMVersion, PrototypeID


@dataclass(slots=True)
class BundleService:
    adcm_version: CurrentADCMVersion
    parsers: list[tuple[parsing.VersionInfo, parsing.BundleParser]]
    definition_to_spec_converter: ConvertConfigDefinition

    repo: BundleRepoI

    config_service: config.ConfigService

    def create_bundle_from_definitions(self, definitions: DefinitionsMap, bundle_info: BundleInfo) -> BundleID:
        bundle_id = self.repo.save_definitions(definitions=definitions, bundle_info=bundle_info)
        self.repo.update_prototype_licenses(bundle_id=bundle_id)
        self.repo.recollect_categories()
        return bundle_id

    def read_root_bundle_entries_from_fs(self, bundle_root: Path) -> list[parsing.RootEntry]:
        config_files = get_config_files(bundle_root)
        root_entries = map(read_root_entries_from_yaml_file, config_files)
        return list(chain.from_iterable(root_entries))

    def parse_to_definitions(
        self, entries: Collection[parsing.RootEntry], bundle_root: Path
    ) -> tuple[parsing.ParsingMeta, DefinitionsMap]:
        meta = parsing.extract_parsing_meta(entries)
        parsing.check_adcm_min_version(current=self.adcm_version, required=meta.adcm_min_version)
        parser = parsing.pick_suitable_parser(version=meta.contract_version, parsers=self.parsers)
        definitions = parser.parse_root_entries(entries=entries, bundle_root=bundle_root)
        check_has_valid_definitions_set(definitions)
        context = ValidationContext(bundle_root=bundle_root, to_spec_and_defaults=self.definition_to_spec_converter)
        check_definitions_are_valid(definitions=definitions, context=context, config_service=self.config_service)
        return meta, definitions

    def parse_to_spec_with_defaults(
        self,
        data: list[dict],
        bundle_context: BundleContext,
        template_path: Path,
        owner: CoreObjectDescriptor,
    ) -> tuple[config.spec.FullSpec, config.Defaults]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        definition = parser.parse_config(config=data, bundle_root=bundle_context.root, template_path=template_path)
        owner_spec = self.config_service.retrieve_partial_specification(
            owner=owner, only_for_types=[config.spec.p.VariantParameter]
        )
        check_dynamic_config_definition(definition=definition, bundle_root=bundle_context.root, spec=owner_spec)
        specification, defaults = self.definition_to_spec_converter(definition, bundle_context.root)
        check_config_defaults(specification=specification, defaults=defaults, config_service=self.config_service)
        return specification, defaults

    def parse_to_action_scripts(
        self,
        data: list[dict],
        bundle_context: BundleContext,
        template_path: Path,
        action_allow_to_terminate: bool,
    ) -> list[action.JobSpec]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        return parser.parse_scripts(
            scripts=data,
            template_path=template_path,
            action_allow_to_terminate=action_allow_to_terminate,
            mode="action",
        )

    def parse_to_upgrade_scripts(
        self,
        data: list[dict],
        bundle_context: BundleContext,
        template_path: Path,
        action_allow_to_terminate: bool,
    ) -> list[action.JobSpec]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        return parser.parse_scripts(
            scripts=data,
            template_path=template_path,
            action_allow_to_terminate=action_allow_to_terminate,
            mode="upgrade",
        )

    def parse_to_wizard_scripts(
        self,
        data: list[dict],
        bundle_context: BundleContext,
        template_path: Path,
        action_allow_to_terminate: bool,
    ) -> list[action.JobSpec]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        return parser.parse_scripts(
            scripts=data,
            template_path=template_path,
            action_allow_to_terminate=action_allow_to_terminate,
            mode="wizard",
        )

    def parse_to_wizard_stages(
        self,
        data: list[dict],
        bundle_context: BundleContext,
        template_path: Path,
    ) -> list[action.wizard.Stage]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        return parser.parse_wizard_stages(stages=data, template_path=template_path)

    def parse_to_mapping_rules(
        self,
        data: list[dict],
        bundle_context: BundleContext,
    ) -> list[mapping.MappingRule]:
        parser = parsing.pick_suitable_parser(version=bundle_context.contract_version, parsers=self.parsers)
        component_keys = self.repo.retrieve_component_keys(bundle_id=bundle_context.id)
        return parser.parse_mapping_rules(rules=data, component_keys=component_keys)

    def find_contract_compatibility_violations(self) -> BundleCompatibilityReport:
        versions_info = self.repo.retrieve_versions_info()

        supported_versions = {item[0].tag for item in self.parsers if item[0].status == VersionSupportStatus.SUPPORTED}
        deprecated_versions = {
            item[0].tag for item in self.parsers if item[0].status == VersionSupportStatus.DEPRECATED
        }
        report = BundleCompatibilityReport(
            supported_versions=supported_versions, deprecated_versions=deprecated_versions
        )

        for item in versions_info:
            if item.contract_version not in supported_versions:
                report.unsupported_version_bundles.add(item)

            if item.contract_version in deprecated_versions:
                report.deprecated_version_bundles.add(item)

        return report

    def retrieve_bundle_context_from_prototype(self, prototype_id: PrototypeID) -> BundleContext:
        return self.repo.retrieve_bundle_context_from_prototype(prototype_id=prototype_id)

    def clear_old_versions_adcm_bundles(self) -> None:
        self.repo.clear_old_versions_adcm_bundles()
