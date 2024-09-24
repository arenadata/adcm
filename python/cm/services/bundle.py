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

from abc import ABC
from collections import defaultdict, deque
from pathlib import Path

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
from django.conf import settings

from cm.models import ObjectType, Prototype


def detect_relative_path_to_bundle_root(source_file_dir: str | Path, raw_path: str) -> Path:
    """
    :param source_file_dir: Directory with file where given `path` is defined
    :param raw_path: Path to resolve

    >>> from pathlib import Path
    >>> this = detect_relative_path_to_bundle_root
    >>> this("", "./script.yaml") == Path("script.yaml")
    True
    >>> str(this(".", "./some/script.yaml")) == "some/script.yaml"
    True
    >>> str(this(Path(""), "script.yaml")) == "script.yaml"
    True
    >>> str(this(Path("inner"), "atroot/script.yaml")) == "atroot/script.yaml"
    True
    >>> str(this(Path("inner"), "./script.yaml")) == "inner/script.yaml"
    True
    >>> str(this(Path("inner"), "./alongside/script.yaml")) == "inner/alongside/script.yaml"
    True
    """
    if raw_path.startswith("./"):
        return Path(source_file_dir) / raw_path

    return Path(raw_path)


def is_path_correct(raw_path: str) -> bool:
    """
    Return whether given path meets ADCM path description requirements

    >>> this = is_path_correct
    >>> this("relative_to_bundle/path.yaml")
    True
    >>> this("./relative/to/file.yaml")
    True
    >>> this(".secret")
    True
    >>> this("../hack/system")
    False
    >>> this("/hack/system")
    False
    >>> this(".././hack/system")
    False
    >>> this("../../hack/system")
    False
    """
    return raw_path.startswith("./") or not raw_path.startswith(("..", "/"))


class PathResolver(ABC):
    __slots__ = ("_root",)

    _root: Path

    @property
    def bundle_root(self) -> Path:
        return self._root

    def resolve(self, path: str | Path) -> Path:
        return self._root / path


class BundlePathResolver(PathResolver):
    def __init__(self, bundle_hash: str):
        self._root = settings.BUNDLE_DIR / bundle_hash


class ADCMBundlePathResolver(PathResolver):
    def __init__(self):
        self._root = settings.BASE_DIR / "conf" / "adcm"


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
