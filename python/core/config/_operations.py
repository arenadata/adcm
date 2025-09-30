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
from typing import Callable, TypeAlias, TypeVar

from core.config import spec
from core.config._config import (
    detect_active_groups,
    detect_changes,
    flat_to_nested,
    get_by_full_name,
    nested_to_flat,
    set_by_full_name,
)
from core.config._names import full_name_to_file_name
from core.config._types import (
    Attributes,
    ConfigFlatValues,
    ConfigOwnerObjectInfo,
    Configuration,
    ConfigValues,
    FlatConfiguration,
    ParameterFullName,
)
from core.config._validate import (
    Validators,
    Violations,
    validate_changes_are_allowed,
    validate_configuration_is_consistent,
    validate_values_are_correct,
)
from core.result import Fail, Success, is_fail

# Types


@dataclass(slots=True)
class ValidationResult:
    config: Configuration
    changes: set[ParameterFullName]

    @property
    def has_changed(self) -> bool:
        return bool(self.changes)


_EncryptFunc: TypeAlias = Callable[[str], str]

_FileParameterIdentifier: TypeAlias = str
_FileTextContent: TypeAlias = str
_FileIdentifier = TypeVar("_FileIdentifier")

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
    owner_info: ConfigOwnerObjectInfo,
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
    """

    validate_consistency_result = validate_configuration_is_consistent(configuration=new, specification=specification)
    if is_fail(validate_consistency_result):
        # no point in gathering other errors if input is inconsistent
        return validate_consistency_result

    changes = detect_changes(previous=previous, new=new, specification=specification)
    active_groups = detect_active_groups(attributes=new.attributes)
    stateful_parameters = spec.detect_stateful_parameters(
        spec=specification, owner_state=owner_info.state, active_groups=active_groups
    )

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

    for name, param in specification.parameters.items():
        match param:
            case spec.p.StringParameter(is_secret=True):
                convert = encrypt
            case spec.p.MapParameter(is_secret=True):
                convert = partial(_encrypt_dict, encrypt=encrypt)
            case _:
                continue

        matched_value = get_by_full_name(name=name, values=out)
        if matched_value is None:
            continue

        value_to_set = convert(matched_value)
        set_by_full_name(new_value=value_to_set, name=name, values=out)

    return Success(out)


# Utilities


def _encrypt_dict(value: dict, encrypt: _EncryptFunc) -> dict:
    return {key: encrypt(val) if isinstance(val, str) else val for key, val in value.items()}
