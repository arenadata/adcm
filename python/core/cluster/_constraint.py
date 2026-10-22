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

from collections.abc import Callable, Sequence
from functools import partial
from typing import NamedTuple, TypeAlias

HostsAmount: TypeAlias = int

# Constraint of component on amount of hosts it's mapped to,
# like `[0, "+"]`, `[1]`, `["odd"]` (stored as list, defined in bundle as list too)
SupportedConstraintFormat: TypeAlias = Sequence[HostsAmount | str]


class Constraint(NamedTuple):
    internal: SupportedConstraintFormat
    checks: tuple[Callable[[HostsAmount, HostsAmount], bool], ...]


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


def is_constraint_restriction_satisfied(
    constraint: Constraint, hosts_with_component: HostsAmount, hosts_in_cluster: HostsAmount
) -> bool:
    return all(
        constraint_is_satisfied(hosts_with_component, hosts_in_cluster) for constraint_is_satisfied in constraint.checks
    )


def is_mapping_required(constraint: Constraint) -> bool:
    """Whether component with given constraint has to be mapped at least on one host"""
    return not is_constraint_restriction_satisfied(constraint=constraint, hosts_with_component=0, hosts_in_cluster=0)


# Checks


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
