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
from typing import Iterable, TypeAlias

from core.bundle.types import (
    BundleRestrictions,
    ComponentRestrictionOwner,
    MissingServiceRequiresViolation,
    ServiceDependencies,
    ServiceRestrictionOwner,
)
from core.cluster.types import NamedMapping
from core.types import ServiceName

HasIssue: TypeAlias = bool


def find_unsatisfied_service_requirements(
    services_restrictions: ServiceDependencies, named_mapping: NamedMapping
) -> tuple[MissingServiceRequiresViolation, ...]:
    if not services_restrictions:
        return ()

    violations = deque()

    existing_services = set(named_mapping)

    for dependant_object, requires in services_restrictions.items():
        # if dependant object isn't added, requires shouldn't be checked
        if (
            isinstance(dependant_object, ComponentRestrictionOwner)
            and dependant_object.component not in named_mapping.get(dependant_object.service, ())
        ) or (
            isinstance(dependant_object, ServiceRestrictionOwner) and dependant_object.service not in existing_services
        ):
            continue

        if not_found_services := requires - existing_services:
            violations.extend(
                MissingServiceRequiresViolation(dependant_object=dependant_object, required_service=service)
                for service in not_found_services
            )

    return tuple(violations)


def find_not_added_required_services(
    bundle_restrictions: BundleRestrictions, existing_services: Iterable[ServiceName]
) -> set[ServiceName]:
    if not bundle_restrictions.required_services:
        return set()

    return bundle_restrictions.required_services.difference(existing_services)


def cluster_has_required_services_issue(
    bundle_restrictions: BundleRestrictions, existing_services: Iterable[ServiceName]
) -> HasIssue:
    return bool(
        find_not_added_required_services(bundle_restrictions=bundle_restrictions, existing_services=existing_services)
    )
