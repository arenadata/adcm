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
from typing import Callable, Literal, TypeAlias, TypeVar
import logging

from core.config import spec
from core.config._config import (
    build_apply_if,
    change_by_full_name,
    detect_active_groups,
    detect_changes,
    flat_to_nested,
    get_by_full_name,
    nested_to_flat,
    set_by_full_name,
    set_by_full_name_returning_old,
)
from core.config._names import full_name_to_file_name
from core.config._predicates import is_none, is_not_none, is_str
from core.config._types import (
    Attributes,
    ConfigFlatValues,
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
from core.result import Fail, Success, fail_with_call_on_error, is_fail, log_and_ignore

log = logging.getLogger("core.config")

# Types


@dataclass(slots=True)
class ValidationResult:
    config: Configuration
    changes: set[ParameterFullName]

    @property
    def has_changed(self) -> bool:
        return bool(self.changes)


T = TypeVar("T")

_EncryptFunc: TypeAlias = Callable[[str], str]

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
    values = flat_to_nested(flat_values)

    return Configuration(values=values, attributes=attributes)


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
        change_restrictions = spec.detect_stateful_parameters(
            spec=specification, owner_state="", active_groups=active_groups
        )
        deactivated_parameters = change_restrictions.deactivated

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
    stateful_parameters: spec.StatefulParameters,
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
        read_only=stateful_parameters.read_only,
        desync_allowed=specification.attributes.desyncable_parameters,
    )
    if is_fail(validate_changes_result):
        violations.extend(validate_changes_result.value)

    flat_new_config = nested_to_flat(configuration=new, specification=specification)
    validate_values_result = validate_values_are_correct(
        values=flat_new_config.values,
        specification=specification,
        deactivated_parameters=stateful_parameters.deactivated,
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
    main: Configuration,
    host_group: Configuration,
) -> Success[Configuration]:
    target = deepcopy(main)
    source = host_group

    desynced = (name for name, value in source.attributes.items() if value.synchronization and not value.is_synced)

    for param_name in desynced:
        if param_name in target.attributes:
            target.attributes[param_name].is_active = source.attributes[param_name].is_active
        else:
            value = get_by_full_name(param_name, values=source.values)
            set_by_full_name(new_value=value, name=param_name, values=target.values)

    # recover sync values for attributes,
    # because they are missing in main config
    for param_name, attr in source.attributes.items():
        if param_name not in target.attributes:
            target.attributes[param_name] = Attributes(is_synced=attr.is_synced)
        else:
            target.attributes[param_name].is_synced = attr.is_synced

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
                content = get_by_full_name(name=name.full, values=values)
                if content is not None:
                    param_filename = full_name_to_file_name(full=name.full)
                    file_identifier = write(param_filename, content)
                    result.append(file_identifier)

    return Success(result)


def encrypt_secrets(
    values: ConfigValues, specification: spec.FullSpec, *, encrypt: _EncryptFunc, inplace: bool = False
) -> Success[ConfigValues]:
    out: ConfigValues = values if inplace else deepcopy(values)

    encrypt_str = partial(change_by_full_name, func=build_apply_if(func=encrypt, when=is_not_none), values=out)
    encrypt_dict = partial(
        change_by_full_name,
        func=build_apply_if(func=partial(_encrypt_dict, encrypt=encrypt), when=is_not_none),
        values=out,
    )

    for name, param in specification.parameters.items():
        match param:
            case spec.p.StringParameter(is_secret=True):
                encrypt_str(name=name)
            case spec.p.MapParameter(is_secret=True):
                encrypt_dict(name=name)
            case _:
                continue

    return Success(out)


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
                _change_value_ignoring_missing(name=name, func=construct_path_if_not_none, values=target.values)
            # set secret
            case spec.p.StringParameter(is_secret=True):
                _change_value_ignoring_missing(name=name, func=_to_ansible_vault_dict_if_is_str, values=target.values)
            case spec.p.MapParameter(is_secret=True):
                _change_value_ignoring_missing(
                    name=name, func=_nested_dict_values_to_ansible_vault, values=target.values
                )
            # set unsafe
            case spec.p.StringParameter(ansible=spec.p.AnsibleOptions(unsafe=True)):
                _change_value_ignoring_missing(name=name, func=_to_ansible_unsafe_dict_if_is_str, values=target.values)
            # set empty
            case spec.p.ListParameter():
                _change_value_ignoring_missing(name=name, func=to_empty_list_if_is_none, values=target.values)
            case spec.p.MapParameter(is_secret=False):
                _change_value_ignoring_missing(name=name, func=to_empty_dict_if_is_none, values=target.values)

    deactivated_groups = specification.attributes.activatable_groups - active_groups
    for group_name in deactivated_groups:
        set_by_full_name(name=group_name, new_value=None, values=target.values)

    return Success(target)


