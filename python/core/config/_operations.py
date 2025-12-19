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
from dataclasses import dataclass
from functools import partial
from itertools import chain, filterfalse
from typing import Any, Callable, Generator, Literal, TypeAlias, TypeVar
import logging

from core.config import spec
from core.config._config import (
    MissingKeyError,
    build_apply_if,
    change_by_full_name_skip_missing,
    detect_active_groups,
    detect_changes,
    flat_to_nested,
    get_by_full_name,
    get_by_full_name_or_none,
    nested_to_flat,
    set_by_full_name,
    set_by_full_name_returning_old,
)
from core.config._names import (
    full_name_to_file_name,
    full_name_to_level_names,
    is_part_of_group,
    join_level_name_with_group_name,
    level_names_to_full_name,
    remove_group_from_name,
)
from core.config._predicates import is_non_empty_string, is_none, is_not_none, is_str
from core.config._types import (
    Attributes,
    ChangeRequest,
    ConfigFlatValues,
    Configuration,
    ConfigValues,
    Defaults,
    FlatConfiguration,
    ParameterFullName,
    ParameterLevelName,
)
from core.config._validate import (
    Validators,
    Violation,
    Violations,
    validate_changes_are_allowed,
    validate_configuration_is_consistent,
    validate_values_are_correct,
)
from core.result import Fail, Success, is_fail

log = logging.getLogger("core.config")

# Types


@dataclass(slots=True)
class ValidationResult:
    config: Configuration
    changes: set[ParameterFullName]

    @property
    def has_changed(self) -> bool:
        return bool(self.changes)


ChangesToApply = list[ChangeRequest]

T = TypeVar("T")

_StrToStr: TypeAlias = Callable[[str], str]

_FileParameterIdentifier: TypeAlias = str
"""
"Own" part of filepath based on parameter name itself,
without bounds to config owner / caller environment
"""
_FileTextContent: TypeAlias = str
_FileIdentifier = TypeVar("_FileIdentifier")
_ParameterPathBuilder: TypeAlias = Callable[[_FileParameterIdentifier], str]

_HasChanged: TypeAlias = bool


# Public


def prepare_config_from_defaults(default_values: ConfigFlatValues, specification: spec.FullSpec) -> Configuration:
    attributes = {
        group_name: Attributes(is_active=param.activation.is_active_by_default)
        for group_name, param in specification.groups.items()
        if param.activation
    }

    flat_values = {name: default_values.get(name, None) for name in specification.parameters}

    groups_selections = {name: group.selection for name, group in specification.groups.items() if group.selection}
    # in order to keep algorithm working, ensure groups are patched from "deepest" to closest to root
    # see ADCM-7418 for problematic case
    selections_ordered_by_level = sorted(
        groups_selections.items(), key=lambda kv: len(full_name_to_level_names(kv[0])), reverse=True
    )

    for group_name, selection in selections_ordered_by_level:
        is_in_selection_group = partial(is_part_of_group, group=group_name)
        selection_group_children = set(filter(is_in_selection_group, chain(flat_values, attributes)))

        if selection.use_as_default:
            default_group_name = join_level_name_with_group_name(name=selection.use_as_default, group=group_name)
            is_in_default_group = partial(is_part_of_group, group=default_group_name)
            to_remove = set(filterfalse(is_in_default_group, selection_group_children))
        else:
            to_remove = selection_group_children
            # it's "sort of" hack, because usually group values aren't `None`s in any case,
            # yet for selection group `None` is a possible value instead of `{}`,
            # so this assignment is OK if no other code uses this "hack"
            flat_values[group_name] = None

        for param_name in to_remove:
            # may be absent, since selection_group_children is build from both flat values and attributes
            flat_values.pop(param_name, None)
            attributes.pop(param_name, None)

    values = flat_to_nested(flat_values)

    return Configuration(values=values, attributes=attributes)


