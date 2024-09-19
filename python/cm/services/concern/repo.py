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

from collections import defaultdict, deque

from core.concern.checks import parse_constraint
from core.concern.types import (
    BundleRestrictions,
    ComponentNameKey,
    ComponentRestrictionOwner,
    MappingRestrictions,
    ServiceDependencies,
    ServiceRestrictionOwner,
)
from core.types import BundleID

from cm.models import ObjectType, Prototype


def retrieve_bundle_restrictions(bundle_id: BundleID) -> BundleRestrictions:
    mapping_restrictions = MappingRestrictions(
        constraints={}, required_components=defaultdict(deque), required_services=defaultdict(set), binds={}
    )
    service_requires: ServiceDependencies = defaultdict(set)

    for component_name, service_name, constraint, requires, bound_to in (
        Prototype.objects.select_related("parent")
        .values_list("name", "parent__name", "constraint", "requires", "bound_to")
        .filter(bundle_id=bundle_id, type=ObjectType.COMPONENT)
    ):
        key = ComponentRestrictionOwner(service=service_name, component=component_name)

        for requirement in requires:
            # Requires that have `component` specified aren't the same with only service specified
            # (regardless of restriction source):
            #   - "service-only" require presence of service in cluster,
            #     so it's enough to "add" required service.
            #   - ones with `component` key adds restriction on mapping,
            #     because such component should be mapped on at least one host.
            #
            # "service" requires from component are relative only to mapping checks,
            # it doesn't affect service-related concerns.
            required_service_name = requirement["service"]
            if required_component_name := requirement.get("component"):
                mapping_restrictions.required_components[key].append(
                    ComponentNameKey(component=required_component_name, service=required_service_name)
                )
            else:
                mapping_restrictions.required_services[key].add(required_service_name)

        constraint = parse_constraint(constraint)
        if constraint.checks:
            mapping_restrictions.constraints[key] = constraint

        if bound_to:
            mapping_restrictions.binds[key] = ComponentNameKey(
                component=bound_to["component"], service=bound_to["service"]
            )

    for service_name, requires in Prototype.objects.values_list("name", "requires").filter(
        bundle_id=bundle_id, type=ObjectType.SERVICE
    ):
        if not requires:
            continue

        key = ServiceRestrictionOwner(name=service_name)

        for requirement in requires:
            required_service_name = requirement["service"]
            service_requires[key].add(required_service_name)
            if component_name := requirement.get("component"):
                mapping_restrictions.required_components[key].append(
                    ComponentNameKey(component=component_name, service=required_service_name)
                )

    return BundleRestrictions(service_requires=service_requires, mapping=mapping_restrictions)