def apply_changes(
    changes: FlatConfiguration, configuration: Configuration
) -> Success[tuple[Configuration, _HasChanged]] | Fail[Violations]:
    target = deepcopy(configuration)

    has_changed = False
    violations = []

    for key, value in changes.values.items():
        try:
            previous = set_by_full_name_returning_old(name=key, new_value=value, values=target.values)
            if previous != value:
                has_changed = True
        except KeyError:
            violation = Violation(parameter=key, check="structure", reason="no such key in configuration's values")
            violations.append(violation)

    for key, attributes in changes.attributes.items():
        try:
            previous = target.attributes[key]
            target.attributes[key] = attributes
            if previous != attributes:
                has_changed = True
        except KeyError:
            violation = Violation(parameter=key, check="structure", reason="no such key in configuration's attributes")
            violations.append(violation)

    if violations:
        return Fail(violations)

    return Success((target, has_changed))


def adapt_configuration_for_new_specification(
    configuration: Configuration,
    specification: spec.FullSpec,
    defaults: Defaults,
    new_specification: spec.FullSpec,
    new_defaults: Defaults,
) -> Success[Configuration]:
    flat_config = nested_to_flat(configuration=configuration, specification=specification)

    non_default_values_in_config = {k: v for k, v in flat_config.values.items() if v != defaults.get(k)}
    new_values = new_defaults | non_default_values_in_config

    new_default_attributes = {
        k: Attributes(is_active=v.activation.is_active_by_default)
        for k, v in new_specification.groups.items()
        if v.activation
    }
    new_attributes = new_default_attributes | flat_config.attributes

    adapted_config = Configuration(values=flat_to_nested(new_values), attributes=new_attributes)

    return Success(adapted_config)


# Overrides


_log_exception = partial(
    log_and_ignore,
    log_func=partial(log.exception, "failed to change value, probably non-required field is missing: %s"),
)
_change_value_ignoring_missing = fail_with_call_on_error(on_error=_log_exception)(change_by_full_name)
"""
In old versions it was possible to save configuration without required fields.
We could reconstruct config on inventory operations, but for now we just log and ignore errors.
"""

# Utilities


def _encrypt_dict(value: dict, encrypt: _EncryptFunc) -> dict:
    return {key: encrypt(val) if isinstance(val, str) else val for key, val in value.items()}


def _to_ansible_vault_dict_if_is_str(value: T) -> dict[Literal["__ansible_vault"], str] | T:
    if is_str(value):
        return {"__ansible_vault": value}

    return value


def _to_ansible_unsafe_dict_if_is_str(value: T) -> dict[Literal["__ansible_unsafe"], str] | T:
    if is_str(value):
        return {"__ansible_unsafe": value}

    return value


def _nested_dict_values_to_ansible_vault(value: T) -> dict | T:
    if isinstance(value, dict):
        return {key: _to_ansible_vault_dict_if_is_str(val) for key, val in value.items()}

    return value
