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

from copy import deepcopy
from pathlib import Path
from typing import Final, Iterable, Literal

from core.bundle._definitions import Definition, DefinitionsMap
from core.bundle._parsing.shared.conversion import convert_object
from core.bundle._parsing.shared.parser import PydanticParser
from core.bundle._parsing.v_2_0.targets import (
    ADCMSchema,
    Cluster,
    DynamicActionScripts,
    DynamicConfig,
    DynamicUpgradeScripts,
    DynamicWizardScripts,
    Host,
    ObjectTarget,
    Provider,
    RootTarget,
    Service,
)
from core.bundle._predicates import is_component_key
from core.bundle._representation import find_parent, repr_from_key
from core.bundle._types import BundleDefinitionKey
from core.errors import localize_error

TYPE_SCHEMA_MAP: Final[dict[str, type[RootTarget]]] = {
    "cluster": Cluster,
    "service": Service,
    "provider": Provider,
    "host": Host,
    "adcm": ADCMSchema,
}


class Parser(PydanticParser[RootTarget, ObjectTarget]):
    def _get_schema_mapping(self) -> dict[str, type[RootTarget]]:
        return TYPE_SCHEMA_MAP

    def _get_config_model(self) -> type[DynamicConfig]:
        return DynamicConfig

    def _get_scripts_model(
        self, mode: Literal["action", "upgrade", "wizard"]
    ) -> type[DynamicActionScripts | DynamicUpgradeScripts | DynamicWizardScripts]:
        match mode:
            case "action":
                return DynamicActionScripts
            case "upgrade":
                return DynamicUpgradeScripts
            case "wizard":
                return DynamicWizardScripts

    def _flatten_definitions(self, definition: RootTarget) -> Iterable[tuple[BundleDefinitionKey, ObjectTarget]]:
        if not isinstance(definition, Service):
            yield (definition.type,), definition
            return

        yield (definition.type, definition.name), definition

        for component_name, component_def in (definition.components or {}).items():
            yield ("component", definition.name, component_name), component_def

    def _convert_objects(
        self,
        definitions: dict[BundleDefinitionKey, ObjectTarget],
        relative_definition_paths: dict[BundleDefinitionKey, str],
        bundle_root: Path,
    ) -> DefinitionsMap:
        dict_definitions = {
            key: entry.model_dump(exclude_unset=True, exclude_defaults=True) for key, entry in definitions.items()
        }

        _propagate_attributes(dict_definitions)

        return {
            key: _schema_entry_to_definition(
                key=key,
                entry=definition,
                entries=dict_definitions,
                source_relative_path=relative_definition_paths[key],
                bundle_root=bundle_root,
            )
            for key, definition in dict_definitions.items()
        }


def _propagate_attributes(definitions: dict[BundleDefinitionKey, dict]) -> None:
    # order definitions to propagate from parent to child consistently
    weights = {"cluster": 0, "provider": 0, "adcm": 0, "service": 1, "host": 1, "component": 2}
    ordered_definitions = sorted(definitions.items(), key=lambda kv: weights[kv[0][0]])

    for key, definition in ordered_definitions:
        with localize_error(repr_from_key(key)):
            propagate_from_parent_to_child = ("venv", "flag_autogeneration")
            parent = None

            # bad section with parent detection, require improvement
            match key:
                case ("host",):
                    parent_key = ("provider",)
                    parent = definitions[parent_key]

                case ("service", _):
                    parent_key = ("cluster",)
                    parent = definitions[parent_key]
                    propagate_from_parent_to_child = (*propagate_from_parent_to_child, "config_group_customization")

                    # patch hc_acl entries where can be patched
                    for action in (definition.get("actions") or {}).values():
                        for entry in action.get("hc_acl") or ():
                            if entry.get("service") is None:
                                entry["service"] = definition["name"]

                case ("component", service_name, _):
                    parent_key = ("service", service_name)
                    parent = definitions[parent_key]
                    propagate_from_parent_to_child = (*propagate_from_parent_to_child, "config_group_customization")

                    for requirement in definition.get("requires") or ():
                        if requirement.get("service") is None:
                            requirement["service"] = service_name

            if parent:
                for property_key in propagate_from_parent_to_child:
                    _propagate(property_key, source=parent, target=definition)

            for action in (definition.get("actions") or {}).values():
                action["type"] = "task"  # required for conversion
                _propagate("venv", source=definition, target=action)

                for script in action.get("scripts") or ():
                    _propagate("allow_to_terminate", source=action, target=script)

            for upgrade in definition.get("upgrade") or ():
                _propagate("venv", source=definition, target=upgrade)


def _propagate(key: str, source: dict, target: dict) -> None:
    if target.get(key) is None:
        target[key] = source.get(key)


def _schema_entry_to_definition(
    key: BundleDefinitionKey,
    entry: dict,
    entries: dict[BundleDefinitionKey, dict],
    source_relative_path: str,
    bundle_root: Path,
) -> Definition:
    plain_entity = deepcopy(entry)

    context = {"bundle_root": bundle_root, "path": source_relative_path, "key": key, "object": plain_entity}

    if is_component_key(key):
        parent = find_parent(key, entries)
        inherited = {
            "name": key[-1],
            "version": parent["version"],
            "type": "component",
            "adcm_min_version": parent.get("adcm_min_version"),
        }
        plain_entity |= inherited

    definition: Definition = convert_object(plain_entity, context)

    return definition
