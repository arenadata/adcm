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

    for name, param in specification.parameters.items():
        if param.type == core.config.spec.p.ParameterType.JSON:
            json_value = core.config.get_by_full_name(name=name, values=values)
            if json_value is not None:
                try:
                    parsed_value = json.loads(json_value)
                except (json.JSONDecodeError, TypeError) as e:
                    raise AdcmEx(
                        code="CONFIG_KEY_ERROR",
                        msg=f"Value of '{name}' must be correct json string.",
                    ) from e

                core.config.set_by_full_name(new_value=parsed_value, name=name, values=values)

    return values


def convert_main_config(configuration: dict, specification: core.config.spec.FullSpec) -> core.config.Configuration:
    attributes = convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive"})
    values = convert_values(input_values=configuration["config"], specification=specification)
    return core.config.Configuration(values=values, attributes=attributes)


def convert_group_config(configuration: dict, specification: core.config.spec.FullSpec) -> core.config.Configuration:
    attributes = convert_to_attributes(attr=configuration["attr"], allowed_keys={"isActive", "isSynchronized"})
    values = convert_values(input_values=configuration["config"], specification=specification)
    return core.config.Configuration(values=values, attributes=attributes)
