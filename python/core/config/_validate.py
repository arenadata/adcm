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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import chain
from typing import Any, Callable, Iterable, Protocol, TypeAlias

from core.config import _yspec, spec
from core.config._config import detect_active_groups
from core.config._names import is_part_of_group, join_level_name_with_group_name, level_names_to_full_name
from core.config._types import (
    Change,
    ConfigAttrs,
    ConfigFlatValues,
    Configuration,
    ConfigValues,
    ParameterFullName,
    ParameterLevelName,
)
from core.result import Fail, Success
from core.types import CoreObjectDescriptor

# External Interface


class VariantValidator(Protocol):
    def is_value_allowed(self, value: Any, parameter: spec.p.VariantParameter) -> bool:
        ...


class PatternValidator(Protocol):
    def is_match(self, value: str, pattern: str) -> bool:
        ...


class AlwaysPassValidator(VariantValidator, PatternValidator):
    def is_value_allowed(self, value: Any, parameter: spec.p.VariantParameter) -> bool:
        _ = value, parameter
        return True

    def is_match(self, value: str, pattern: str) -> bool:
        _ = value, pattern
        return True


@dataclass(slots=True)
class Validators:
    variant: VariantValidator
    pattern: PatternValidator


@dataclass(slots=True)
class MainConfigVariantResolver(ABC, VariantValidator):
    owner: CoreObjectDescriptor
    reference_config: Configuration

    # todo rethink variant validator interface,
    #  maybe it'll actually work with `resolve` method and check in validation
    @abstractmethod
    def resolve(self, parameter: spec.p.VariantParameter) -> tuple:
        ...


# Types & Constants


@dataclass(slots=True, frozen=True)
class Violation:
    parameter: ParameterFullName
    check: str
    reason: str

    @property
    def message(self) -> str:
        return f'Validation failed on check "{self.check}" for config parameter "{self.parameter}": {self.reason}'


Violations: TypeAlias = list[Violation]


# Public


def validate_configuration_is_consistent(
    configuration: Configuration, specification: spec.FullSpec
) -> Success[None] | Fail[Violations]:
    """
    Check if given configuration has all value fields present and its attributes aren't conflicting with spec
    having all important attributes specified.
    """
    active_groups = detect_active_groups(attributes=configuration.attributes)
    # Set of deactivated groups may be incorrect in here, because attribute violations are checked later,
    # but it's enough for values violations checks.
    deactivated_groups = spec.detect_deactivated_groups(spec=specification, active_groups=active_groups)

    values_violations = _find_values_violations(
        configuration=configuration.values,
        hierarchy=specification.hierarchy,
        deactivated_groups=deactivated_groups,
    )
    if values_violations:
        # can't continue if values aren't correct
        return Fail(values_violations)

    excluded_groups = _detect_excluded_groups_from_values(
        values=configuration.values, hierarchy=specification.hierarchy
    )

    attribute_violations = _find_attribute_violations(
        attributes=configuration.attributes, specification=specification, excluded_groups=set(excluded_groups)
    )

    if attribute_violations:
        return Fail(attribute_violations)

    return Success(None)


def validate_changes_are_allowed(
    changes: list[Change],
    attributes: ConfigAttrs,
    desync_allowed: set[ParameterFullName],
) -> Success[None] | Fail[Violations]:
    """
    Check if changes performed on two configurations are allowed based on restrictions.
    """

    changed_params = {change.parameter for change in changes}
    desync_disallowed = changed_params.difference(desync_allowed)
    desync_disallowed_attrs = {name: attributes[name] for name in desync_disallowed if name in attributes}
    changed_but_synced = tuple(
        name for name, attrs in desync_disallowed_attrs.items() if attrs.synchronization and not attrs.is_synced
    )
    if changed_but_synced:
        errors = [
            Violation(parameter=name, check="change", reason="parameter can not be desynchronized with configuration")
            for name in changed_but_synced
        ]
        return Fail(errors)

    return Success(None)


