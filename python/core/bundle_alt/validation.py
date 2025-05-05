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
from typing import Collection, Iterable

from graphlib import CycleError, TopologicalSorter
from jinja2 import Template, TemplateError

from core.bundle_alt._config import check_default_values, key_to_str
from core.bundle_alt._yspec import FormatError, check_rule, process_rule
from core.bundle_alt.errors import BundleValidationError
from core.bundle_alt.predicates import has_requires, is_component, is_component_key, is_service
from core.bundle_alt.representation import dependency_entry_to_key, repr_from_key
from core.bundle_alt.types import (
    ActionDefinition,
    BundleDefinitionKey,
    ConfigDefinition,
    DefinitionsMap,
    ImportDefinition,
    UpgradeDefinition,
)
from core.errors import localize_error
from core.job.types import JobSpec, ScriptType

# This section should be in sort of global consts module
ADCM_HOST_TURN_ON_MM_ACTION_NAME = "adcm_host_turn_on_maintenance_mode"
ADCM_HOST_TURN_OFF_MM_ACTION_NAME = "adcm_host_turn_off_maintenance_mode"
ADCM_TURN_ON_MM_ACTION_NAME = "adcm_turn_on_maintenance_mode"
ADCM_TURN_OFF_MM_ACTION_NAME = "adcm_turn_off_maintenance_mode"
# section end


def check_definitions_are_valid(definitions: DefinitionsMap, bundle_root: Path, yspec_schema: dict) -> None:
    # special, require too much context to include it in main loop
    check_requires(definitions)

    for key, definition in definitions.items():
        with localize_error(repr_from_key(key)):
            check_import_defaults_exist_in_config(imports=definition.imports, config=definition.config)
            check_exported_values_exists_in_config(exports=definition.exports, config=definition.config)
            check_upgrades(upgrades=definition.upgrades, definitions=definitions)

            if definition.config:
                check_config(config=definition.config, bundle_root=bundle_root, yspec_schema=yspec_schema)

            check_actions(
                actions=definition.actions,
                definitions=definitions,
                bundle_root=bundle_root,
                definition_type=definition.type,
            )

            # unify check arguments and make it a map for each type?
            if is_component_key(key) and definition.bound_to:
                check_bound_to(bound_to=definition.bound_to, owner_key=key)


def check_requires(definitions: DefinitionsMap) -> None:
    requires_tree = TopologicalSorter()

    definitions_with_requires = filter(
        lambda kv: (is_service(kv[1]) or is_component(kv[1])) and has_requires(kv[1]), definitions.items()
    )

    for key, definition in definitions_with_requires:
        with localize_error(repr_from_key(key)):
            for requires in definition.requires:
                required_entry_key = dependency_entry_to_key(requires)
                if required_entry_key == key:
                    message = f'{key[0].capitalize()} can not require themself "{definition.name}"'
                    raise BundleValidationError(message)

                if required_entry_key not in definitions:
                    if is_component_key(required_entry_key):
                        _, service_name, component_name = required_entry_key
                        message = f'No required component "{component_name}" of service "{service_name}"'
                    else:
                        _, service_name = required_entry_key
                        message = f'No required service "{service_name}"'

                    raise BundleValidationError(message)

                if is_component_key(required_entry_key):
                    parent_key = ("service", required_entry_key[1])
                    requires_tree.add(key, parent_key, required_entry_key)

    try:
        requires_tree.prepare()
    except CycleError as err:
        raise BundleValidationError(f"Requires should not be cyclic: {err.args[1]}") from err


def check_bound_to(bound_to: dict, owner_key: BundleDefinitionKey) -> None:
    bound_entry_key = dependency_entry_to_key(bound_to)
    if bound_entry_key == owner_key:
        message = 'Component can not require themself in "bound_to"'
        raise BundleValidationError(message)


def check_config(config: ConfigDefinition, bundle_root: Path, yspec_schema: dict) -> None:
    for key, parameter in config.parameters.items():
        with localize_error(f"Configuration parameter: {key_to_str(key)}"):
            if parameter.type in ("file", "secretfile"):
                default = config.default_values.get(key)
                if default:
                    check_file_path_in_config(bundle_root, default, key)

            if parameter.type == "structure":
                param_schema = parameter.limits["yspec"]
                key_repr = key_to_str(key)
                try:
                    process_rule(data=param_schema, rules=yspec_schema, name="root")
                except FormatError as error:
                    message = f"Error in yspec file of config key {key_repr}: {error}"
                    raise BundleValidationError(message) from error

                success, error = check_rule(rules=param_schema)
                if not success:
                    message = f'yspec file of config key "{key_repr}" error: {error}'
                    raise BundleValidationError(message)

                for value in param_schema.values():
                    if value["match"] in {"one_of", "dict_key_selection", "set", "none", "any"}:
                        message = f"yspec file of config key '{key_repr}': '{value['match']}' rule is not supported"
                        raise BundleValidationError(message)

    check_default_values(parameters=config.parameters, values=config.default_values, attributes=config.default_attrs)


