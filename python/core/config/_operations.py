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
from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass
from functools import partial, reduce
from itertools import chain, filterfalse
from pathlib import Path
from typing import Any, Final, Literal, TypeAlias, TypeVar

from core.config import _yspec, spec
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
from core.config._files import construct_parameter_file_full_name
from core.config._helpers import recursive_defaultdict
from core.config._names import (
    full_name_to_file_name,
    full_name_to_level_names,
    full_name_without_root_prefix,
    is_part_of_group,
    join_level_name_with_group_name,
    remove_group_from_name,
)
from core.config._predicates import is_non_empty_string, is_none, is_not_none, is_str
from core.config._types import (
    Attributes,
    Change,
    ChangeRequest,
    ChangeType,
    ConfigParameterValue,
    Configuration,
    ConfigValues,
    Defaults,
    FlatConfiguration,
    ParameterFullName,
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

# Constants

_FORBIDDEN_YSPEC_RULES: Final = frozenset({"one_of", "dict_key_selection", "set", "none", "any"})

# Types


@dataclass(slots=True)
class ValidationResult:
    config: Configuration
    changes: list[Change]

    @property
    def has_changed(self) -> bool:
        return bool(self.changes)


@dataclass(slots=True)
class MissingDefaults:
    value: ConfigParameterValue = None
    activation: bool = False
    selection: str | None = None


_MISSING_DEFAULTS = MissingDefaults()


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


def prepare_config_from_defaults(
    defaults: Defaults,
    specification: spec.FullSpec,
    *,
    missing_defaults: MissingDefaults = _MISSING_DEFAULTS,
) -> Configuration:
    attributes = {
        group_name: Attributes(is_active=defaults.activation.get(group_name, missing_defaults.activation))
        for group_name, param in specification.groups.items()
        if param.activation
    }

    flat_values = {name: defaults.values.get(name, missing_defaults.value) for name in specification.parameters}

    # in order to keep algorithm working, ensure groups are patched from "deepest" to closest to root
    # see ADCM-7418 for problematic case
    selections_ordered_by_level = sorted(
        (name for name, group in specification.groups.items() if group.selection),
        key=lambda name: len(full_name_to_level_names(name)),
        reverse=True,
    )

    for group_name in selections_ordered_by_level:
        is_in_selection_group = partial(is_part_of_group, group=group_name)
        selection_group_children = set(filter(is_in_selection_group, chain(flat_values, attributes)))

        default_selection = defaults.selection.get(group_name, missing_defaults.selection)

        if default_selection:
            default_group_name = join_level_name_with_group_name(name=default_selection, group=group_name)
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


def validate_structure_parameters_schema(
    specification: spec.FullSpec, yspec_schema: dict
) -> Success[None] | Fail[Violations]:
    for name, parameter in specification.parameters.items():
        if parameter.type == spec.p.ParameterType.STRUCTURE:
            param_schema = parameter.yspec
            try:
                _yspec.process_rule(data=param_schema, rules=yspec_schema, name="root")
            except _yspec.FormatError as error:
                message = f"yspec schema is incorrect: {error}"
                violation = Violation(parameter=name, reason=message, check="value")
                return Fail([violation])

            success, error = _yspec.check_rule(rules=param_schema)
            if not success:
                message = f"yspec schema is incorrect: {error}"
                violation = Violation(parameter=name, reason=message, check="value")
                return Fail([violation])

            for value in param_schema.values():
                if value["match"] in _FORBIDDEN_YSPEC_RULES:
                    message = f"yspec schema is incorrect: '{value['match']}' rule is not supported"
                    violation = Violation(parameter=name, reason=message, check="value")
                    return Fail([violation])

    return Success(None)


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

    present_names = set(nested_to_flat(configuration=target, specification=specification).values)
    desynced_names = {
        name for name, attrs in source.attributes.items() if attrs.synchronization and not attrs.is_synced
    }

    for name in chain(present_names, target.attributes):
        attrs = target.attributes.setdefault(name, Attributes(is_synced=True))
        attrs.is_synced = name not in desynced_names
        if not attrs.is_synced:
            if attrs.activation:
                # is activatable group, need to sync it's `is_active` value
                attrs.is_active = source.attributes[name].is_active
            else:
                # is regular value, need to sync value itself
                value = get_by_full_name(name, values=source.values)
                set_by_full_name(new_value=value, name=name, values=target.values)

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


def create_symlinks_for_files(
    specification: spec.FullSpec, original_prefix: str, duplicate_prefix: str, files_dir: Path
) -> None:
    for parameter in specification.parameters.values():
        match parameter:
            case spec.p.StringParameter(identifier=name, as_file=True):
                file_identifier = full_name_to_file_name(full=name.full)
                original_filename = construct_parameter_file_full_name(
                    owner_prefix=original_prefix, file_identifier=file_identifier
                )
                duplicate_filename = construct_parameter_file_full_name(
                    owner_prefix=duplicate_prefix, file_identifier=file_identifier
                )

                Path(files_dir / duplicate_filename).symlink_to(files_dir / original_filename)


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
            case ChangeType.VALUE:
                change_registered = _apply_value_change_registering_violation(
                    key=change.parameter, value=change.value, target=target, violations=violations
                )

            case ChangeType.SELECTION:
                change_registered = _apply_selection_group_change_registering_violation(
                    key=change.parameter, value=change.value, target=target, defaults=defaults, violations=violations
                )

            case ChangeType.ACTIVATION:
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
    include_synchronization: bool,
) -> Success[Configuration]:
    previous_values = nested_to_flat(configuration=configuration, specification=specification).values
    previous_default_values = nested_to_flat(
        configuration=prepare_config_from_defaults(defaults=defaults, specification=specification),
        specification=specification,
    ).values

    chosen_options = _resolve_chosen_options(
        new_specification=new_specification,
        new_defaults=new_defaults,
        previous_values=previous_values,
        previous_default_values=previous_default_values,
    )

    values = _pick_values_for_new_specification(
        new_specification=new_specification,
        defaults=defaults,
        new_defaults=new_defaults,
        previous_values=previous_values,
        chosen_options=chosen_options,
    )

    attributes = _build_attributes_for_new_specification(
        new_specification=new_specification,
        new_defaults=new_defaults,
        previous_attributes=configuration.attributes,
        chosen_options=chosen_options,
    )

    for name, chosen in chosen_options.items():
        if chosen is None:
            # `None` is a possible value of selection group, same as in `prepare_config_from_defaults`
            values[name] = None

    if include_synchronization:
        _set_synchronization(
            attributes=attributes, present_parameters=set(values), previous_attributes=configuration.attributes
        )

    return Success(Configuration(values=flat_to_nested(values), attributes=attributes))


