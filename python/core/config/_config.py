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
from contextlib import suppress
from functools import partial
from typing import Any, Callable, TypeVar

from core.config import spec
from core.config._names import full_name_to_level_names
from core.config._predicates import Predicate
from core.config._types import (
    ConfigAttrs,
    Configuration,
    ConfigValues,
    FlatConfiguration,
    ParameterFullName,
    ParameterLevelName,
)

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
New = TypeVar("New")
Old = TypeVar("Old")


def detect_changes(previous: Configuration, new: Configuration, specification: spec.FullSpec) -> set[ParameterFullName]:
    """
    Find difference values and attribute between two configuration.
    Configurations in given result contains only changed values/attributes.

    Notes:
    - It is assumed that both configurations are valid and has the same fields based on specification
    - Attribute changes are registered even when only one of fields changed.
    """
    changed = set()

    for name in specification.parameters:
        new_value = get_by_full_name_or_none(name=name, values=new.values)
        previous_value = get_by_full_name_or_none(name=name, values=previous.values)

        if new_value != previous_value:
            changed.add(name)
            continue

        new_attr = new.attributes.get(name)
        previous_attr = previous.attributes.get(name)

        if new_attr != previous_attr:
            changed.add(name)

    for name in specification.attributes.activatable_groups:
        new_attr = new.attributes.get(name)
        previous_attr = previous.attributes.get(name)

        if new_attr != previous_attr:
            changed.add(name)

    return changed


def get_by_full_name_or_none(name: ParameterFullName, values: ConfigValues) -> None | Any:
    try:
        return get_by_full_name(name=name, values=values)
    except KeyError:
        return None


def get_by_full_name(name: ParameterFullName, values: ConfigValues) -> Any:
    level_name, group_values = get_group_with_value(name=name, values=values)
    return group_values[level_name]


def get_group_with_value(name: ParameterFullName, values: ConfigValues) -> tuple[ParameterLevelName, ConfigValues]:
    return _get_group_with_value(level_names=full_name_to_level_names(name), values=values)


def set_by_full_name(name: ParameterFullName, new_value: Any, values: ConfigValues) -> None:
    own_name, group = get_group_with_value(name=name, values=values)
    group[own_name] = new_value


def set_by_full_name_returning_old(name: ParameterFullName, new_value: Any, values: ConfigValues) -> Any:
    own_name, group = get_group_with_value(name=name, values=values)
    previous = group[own_name]
    group[own_name] = new_value
    return previous


def change_by_full_name(name: ParameterFullName, func: Callable[[Any], New], values: ConfigValues) -> None:
    own_name, group = get_group_with_value(name=name, values=values)
    new_value = func(group[own_name])
    group[own_name] = new_value


def apply_if(value: Old, func: Callable[[Old], New], when: Predicate[Old]) -> Old | New:
    if when(value):
        return func(value)

    return value


def build_apply_if(func: Callable[[Old], New], when: Predicate[Old]) -> Callable[[Old], Old | New]:
    return partial(apply_if, func=func, when=when)


def detect_active_groups(attributes: ConfigAttrs) -> set[ParameterFullName]:
    return {name for name, attrs in attributes.items() if attrs.activation and attrs.is_active}


def nested_to_flat(configuration: Configuration, specification: spec.FullSpec) -> FlatConfiguration:
    """
    Convert to flat configuration in a way that is correct for existing operations: missing fields aren't included
    (since structure is checked, it's ok + won't conflict with potential new features like exclusive groups).

    No copying happens, so changes will follow, thou you shouldn't do that actually.
    """

    result = FlatConfiguration(attributes=configuration.attributes)

    for name in specification.parameters:
        with suppress(KeyError):
            value = get_by_full_name(name=name, values=configuration.values)
            result.values[name] = value

    return result


def flat_to_nested(flat_config: dict[ParameterFullName, Any]) -> ConfigValues:
    result = _recursive_defaultdict()

    for name, value in flat_config.items():
        own_name, group = get_group_with_value(name=name, values=result)
        group[own_name] = value

    return _recursive_defaultdict_to_dict(result)


def _get_group_with_value(
    level_names: tuple[ParameterLevelName, ...] | list[ParameterLevelName], values: ConfigValues
) -> tuple[ParameterLevelName, ConfigValues]:
    level_name, *rest = level_names
    if not rest:
        return level_name, values

    return _get_group_with_value(values=values[level_name], level_names=rest)


def _recursive_defaultdict():
    return defaultdict(_recursive_defaultdict)


def _recursive_defaultdict_to_dict(d: defaultdict[K, V]) -> dict[K, V]:
    return {k: _recursive_defaultdict_to_dict(v) if isinstance(v, defaultdict) else v for k, v in d.items()}
