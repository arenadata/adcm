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

from core.bundle.types import (
    ComponentRestrictionOwner,
    MissingServiceRequiresViolation,
    ServiceDependencies,
    ServiceRestrictionOwner,
)
from core.cluster.types import NamedMapping


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