def check_file_path_in_config(bundle_root: Path, default: str, key: Iterable[str]):
    path = bundle_root / default

    full_path_bytes = str(path).encode("utf-8")
    file_name_bytes = (bundle_root / default).name.encode("utf-8")
    if len(full_path_bytes) > 4096 or len(file_name_bytes) > 255:
        message = f"Default file for {'.'.join(key)}: {path} can't exceed 4096 bytes in path and 255 bytes in file name"
        raise BundleValidationError(message)

    try:
        path.resolve(strict=True)
    except (OSError, PermissionError, FileNotFoundError) as e:
        message = f"Error in resolving default file for {'.'.join(key)}: {default}: {e}"
        raise BundleValidationError(message) from e

    if not path.is_file():
        message = f"Default file is missing for {'.'.join(key)}: {default}"
        raise BundleValidationError(message)


def check_actions(
    actions: list[ActionDefinition], definitions: DefinitionsMap, definition_type: str, bundle_root: Path
) -> None:
    for action in actions:
        with localize_error(f"Action {action.name}"):
            check_no_bundle_switch(scripts=action.scripts)
            check_mm_host_action_is_allowed(action=action, definition_type=definition_type)
            check_action_hc_acl_rules(hostcomponentmap=action.hostcomponentmap, definitions=definitions)
            check_jinja_templates_are_correct(action=action, bundle_root=bundle_root)


def check_upgrades(upgrades: list[UpgradeDefinition], definitions: DefinitionsMap) -> None:
    for upgrade in upgrades:
        if not upgrade.action:
            continue

        with localize_error(f"Upgrade {upgrade.name}"):
            check_action_hc_acl_rules(hostcomponentmap=upgrade.action.hostcomponentmap, definitions=definitions)
            check_bundle_switch_amount_for_upgrade_action(upgrade=upgrade)


def check_jinja_templates_are_correct(action: ActionDefinition, bundle_root: Path) -> None:
    if action.config_jinja:
        check_file_is_correct_template(bundle_root / action.config_jinja)

    if action.scripts_jinja:
        check_file_is_correct_template(bundle_root / action.scripts_jinja)


# Atomic checks


def check_no_bundle_switch(scripts: Iterable[JobSpec]) -> None:
    for script in scripts:
        if script.script_type == ScriptType.INTERNAL and script.script == "bundle_switch":
            message = f"bundle_switch is disallowed for {script.name} script"
            raise BundleValidationError(message)


def check_mm_host_action_is_allowed(action: ActionDefinition, definition_type: str) -> None:
    if action.name not in (ADCM_HOST_TURN_OFF_MM_ACTION_NAME, ADCM_HOST_TURN_ON_MM_ACTION_NAME):
        return

    if definition_type != "cluster":
        message = f'Action named "{action.name}" should be defined in cluster context only'
        raise BundleValidationError(message)

    if not action.is_host_action:
        message = f'Action named "{action.name}" should be "host action"'
        raise BundleValidationError(message)


def check_action_hc_acl_rules(hostcomponentmap: list, definitions: Collection[BundleDefinitionKey]) -> None:
    for hc_entry in hostcomponentmap:
        hc_entry_key = dependency_entry_to_key(hc_entry)
        if hc_entry_key not in definitions:
            _, service_name, component_name = hc_entry_key
            message = f'Unknown component "{component_name}" of service "{service_name}"'
            raise BundleValidationError(message)


def check_file_is_correct_template(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
        Template(source=content)
    except (FileNotFoundError, TemplateError) as e:
        message = f"Incorrect template for jinja_* template at {path}: {e}"
        raise BundleValidationError(message) from e


def check_bundle_switch_amount_for_upgrade_action(upgrade: UpgradeDefinition) -> None:
    if not upgrade.action:
        return

    scripts = upgrade.action.scripts

    scripts_with_bundle_switch = tuple(
        script for script in scripts if script.script_type == "internal" and script.script == "bundle_switch"
    )

    amount_of_bundle_switches = len(scripts_with_bundle_switch)

    if amount_of_bundle_switches == 0:
        message = f'Scripts block must contain exact one block with script "bundle_switch" in upgrade "{upgrade.name}"'
        raise BundleValidationError(message)

    if amount_of_bundle_switches > 1:
        message = f'Script with script_type "internal" must be unique in upgrade "{upgrade.name}"'
        raise BundleValidationError(message)


def check_exported_values_exists_in_config(exports: Iterable[str], config: ConfigDefinition | None) -> None:
    for value in exports or ():
        key = (value,)
        if not config or key not in config.parameters or {}:
            message = f"Group specified for export is missing in configuration: {value}"
            raise BundleValidationError(message)


def check_import_defaults_exist_in_config(imports: Iterable[ImportDefinition], config: ConfigDefinition | None) -> None:
    group_names_in_config = {}
    if config:
        group_names_in_config = {entry.name for entry in config.parameters.values() if entry.type == "group"}

    for entry in imports:
        for default_name in entry.default or ():
            if default_name not in group_names_in_config:
                message = (
                    f"Group specified as default for import {entry.name} "
                    f"is missing in configuration: {default_name}"
                )
                raise BundleValidationError(message)
