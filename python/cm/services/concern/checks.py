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

from core.bundle.types import BundleRestrictions, MappingRestrictions, ServiceDependencies
from core.cluster.types import ClusterTopology
from core.concern.checks import find_cluster_mapping_issues, find_unsatisfied_service_requirements
from core.converters import named_mapping_from_topology
from core.types import ClusterID, ConfigID, ObjectID
from django.db.models import Q

from cm.errors import AdcmEx
from cm.models import (
    Cluster,
    ClusterBind,
    Component,
    Host,
    ObjectConfig,
    Prototype,
    PrototypeImport,
    Provider,
    Service,
)
from cm.services.bundle import retrieve_bundle_restrictions
from cm.services.cluster import retrieve_cluster_topology
from cm.services.config import retrieve_config_attr_pairs
from cm.services.config.spec import FlatSpec, retrieve_flat_spec_for_objects

ObjectWithConfig: TypeAlias = Cluster | Service | Component | Provider | Host
HasIssue: TypeAlias = bool
RequiresEntry: TypeAlias = dict[Literal["service", "component"], str]


class MissingRequirement(NamedTuple):
    type: Literal["service", "component"]
    name: str


def object_configuration_has_issue(target: ObjectWithConfig) -> HasIssue:
    config_spec = next(iter(retrieve_flat_spec_for_objects(prototypes=(target.prototype_id,)).values()), None)
    if not config_spec:
        return False

    return target.id in filter_objects_with_configuration_issues(config_spec, target)


def object_imports_has_issue(target: Cluster | Service) -> HasIssue:
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


def object_has_required_services_issue(cluster: Cluster) -> HasIssue:
    bundle_id = cluster.prototype.bundle_id

    required_protos = Prototype.objects.filter(bundle_id=bundle_id, type="service", required=True)

    if (required_count := required_protos.count()) == 0:
        return False

    existing_required_objects = Service.objects.filter(cluster=cluster, prototype__in=required_protos)
    return existing_required_objects.count() != required_count


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
                if not attr.get(group_name, {}).get("active", True):
                    continue

                if config[group_name][field_name] is None:
                    objects_with_issues.append(object_.id)
                    break

            elif config[field_name] is None:
                objects_with_issues.append(object_.id)
                break

    return objects_with_issues


def service_requirements_has_issue(service: Service) -> HasIssue:
    bundle_restrictions = retrieve_bundle_restrictions(service.prototype.bundle_id)
    service_name = service.prototype.name
    service_related_restrictions = {}
    for key, required_services in bundle_restrictions.service_requires.items():
        if key.service == service_name:
            service_related_restrictions[key] = required_services

    return bool(
        find_unsatisfied_service_requirements(
            services_restrictions=service_related_restrictions,
            named_mapping=named_mapping_from_topology(retrieve_cluster_topology(service.cluster_id)),
        )
    )


def check_service_requirements(
    services_restrictions: ServiceDependencies,
    topology: ClusterTopology,
):
    issues = find_unsatisfied_service_requirements(
        services_restrictions=services_restrictions, named_mapping=named_mapping_from_topology(topology)
    )
    if issues:
        issue_to_show = issues[0]
        raise AdcmEx(
            code="SERVICE_CONFLICT",
            msg=f'No required service "{issue_to_show.required_service}" for {issue_to_show.dependant_object}',
        )


def cluster_mapping_has_issue_orm_version(cluster: Cluster) -> HasIssue:
    """
    Checks:
      - requires (components only)
      - constraint
      - bound_to
    """

    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))

    return cluster_mapping_has_issue(cluster_id=cluster.id, bundle_restrictions=bundle_restrictions)


def cluster_mapping_has_issue(cluster_id: ClusterID, bundle_restrictions: BundleRestrictions) -> HasIssue:
    topology = retrieve_cluster_topology(cluster_id=cluster_id)

    issues = find_cluster_mapping_issues(
        restrictions=bundle_restrictions.mapping,
        named_mapping=named_mapping_from_topology(topology),
        amount_of_hosts_in_cluster=len(topology.hosts),
    )

    return len(issues) != 0


def check_mapping_restrictions(
    mapping_restrictions: MappingRestrictions,
    topology: ClusterTopology,
    *,
    error_message_template: str = "{}",
) -> None:
    issues = find_cluster_mapping_issues(
        restrictions=mapping_restrictions,
        named_mapping=named_mapping_from_topology(topology),
        amount_of_hosts_in_cluster=len(topology.hosts),
    )
    if issues:
        issue_to_show = issues[0]
        raise AdcmEx(code="COMPONENT_CONSTRAINT_ERROR", msg=error_message_template.format(issue_to_show.message))
