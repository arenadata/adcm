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

from typing import Iterable

from core.config._types import (
    PARAMETER_FILE_NAME_SEPARATOR,
    PARAMETER_NAME_ROOT_PREFIX,
    PARAMETER_NAME_SEPARATOR,
    ParameterFullName,
    ParameterLevelName,
)


def ensure_full_name(name: str) -> ParameterFullName:
    if not name.startswith(PARAMETER_NAME_ROOT_PREFIX):
        return f"{PARAMETER_NAME_ROOT_PREFIX}{name}"

    return name


def full_name_to_level_names(full: ParameterFullName) -> tuple[ParameterLevelName, ...]:
    return tuple(filter(bool, full.split(PARAMETER_NAME_SEPARATOR)))


def level_names_to_full_name(levels: Iterable[ParameterLevelName]) -> ParameterFullName:
    return ensure_full_name(PARAMETER_NAME_SEPARATOR.join(levels))


def level_names_to_full_name_safe(levels: Iterable[ParameterLevelName | None]) -> ParameterFullName:
    non_empty_strings: Iterable[ParameterLevelName] = (level for level in levels if level)
    return level_names_to_full_name(non_empty_strings)


def join_full_name_with_group_name(full: ParameterFullName, group: ParameterLevelName) -> ParameterFullName:
    return ensure_full_name(f"{group}{full}")


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


def is_part_of_group(parameter: ParameterFullName, group: ParameterFullName) -> bool:
    return parameter.startswith(group)
