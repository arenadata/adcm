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

from collections import defaultdict
from collections.abc import Callable, Collection, Iterable
from dataclasses import dataclass
from functools import partial
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Final, TypeAlias, cast

from core import action, config
from core.bundle._definitions import (
    ActionDefinition,
    ConfigDefinition,
    DefinitionsMap,
    ImportDefinition,
    UpgradeDefinition,
)
from core.bundle._errors import BundleValidationError
from core.bundle._predicates import has_requires, is_component, is_component_key, is_service
from core.bundle._representation import dependency_entry_to_key, repr_from_key
from core.bundle._types import BundleDefinitionKey
from core.constants import ADCM_HOST_TURN_OFF_MM_ACTION_NAME, ADCM_HOST_TURN_ON_MM_ACTION_NAME
from core.errors import localize_error
from core.result import Fail, Success
from core.templates import RendererEnv, Template, get_renderer
from core.types import ADCMCoreType

FILE_TYPES: Final = {"file", "secretfile"}

ConvertConfigDefinition: TypeAlias = Callable[[ConfigDefinition, Path], tuple[config.spec.FullSpec, config.Defaults]]


@dataclass(slots=True)
class ValidationContext:
    bundle_root: Path
    to_spec_and_defaults: ConvertConfigDefinition


def check_has_valid_definitions_set(keys: Iterable[BundleDefinitionKey]) -> None:
    definition_types = {k[0] for k in keys}

    is_adcm_bundle = definition_types == {ADCMCoreType.ADCM}
    is_provider_bundle = definition_types == {ADCMCoreType.PROVIDER, ADCMCoreType.HOST}

    allowed_for_cluster_bundle = {ADCMCoreType.CLUSTER, ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}
    is_cluster_bundle = (
        allowed_for_cluster_bundle.issuperset(definition_types) and ADCMCoreType.CLUSTER in definition_types
    )

    if not any((is_adcm_bundle, is_provider_bundle, is_cluster_bundle)):
        message = (
            "Definitions in bundle doesn't fit cluster, provider or ADCM format: "
            f"{', '.join(sorted(map(str.lower, definition_types)))}"
        )
        raise BundleValidationError(message)


