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

"""
Added as part of ADCM-6355.

This module should be moved to `core.config` or something like that
when bundle rework feature will come to a conclusion.
"""


from functools import partial
from operator import methodcaller
from typing import Any, Callable, TypeAlias

from core.bundle_alt._pattern import Pattern
from core.bundle_alt._yspec import FormatError, SchemaError, process_rule
from core.bundle_alt.types import ConfigParamPlainSpec, ParameterKey
from core.errors import ConfigValueError, localize_error

STACK_COMPLEX_FIELD_TYPES = frozenset(("json", "structure", "list", "map", "secretmap"))
ANSIBLE_VAULT_HEADER = "$ANSIBLE_VAULT;1.1;AES256"

# unite with core.config.types.ParameterKey when the time comes
_ParamType: TypeAlias = str


def key_to_str(key: ParameterKey) -> str:
    if len(key) == 1:
        return f"{key[0]}/"

    return "/".join(key)


def is_encrypted(value: str | None) -> bool:
    return (value or "").startswith(ANSIBLE_VAULT_HEADER)


# irritating text put to const to avoid unintended "fixing"
_SHOULD_NOT_BE_EMPTY = "should be not empty"

# sentinel for unset values in error
_UNSET = object()


class _ValueCheckFailedError(Exception):
    def __init__(
        self, reason: str, *, value=_UNSET, parent: Exception | None = None, pre_key_message: str = ""
    ) -> None:
        super().__init__()

        self.reason = reason

        self.should_add_value = False
        self.value = None
        if value is not _UNSET:
            self.should_add_value = True
            self.value = value

        self.parent = parent
        self.pre_key_message = pre_key_message


class _ValueViolatesPatternError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__()

        self.message = message


def check_default_values(
    parameters: dict[ParameterKey, ConfigParamPlainSpec],
    values: dict[ParameterKey, Any],
    attributes: dict[ParameterKey, dict],
):
    extra_checks = {
        "file": (_check_file_path_length,),
        "secretfile": (_check_file_path_length,),
    }
    value_checks = _generate_value_checks_map(extra=extra_checks)

    # object_ must be passed positionaly
    error_converter = partial(_build_config_value_error, prefix="default value")

    _check_config_values(parameters, values, attributes, convert_err=error_converter, value_checks=value_checks)


def check_values(
    parameters: dict[ParameterKey, ConfigParamPlainSpec],
    values: dict[ParameterKey, Any],
    attributes: dict[ParameterKey, dict],
):
    extra_checks = {"variant": (_check_variant_for_non_default,)}
    value_checks = _generate_value_checks_map(extra=extra_checks)

    error_converter = _build_config_value_error

    _check_config_values(parameters, values, attributes, convert_err=error_converter, value_checks=value_checks)


def _check_config_values(
    parameters: dict[ParameterKey, ConfigParamPlainSpec],
    values: dict[ParameterKey, Any],
    attributes: dict[ParameterKey, dict],
    *,
    convert_err: Callable[[ParameterKey, _ValueCheckFailedError], ConfigValueError],
    value_checks: dict[_ParamType, tuple[Callable, ...]],
):
    consider_empty: dict[_ParamType, tuple[Any]] = {
        "map": ({},),
        "secretmap": ({},),
        "list": ([],),
    } | {str_type: ("",) for str_type in ("string", "password", "text", "secrettext")}

    # iterate over values to allow specifying subset of values to check
    # (e.g. changes, defaults in bundle, etc.)
    for key, value in values.items():
        with localize_error(f"Value of parameter {key_to_str(key)}"):
            parameter = parameters[key]
            type_ = parameter.type

            try:
                empty_values = (None, *(consider_empty.get(type_, ())))
                if value in empty_values:
                    # expected to get normalized spec
                    is_required = parameter.required
                    is_in_deactivated_group = _is_part_of_deactivated_group(key, attributes)
                    if is_required and not is_in_deactivated_group:
                        raise _ValueCheckFailedError("is required")

                    continue

                # check unsuitable for type based check,
                # left for backward compatibility
                if type_ not in STACK_COMPLEX_FIELD_TYPES and isinstance(value, (list, dict)):
                    raise _ValueCheckFailedError("should be flat")

                checks_for_type = value_checks.get(type_, ())
                for check in checks_for_type:
                    check(value, parameter)

            except _ValueCheckFailedError as err:
                error = convert_err(key, err)
                raise error from err.parent

            except _ValueViolatesPatternError as err:
                key_repr = key_to_str(key)
                message = err.message.format(key=key_repr)
                raise ConfigValueError(message) from None


