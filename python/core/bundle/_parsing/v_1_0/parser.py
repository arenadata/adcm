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

from pathlib import Path
from typing import Final, Iterable, Literal, TypeAlias, cast

from core.bundle._definitions import Definition, DefinitionsMap
from core.bundle._errors import BundleParsingError
from core.bundle._parsing.shared.conversion import convert_object
from core.bundle._parsing.shared.parser import PydanticParser
from core.bundle._parsing.v_1_0.schema import (
    ADCMSchema,
    ClusterSchema,
    ComponentSchema,
    ConfigJinjaSchema,
    DynamicScriptsSchema,
    HasConfigGroupCustomization,
    HasName,
    HasScripts,
    HasUpgrade,
    HostSchema,
    ProviderSchema,
    ServiceSchema,
    WizardScriptsSchema,
)
from core.bundle._predicates import is_component_key
from core.bundle._representation import build_parent_key_safe, find_parent, repr_from_key
from core.bundle._types import BundleDefinitionKey
from core.errors import localize_error

_ParsedRootDefinition: TypeAlias = ClusterSchema | ServiceSchema | ProviderSchema | HostSchema | ADCMSchema
_ParsedDefinition: TypeAlias = _ParsedRootDefinition | ComponentSchema
_RelativePath: TypeAlias = str

TYPE_SCHEMA_MAP: Final = {
    "cluster": ClusterSchema,
    "service": ServiceSchema,
    "provider": ProviderSchema,
    "host": HostSchema,
    "adcm": ADCMSchema,
}


class Parser(PydanticParser[_ParsedRootDefinition, _ParsedDefinition]):
    def _get_schema_mapping(self) -> dict[str, type[_ParsedRootDefinition]]:
        return TYPE_SCHEMA_MAP

    def _get_config_model(self) -> type[ConfigJinjaSchema]:
        return ConfigJinjaSchema

    def _get_scripts_model(self, mode: Literal["action", "wizard"]) -> type[DynamicScriptsSchema | WizardScriptsSchema]:
        match mode:
            case "action":
                return DynamicScriptsSchema
            case "wizard":
                return WizardScriptsSchema

    def _flatten_definitions(
        self, definition: _ParsedRootDefinition
    ) -> Iterable[tuple[BundleDefinitionKey, _ParsedDefinition]]:
        if not isinstance(definition, ServiceSchema):
            yield (definition.type,), definition
            return

        yield (definition.type, definition.name), definition

        for component_name, component_def in (definition.components or {}).items():
            yield ("component", definition.name, component_name), component_def

    def _convert_objects(
        self,
        definitions: dict[BundleDefinitionKey, _ParsedDefinition],
        relative_definition_paths: dict[BundleDefinitionKey, _RelativePath],
        bundle_root: Path,
    ) -> DefinitionsMap:
        _propagate_attributes(definitions)
        return _normalize_definitions(
            definitions=definitions, relative_definition_paths=relative_definition_paths, bundle_root=bundle_root
        )


def _propagate_attributes(definitions: dict[BundleDefinitionKey, _ParsedDefinition]) -> None:
    for key, definition in definitions.items():
        with localize_error(repr_from_key(key)):
            for action in (definition.actions or {}).values():
                if action.venv is None:
                    action.venv = definition.venv

                if isinstance(action, HasScripts):
                    for script in action.scripts or ():
                        if script.allow_to_terminate is None:
                            script.allow_to_terminate = action.allow_to_terminate
                        if script.params is None:
                            script.params = action.params  # pyright: ignore [reportAttributeAccessIssue]

            if isinstance(definition, HasUpgrade):
                for upgrade in definition.upgrade or ():
                    if upgrade.venv is None:
                        upgrade.venv = definition.venv

            if isinstance(definition, HostSchema) and definition.flag_autogeneration is None:
                definition.flag_autogeneration = definitions[("provider",)].flag_autogeneration

            parent_key = build_parent_key_safe(key)
            if not parent_key:
                continue

            try:
                parent = definitions[parent_key]
            except KeyError as e:
                raise BundleParsingError("There isn't any cluster or host provider definition in bundle") from e

            if definition.flag_autogeneration is None:
                definition.flag_autogeneration = parent.flag_autogeneration

            # now all objects with parents has config_group_customization
            if (
                isinstance(definition, HasConfigGroupCustomization)
                and isinstance(parent, HasConfigGroupCustomization)
                and definition.config_group_customization is None
            ):
                definition.config_group_customization = parent.config_group_customization

            if isinstance(definition, ComponentSchema):
                for requirement in definition.requires or ():
                    if requirement.get("service") is None and isinstance(parent, HasName):
                        requirement["service"] = parent.name

            # patch hc_acl entries where can be patched
            if isinstance(definition, ServiceSchema):
                for action in (definition.actions or {}).values():
                    for entry in action.hc_acl or ():
                        if entry.get("service") is None and isinstance(definition, HasName):
                            entry["service"] = definition.name


def _normalize_definitions(
    definitions: dict[BundleDefinitionKey, _ParsedDefinition],
    relative_definition_paths: dict[BundleDefinitionKey, _RelativePath],
    bundle_root: Path,
) -> DefinitionsMap:
    return {
        key: _schema_entry_to_definition(
            key=key,
            entry=definition,
            entries=definitions,
            source_relative_path=relative_definition_paths[key],
            bundle_root=bundle_root,
        )
        for key, definition in definitions.items()
    }


def _schema_entry_to_definition(
    key: BundleDefinitionKey,
    entry: ClusterSchema | ServiceSchema | ComponentSchema | ProviderSchema | HostSchema | ADCMSchema,
    entries: dict[
        BundleDefinitionKey, ClusterSchema | ServiceSchema | ComponentSchema | ProviderSchema | HostSchema | ADCMSchema
    ],
    source_relative_path: str,
    bundle_root: Path,
) -> Definition:
    plain_entity = entry.model_dump(exclude_unset=True, exclude_defaults=True)
    context = {"bundle_root": bundle_root, "path": source_relative_path, "key": key, "object": plain_entity}

    if is_component_key(key):
        parent = find_parent(key, entries)
        parent = cast(ClusterSchema | ServiceSchema, parent)
        inherited = {
            "name": key[-1],
            "version": parent.version,
            "type": "component",
            "adcm_min_version": parent.adcm_min_version,
        }
        plain_entity |= inherited

    definition: Definition = convert_object(plain_entity, context)

    return definition