def validate_values_are_correct(
    values: ConfigFlatValues,
    specification: spec.FullSpec,
    deactivated_parameters: set[ParameterFullName],
    validators: Validators,
) -> Success[None] | Fail[Violations]:
    """
    Check if `values` from given configuration are of correct type and it's exact value is allowed.
    """
    errors = []

    for name, value in values.items():
        param = specification.parameters[name]

        if _is_empty(value=value, param=param):
            is_required_and_not_deactivated = param.is_required and name not in deactivated_parameters
            if is_required_and_not_deactivated:
                _add_empty_violation(name=name, value=value, errors=errors)

            continue

        match param:
            case spec.p.StringParameter(pattern=pattern):
                if not isinstance(value, str):
                    _add_type_violation(name=name, allowed="string", errors=errors)
                elif pattern is not None:
                    matches_pattern = validators.pattern.is_match(value=value, pattern=pattern)
                    if not matches_pattern:
                        _add_value_violation(name=name, reason=f'does not match pattern: "{pattern}"', errors=errors)

            case spec.p.NumberParameter(is_float=is_float, min=min_, max=max_):
                types = (float, int) if is_float else (int,)
                if not isinstance(value, types):
                    type_name = "float" if is_float else "integer"
                    _add_type_violation(name=name, allowed=type_name, errors=errors)
                elif min_ is not None and value < min_:
                    _add_value_violation(name=name, reason=f"should be greater than {min_}", errors=errors)
                elif max_ is not None and value > max_:
                    _add_value_violation(name=name, reason=f"should be lesser than {max_}", errors=errors)

            case spec.p.MapParameter():
                if not isinstance(value, dict):
                    _add_type_violation(name=name, allowed="map", errors=errors)
                elif not all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
                    _add_value_violation(name=name, reason="all keys and values must be strings", errors=errors)

            case spec.p.ListParameter():
                if not isinstance(value, list):
                    _add_type_violation(name=name, allowed="list", errors=errors)
                elif not all(isinstance(e, str) for e in value):
                    _add_value_violation(name=name, reason="all entries must be strings", errors=errors)

            case spec.p.BooleanParameter():
                if not isinstance(value, bool):
                    _add_type_violation(name=name, allowed="boolean", errors=errors)

            case spec.p.OptionParameter(options=options):
                allowed_values = options.values()
                if value not in allowed_values:
                    allowed_values_repr = ", ".join(sorted(map(str, allowed_values)))
                    _add_value_violation(
                        name=name, reason=f'not in option list: "{allowed_values_repr}"', errors=errors
                    )

            case spec.p.StructureParameter(yspec=schema):
                reason = None
                try:
                    _yspec.process_rule(data=value, rules=schema, name="root")
                except _yspec.FormatError as e:
                    reason = f"yspec error: {str(e)} at block {e.data}"
                except _yspec.SchemaError as e:
                    reason = f"yspec error: {str(e)}"

                if reason is not None:
                    _add_value_violation(name=name, reason=reason, errors=errors)

            case spec.p.VariantParameter(is_strict=True):
                is_allowed = validators.variant.is_value_allowed(value=value, parameter=param)
                if not is_allowed:
                    _add_value_violation(name=name, reason="not in variant list", errors=errors)

    if errors:
        return Fail(errors)

    return Success(None)


# Steps And Utilities

_AnyAsConfigValues = ConfigValues | Any
_ValuesStructureValidator = Callable[
    [_AnyAsConfigValues, spec.SpecHierarchyLevel, tuple[ParameterLevelName, ...]], Violations
]