def check_definitions_are_valid(
    definitions: DefinitionsMap, context: ValidationContext, config_service: config.ConfigService
) -> None:
    # special, require too much context to include it in main loop
    check_requires(definitions)
    check_display_names_are_unique(definitions)

    for key, definition in definitions.items():
        with localize_error(repr_from_key(key)):
            check_import_defaults_exist_in_config(imports=definition.imports, config=definition.config)
            check_exported_values_exists_in_config(exports=definition.exports, config=definition.config)
            check_upgrades(upgrades=definition.upgrades, definitions=definitions, bundle_root=context.bundle_root)

            if definition.config:
                check_config_definition(definition=definition.config, bundle_root=context.bundle_root)
                specification, defaults = context.to_spec_and_defaults(definition.config, context.bundle_root)
                check_config_defaults(specification=specification, defaults=defaults, config_service=config_service)

            check_actions(
                actions=definition.actions,
                definitions=definitions,
                bundle_root=context.bundle_root,
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
                    match required_entry_key:
                        case ("component", service_name, component_name):
                            message = f'No required component "{component_name}" of service "{service_name}"'
                        case ("service", service_name):
                            message = f'No required service "{service_name}"'
                        case _:
                            message = f"No required entity {required_entry_key}"
                    raise BundleValidationError(message)

                match required_entry_key:
                    case ("component", service_name, component_name):
                        parent_key: BundleDefinitionKey = ("service", service_name)
                        requires_tree.add(key, parent_key, required_entry_key)

    try:
        requires_tree.prepare()
    except CycleError as err:
        raise BundleValidationError(f"Requires should not be cyclic: {err.args[1]}") from err


def check_display_names_are_unique(definitions: DefinitionsMap) -> None:
    component_display_names_per_service = defaultdict(set)
    component_keys = filter(is_component_key, definitions.keys())

    for key in component_keys:
        service_key = cast(tuple[str, str], key[0:2])
        service_name = service_key
        component_definition = definitions[key]
        component_display_name = component_definition.display_name
        if component_display_name in component_display_names_per_service[service_name]:
            raise BundleValidationError(
                f"Display name for component within one service must be unique. "
                f"Incorrect definition of component '{component_definition.name}'"
            )

        component_display_names_per_service[service_name].add(component_display_name)


def check_bound_to(bound_to: dict, owner_key: BundleDefinitionKey) -> None:
    bound_entry_key = dependency_entry_to_key(bound_to)
    if bound_entry_key == owner_key:
        message = 'Component can not require themself in "bound_to"'
        raise BundleValidationError(message)


def _is_parameter_present_in_definition(name: str, definition: ConfigDefinition) -> bool:
    return config.names.full_name_to_level_names(name) in definition.parameters


def check_config_definition(definition: ConfigDefinition, bundle_root: Path):
    _check_config_definition(
        definition=definition,
        bundle_root=bundle_root,
        is_parameter_present_in_config=partial(_is_parameter_present_in_definition, definition=definition),
    )


def _is_parameter_present_in_fullspec(name: str, spec: config.spec.FullSpec) -> bool:
    return name in spec.parameters


def check_dynamic_config_definition(
    definition: ConfigDefinition,
    bundle_root: Path,
    spec: config.spec.FullSpec,
):
    _check_config_definition(
        definition=definition,
        bundle_root=bundle_root,
        is_parameter_present_in_config=partial(_is_parameter_present_in_fullspec, spec=spec),
    )


def _check_config_definition(
    definition: ConfigDefinition,
    bundle_root: Path,
    is_parameter_present_in_config: Callable[[str], bool],
) -> None:
    # For now performing these checks in here,
    # because later they will be "invalidated" by conversion to spec and defaults.
    # Maybe later these can be moved to parsing level,
    # because they are "sort-of" contract-dependant.
    for key, parameter in definition.parameters.items():
        full_name = config.names.level_names_to_full_name(key)
        with localize_error(f"Configuration parameter {full_name}"):
            if parameter.type in FILE_TYPES:
                default = definition.default_values.get(key)
                if default:
                    check_file_path_in_config(
                        bundle_root=bundle_root,
                        default=default,
                        name=config.names.level_names_to_full_name(key),
                    )
            elif parameter.type == "variant":
                source = parameter.limits["source"]
                if source["type"] == "config":
                    dependency_name = config.names.ensure_full_name(source["name"])
                    if not is_parameter_present_in_config(dependency_name):
                        message = (
                            f"variant parameter is dependant on {dependency_name}, "
                            "but it is missing in configuration"
                        )
                        raise BundleValidationError(message)

            elif parameter.type == "selection_group" and parameter.group_customization:
                message = (
                    "selection group isn't allowed to be desynchronized from main configuration: "
                    "group_customization must be false"
                )
                raise BundleValidationError(message)


def check_config_defaults(
    specification: config.spec.FullSpec,
    defaults: config.Defaults,
    config_service: config.ConfigService,
):
    violations = config_service.validate_configuration_definition(specification=specification, defaults=defaults)
    if violations:
        violations_list_repr = "; ".join(
            f"- {specification.get_full_display_name(v.parameter)} [{v.check}]: {v.reason}" for v in violations
        )
        raise BundleValidationError(message=f"object's defaults are invalid: {violations_list_repr}")


def check_file_path_in_config(bundle_root: Path, default: str, name: str):
    path = bundle_root / default

    full_path_bytes = str(path).encode("utf-8")
    file_name_bytes = (bundle_root / default).name.encode("utf-8")
    if len(full_path_bytes) > 4096 or len(file_name_bytes) > 255:
        message = f"Default file for {name}: {path} can't exceed 4096 bytes in path and 255 bytes in file name"
        raise BundleValidationError(message)

    try:
        path.resolve(strict=True)
    except (OSError, PermissionError, FileNotFoundError) as e:
        message = f"Error in resolving default file for {name}: {default}: {e}"
        raise BundleValidationError(message) from e

    if not path.is_file():
        message = f"Default file is missing for {name}: {default}"
        raise BundleValidationError(message)


def check_actions(
    actions: list[ActionDefinition], definitions: DefinitionsMap, definition_type: str, bundle_root: Path
) -> None:
    for action_definition in actions:
        with localize_error(f"Action {action_definition.name}"):
            check_no_bundle_switch(scripts=action_definition.scripts)
            check_mm_host_action_is_allowed(action=action_definition, definition_type=definition_type)
            check_action_hc_acl_rules(hostcomponentmap=action_definition.hostcomponentmap, definitions=definitions)
            check_templates_are_correct(action=action_definition, bundle_root=bundle_root)
            check_action_scripts(action=action_definition)


def check_action_scripts(action: ActionDefinition):
    for script in action.scripts:
        if script.script_type == "internal" and script.script == "hc_apply" and "rules" in script.params:
            apply_rules = {(entry["action"], entry["service"], entry["component"]) for entry in script.params["rules"]}
            action_rules = {
                (entry["action"], entry["service"], entry["component"]) for entry in action.hostcomponentmap
            }

            extra_rules = apply_rules - action_rules
            if extra_rules:
                extra_rules_repr = ", ".join(
                    map(
                        str,
                        (
                            {"action": action, "service": service, "component": component}
                            for action, service, component in extra_rules
                        ),
                    )
                )
                message = (
                    "HC rules in hc_apply script should follow action's hc_acl rules, "
                    f"but following are missing in action's definition: {extra_rules_repr}"
                )
                raise BundleValidationError(message)


def check_upgrades(upgrades: list[UpgradeDefinition], definitions: DefinitionsMap, bundle_root: Path) -> None:
    for upgrade in upgrades:
        if not upgrade.action:
            continue

        with localize_error(f"Upgrade {upgrade.name}"):
            check_action_hc_acl_rules(hostcomponentmap=upgrade.action.hostcomponentmap, definitions=definitions)
            if upgrade.action.scripts_template is None:
                check_bundle_switch_amount_for_upgrade_action(upgrade=upgrade)
            else:
                check_templates_are_correct(action=upgrade.action, bundle_root=bundle_root)


def check_templates_are_correct(action: ActionDefinition, bundle_root: Path) -> None:
    for template in filter(None, (action.wizard_template, action.config_template, action.scripts_template)):
        check_file_is_correct_template(template=template, bundle_root=bundle_root)


# Atomic checks


def check_no_bundle_switch(scripts: Iterable[action.JobSpec]) -> None:
    for script in scripts:
        if script.script_type == action.ScriptType.INTERNAL and script.script == "bundle_switch":
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
        try:
            hc_entry_key = dependency_entry_to_key(hc_entry)
        except KeyError as e:
            raise BundleValidationError('"service" field is required in hc_acl for cluster and component') from e

        if hc_entry_key not in definitions:
            match hc_entry_key:
                case ("component", service_name, component_name):
                    message = f'Unknown component "{component_name}" of service "{service_name}"'
                    raise BundleValidationError(message)


def check_file_is_correct_template(bundle_root: Path, template: Template) -> None:
    renderer = get_renderer(template=template, environment=RendererEnv(discovery_root=bundle_root))
    if not renderer.can_be_rendered():
        message = f"Incorrect template for *_template at {template.file.path}"
        raise BundleValidationError(message)


def check_bundle_switch_amount_for_upgrade_action(upgrade: UpgradeDefinition) -> None:
    if not upgrade.action:
        return

    scripts = upgrade.action.scripts

    match validate_bundle_switch_amount(scripts):
        case Fail(value=err_message):
            message = f'{err_message} in upgrade "{upgrade.name}"'
            raise BundleValidationError(message)


# scripts typehint is bad due to this function requirements to be quite universal,
# yet current typesystem handles it differently
def validate_bundle_switch_amount(scripts: list) -> Success[None] | Fail[str]:
    scripts_with_bundle_switch = tuple(
        script for script in scripts if script.script_type == "internal" and script.script == "bundle_switch"
    )

    amount_of_bundle_switches = len(scripts_with_bundle_switch)

    if amount_of_bundle_switches == 0:
        return Fail('Scripts block must contain exact one block with script "bundle_switch"')

    if amount_of_bundle_switches > 1:
        return Fail('Script with script_type "bundle_switch" must be unique')

    return Success(None)


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