def prepare_initial_config_of_host_group(
    configuration: Configuration, specification: spec.FullSpec
) -> Success[Configuration]:
    present_parameter_values = set(
        nested_to_flat(configuration=configuration, specification=specification).values.keys()
    )
    owner_attrs = {
        k: Attributes(is_active=attrs.is_active, is_synced=True) for k, attrs in configuration.attributes.items()
    }
    parameter_attrs = {k: Attributes(is_synced=True) for k in specification.parameters if k in present_parameter_values}

    return Success(Configuration(values=configuration.values, attributes=owner_attrs | parameter_attrs))


def validate_values(
    configuration: FlatConfiguration,
    specification: spec.FullSpec,
    validators: Validators,
    *,
    check_inside_deactivated_groups: bool = True,
) -> Success[FlatConfiguration] | Fail[Violations]:
    """
    Validate given values based on specification.

    If `check_inside_deactivated_groups` is `True`, parameters in deactivated groups are checked
    against required rules, otherwise skipped (other checks will be performed).

    Major use cases for this function are checking defaults (don't provide `None`s in values then)
    and general validation for concern-related cases.
    """

    if check_inside_deactivated_groups:
        deactivated_parameters = set()
    else:
        active_groups = detect_active_groups(attributes=configuration.attributes)
        deactivated_parameters = spec.detect_deactivated_parameters(spec=specification, active_groups=active_groups)

    result = validate_values_are_correct(
        values=configuration.values,
        specification=specification,
        deactivated_parameters=deactivated_parameters,
        validators=validators,
    )

    if is_fail(result):
        return result

    return Success(configuration)


def validate_new_changes_in_main_configuration(
    new: Configuration,
    previous: Configuration,
    specification: spec.FullSpec,
    deactivated_parameters: set[ParameterFullName],
    validators: Validators,
) -> Success[ValidationResult] | Fail[Violations]:
    """
    Validate given configuration, ensuring that:
    - it is consistent with specification
    - parameters have valid and correct values/attributes

    Restrictions:
    - `previous` configuration is expected to be valid and not checked
    - Both `new` and `previous` configurations should be based on same `specification` and belong to the same `owner`
    - Configurations values are plain, no encryption/decryption is performed
      (otherwise should be handled in validators)
    """

    validate_consistency_result = validate_configuration_is_consistent(configuration=new, specification=specification)
    if is_fail(validate_consistency_result):
        # no point in gathering other errors if input is inconsistent
        return validate_consistency_result

    changes = detect_changes(previous=previous, new=new, specification=specification)

    violations: Violations = []

    validate_changes_result = validate_changes_are_allowed(
        changes=changes,
        attributes=new.attributes,
        desync_allowed=specification.attributes.desyncable_parameters,
    )
    if is_fail(validate_changes_result):
        violations.extend(validate_changes_result.value)

    flat_new_config = nested_to_flat(configuration=new, specification=specification)
    validate_values_result = validate_values_are_correct(
        values=flat_new_config.values,
        specification=specification,
        deactivated_parameters=deactivated_parameters,
        validators=validators,
    )
    if is_fail(validate_values_result):
        violations.extend(validate_values_result.value)

    if violations:
        return Fail(violations)

    return Success(ValidationResult(config=new, changes=changes))


def validate_action_configuration(
    configuration: Configuration, specification: spec.FullSpec, validators: Validators
) -> Success[Configuration] | Fail[Violations]:
    """
    Validate given configuration, ensuring that:
    - it is consistent with specification
    - parameters have valid and correct values/attributes

    Restrictions:
    - Configurations values are plain, no encryption/decryption is performed
      (otherwise should be handled in validators)
    """
    validate_consistency_result = validate_configuration_is_consistent(
        configuration=configuration, specification=specification
    )
    if is_fail(validate_consistency_result):
        # no point in gathering other errors if input is inconsistent
        return validate_consistency_result

    active_groups = detect_active_groups(attributes=configuration.attributes)
    deactivated_parameters = spec.detect_deactivated_parameters(spec=specification, active_groups=active_groups)

    flat_new_config = nested_to_flat(configuration=configuration, specification=specification)
    validate_values_result = validate_values_are_correct(
        values=flat_new_config.values,
        specification=specification,
        deactivated_parameters=deactivated_parameters,
        validators=validators,
    )
    if is_fail(validate_values_result):
        return Fail(validate_values_result.value)

    return Success(configuration)


