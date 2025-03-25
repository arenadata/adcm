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

from contextlib import suppress
from operator import itemgetter
from pathlib import Path
from typing import Any, Generator, Hashable, Iterable, TypeAlias
import warnings
import collections.abc

from adcm_version import compare_adcm_versions
from ruyaml.error import ReusedAnchorWarning
from typing_extensions import TypedDict
import yaml
import ruyaml

from core.bundle_alt.bundle_load import get_config_files
from core.bundle_alt.convertion import extract_scripts, schema_entry_to_definition
from core.bundle_alt.errors import (
    BundleParsingError,
    BundleProcessingError,
    BundleValidationError,
    convert_validation_to_bundle_error,
)
from core.bundle_alt.representation import build_parent_key_safe, repr_from_key, repr_from_raw
from core.bundle_alt.schema import (
    ADCMSchema,
    ClusterSchema,
    ComponentSchema,
    HostSchema,
    ProviderSchema,
    ScriptsJinjaSchema,
    ServiceSchema,
    parse,
)
from core.bundle_alt.types import BundleDefinitionKey, Definition
from core.bundle_alt.validation import check_definitions_are_valid
from core.errors import localize_error
from core.job.types import JobSpec

_ParsedRootDefinition: TypeAlias = ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema
_ParsedDefinition: TypeAlias = _ParsedRootDefinition | ComponentSchema
_RelativePath: TypeAlias = str


class ScriptJinjaContext(TypedDict):
    source_dir: Path
    action_allow_to_terminate: bool


class ConfigJinjaContext(TypedDict):
    bundle_root: Path
    path: str  # dir with jinja template, relative to bundle root
    object: dict


# COPIED FROM cm.checker DURING ADCM-6411
#
# This takes much more time than regular load,
# but some bundles contain duplicates in dict keys and stuff,
# when it's required to keep first element (at least for studied case),
# so we were forced to return this until the better solution is found.
def round_trip_load(stream, version=None, preserve_quotes=None, allow_duplicate_keys=False):
    """
    Parse the first YAML document in a stream and produce the corresponding Python object.

    This is a replace for ruyaml.round_trip_load() function which can switch off
    duplicate YAML keys error
    """

    loader = ruyaml.RoundTripLoader(stream, version, preserve_quotes=preserve_quotes)
    loader._constructor.allow_duplicate_keys = allow_duplicate_keys
    try:
        return loader._constructor.get_single_data()
    finally:
        loader._parser.dispose()
        with suppress(AttributeError):
            loader._reader.reset_reader()
        with suppress(AttributeError):
            loader._scanner.reset_scanner()


class FirstExplicitKeyLoader(yaml.SafeLoader):
    """
    Alternative Safe Loader that imitates ruyaml behavior
    in terms of overwritting keys, (when it's important for us)

    Code is copied from SafeLoader implementation with minor changes to ensure:
    1. First unique key in map stays, others are dropped silently
    2. Entries in mapping that came from anchors (<<: * syntax)
       have lower priority than "explicitly" defined.
       They are processed after "explicitly" defined
       => if they duplicate some key, they will be dropped.
    """

    def construct_mapping(self, node, deep: bool = False) -> dict[Hashable, Any]:
        if not isinstance(node, yaml.MappingNode):
            raise yaml.constructor.ConstructorError(
                None, None, "expected a mapping node, but found %s" % node.id, node.start_mark
            )

        self.flatten_mapping(node)

        mapping = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, collections.abc.Hashable):
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping", node.start_mark, "found unhashable key", key_node.start_mark
                )

            if key in mapping:
                continue

            value = self.construct_object(value_node, deep=deep)
            mapping[key] = value

        return mapping

    def flatten_mapping(self, node):
        merge = []
        index = 0
        while index < len(node.value):
            key_node, value_node = node.value[index]
            if key_node.tag == "tag:yaml.org,2002:merge":
                del node.value[index]
                if isinstance(value_node, yaml.MappingNode):
                    self.flatten_mapping(value_node)
                    merge.extend(value_node.value)
                elif isinstance(value_node, yaml.SequenceNode):
                    submerge = []
                    for subnode in value_node.value:
                        if not isinstance(subnode, yaml.MappingNode):
                            raise yaml.constructor.ConstructorError(
                                "while constructing a mapping",
                                node.start_mark,
                                "expected a mapping for merging, but found %s" % subnode.id,
                                subnode.start_mark,
                            )
                        self.flatten_mapping(subnode)
                        submerge.append(subnode.value)
                    submerge.reverse()
                    for value in submerge:
                        merge.extend(value)
                else:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        "expected a mapping or list of mappings for merging, but found %s" % value_node.id,
                        value_node.start_mark,
                    )
            elif key_node.tag == "tag:yaml.org,2002:value":
                key_node.tag = "tag:yaml.org,2002:str"
                index += 1
            else:
                index += 1
        if merge:
            # the only changed line to change priority of anchors
            node.value += merge


