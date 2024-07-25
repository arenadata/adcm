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
from operator import attrgetter
from typing import Iterable, Literal, NamedTuple, TypeAlias

from core.types import ClusterID, ConfigID, ObjectID
from django.db.models import Q

from cm.models import (
    Cluster,
    ClusterBind,
    ClusterObject,
    Host,
    HostProvider,
    ObjectConfig,
    PrototypeImport,
    ServiceComponent,
)
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects

ObjectWithConfig: TypeAlias = Cluster | ClusterObject | ServiceComponent | HostProvider | Host
HasIssue: TypeAlias = bool


class MissingRequirement(NamedTuple):
    type: Literal["service", "component"]
    name: str


def object_configuration_has_issue(target: ObjectWithConfig) -> HasIssue:
    config_spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(target.prototype_id,)).values()), None)
    if not config_spec:
        return False

    return target.id in filter_objects_with_configuration_issues(config_spec, target)


def object_imports_has_issue(target: Cluster | ClusterObject) -> HasIssue:
    prototype_id = target.prototype_id
    prototype_imports = PrototypeImport.objects.filter(prototype_id=prototype_id)
    required_import_names = set(prototype_imports.values_list("name", flat=True).filter(required=True))

    if not required_import_names:
        return False

    if not any(prototype_imports.values_list("required", flat=True)):
        return False

    for cluster_name, service_name in ClusterBind.objects.values_list(
        "source_cluster__prototype__name", "source_service__prototype__name"
    ).filter(Q(cluster__prototype_id=prototype_id) | Q(service__prototype_id=prototype_id)):
        if service_name:
            required_import_names -= {service_name}
        elif cluster_name:
            required_import_names -= {cluster_name}

    return required_import_names != set()


def filter_objects_with_configuration_issues(config_spec: FlatSpec, *objects: ObjectWithConfig) -> Iterable[ObjectID]:
    required_fields = tuple(name for name, spec in config_spec.items() if spec.required and spec.type != "group")
    if not required_fields:
        return ()

    object_config_log_map: dict[int, ConfigID] = dict(
        ObjectConfig.objects.values_list("id", "current").filter(id__in=map(attrgetter("config_id"), objects))
    )
    config_pairs = retrieve_config_attr_pairs(configurations=object_config_log_map.values())

    objects_with_issues: deque[ObjectID] = deque()
    for object_ in objects:
        config, attr = config_pairs[object_config_log_map[object_.config_id]]

        for composite_name in required_fields:
            group_name, field_name, *_ = composite_name.split("/")
            if not field_name:
                field_name = group_name
                group_name = None

            if group_name:
                if not attr.get(group_name, {}).get("active", False):
                    continue

                if config[group_name][field_name] is None:
                    objects_with_issues.append(object_.id)
                    break

            elif config[field_name] is None:
                objects_with_issues.append(object_.id)
                break

    return objects_with_issues


def service_requirements_has_issue(service: ClusterObject) -> HasIssue:
    return bool(find_unsatisfied_requirements(cluster_id=service.cluster_id, requires=service.prototype.requires))


def find_unsatisfied_requirements(
    cluster_id: ClusterID, requires: list[dict[Literal["service", "component"], str]]
) -> tuple[MissingRequirement, ...]:
    if not requires:
        return ()

    names_of_required_services: set[str] = set()
    required_components: set[tuple[str, str]] = set()

    for requirement in requires:
        service_name = requirement["service"]

        if component_name := requirement.get("component"):
            required_components.add((service_name, component_name))
        else:
            names_of_required_services.add(service_name)

    missing_requirements = deque()

    if names_of_required_services:
        for missing_service_name in names_of_required_services.difference(
            ClusterObject.objects.values_list("prototype__name", flat=True).filter(cluster_id=cluster_id)
        ):
            missing_requirements.append(MissingRequirement(type="service", name=missing_service_name))

    if required_components:
        for _, missing_component_name in required_components.difference(
            ServiceComponent.objects.values_list("service__prototype__name", "prototype__name").filter(
                cluster_id=cluster_id
            )
        ):
            missing_requirements.append(MissingRequirement(type="component", name=missing_component_name))

    return tuple(missing_requirements)