def changes_to_revision_diff(changes: list[Change]) -> dict[Literal["diff", "attr_diff"], dict]:
    diff = recursive_defaultdict()
    attr_diff = defaultdict(dict)

    for change in changes:
        match change.type:
            case ChangeType.VALUE:
                levels = full_name_to_level_names(change.parameter)
                node = reduce(dict.__getitem__, levels, diff)
                node["value"] = [change.old, change.new]

            case ChangeType.ACTIVATION | ChangeType.SELECTION:
                attr_name = "active" if change.type == ChangeType.ACTIVATION else "selection"
                key = full_name_without_root_prefix(change.parameter)
                attr_diff[key][attr_name] = {"value": [change.old, change.new]}

    return {"diff": diff, "attr_diff": attr_diff}


# Utilities


def _resolve_chosen_options(
    new_specification: spec.FullSpec,
    new_defaults: Defaults,
    previous_values: ConfigValues,
    previous_default_values: ConfigValues,
) -> dict[ParameterFullName, str | None]:
    """
    Detect option of each selection group of new specification.

    Selection group is "not changed" when its whole subtree in previous configuration
    is the same as in previous default configuration: neither the option nor values in it were touched.
    Such group takes new default option, changed one keeps the option chosen by user.
    """
    # outer groups should be resolved first, because they define which nested ones are present at all
    selection_groups = sorted(
        (name for name, group in new_specification.groups.items() if group.selection),
        key=lambda name: len(full_name_to_level_names(name)),
    )

    chosen_options = {}

    for name in selection_groups:
        if not _is_present_in_chosen_options(name=name, chosen_options=chosen_options):
            continue

        is_changed = _extract_subtree(values=previous_values, group=name) != _extract_subtree(
            values=previous_default_values, group=name
        )
        if not is_changed:
            chosen_options[name] = new_defaults.selection.get(name)
            continue

        previously_chosen = _detect_chosen_option(values=previous_values, group=name)
        if previously_chosen is None:
            # nothing was chosen by user and that is their choice too
            chosen_options[name] = None
            continue

        if join_level_name_with_group_name(name=previously_chosen, group=name) in new_specification.groups:
            chosen_options[name] = previously_chosen
        else:
            # option that is gone from new specification can't be kept, so new default is used instead
            chosen_options[name] = new_defaults.selection.get(name)

    return chosen_options


