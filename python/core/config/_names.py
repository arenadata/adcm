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
Configuration-flavoured names for generic specification key operations.

Everything but the file-name helpers is a re-link to `core.spec.keys`,
kept under the historical `*_name` naming so config's own signatures stay intact.
"""

from collections.abc import Iterable

from core.config._types import PARAMETER_FILE_NAME_SEPARATOR, ParameterFullName, ParameterLevelName
from core.spec.keys import (
    ensure_full_key,
    full_key_to_level_keys,
    full_key_without_root_prefix,
    join_full_key_with_group_key,
    join_level_key_with_group_key,
    level_key_from_full_key,
    level_keys_to_full_key,
    level_keys_to_full_key_safe,
    remove_group_from_key,
)
from core.spec.keys import is_part_of_group as _is_part_of_group


def ensure_full_name(name: str) -> ParameterFullName:
    return ensure_full_key(name)


def full_name_to_level_names(full: ParameterFullName) -> tuple[ParameterLevelName, ...]:
    return full_key_to_level_keys(full)


def full_name_without_root_prefix(full: ParameterFullName) -> str:
    return full_key_without_root_prefix(full)


def level_names_to_full_name(levels: Iterable[ParameterLevelName]) -> ParameterFullName:
    return level_keys_to_full_key(levels)


def level_names_to_full_name_safe(levels: Iterable[ParameterLevelName | None]) -> ParameterFullName:
    return level_keys_to_full_key_safe(levels)


def level_name_from_full_name(full: ParameterFullName) -> ParameterLevelName:
    return level_key_from_full_key(full)


def join_full_name_with_group_name(full: ParameterFullName, group: ParameterLevelName) -> ParameterFullName:
    return join_full_key_with_group_key(full=full, group=group)


def join_level_name_with_group_name(name: ParameterLevelName, group: ParameterFullName) -> ParameterFullName:
    return join_level_key_with_group_key(key=name, group=group)


def remove_group_from_name(name: ParameterFullName, group: ParameterFullName) -> ParameterFullName:
    return remove_group_from_key(key=name, group=group)


def is_part_of_group(name: ParameterFullName, group: ParameterFullName) -> bool:
    return _is_part_of_group(key=name, group=group)


def full_name_to_file_name(full: ParameterFullName) -> str:
    """
    Convert full name of parameter to "own name" of file (indifferent to object)
    """

    levels = full_name_to_level_names(full)
    if len(levels) == 1:
        # backward compatibility
        # first-leveled parameters' names ended with "."
        return f"{levels[0]}{PARAMETER_FILE_NAME_SEPARATOR}"

    return PARAMETER_FILE_NAME_SEPARATOR.join(levels)


def is_parameter_file_name_startswith(file_name: str, name: ParameterLevelName) -> bool:
    return file_name.startswith(f"{name}{PARAMETER_FILE_NAME_SEPARATOR}")