def update_config_of_host_group(
    main: Configuration, host_group: Configuration, specification: spec.FullSpec
) -> Success[Configuration]:
    """
    It is expected that both configurations are based on same schema,
    so in cases like upgrade both should be converted to one format first,
    only then updated with this function
    """
    target = deepcopy(main)
    source = host_group

    desynced = (name for name, value in source.attributes.items() if value.synchronization and not value.is_synced)

    for name in desynced:
        if name in target.attributes:
            target.attributes[name].is_active = source.attributes[name].is_active
            target.attributes[name].is_synced = False
        else:
            value = get_by_full_name(name, values=source.values)
            set_by_full_name(new_value=value, name=name, values=target.values)

    # set "sync" values for those activatable groups that has it unset:
    # at this point only activatable groups are expected in attributes
    for attrs in target.attributes.values():
        if not attrs.synchronization:
            attrs.is_synced = True

    present_parameters = set(nested_to_flat(configuration=target, specification=specification).values)

    # re-build sync values for attributes, because they are missing in main config
    for name in present_parameters:
        is_synced = True

        if (previous_attributes := source.attributes.get(name)) and previous_attributes.synchronization:
            is_synced = previous_attributes.is_synced

        target.attributes[name] = Attributes(is_synced=is_synced)

    return Success(target)


def store_files(
    values: ConfigValues,
    specification: spec.FullSpec,
    *,
    write: Callable[[_FileParameterIdentifier, _FileTextContent], _FileIdentifier],
) -> Success[list[_FileIdentifier]]:
    result = []

    for parameter in specification.parameters.values():
        match parameter:
            case spec.p.StringParameter(identifier=name, as_file=True):
                content = get_by_full_name_or_none(name=name.full, values=values)
                if content is not None:
                    param_filename = full_name_to_file_name(full=name.full)
                    file_identifier = write(param_filename, content)
                    result.append(file_identifier)

    return Success(result)


def encrypt_secrets(
    values: ConfigValues, specification: spec.FullSpec, *, encrypt: _StrToStr, inplace: bool = False
) -> Success[ConfigValues]:
    return _apply_to_secrets(values=values, specification=specification, func=encrypt, inplace=inplace)


def decrypt_secrets(
    values: ConfigValues, specification: spec.FullSpec, *, decrypt: _StrToStr, inplace: bool = False
) -> Success[ConfigValues]:
    return _apply_to_secrets(values=values, specification=specification, func=decrypt, inplace=inplace)