def _pick_values_for_new_specification(
    new_specification: spec.FullSpec,
    defaults: Defaults,
    new_defaults: Defaults,
    previous_values: ConfigValues,
    chosen_options: dict[ParameterFullName, str | None],
) -> dict[ParameterFullName, ConfigParameterValue]:
    """
    Pick value for each parameter that is present in new specification:
    the one set by user is kept, untouched one takes new default.
    """
    values = {}
    secret_parameters = spec.get_secret_parameters_names(new_specification)

    for name in new_specification.parameters:
        if not _is_present_in_chosen_options(name=name, chosen_options=chosen_options):
            continue

        previous_default = defaults.values.get(name)
        has_previous_value = name in previous_values

        if name in secret_parameters and has_previous_value:
            # secrets are never migrated to new defaults, see ADCM-7444
            values[name] = previous_values[name]
        elif has_previous_value and previous_values[name] != previous_default:
            values[name] = previous_values[name]
        elif name in new_defaults.values and new_defaults.values[name] is None and previous_default is not None:
            # if default became `None`, old default should be kept
            values[name] = previous_default
        else:
            values[name] = new_defaults.values.get(name)

    return values


def _build_attributes_for_new_specification(
    new_specification: spec.FullSpec,
    new_defaults: Defaults,
    previous_attributes: dict[ParameterFullName, Attributes],
    chosen_options: dict[ParameterFullName, str | None],
) -> dict[ParameterFullName, Attributes]:
    """Activation set by user wins over new default, groups unknown to previous configuration take new default"""
    attributes = {}

    for name, group in new_specification.groups.items():
        if not group.activation:
            continue

        if not _is_present_in_chosen_options(name=name, chosen_options=chosen_options):
            continue

        previous = previous_attributes.get(name)
        is_active = (
            previous.is_active
            if previous is not None and previous.activation
            else new_defaults.activation.get(name, False)
        )

        attributes[name] = Attributes(is_active=is_active)

    return attributes


def _set_synchronization(
    attributes: dict[ParameterFullName, Attributes],
    present_parameters: set[ParameterFullName],
    previous_attributes: dict[ParameterFullName, Attributes],
) -> None:
    for name, group_attributes in attributes.items():
        group_attributes.is_synced = _detect_is_synced_value(name=name, previous_attributes=previous_attributes)

    for name in present_parameters:
        if name in attributes:
            continue

        attributes[name] = Attributes(
            is_synced=_detect_is_synced_value(name=name, previous_attributes=previous_attributes)
        )


def _is_present_in_chosen_options(name: ParameterFullName, chosen_options: dict[ParameterFullName, str | None]) -> bool:
    """Detect whether `name` belongs to options that are chosen in their selection groups"""
    for selection_group, chosen in chosen_options.items():
        if not is_part_of_group(name=name, group=selection_group):
            continue

        if chosen is None:
            return False

        if not is_part_of_group(name=name, group=join_level_name_with_group_name(name=chosen, group=selection_group)):
            return False

    return True


