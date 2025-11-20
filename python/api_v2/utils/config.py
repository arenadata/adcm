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
from functools import partial
from typing import Any, Callable
import json

from cm.errors import AdcmEx
from rest_framework.exceptions import ValidationError
import core


def convert_to_attributes(
    attr: dict, allowed_keys: set[str]
) -> dict[core.config.ParameterFullName, core.config.Attributes]:
    attributes = {}

    for name, value in attr.items():
        if not isinstance(value, dict):
            raise ValidationError("adcmMeta values should be dictionaries")

        if not (value.keys() and allowed_keys.issuperset(value.keys())):
            raise AdcmEx(
                code="ATTRIBUTE_ERROR",
                msg=f"Incorrect attributes, at least one of {', '.join(sorted(allowed_keys))}, extra not allowed",
            )

        try:
            attributes[name] = core.config.Attributes(
                is_active=value.get("isActive"), is_synced=value.get("isSynchronized")
            )
        except ValueError as e:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=str(e)) from e

    return attributes


def convert_values(input_values: dict, specification: core.config.spec.FullSpec):
    values = deepcopy(input_values)

    for name, group in specification.groups.items():
        if group.selection:
            core.config.change_by_full_name_skip_missing(name=name, values=values, func=_remove_selection)

    for name, param in specification.parameters.items():
        if param.type == core.config.spec.p.ParameterType.JSON:
            convert = partial(_convert_or_raise_error, name=name)
            core.config.change_by_full_name_skip_missing(name=name, values=values, func=convert)

    return values


def convert_main_config(configuration: dict, specification: core.config.spec.FullSpec) -> core.config.Configuration:
    attributes = convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive"})
    values = convert_values(input_values=configuration["config"], specification=specification)
    return core.config.Configuration(values=values, attributes=attributes)


def convert_group_config(configuration: dict, specification: core.config.spec.FullSpec) -> core.config.Configuration:
    attributes = convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive", "isSynchronized"})
    values = convert_values(input_values=configuration["config"], specification=specification)
    return core.config.Configuration(values=values, attributes=attributes)


def add_selection_for_selectable_groups(
    values: dict, spec: core.config.spec.FullSpec, *, inplace: bool = False
) -> dict:
    return _apply_to_selection_groups(func=_add_selection, values=values, spec=spec, inplace=inplace)


def convert_json_fields_to_strings(values: dict, spec: core.config.spec.FullSpec, *, inplace: bool = False) -> dict:
    return _apply_to_json_fields(func=_to_string, values=values, spec=spec, inplace=inplace)


def parse_json_fields_from_strings(values: dict, spec: core.config.spec.FullSpec, *, inplace: bool = False) -> dict:
    return _apply_to_json_fields(func=_from_string, values=values, spec=spec, inplace=inplace)


def _apply_to_selection_groups(
    func: Callable[[Any], Any], values: dict, spec: core.config.spec.FullSpec, *, inplace: bool = False
):
    selection_groups = tuple(name for name, group in spec.groups.items() if group.selection)
    if not selection_groups:
        return values

    values_copy = deepcopy(values) if not inplace else values

    for selection_group_name in selection_groups:
        core.config.change_by_full_name_skip_missing(name=selection_group_name, func=func, values=values_copy)

    return values_copy


def _apply_to_json_fields(
    func: Callable[[Any], Any], values: dict, spec: core.config.spec.FullSpec, *, inplace: bool = False
) -> dict:
    json_params = tuple(
        name for name, param in spec.parameters.items() if isinstance(param, core.config.spec.p.JSONParameter)
    )
    if not json_params:
        return values

    values_copy = deepcopy(values) if not inplace else values

    for json_param_name in json_params:
        core.config.change_by_full_name_skip_missing(name=json_param_name, func=func, values=values_copy)

    return values_copy


def _convert_or_raise_error(value: Any, name: core.config.ParameterFullName) -> str | None:
    if value is None:
        return None

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError) as e:
        raise AdcmEx(
            code="CONFIG_KEY_ERROR",
            msg=f"Value of '{name}' must be correct json string.",
        ) from e


def _add_selection(x: Any) -> Any:
    if not isinstance(x, dict):
        return x

    # must fail if no key
    key = next(iter(x.keys()))
    return {"_selection": key} | x


def _remove_selection(x: Any) -> Any:
    if not isinstance(x, dict):
        return x

    return {k: v for k, v in x.items() if k != "_selection"}


def _to_string(x: Any) -> Any:
    return x if x is None else json.dumps(x)


def _from_string(x: Any) -> Any:
    return x if isinstance(x, str) else json.loads(x)
