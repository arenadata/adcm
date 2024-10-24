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
from typing import TypeAlias

from core.bundle.types import BundleRestrictions
from core.types import ComponentNameKey, ServiceNameKey

_DependencyMap: TypeAlias = dict[ServiceNameKey | ComponentNameKey, set[ServiceNameKey | ComponentNameKey]]


class RequiresDependencies:
    __slots__ = ("_direct", "_full")

    def __init__(self, direct_dependencies: _DependencyMap) -> None:
        self._direct = direct_dependencies
        self._full: _DependencyMap = {}

    def __getitem__(self, item: ServiceNameKey | ComponentNameKey) -> set[ServiceNameKey | ComponentNameKey]:
        if item not in self._direct:
            return set()

        if all_dependencies := self._full.get(item):
            return all_dependencies

        all_dependencies = self._resolve_full_dependencies(key=item, processed=set())
        self._full[item] = all_dependencies

        return all_dependencies

    def _resolve_full_dependencies(
        self, key: ServiceNameKey | ComponentNameKey, processed: set[ServiceNameKey | ComponentNameKey]
    ) -> set[ServiceNameKey | ComponentNameKey]:
        dependencies = set()

        for dependency in self._direct.get(key, ()):
            dependencies.add(dependency)

            if dependency not in processed:
                processed.add(dependency)
                dependencies |= self._resolve_full_dependencies(key=key, processed=processed)

        return dependencies - {key}


def build_requires_dependencies_map(bundle_restrictions: BundleRestrictions) -> RequiresDependencies:
    requires: _DependencyMap = defaultdict(set)

    for dependant_object, required_service_names in bundle_restrictions.service_requires.items():
        requires[dependant_object].update(map(ServiceNameKey, required_service_names))

    for dependant_object, required_components in bundle_restrictions.mapping.required_components.items():
        requires[dependant_object].update(required_components)

    for dependant_component, required_service_names in bundle_restrictions.mapping.required_services.items():
        requires[dependant_component].update(map(ServiceNameKey, required_service_names))

    return RequiresDependencies(direct_dependencies=requires)