def prepare_config_for_ansible(
    configuration: Configuration,
    specification: spec.FullSpec,
    construct_parameter_path: _ParameterPathBuilder,
    *,
    inplace: bool = False,
) -> Success[Configuration]:
    target = configuration if inplace else deepcopy(configuration)

    active_groups = detect_active_groups(attributes=configuration.attributes)
    deactivated = spec.detect_deactivated_parameters(spec=specification, active_groups=active_groups)

    to_empty_dict_if_is_none = build_apply_if(func=lambda _: {}, when=is_none)
    to_empty_list_if_is_none = build_apply_if(func=lambda _: [], when=is_none)
    add_selection_if_is_not_none = build_apply_if(func=_add_selection, when=is_not_none)

    for name, param in specification.parameters.items():
        if name in deactivated:
            continue

        match param:
            # set filepath
            case spec.p.StringParameter(as_file=True):
                construct_path_if_not_none = build_apply_if(
                    func=lambda _, name_=name: construct_parameter_path(full_name_to_file_name(full=name_)),
                    when=is_not_none,
                )
                change_by_full_name_skip_missing(name=name, func=construct_path_if_not_none, values=target.values)
            # set secret
            case spec.p.StringParameter(is_secret=True):
                change_by_full_name_skip_missing(
                    name=name, func=_to_ansible_vault_dict_if_is_non_empty_str, values=target.values
                )
            case spec.p.MapParameter(is_secret=True):
                change_by_full_name_skip_missing(
                    name=name, func=_nested_dict_values_to_ansible_vault, values=target.values
                )
            # set unsafe
            case spec.p.StringParameter(ansible=spec.p.AnsibleOptions(unsafe=True)):
                change_by_full_name_skip_missing(
                    name=name, func=_to_ansible_unsafe_dict_if_is_str, values=target.values
                )
            # set empty
            case spec.p.ListParameter():
                change_by_full_name_skip_missing(name=name, func=to_empty_list_if_is_none, values=target.values)
            case spec.p.MapParameter(is_secret=False):
                change_by_full_name_skip_missing(name=name, func=to_empty_dict_if_is_none, values=target.values)

    deactivated_groups = specification.attributes.activatable_groups - active_groups
    for name, group in specification.groups.items():
        if group.selection:
            change_by_full_name_skip_missing(name=name, func=add_selection_if_is_not_none, values=target.values)
        elif group.activation and name in deactivated_groups:
            change_by_full_name_skip_missing(name=name, func=_set_none, values=target.values)

    return Success(target)


def apply_changes(
    changes: ChangesToApply, configuration: Configuration, defaults: Defaults
) -> Success[tuple[Configuration, _HasChanged]] | Fail[Violations]:
    target = deepcopy(configuration)

    ordered_changes = sorted(changes, key=lambda change: len(full_name_to_level_names(change.parameter)))

    has_changed = False
    violations = []

    for change in ordered_changes:
        match change.type:
            case "value":
                change_registered = _apply_value_change_registering_violation(
                    key=change.parameter, value=change.value, target=target, violations=violations
                )

            case "selection":
                change_registered = _apply_selection_group_change_registering_violation(
                    key=change.parameter, value=change.value, target=target, defaults=defaults, violations=violations
                )

            case "activation":
                change_registered = _apply_activation_change_registering_violation(
                    key=change.parameter, value=change.value, target=target, violations=violations
                )

        if change_registered:
            has_changed = True

    if violations:
        return Fail(violations)

    return Success((target, has_changed))


def adapt_configuration_for_new_specification(
    configuration: Configuration,
    specification: spec.FullSpec,
    defaults: Defaults,
    new_specification: spec.FullSpec,
    new_defaults: Defaults,
    # now I don't see another approach  to distinct cases of host group / main config
    # without guessing, so made a flag
    include_synchronization: bool,
) -> Success[Configuration] | Fail[Violations]:
    # todo: clarify this function after logic confirmed by tests,
    #       now it's a bit of mess and joggling

    previous_default_config = prepare_config_from_defaults(default_values=defaults, specification=specification)

    groups_with_selection = {name for name, group in new_specification.groups.items() if group.selection}
    parameters_and_groups_with_selection = groups_with_selection | set(new_specification.parameters)

    relevant_changes = []
    for change in _find_changes_from_level(
        values=configuration.values, reference=previous_default_config.values, level=new_specification.hierarchy
    ):
        is_existing_selection_change = change.type == "selection" and change.parameter in groups_with_selection
        is_existing_value_change = change.type == "value" and change.parameter in parameters_and_groups_with_selection

        if is_existing_selection_change or is_existing_value_change:
            relevant_changes.append(change)

    new_configuration = prepare_config_from_defaults(default_values=new_defaults, specification=new_specification)

    apply_result = apply_changes(changes=relevant_changes, configuration=new_configuration, defaults=new_defaults)

    match apply_result:
        case Success((config_with_changed_values, _)):
            new_configuration = config_with_changed_values
        case Fail():
            return apply_result

    present_in_new_config = set(nested_to_flat(configuration=new_configuration, specification=new_specification).values)

    # if default became None, old default should be kept
    new_none_defaults = {
        name for name, value in new_defaults.items() if value is None and defaults.get(name) is not None
    }
    if new_none_defaults:
        changed_parameters = {change.parameter for change in relevant_changes}
        present_and_change_required = (new_none_defaults - changed_parameters) & present_in_new_config
        keep_old_default_changes = [
            ChangeRequest.for_value(name=name, value=defaults[name]) for name in present_and_change_required
        ]
        apply_result = apply_changes(
            changes=keep_old_default_changes, configuration=new_configuration, defaults=new_defaults
        )

        match apply_result:
            case Success((config_with_changed_values, _)):
                new_configuration = config_with_changed_values
            case Fail():
                return apply_result

    for name, old_attributes in configuration.attributes.items():
        if not old_attributes.activation:
            continue

        new_attributes = new_configuration.attributes.get(name)
        if new_attributes and new_attributes.activation:
            new_attributes.is_active = old_attributes.is_active

    if include_synchronization:
        # sync groups
        for name, attrs in new_configuration.attributes.items():
            attrs.is_synced = _detect_is_synced_value(
                name=name,
                previous_attributes=configuration.attributes,
            )

        # sync for parameters
        for name in present_in_new_config:
            new_configuration.attributes[name] = Attributes(
                is_synced=_detect_is_synced_value(name=name, previous_attributes=configuration.attributes)
            )

    return Success(new_configuration)