def retrieve_bundle_definitions(
    bundle_dir: Path, *, adcm_version: str, yspec_schema: dict
) -> dict[BundleDefinitionKey, Definition]:
    with localize_error(f"Bundle at {bundle_dir}"):
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


@convert_validation_to_bundle_error
def parse_scripts_jinja(data: list[dict], context: ScriptJinjaContext) -> Generator[JobSpec, None, None]:
    scripts = ScriptsJinjaSchema.model_validate({"scripts": data}, strict=True)
    scripts = scripts.model_dump(exclude_unset=True, exclude_defaults=True)["scripts"]

    for script in scripts:  # propagate `allow_to_terminate` attr from action if not set
        if not script.get("allow_to_terminate"):
            script["allow_to_terminate"] = context["action_allow_to_terminate"]

    yield from extract_scripts(scripts=scripts, path_resolution_root=context["source_dir"])


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

    # ensure it's re-entrable
    pairs = tuple(definition_path_pairs)

    # need to check all versions first
    for raw_definition, path_to_source in pairs:
        with localize_error(f"In file {path_to_source}", repr_from_raw(raw_definition)):
            check_adcm_min_version(current=adcm_version, required=str(raw_definition.get("adcm_min_version", "0")))

    for raw_definition, path_to_source in pairs:
        # todo add convertion func for localize_error
        with localize_error(f"In file: {path_to_source}", repr_from_raw(raw_definition)):
            root_level_definition = parse(raw_definition)
            for key, parsed_definition in _flatten_definitions(root_level_definition):
                _check_is_not_duplicate(key, definitions_map)
                definitions_map[key] = parsed_definition
                paths_map[key] = str(path_to_source.relative_to(bundle_root).parent)

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
        raise BundleValidationError(message)


def _propagate_attributes(definitions: dict[BundleDefinitionKey, _ParsedDefinition]) -> None:
    for key, definition in definitions.items():
        with localize_error(repr_from_key(key)):
            for action in (definition.actions or {}).values():
                if action.venv is None:
                    action.venv = definition.venv

                if hasattr(action, "scripts"):
                    for script in action.scripts or ():
                        if script.get("allow_to_terminate") is None:
                            script["allow_to_terminate"] = action.allow_to_terminate
                        if script.get("params") is None:
                            script["params"] = action.params

            if hasattr(definition, "upgrade"):
                for upgrade in definition.upgrade or ():
                    if upgrade.venv is None:
                        upgrade.venv = definition.venv

            parent_key = build_parent_key_safe(key)
            if not parent_key:
                continue

            parent = definitions[parent_key]

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
                for entry in action.hc_acl or ():
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
        raise BundleParsingError(f"Duplicate definition of {key}")


# Probably worth moving the section below in separate modules
def check_adcm_min_version(current: str, required: str):
    if compare_adcm_versions(required, current) > 0:
        raise BundleParsingError(
            f"This bundle required ADCM version equal to {required} or newer.",
        )


def read_raw_bundle_definitions(bundle_root: Path) -> Iterable[tuple[dict, Path]]:
    for _, path in get_config_files(bundle_root):
        content = _read_config_file(path)
        definitions = _config_content_to_list(content)

        for definition in definitions:
            yield definition, path


def _read_config_file(path: Path) -> Any:
    warnings.simplefilter(action="error", category=ReusedAnchorWarning)
    content = path.read_text(encoding="utf-8")
    try:
        # Check is silenced, because Loader inherits from SafeLoader
        # and doesn't override important safe-related stuff
        return yaml.load(content, Loader=FirstExplicitKeyLoader)  # noqa: S506
    except yaml.error.YAMLError as e:
        message = f'Error during parsing yaml file at "{path}": {e}'
        raise BundleProcessingError(message) from e


def _config_content_to_list(config_file_content: Any) -> list[dict]:
    if isinstance(config_file_content, dict):
        return [config_file_content]

    if not isinstance(config_file_content, list):
        raise TypeError(f"config.yaml contents are expected to be lists of dicts, not {type(config_file_content)}")

    if not all(isinstance(e, dict) for e in config_file_content):
        raise TypeError("All entries in definitions list in config.yaml should be dictionaries")

    return config_file_content
