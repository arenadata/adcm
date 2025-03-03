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

from operator import itemgetter
from pathlib import Path
from typing import Any, Iterable, TypeAlias

from adcm_version import compare_adcm_versions
import yaml

from core.bundle_alt.bundle_load import get_config_files
from core.bundle_alt.convertion import schema_entry_to_definition
from core.bundle_alt.representation import build_parent_key_safe, find_parent
from core.bundle_alt.schema import (
    ADCMSchema,
    ClusterSchema,
    ComponentSchema,
    HostSchema,
    ProviderSchema,
    ServiceSchema,
    parse_raw_definition,
)
from core.bundle_alt.types import BundleDefinitionKey, Definition
from core.bundle_alt.validation import check_definitions_are_valid
from core.errors import BundleParsingError

_ParsedRootDefinition: TypeAlias = ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema
_ParsedDefinition: TypeAlias = _ParsedRootDefinition | ComponentSchema
_RelativePath: TypeAlias = str


def retrieve_bundle_definitions(
    bundle_dir: Path, *, adcm_version: str, yspec_schema: dict
) -> dict[BundleDefinitionKey, Definition]:
    definition_path_pairs = read_raw_bundle_definitions(bundle_root=bundle_dir)
    parsed_definitions_map, definition_path_map = _parse_bundle_definitions(
        definition_path_pairs, bundle_root=bundle_dir, adcm_version=adcm_version
    )
    _check_no_definition_type_conflicts(parsed_definitions_map)
    _propagate_attributes(parsed_definitions_map)
    normalized_definitions = _normalize_definitions(
        definitions=parsed_definitions_map, relative_definition_paths=definition_path_map, bundle_root=bundle_dir
    )
    check_definitions_are_valid(normalized_definitions, bundle_root=bundle_dir, yspec_schema=yspec_schema)
    return normalized_definitions


def _normalize_definitions(
    definitions: dict[BundleDefinitionKey, _ParsedDefinition],
    relative_definition_paths: dict[BundleDefinitionKey, _RelativePath],
    bundle_root: Path,
):
    # + check per-object stuff?
    return {
        key: schema_entry_to_definition(
            key=key,
            entry=definition,
            entries=definitions,
            source_relative_path=relative_definition_paths[key],
            bundle_root=bundle_root,
        )
        for key, definition in definitions.items()
    }


def _parse_bundle_definitions(
    definition_path_pairs: Iterable[tuple[dict, Path]], bundle_root: Path, adcm_version: str
) -> tuple[dict[BundleDefinitionKey, _ParsedDefinition], dict[BundleDefinitionKey, _RelativePath]]:
    definitions_map = {}
    paths_map = {}

    for raw_definition, path_to_source in definition_path_pairs:
        check_adcm_min_version(current=adcm_version, required=str(raw_definition.get("adcm_min_version", "0")))
        root_level_definition = parse_raw_definition(raw_definition)
        for key, parsed_definition in _flatten_definitions(root_level_definition):
            _check_is_not_duplicate(key, definitions_map)
            definitions_map[key] = parsed_definition
            paths_map[key] = str(path_to_source.relative_to(bundle_root))

    return definitions_map, paths_map


def _check_no_definition_type_conflicts(keys: Iterable[BundleDefinitionKey]) -> None:
    definition_types = set(map(itemgetter(0), keys))

    allowed_adcm_bundle = {"adcm"}
    allowed_provider_bundle = {"provider", "host"}
    allowed_cluster_bundle = {"cluster", "service", "component"}

    is_cluster_bundle = allowed_cluster_bundle.issuperset(definition_types)
    is_provider_bundle = allowed_provider_bundle == definition_types
    is_adcm_bundle = allowed_adcm_bundle == definition_types

    if not any((is_cluster_bundle, is_provider_bundle, is_adcm_bundle)):
        message = (
            "Definitions in bundle doesn't fit cluster, provider or ADCM format: "
            f"{', '.join(sorted(definition_types))}"
        )
        raise BundleParsingError(code="BUNDLE_ERROR", msg=message)

    if is_cluster_bundle and not definition_types.issuperset({"cluster", "service"}):
        raise BundleParsingError(
            code="BUNDLE_ERROR", msg="Both cluster and service definitions should be present in cluster bundle"
        )


def _propagate_attributes(definitions: dict[BundleDefinitionKey, _ParsedDefinition]) -> None:
    for key, definition in definitions.items():
        parent_key = build_parent_key_safe(key)
        if not parent_key:
            continue

        parent = find_parent(parent_key, definitions)

        if definition.flag_autogeneration is None:
            definition.flag_autogeneration = parent.flag_autogeneration

        # now all objects with parents has config_group_customization
        if definition.config_group_customization is None:
            definition.config_group_customization = parent.config_group_customization

        if isinstance(definition, ComponentSchema):
            for requirement in definition.requires or ():
                if requirement.get("service") is None:
                    requirement["service"] = parent.name

        # patch hc_acl entries where can be patched
        service_from = parent if isinstance(definition, ComponentSchema) else definition

        for action in (definition.actions or {}).values():
            for entry in getattr(action, "hc_acl", ()):
                if not entry.get("service"):
                    entry["service"] = service_from.name


def _flatten_definitions(definition: _ParsedRootDefinition) -> Iterable[tuple[BundleDefinitionKey, _ParsedDefinition]]:
    if not isinstance(definition, ServiceSchema):
        yield (definition.type,), definition
        return

    yield (definition.type, definition.name), definition

    for component_name, component_def in (definition.components or {}).items():
        yield ("component", definition.name, component_name), component_def


def _check_is_not_duplicate(key: BundleDefinitionKey, existing_entries: Iterable[BundleDefinitionKey]) -> None:
    if key in existing_entries:
        raise BundleParsingError(code="INVALID_OBJECT_DEFINITION", msg=f"Duplicate definition of {key}")


# Probably worth moving the section below in separate modules
def check_adcm_min_version(current: str, required: str):
    if compare_adcm_versions(required, current) > 0:
        raise BundleParsingError(
            code="BUNDLE_VERSION_ERROR",
            msg=f"This bundle required ADCM version equal to {required} or newer.",
        )


def read_raw_bundle_definitions(bundle_root: Path) -> Iterable[tuple[dict, Path]]:
    for _, path in get_config_files(bundle_root):
        content = _read_config_file(path)
        definitions = _config_content_to_list(content)

        for definition in definitions:
            yield definition, path


def _read_config_file(path: Path) -> Any:
    text_content = path.read_text(encoding="utf-8")
    return yaml.safe_load(stream=text_content)


def _config_content_to_list(config_file_content: Any) -> list[dict]:
    if isinstance(config_file_content, dict):
        return [config_file_content]

    if not isinstance(config_file_content, list):
        raise TypeError(f"config.yaml contents are expected to be lists of dicts, not {type(config_file_content)}")

    if not all(isinstance(e, dict) for e in config_file_content):
        raise TypeError("All entries in definitions list in config.yaml should be dictionaries")

    return config_file_content