# Utilities


def _apply_value_change_registering_violation(
    key: ParameterFullName, value: Any, target: Configuration, violations: Violations
) -> _HasChanged:
    try:
        previous = set_by_full_name_returning_old(name=key, new_value=value, values=target.values)
        if previous != value:
            return True

    except MissingKeyError:
        violation = Violation(parameter=key, check="structure", reason="no such key in configuration's values")
        violations.append(violation)

    return False


def _apply_selection_group_change_registering_violation(
    key: ParameterFullName, value: Any, target: Configuration, defaults: Defaults, violations: Violations
) -> _HasChanged:
    if value is not None:
        if not isinstance(value, str):
            message = (
                f"Don't know how to apply selection group change for value that isn't string or None: {type(value)=}"
            )
            raise TypeError(message)

        # detect if changes are required, otherwise skip change
        current_value = get_by_full_name(name=key, values=target.values)
        if not (isinstance(current_value, dict) or current_value is None):
            message = (
                "Don't know how to apply selection group change to value that isn't dict or None, "
                f"got {type(current_value)=}"
            )
            raise TypeError(message)

        if value in (current_value or ()):
            # current choice is one's to set, so no need in changes
            return False

        new_group_key = join_level_name_with_group_name(name=value, group=key)
        group_defaults = {
            remove_group_from_name(name=param, group=key): default_value
            for param, default_value in defaults.items()
            if is_part_of_group(name=param, group=new_group_key)
        }
        # else required for case when non-existent group is specified or no default found for some reason,
        # yet we need to consider provided name as group in order to process it as valid entry
        value = flat_to_nested(group_defaults) if group_defaults else {value: {}}

    return _apply_value_change_registering_violation(key=key, value=value, target=target, violations=violations)


def _apply_activation_change_registering_violation(
    key: ParameterFullName, value: bool, target: Configuration, violations: Violations
):
    try:
        previous = target.attributes[key].is_active
        target.attributes[key].is_active = value
        if previous != value:
            return True
    except KeyError:
        violation = Violation(parameter=key, check="structure", reason="no such key in configuration's attributes")
        violations.append(violation)

    return False


