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

from contextlib import contextmanager, suppress
from functools import partial
from typing import Any, Callable, Generator, TypeVar

from core.config import spec
from core.config._helpers import recursive_defaultdict, recursive_defaultdict_to_dict
from core.config._names import full_name_to_level_names
from core.config._predicates import Predicate
from core.config._types import (
    Change,
    ChangeType,
    ConfigAttrs,
    Configuration,
    ConfigValues,
    FlatConfiguration,
    ParameterFullName,
    ParameterLevelName,
)
from core.result import Fail, Success
from core.types import ADCMMessageError

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
New = TypeVar("New")
Old = TypeVar("Old")


class MissingKeyError(ADCMMessageError):
    """
    Error to reraise on absence of key in config.

    Shouldn't be catched outside `core.config` package.
    """


def detect_changes(previous: Configuration, new: Configuration, specification: spec.FullSpec) -> list[Change]:
    """
    Find difference values and attribute between two configuration.

    Notes:
    - It is assumed that both configurations are valid and has the same fields based on specification.
    - Attribute changes are registered per attribute.
    - One parameter may appear in result more than once (e.g. it's sync and attr were changed).
    - Current algorithm may underperform for big configs (deep, actually) due to values extraction per parameter,
      yet it's simpler than recursive values approach;
      change only if performance issues are detected in this function.
    """
    changes = []

    for name in specification.parameters:
        new_value = get_by_full_name_or_none(name=name, values=new.values)
        previous_value = get_by_full_name_or_none(name=name, values=previous.values)

        if new_value != previous_value:
            changes.append(Change(parameter=name, type=ChangeType.VALUE, old=previous_value, new=new_value))

        activation_changes = _detect_attribute_changes(
            name=name, previous_attributes=previous.attributes, new_attributes=new.attributes
        )
        changes.extend(activation_changes)

    for name, group in specification.groups.items():
        if group.selection:
            new_value = get_by_full_name_or_none(name=name, values=new.values)
            previous_value = get_by_full_name_or_none(name=name, values=previous.values)

            new_selection = _detect_selected_group_name(value=new_value)
            previous_selection = _detect_selected_group_name(value=previous_value)
            if previous_selection != new_selection:
                changes.append(
                    Change(
                        parameter=name,
                        type=ChangeType.SELECTION,
                        old=previous_selection,
                        new=new_selection,
                    )
                )

        if group.activation:
            activation_changes = _detect_attribute_changes(
                name=name, previous_attributes=previous.attributes, new_attributes=new.attributes
            )
            changes.extend(activation_changes)

    return changes


def get_by_full_name_or_none(name: ParameterFullName, values: ConfigValues) -> None | Any:
    with suppress(MissingKeyError):
        return get_by_full_name(name=name, values=values)

    return None


def get_by_full_name(name: ParameterFullName, values: ConfigValues) -> Any:
    level_name, group_values = _get_group_with_value_by_full_name(name=name, values=values)
    with _convert_node_access_errors_to_missing_key(name=name):
        return group_values[level_name]


def set_by_full_name(name: ParameterFullName, new_value: Any, values: ConfigValues) -> None:
    own_name, group = _get_group_with_value_by_full_name(name=name, values=values)
    with _convert_node_access_errors_to_missing_key(name=name):
        group[own_name] = new_value


def set_by_full_name_returning_old(name: ParameterFullName, new_value: Any, values: ConfigValues) -> Any:
    own_name, group = _get_group_with_value_by_full_name(name=name, values=values)

    with _convert_node_access_errors_to_missing_key(name=name):
        previous = group[own_name]

    group[own_name] = new_value
    return previous


def change_by_full_name_skip_missing(
    name: ParameterFullName, func: Callable[[Any], New], values: ConfigValues
) -> Success[None] | Fail[None]:
    with suppress(MissingKeyError):
        change_by_full_name(name=name, func=func, values=values)
        return Success(None)

    return Fail(None)


def change_by_full_name(name: ParameterFullName, func: Callable[[Any], New], values: ConfigValues) -> None:
    own_name, group = _get_group_with_value_by_full_name(name=name, values=values)

    with _convert_node_access_errors_to_missing_key(name=name):
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

    # NOTE
    #  Retrieval by full name has its costs (string spawning)
    #  and for deeply nested configs retrieval of node may have a cost too.
    #  That price is paid for simplicity of algorithm.
    #  If this became a problem, look into recursive implemetation based on hierarchy.
    for name in specification.parameters:
        with suppress(MissingKeyError):
            value = get_by_full_name(name=name, values=configuration.values)
            result.values[name] = value

    return result


def flat_to_nested(flat_config: dict[ParameterFullName, Any]) -> ConfigValues:
    result = recursive_defaultdict()

    for name, value in flat_config.items():
        own_name, group = _get_group_with_value_by_full_name(name=name, values=result)
        group[own_name] = value

    return recursive_defaultdict_to_dict(result)


def _detect_selected_group_name(value: dict | None) -> str | None:
    if value is None:
        return None

    selected_keys = tuple(value.keys())
    is_unsupported_format = len(selected_keys) != 1 or selected_keys[0] == "_selection"
    if is_unsupported_format:
        raise ValueError(
            "Unsupported selection group format: expected exactly one selected-group key and no '_selection' key"
        )

    return selected_keys[0]


def _detect_attribute_changes(
    name: ParameterFullName,
    previous_attributes: ConfigAttrs,
    new_attributes: ConfigAttrs,
) -> Generator[Change, None, None]:
    previous = previous_attributes.get(name)
    new = new_attributes.get(name)

    previous_activation = previous.is_active if previous else None
    new_activation = new.is_active if new else None
    if previous_activation != new_activation:
        yield Change(parameter=name, type=ChangeType.ACTIVATION, old=previous_activation, new=new_activation)

    previous_synchronization = previous.is_synced if previous else None
    new_synchronization = new.is_synced if new else None
    if previous_synchronization != new_synchronization:
        yield Change(
            parameter=name,
            type=ChangeType.SYNCHRONIZATION,
            old=previous_synchronization,
            new=new_synchronization,
        )


def _get_group_with_value_by_full_name(
    name: ParameterFullName, values: ConfigValues
) -> tuple[ParameterLevelName, ConfigValues]:
    with _convert_node_access_errors_to_missing_key(name=name):
        return _get_group_with_value(level_names=full_name_to_level_names(name), values=values)


def _get_group_with_value(
    level_names: tuple[ParameterLevelName, ...] | list[ParameterLevelName], values: ConfigValues
) -> tuple[ParameterLevelName, ConfigValues]:
    level_name, *rest = level_names
    if not rest:
        return level_name, values

    return _get_group_with_value(values=values[level_name], level_names=rest)


@contextmanager
def _convert_node_access_errors_to_missing_key(name: ParameterFullName) -> Generator[None, None, None]:
    try:
        yield
    except (KeyError, TypeError) as e:
        raise MissingKeyError(message=f'Value is missing for full name: "{name}"') from e