def _find_values_violations(
    configuration: _AnyAsConfigValues,
    hierarchy: spec.SpecHierarchyLevel,
    deactivated_groups: set[ParameterFullName],
    group_prefix: tuple[ParameterLevelName, ...] = (),
) -> Violations:
    is_in_deactivated_group = level_names_to_full_name(group_prefix) in deactivated_groups
    validate = _detect_values_validator_for_level_rule(
        rule=hierarchy.rule, in_deactivated_group=is_in_deactivated_group
    )
    violations = validate(configuration, hierarchy, group_prefix)

    if not isinstance(configuration, dict):
        return violations

    for child_name, child_hierarchy in hierarchy.child_groups.items():
        if child_name in configuration:
            child_configuration = configuration[child_name]
            violations += _find_values_violations(
                configuration=child_configuration,
                hierarchy=child_hierarchy,
                deactivated_groups=deactivated_groups,
                group_prefix=(*group_prefix, child_name),
            )

    return violations


def _detect_values_validator_for_level_rule(
    rule: spec.HierarchyValidationRule, in_deactivated_group: bool
) -> _ValuesStructureValidator:
    match rule:
        case spec.HierarchyValidationRule.ALL:
            return _find_values_violations_rule_all
        case spec.HierarchyValidationRule.EXACTLY_ONE if not in_deactivated_group:
            return _find_values_violations_rule_exactly_one
        case spec.HierarchyValidationRule.AT_MOST_ONE | spec.HierarchyValidationRule.EXACTLY_ONE:
            return _find_values_violations_rule_at_most_one


def _find_values_violations_rule_all(
    configuration: _AnyAsConfigValues, hierarchy: spec.SpecHierarchyLevel, group_prefix: tuple[ParameterLevelName, ...]
) -> Violations:
    if not isinstance(configuration, dict):
        violation = Violation(
            parameter=level_names_to_full_name(group_prefix),
            check="structure",
            reason="incorrect group value type, expected dict",
        )
        return [violation]

    required_fields = set(hierarchy.fields)
    present_fields = set(configuration.keys())

    missing_fields = required_fields - present_fields
    unexpected_fields = present_fields - required_fields

    missing_violations = [
        Violation(
            parameter=level_names_to_full_name((*group_prefix, name)),
            check="structure",
            reason="value is missing",
        )
        for name in missing_fields
    ]
    unexpected_violations = [
        Violation(
            parameter=level_names_to_full_name((*group_prefix, name)),
            check="structure",
            reason="value is unexpected",
        )
        for name in unexpected_fields
    ]

    return missing_violations + unexpected_violations


def _find_values_violations_rule_exactly_one(
    configuration: _AnyAsConfigValues, hierarchy: spec.SpecHierarchyLevel, group_prefix: tuple[ParameterLevelName, ...]
) -> Violations:
    if not isinstance(configuration, dict):
        violation = Violation(
            parameter=level_names_to_full_name(group_prefix),
            check="structure",
            reason="incorrect group value type, expected dict",
        )
        return [violation]

    if (children_amount := len(configuration)) != 1:
        violation = Violation(
            parameter=level_names_to_full_name(group_prefix),
            check="structure",
            reason=f"exactly one child expected, found: {children_amount}",
        )
        return [violation]

    chosen_name = next(iter(configuration))
    if chosen_name not in hierarchy.fields:
        violation = Violation(
            parameter=level_names_to_full_name((*group_prefix, chosen_name)),
            check="structure",
            reason="value is unexpected",
        )
        return [violation]

    return []


def _find_values_violations_rule_at_most_one(
    configuration: _AnyAsConfigValues, hierarchy: spec.SpecHierarchyLevel, group_prefix: tuple[ParameterLevelName, ...]
) -> Violations:
    if configuration is None:
        return []

    return _find_values_violations_rule_exactly_one(configuration, hierarchy, group_prefix)


