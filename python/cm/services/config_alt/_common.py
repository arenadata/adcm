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

from typing import Any, Callable, TypeVar

from cm.services.config_alt.types import (
    ConfigOwnerObjectInfo,
    ParameterFullName,
    ParameterLevelName,
    ReadOnlyRule,
    WritableRule,
    full_name_to_level_names,
)

T = TypeVar("T")

# ENCRYPTION


def encrypt_if_possible(value: T, encryptor: Callable[[str], str]) -> T:
    if isinstance(value, str):
        return encryptor(value)

    if isinstance(value, dict):
        return {k: encrypt_if_possible(value=v, encryptor=encryptor) for k, v in value.items()}

    return value


def decrypt_if_possible(value: T, decryptor: Callable[[str], str | None]) -> T:
    if isinstance(value, str):
        return decryptor(value)

    if isinstance(value, dict):
        return {k: decrypt_if_possible(value=v, decryptor=decryptor) for k, v in value.items()}

    return value


# READ ONLY


def is_editable(rule: WritableRule | ReadOnlyRule, owner: ConfigOwnerObjectInfo) -> bool:
    if isinstance(rule, WritableRule):
        return rule.writable == "any" or owner.state in rule.writable

    return not (rule.read_only == "any" or owner.state in rule.read_only)


# CONFIG MANIPULATIONS


def get_group_with_value(config: dict[str, Any], name: ParameterFullName) -> tuple[dict[str, Any], ParameterLevelName]:
    return _get_group_with_value(config=config, level_names=full_name_to_level_names(name))


def _get_group_with_value(
    config: dict[str, Any], level_names: tuple[ParameterLevelName, ...]
) -> tuple[dict[str, Any], ParameterLevelName]:
    level_name, *rest = level_names
    if not rest:
        return config, level_name

    return _get_group_with_value(config=config[level_name], level_names=rest)


def get_nested_config_value(config: dict[str, Any], name: ParameterFullName) -> Any:
    group, level_name = get_group_with_value(config=config, name=name)
    return group[level_name]


def set_nested_config_value(config: dict[str, Any], name: ParameterFullName, value: T) -> T:
    group, level_name = get_group_with_value(config=config, name=name)
    group[level_name] = value
    return value


def change_nested_config_value(config: dict[str, Any], name: ParameterFullName, func: Callable[[Any], T]) -> T:
    group, level_name = get_group_with_value(config=config, name=name)
    group[level_name] = func(group[level_name])
    return group[level_name]