def _find_changes_from_level(
    values: ConfigValues,
    reference: ConfigValues,
    level: spec.SpecHierarchyLevel,
    level_names: tuple[ParameterLevelName, ...] = (),
) -> Generator[ChangeRequest, None, None]:
    match level.rule:
        case spec.HierarchyValidationRule.ALL:
            present_at_level = set(reference.keys())

            present_parameters = present_at_level.difference(level.child_groups.keys()).intersection(values.keys())
            for name in present_parameters:
                new_value = values[name]
                if new_value != reference[name]:
                    chosen_group_name = level_names_to_full_name((*level_names, name))
                    yield ChangeRequest.for_value(name=chosen_group_name, value=new_value)

            present_groups = present_at_level.intersection(level.child_groups).intersection(values.keys())
            for name in present_groups:
                child_level = level.child_groups[name]
                child_values = values[name]
                if not isinstance(child_values, dict):
                    # todo check AT MOST ONE
                    if (
                        child_level.rule != spec.HierarchyValidationRule.ALL
                        and child_values is None
                        and reference[name] is not None
                    ):
                        chosen_group_name = level_names_to_full_name((*level_names, name))
                        yield ChangeRequest.for_group_selection(name=chosen_group_name, value=None)

                    continue

                yield from _find_changes_from_level(
                    values=child_values, reference=reference[name], level=child_level, level_names=(*level_names, name)
                )

        case spec.HierarchyValidationRule.AT_MOST_ONE | spec.HierarchyValidationRule.EXACTLY_ONE:
            if values == reference:
                return

            name = next(iter(values.keys()), None)
            if name not in level.child_groups:
                # either incorrect data came or option is invalid for new hierarchy
                return

            group_name = level_names_to_full_name(level_names)
            # it is based on current apply implementation, you may need a separate type for it later,
            # if you'll need to distinguish cases or add more clarity in what's happening
            yield ChangeRequest.for_value(name=group_name, value=values)


def _detect_is_synced_value(name: ParameterFullName, previous_attributes: dict[ParameterFullName, Attributes]) -> bool:
    # As part of ADCM-7429 it was discussed and decided that we want to keep old behavior
    # that has no implicit conversion of desyncable attribute during upgrade
    #
    # if not is_desyncable:
    #     return True

    if (previous := previous_attributes.get(name)) and previous.is_synced is not None:
        return previous.is_synced

    return True


def _add_selection(value: dict) -> dict:
    # we expect value to have exactly one key here
    chosen_value = next(iter(value.keys()))
    return value | {"_selection": chosen_value}


def _apply_to_secrets(
    values: ConfigValues, specification: spec.FullSpec, *, func: _StrToStr, inplace: bool = False
) -> Success[ConfigValues]:
    out: ConfigValues = values if inplace else deepcopy(values)

    # We use "non empty string" check, because it is possible to put "" as value of string parameter and run action:
    # it should be non-required parameter with "" as default or set to default via API/plugin.
    # See ADCM-7586 for more info.
    apply_to_str = partial(
        change_by_full_name_skip_missing, func=build_apply_if(func=func, when=is_non_empty_string), values=out
    )
    apply_to_dict_values = partial(
        change_by_full_name_skip_missing,
        func=build_apply_if(func=partial(_apply_to_dict_values, func=func), when=is_not_none),
        values=out,
    )

    for name, param in specification.parameters.items():
        match param:
            case spec.p.StringParameter(is_secret=True):
                apply_to_str(name=name)
            case spec.p.MapParameter(is_secret=True):
                apply_to_dict_values(name=name)
            case _:
                continue

    return Success(out)


def _apply_to_dict_values(value: dict, func: _StrToStr) -> dict:
    return {key: func(val) if isinstance(val, str) else val for key, val in value.items()}


def _set_none(_: Any) -> None:
    return None


def _to_ansible_vault_dict_if_is_non_empty_str(value: T) -> dict[Literal["__ansible_vault"], str] | T:
    if is_non_empty_string(value):
        return {"__ansible_vault": value}

    return value


def _to_ansible_unsafe_dict_if_is_str(value: T) -> dict[Literal["__ansible_unsafe"], str] | T:
    if is_str(value):
        return {"__ansible_unsafe": value}

    return value


def _nested_dict_values_to_ansible_vault(value: T) -> dict | T:
    if isinstance(value, dict):
        return {key: _to_ansible_vault_dict_if_is_non_empty_str(val) for key, val in value.items()}

    return value
