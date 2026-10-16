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

from typing import Literal, NamedTuple, TypeAlias

from core.converters import named_mapping_from_topology
from core.legacy.bundle.types import BundleRestrictions, MappingRestrictions, ServiceDependencies
from core.legacy.cluster.types import ClusterTopology
from core.legacy.concern.checks import (
    cluster_has_required_services_issue,
    find_cluster_mapping_issues,
    find_unsatisfied_service_requirements,
)
from core.types import ClusterID
from django.db.models import Q
import core

from cm.converters import orm_object_to_core_descriptor
from cm.errors import AdcmEx
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.models import (
    Cluster,
    ClusterBind,
    Component,
    Host,
    PrototypeImport,
    Provider,
    Service,
)

ObjectWithConfig: TypeAlias = Cluster | Service | Component | Provider | Host
HasIssue: TypeAlias = bool
RequiresEntry: TypeAlias = dict[Literal["service", "component"], str]


class MissingRequirement(NamedTuple):
    type: Literal["service", "component"]
    name: str


def object_configuration_has_issue(target: ObjectWithConfig, config_service: core.config.ConfigService) -> HasIssue:
    descriptor = orm_object_to_core_descriptor(target)
    try:
        return config_service.inspect_has_invalid_configuration(owner=descriptor)
    except core.config.ObjectWithoutConfigError:
        return False


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


def object_has_required_services_issue_orm_version(cluster: Cluster) -> HasIssue:
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))
    existing_services = set(Service.objects.filter(cluster_id=cluster.pk).values_list("prototype__name", flat=True))

    return cluster_has_required_services_issue(
        bundle_restrictions=bundle_restrictions, existing_services=existing_services
    )


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