def _generate_value_checks_map(extra: dict) -> dict[_ParamType, tuple[Callable, ...]]:
    should_be_str = _type_is(str, name="string")

    map_checks = (_type_is(dict, name="map"), _children_are_str(iter_func=methodcaller("items")))
    file_checks = (should_be_str, _check_str_is_not_empty)
    patterned_str_checks = (should_be_str, _check_pattern_is_correct)

    value_checks = {
        "boolean": (_type_is(bool, name="boolean"),),
        "integer": (_type_is(int, name="integer"), _check_min_max),
        "float": (_type_is(int, float, name="float"), _check_min_max),
        "list": (
            _type_is(list, name="array"),
            _children_are_str(iter_func=enumerate),
        ),
        "map": map_checks,
        "secretmap": map_checks,
        "file": file_checks,
        "secretfile": file_checks,
        "string": patterned_str_checks,
        "password": patterned_str_checks,
        "text": patterned_str_checks,
        "secrettext": patterned_str_checks,
        "structure": (_check_structure,),
        "option": (_check_option,),
        "variant": (_check_variant,),
    }

    for key, checks in (extra or {}).items():
        if key in value_checks:
            value_checks[key] = (*value_checks[key], *checks)
        else:
            value_checks[key] = checks

    return value_checks


def _is_part_of_deactivated_group(key: ParameterKey, attributes: dict[ParameterKey, dict]) -> bool:
    *group, _ = key
    not_in_deactivated_group = attributes.get(tuple(group), {}).get("active", True)
    return not not_in_deactivated_group


def _build_config_value_error(key: ParameterKey, details: _ValueCheckFailedError, prefix="value") -> ConfigValueError:
    prefix_part = prefix.capitalize()

    value_part = ""
    if details.should_add_value:
        value_part = f'("{details.value}")'

    key_part = f"of config key {key_to_str(key)}"

    message = " ".join(filter(bool, (prefix_part, value_part, details.pre_key_message, key_part, details.reason)))

    return ConfigValueError(message)


# Type-specifics checks


def _type_is(*types: type, name: str) -> Callable:
    def check_type(value: Any, parameter: ConfigParamPlainSpec):  # noqa: ARG001
        if not isinstance(value, types):
            raise _ValueCheckFailedError(f"should be an {name}")

    return check_type


def _children_are_str(iter_func: Callable) -> Callable:
    def check_all_children_are_str(value: list, parameter: ConfigParamPlainSpec):  # noqa: ARG001
        for i, item in iter_func(value):
            if not isinstance(item, str):
                raise _ValueCheckFailedError("should be string", pre_key_message=f'of element "{i}" of config key')

    return check_all_children_are_str


def _check_str_is_not_empty(value: str, parameter: ConfigParamPlainSpec):  # noqa: ARG001
    if value == "":
        raise _ValueCheckFailedError(_SHOULD_NOT_BE_EMPTY)


def _check_min_max(value: int | float, parameter: ConfigParamPlainSpec):
    limits = parameter.limits
    if "min" in limits and value < limits["min"]:
        msg = f'should be more than {limits["min"]}'
        raise _ValueCheckFailedError(msg, value=value)

    if "max" in limits and value > limits["max"]:
        msg = f'should be less than {limits["max"]}'
        raise _ValueCheckFailedError(msg, value=value)


def _check_option(value: Any, parameter: ConfigParamPlainSpec):
    option = parameter.limits["option"]

    if value not in option.values():
        msg = f'not in option list: "{option.values()}"'
        raise _ValueCheckFailedError(msg, value=value)


def _check_variant(value: Any, parameter: ConfigParamPlainSpec):
    source = parameter.limits["source"]
    if not source["strict"]:
        return

    if source["type"] == "inline" and value not in source["value"]:
        msg = f'not in variant list: "{source["value"]}"'
        raise _ValueCheckFailedError(msg, value=value)


def _check_variant_for_non_default(value: Any, parameter: ConfigParamPlainSpec):
    source = parameter.limits["source"]
    if not source["strict"]:
        return

    # handle this case as extra check for regular config check / default check
    if source["type"] in ("config", "builtin") and value not in source["value"]:
        msg = f'not in variant list: "{source["value"]}"'
        raise _ValueCheckFailedError(msg, value=value)


def _check_structure(value: Any, parameter: ConfigParamPlainSpec):
    schema = parameter.limits["yspec"]
    try:
        process_rule(data=value, rules=schema, name="root")
    except FormatError as e:
        raise _ValueCheckFailedError(f"yspec error: {str(e)} at block {e.data}", parent=e) from e
    except SchemaError as e:
        raise _ValueCheckFailedError(f"yspec error: {str(e)}") from e


def _check_pattern_is_correct(value: str, parameter: ConfigParamPlainSpec):
    if is_encrypted(value):
        return

    pattern_str = parameter.limits.get("pattern")
    if not pattern_str:
        return

    pattern = Pattern(pattern_str)
    if not pattern.matches(value):
        message = f"The value of {{key}} config parameter does not match pattern: {pattern_str}"
        # todo here's altering code for "CONFIG_VALUE_ERROR" was happening `http_code=HTTP_409_CONFLICT`
        raise _ValueViolatesPatternError(message)


def _check_file_path_length(value: str, parameter: ConfigParamPlainSpec):  # noqa: ARG001
    if len(value) > 2048:
        raise _ValueCheckFailedError("is too long")