def _find_attribute_violations(
    attributes: ConfigAttrs, specification: spec.FullSpec, excluded_groups: set[ParameterFullName]
) -> Violations:
    violations = []

    attr_spec = specification.attributes
    with_activation = {name for name, attr in attributes.items() if attr.activation}

    expected_with_activation = set(_remove_excluded(attr_spec.activatable_groups, excluded_groups=excluded_groups))

    if with_activation != expected_with_activation:
        for missing in expected_with_activation - with_activation:
            violation = Violation(parameter=missing, check="attribute", reason="missing activation attribute")
            violations.append(violation)

        for extra in with_activation - expected_with_activation:
            violation = Violation(parameter=extra, check="attribute", reason="unexpected activation attribute")
            violations.append(violation)

    synchronization = {name: attr.is_synced for name, attr in attributes.items() if attr.synchronization}

    if synchronization:
        # means it's config group

        # Maybe this set should be bound to FullSpec since it's business-bound in some sense.
        # On another hand, this check is too specific for input, only desyncable parameters are of interest.
        expected_with_sync = set(
            _remove_excluded(
                chain(specification.parameters.keys(), attr_spec.activatable_groups), excluded_groups=excluded_groups
            )
        )

        for missing in expected_with_sync.difference(synchronization):
            violation = Violation(parameter=missing, check="attribute", reason="missing synchronization attribute")
            violations.append(violation)

        for extra in set(synchronization).difference(expected_with_sync):
            violation = Violation(parameter=extra, check="attribute", reason="unexpected synchronization attribute")
            violations.append(violation)

        allowed_to_be_desynced = {name for name, param in specification.parameters.items() if param.is_desyncable} | {
            name for name, group in specification.groups.items() if group.activation and group.activation.is_desyncable
        }
        desynced = {name for name, is_synced in synchronization.items() if not is_synced}
        for wrongly_desynced in desynced.difference(allowed_to_be_desynced):
            violation = Violation(
                parameter=wrongly_desynced, check="attribute", reason="not allowed to be desynchronized"
            )
            violations.append(violation)

    return violations


def _detect_excluded_groups_from_values(
    values: _AnyAsConfigValues, hierarchy: spec.SpecHierarchyLevel, group: ParameterFullName = ""
) -> list[ParameterFullName]:
    excluded = []

    if hierarchy.rule in (spec.HierarchyValidationRule.AT_MOST_ONE, spec.HierarchyValidationRule.EXACTLY_ONE):
        fields_to_exclude = [*hierarchy.fields]

        if isinstance(values, dict):
            fields_to_exclude.remove(next(iter(values.keys())))

        excluded.extend(join_level_name_with_group_name(field, group=group) for field in fields_to_exclude)

    if isinstance(values, dict):
        for child_name, child_hierarchy in hierarchy.child_groups.items():
            if child_name in values:
                child_values = values[child_name]
                group_name = join_level_name_with_group_name(child_name, group)
                excluded += _detect_excluded_groups_from_values(
                    values=child_values, hierarchy=child_hierarchy, group=group_name
                )

    return excluded


def _remove_excluded(
    names: Iterable[ParameterFullName], excluded_groups: set[ParameterFullName]
) -> set[ParameterFullName]:
    if not excluded_groups:
        return set(names)

    return {name for name in names if not any(is_part_of_group(name, group=group) for group in excluded_groups)}


def _is_empty(value: Any, param: spec.p.SimpleParameter) -> bool:
    return (
        value is None
        or (value == "" and param.type == spec.p.ParameterType.STRING)
        or (value == {} and param.type == spec.p.ParameterType.MAP)
        or (value == [] and param.type == spec.p.ParameterType.LIST)
    )


def _add_empty_violation(name: ParameterFullName, value: Any, errors: Violations) -> Violation:
    err = Violation(parameter=name, check="value", reason=f'value should not be empty, got "{value}"')
    errors.append(err)
    return err


def _add_type_violation(name: ParameterFullName, allowed: str, errors: Violations) -> Violation:
    err = Violation(parameter=name, check="value", reason=f"should be of type {allowed}")
    errors.append(err)
    return err


def _add_value_violation(name: ParameterFullName, reason: str, errors: Violations) -> Violation:
    err = Violation(parameter=name, check="value", reason=reason)
    errors.append(err)
    return err
