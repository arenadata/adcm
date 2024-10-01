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

from collections import deque
from functools import partial
from typing import Iterable

from core.bundle.types import (
    ComponentRestrictionOwner,
    Constraint,
    HostsAmount,
    MappingRestrictions,
    MappingRestrictionType,
    MappingRestrictionViolation,
    ServiceRestrictionOwner,
    SupportedConstraintFormat,
)
from core.cluster.types import NamedMapping
from core.types import ComponentNameKey, HostID


def find_cluster_mapping_issues(
    restrictions: MappingRestrictions, named_mapping: NamedMapping, amount_of_hosts_in_cluster: HostsAmount
) -> tuple[MappingRestrictionViolation, ...]:
    if not (restrictions.constraints or restrictions.required_components or restrictions.binds):
        return ()

    unsatisfied_restrictions = deque()

    component_mapping: dict[ComponentNameKey, set[HostID]] = {
        ComponentNameKey(service=service_name, component=component_name): hosts
        for service_name, components in named_mapping.items()
        for component_name, hosts in components.items()
    }

    for component_key, constraint in restrictions.constraints.items():
        hosts = component_mapping.get(component_key)
        # check if component exists
        if hosts is None:
            continue

        if not is_constraint_restriction_satisfied(
            constraint=constraint, hosts_with_component=len(hosts), hosts_in_cluster=amount_of_hosts_in_cluster
        ):
            unsatisfied_restrictions.append(
                MappingRestrictionViolation(
                    restriction=MappingRestrictionType.CONSTRAINT,
                    owner=component_key,
                    message=f"{str(component_key).capitalize()} has unsatisfied constraint: {constraint.internal}",
                )
            )

    for dependant_object, required_components in restrictions.required_components.items():
        if isinstance(dependant_object, ComponentRestrictionOwner) and not component_mapping.get(dependant_object):
            # restriction from unmapped dependant component shouldn't be checked
            continue

        if isinstance(dependant_object, ServiceRestrictionOwner):
            # In order for "requires" restriction from service to be performed, following condition should be met:
            # 1. Service added to cluster
            # 2. At least one component of this service should be mapped

            at_least_one_mapped = any(named_mapping.get(dependant_object.service, {}).values())
            if not at_least_one_mapped:
                continue

        unsatisfied_requires = find_first_unmapped_component(
            required_components=required_components, named_mapping=named_mapping
        )
        if unsatisfied_requires:
            unsatisfied_restrictions.append(
                MappingRestrictionViolation(
                    restriction=MappingRestrictionType.REQUIRES,
                    owner=dependant_object,
                    message=f"No required {unsatisfied_requires} for {dependant_object}",
                )
            )

    for component_key, required_services in restrictions.required_services.items():
        if not component_mapping.get(component_key):
            continue

        not_existing_services = required_services.difference(named_mapping)
        if not_existing_services:
            unsatisfied_restrictions.append(
                MappingRestrictionViolation(
                    restriction=MappingRestrictionType.REQUIRES,
                    owner=component_key,
                    message=f"Services required for {component_key} are "
                    f"missing: {', '.join(sorted(not_existing_services))}",
                )
            )

    for component_key, bind_component in restrictions.binds.items():
        hosts = component_mapping.get(component_key)
        # check if component exists
        if hosts is None:
            continue

        if not is_bound_to_restriction_satisfied(
            bound_component=bind_component, component_hosts=hosts, named_mapping=named_mapping
        ):
            message = (
                "Component `bound_to` restriction violated.\n"
                f"Each host with {bind_component} should have mapped {component_key}."
            )
            unsatisfied_restrictions.append(
                MappingRestrictionViolation(
                    restriction=MappingRestrictionType.BOUND_TO,
                    owner=component_key,
                    message=message,
                )
            )

    return tuple(unsatisfied_restrictions)


def is_constraint_restriction_satisfied(
    constraint: Constraint, hosts_with_component: HostsAmount, hosts_in_cluster: HostsAmount
) -> bool:
    return all(
        constraint_is_satisfied(hosts_with_component, hosts_in_cluster) for constraint_is_satisfied in constraint.checks
    )


def find_first_unmapped_component(
    required_components: Iterable[ComponentNameKey], named_mapping: NamedMapping
) -> ComponentNameKey | None:
    for component_key in required_components:
        if not named_mapping.get(component_key.service, {}).get(component_key.component, ()):
            return component_key

    return None


def is_bound_to_restriction_satisfied(
    bound_component: ComponentNameKey, component_hosts: set[HostID], named_mapping: NamedMapping
) -> bool:
    # unmapped dependant component satisfies restriction
    if not component_hosts:
        return True

    bound_component_hosts = named_mapping.get(bound_component.service, {}).get(bound_component.component, set())
    return bound_component_hosts == component_hosts


# Constraint Preparation


def check_equal_or_less(mapped_hosts: HostsAmount, _: HostsAmount, argument: int):
    return mapped_hosts <= argument


def check_equal_or_greater(mapped_hosts: HostsAmount, _: HostsAmount, argument: int):
    return mapped_hosts >= argument


def check_exact(mapped_hosts: HostsAmount, _: HostsAmount, argument: int):
    return mapped_hosts == argument


def check_is_odd(mapped_hosts: HostsAmount, _: HostsAmount):
    return mapped_hosts % 2 == 1


def check_is_zero_or_odd(mapped_hosts: HostsAmount, hosts_in_cluster: HostsAmount):
    if mapped_hosts == 0:
        return True

    return check_is_odd(mapped_hosts, hosts_in_cluster)


def check_on_all(mapped_hosts: HostsAmount, hosts_in_cluster: HostsAmount):
    return mapped_hosts > 0 and mapped_hosts == hosts_in_cluster


def parse_constraint(constraint: SupportedConstraintFormat) -> Constraint:
    match constraint:
        case [0, "+"]:
            # no checks actually required, it's the "default"
            checks = ()
        case ["+"]:
            checks = (check_on_all,)
        case ["odd"]:
            checks = (check_is_odd,)
        case [int(exact)]:
            checks = (partial(check_exact, argument=exact),)
        case [0, "odd"]:
            checks = (check_is_zero_or_odd,)
        case [int(min_), "odd"]:
            checks = (partial(check_equal_or_greater, argument=min_), check_is_odd)
        case [int(min_), "+"]:
            checks = (partial(check_equal_or_greater, argument=min_),)
        case [int(min_), int(max_)]:
            checks = (partial(check_equal_or_greater, argument=min_), partial(check_equal_or_less, argument=max_))
        case _:
            # keep this function safe, even though it may lead to "strange" results
            checks = ()

    return Constraint(internal=constraint, checks=checks)