def _extract_subtree(values: ConfigValues, group: ParameterFullName) -> dict:
    return {name: value for name, value in values.items() if is_part_of_group(name=name, group=group)}


def _detect_chosen_option(values: ConfigValues, group: ParameterFullName) -> str | None:
    for name in values:
        if is_part_of_group(name=name, group=group):
            return remove_group_from_name(name=name, group=group).lstrip("/").split("/")[0]

    return None


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


def _extract_group_defaults(
    defaults: Defaults, group: ParameterFullName, *, relative_to: ParameterFullName
) -> ConfigValues:
    """Get defaults of parameters in `group` as nested values with names relative to `relative_to` group"""
    group_defaults = {
        param: default_value
        for param, default_value in defaults.values.items()
        if is_part_of_group(name=param, group=group)
    }

    _keep_only_default_selections(defaults=defaults, group=group, flat_values=group_defaults)

    if not group_defaults:
        return {}

    return flat_to_nested(
        {remove_group_from_name(name=param, group=relative_to): value for param, value in group_defaults.items()}
    )


def _keep_only_default_selections(
    defaults: Defaults, group: ParameterFullName, flat_values: dict[ParameterFullName, ConfigParameterValue]
) -> None:
    """
    Drop values of non-default options of selection groups nested in `group`,
    so extracted defaults are a correct configuration of `group`, not a sum of all its possible options.
    """
    # in order to keep algorithm working, ensure groups are patched from "deepest" to closest to root,
    # see ADCM-7418 for problematic case
    nested_selection_groups = sorted(
        (name for name in defaults.selection if is_part_of_group(name=name, group=group)),
        key=lambda name: len(full_name_to_level_names(name)),
        reverse=True,
    )

    for selection_group in nested_selection_groups:
        default_selection = defaults.selection[selection_group]
        default_group = (
            join_level_name_with_group_name(name=default_selection, group=selection_group)
            if default_selection
            else None
        )

        children = tuple(name for name in flat_values if is_part_of_group(name=name, group=selection_group))
        for name in children:
            if default_group and is_part_of_group(name=name, group=default_group):
                continue

            flat_values.pop(name)

        if not default_group:
            # same "hack" as in `prepare_config_from_defaults`: `None` is a possible value of selection group
            flat_values[selection_group] = None


def _apply_selection_group_change_registering_violation(
    key: ParameterFullName, value: Any, target: Configuration, defaults: Defaults, violations: Violations
) -> _HasChanged:
    new_attributes = {}

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
        group_defaults = _extract_group_defaults(defaults=defaults, group=new_group_key, relative_to=key)
        # only options that are default ones for nested selection groups get into configuration,
        # so attributes should be limited to them the same way values are
        default_selections = {
            name: chosen
            for name, chosen in defaults.selection.items()
            if is_part_of_group(name=name, group=new_group_key)
        }
        new_attributes = {
            name: Attributes(is_active=is_active)
            for name, is_active in defaults.activation.items()
            if is_part_of_group(name=name, group=new_group_key)
            and _is_present_in_chosen_options(name=name, chosen_options=default_selections)
        }
        # else required for case when non-existent group is specified or no default found for some reason,
        # yet we need to consider provided name as group in order to process it as valid entry
        value = group_defaults or {value: {}}

    has_changed = _apply_value_change_registering_violation(key=key, value=value, target=target, violations=violations)
    if has_changed:
        # attributes of previously chosen option have no meaning for the newly chosen one
        _replace_attributes_of_group(group=key, new_attributes=new_attributes, target=target)

    return has_changed


def _replace_attributes_of_group(
    group: ParameterFullName, new_attributes: dict[ParameterFullName, Attributes], target: Configuration
) -> None:
    names_of_group = tuple(name for name in target.attributes if is_part_of_group(name=name, group=group))
    for name in names_of_group:
        target.attributes.pop(name)

    target.attributes.update(new_attributes)


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
