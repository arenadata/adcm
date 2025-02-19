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

from graphlib import CycleError, TopologicalSorter
from jinja2 import Template, TemplateError

from core.bundle_alt._config import check_default_values
from core.bundle_alt.predicates import has_requires, is_component, is_component_key, is_service
from core.bundle_alt.representation import dependency_entry_to_key, find_parent, make_ref
from core.bundle_alt.types import ActionDefinition, BundleDefinitionKey, Definition, DefinitionsMap, UpgradeDefinition
from core.errors import BundleParsingError


def check_definitions_are_valid(definitions: DefinitionsMap, bundle_root: Path) -> None:
    # special, require too much context to include it in main loop
    check_requires(definitions)

    for key, definition in definitions.items():
        check_import_defaults_exist_in_config(definition)
        check_exported_values_exists_in_config(definition)
        check_upgrades(definition, definitions)

        check_config(definition)
        check_actions(definition, definitions, bundle_root)

        # unify check arguments and make it a map for each type?
        if is_component_key(key):
            check_bound_to(key, definition, definitions)
            check_component_constraint_length(definition, find_parent(key, definitions))


def check_requires(definitions: DefinitionsMap) -> None:
    requires_tree = TopologicalSorter()

    definitions_with_requires = filter(
        lambda kv: (is_service(kv[1]) or is_component(kv[1])) and has_requires(kv[1]), definitions.items()
    )

    for key, definition in definitions_with_requires:
        for requires in definition.requires:
            required_entry_key = dependency_entry_to_key(requires)
            if required_entry_key == key:
                parent = find_parent(key=key, definitions=definitions)
                message = f'{key[0].capitalize()} can not require themself "{definition.name}" of {make_ref(parent)}'
                raise BundleParsingError(code="REQUIRES_ERROR", msg=message)

            if required_entry_key not in definitions:
                if is_component_key(required_entry_key):
                    _, service_name, component_name = required_entry_key
                    message = f'No required component "{component_name}" of service "{service_name}"'
                else:
                    _, service_name = required_entry_key
                    message = f'No required service "{service_name}"'

                raise BundleParsingError(code="REQUIRES_ERROR", msg=message)

            if is_component_key(required_entry_key):
                parent_key = ("service", required_entry_key[1])
                requires_tree.add(key, parent_key, required_entry_key)

    try:
        requires_tree.prepare()
    except CycleError as err:
        raise BundleParsingError(code="REQUIRES_ERROR", msg=f"requires should not be cyclic: {err.args[1]}") from err


def check_bound_to(key: BundleDefinitionKey, definition: Definition, definitions: DefinitionsMap) -> None:
    bound_entry_key = dependency_entry_to_key(definition.bound_to)
    if bound_entry_key == key:
        parent = find_parent(key=key, definitions=definitions)
        message = 'Component can not require themself in "bound_to" of ' f'component "{key[-1]}" of {make_ref(parent)}'
        raise BundleParsingError(code="COMPONENT_CONSTRAINT_ERROR", msg=message)


def check_config(definition: Definition) -> None:
    check_default_values(
        parameters=definition.config.parameters,
        values=definition.config.default_values,
        attributes=definition.config.default_attrs,
        object_=definition,
    )


def check_actions(definition: Definition, definitions: DefinitionsMap, bundle_root: Path) -> None:
    for action in definition.actions:
        check_action_hc_acl_rules(action.hostcomponentmap, definition, definitions)
        check_jinja_templates_are_correct(action, bundle_root)


def check_upgrades(definition: Definition, definitions: DefinitionsMap) -> None:
    for upgrade in definition.upgrades:
        check_action_hc_acl_rules(upgrade.hostcomponentmap, definition, definitions)
        check_bundle_switch_amount_for_upgrade_action(definition, upgrade)


def check_jinja_templates_are_correct(action: ActionDefinition, bundle_root: Path) -> None:
    if action.jinja_config:
        check_file_is_correct_template(bundle_root / action.jinja_config)

    if action.jinja_scripts:
        check_file_is_correct_template(bundle_root / action.jinja_scripts)


# Atomic checks


def check_action_hc_acl_rules(hostcomponentmap: list, definition: Definition, definitions: DefinitionsMap) -> None:
    for hc_entry in hostcomponentmap:
        hc_entry_key = dependency_entry_to_key(hc_entry)
        if hc_entry_key not in definitions:
            _, service_name, component_name = hc_entry_key
            message = f'Unknown component "{component_name}" of service "{service_name}" {make_ref(definition)}'
            raise BundleParsingError(code="INVALID_ACTION_DEFINITION", msg=message)


def check_file_is_correct_template(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
        Template(source=content)
    except (FileNotFoundError, TemplateError) as e:
        raise BundleParsingError(code="INVALID_OBJECT_DEFINITION", msg=str(e)) from e


def check_bundle_switch_amount_for_upgrade_action(definition: Definition, upgrade: UpgradeDefinition) -> None:
    scripts = upgrade.scripts

    scripts_with_bundle_switch = tuple(
        script for script in scripts if script.script_type == "internal" and script.script == "bundle_switch"
    )

    amount_of_bundle_switches = len(scripts_with_bundle_switch)

    if amount_of_bundle_switches == 0:
        raise BundleParsingError(
            code="INVALID_UPGRADE_DEFINITION",
            msg=f"Scripts block in upgrade {upgrade.name} of {make_ref(definition)} "
            'must contain exact one block with script "bundle_switch"',
        )

    if amount_of_bundle_switches > 1:
        raise BundleParsingError(
            code="INVALID_UPGRADE_DEFINITION",
            msg='Script with script_type "internal" must be unique '
            f"in upgrade {upgrade.name} of {make_ref(definition)}",
        )


def check_component_constraint_length(definition: Definition, service_def: Definition) -> None:
    if definition.constraint is None:
        return

    constraint_len = len(definition.constraint)

    if constraint_len > 2:
        raise BundleParsingError(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{definition.name}" in {make_ref(service_def)} '
            "should have only 1 or 2 elements",
        )
    if constraint_len == 0:
        raise BundleParsingError(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{definition.name}" in {make_ref(service_def)} should not be empty',
        )


def check_exported_values_exists_in_config(definition: Definition) -> None:
    for value in definition.export or ():
        key = f"/{value}"
        if key not in definition.config.parameters:
            raise BundleParsingError(
                code="INVALID_OBJECT_DEFINITION", msg=f'{make_ref(definition)} does not has "{value}" config group'
            )


def check_import_defaults_exist_in_config(definition: Definition) -> None:
    group_names_in_config = {entry.name for entry in definition.config.parameters.values() if entry.type == "group"}
    for entry in definition.import_ or ():
        for default_name in entry.get("default", ()):
            if default_name not in group_names_in_config:
                raise BundleParsingError(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'No import default group "{default_name}" in config ({make_ref(definition)})',
                )
