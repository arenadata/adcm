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
from operator import attrgetter, itemgetter
from typing import Generator, Iterable

from core.concern.checks import cluster_has_required_services_issue, find_unsatisfied_service_requirements
from core.converters import named_mapping_from_topology
from core.types import ADCMCoreType, Concern, ConcernID, CoreObjectDescriptor, ServiceID, ServiceName
from django.contrib.contenttypes.models import ContentType

from cm.models import Cluster, ClusterObject, ConcernCause, ConcernItem, ConcernType, Host, ServiceComponent
from cm.services.bundle import retrieve_bundle_restrictions
from cm.services.cluster import retrieve_cluster_topology
from cm.services.concern import create_issue, retrieve_issue, retrieve_related_concerns
from cm.services.concern.checks import (
    cluster_mapping_has_issue,
    object_configuration_has_issue,
    object_imports_has_issue,
)
from cm.services.concern.distribution import OwnObjectConcernMap


def recalculate_own_concerns_on_add_clusters(cluster: Cluster) -> OwnObjectConcernMap:
    named_mapping = named_mapping_from_topology(topology=retrieve_cluster_topology(cluster_id=cluster.pk))
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))

    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    cluster_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
    )

    cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)
    for cause, has_issue in cluster_checks:
        if has_issue(cluster):
            issue = create_issue(owner=cluster_cod, cause=cause)
            new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    if cluster_has_required_services_issue(bundle_restrictions=bundle_restrictions, existing_services=named_mapping):
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(
            create_issue(owner=cluster_cod, cause=ConcernCause.SERVICE).pk
        )
    if cluster_mapping_has_issue(cluster_id=cluster.pk, bundle_restrictions=bundle_restrictions):
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(
            create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT).pk
        )

    return new_concerns


def _filter_concerns_by_cause(concerns: Iterable[Concern], cause: str) -> Generator[Concern, None, None]:
    return (concern for concern in concerns if concern.cause == cause)


def recalculate_own_concerns_on_add_services(
    cluster: Cluster, services: Iterable[ClusterObject]
) -> OwnObjectConcernMap:
    named_mapping = named_mapping_from_topology(topology=retrieve_cluster_topology(cluster_id=cluster.pk))
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))

    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))
    cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)

    # create new concerns
    cluster_own_hc_issue = retrieve_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
    if cluster_own_hc_issue is None and cluster_mapping_has_issue(
        bundle_restrictions=bundle_restrictions, cluster_id=cluster.pk
    ):
        issue = create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    service_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
    )
    for service in services:
        service_cod = CoreObjectDescriptor(id=service.id, type=ADCMCoreType.SERVICE)
        for concern_cause, has_issue in service_checks:
            if has_issue(service):
                issue = create_issue(owner=service_cod, cause=concern_cause)
                new_concerns[ADCMCoreType.SERVICE][service.pk].add(issue.pk)

        if find_unsatisfied_service_requirements(
            services_restrictions={
                k: v for k, v in bundle_restrictions.service_requires.items() if k.service == service.prototype.name
            },
            named_mapping=named_mapping,
        ):
            new_concerns[ADCMCoreType.SERVICE][service.pk].add(
                create_issue(owner=service_cod, cause=ConcernCause.REQUIREMENT).pk
            )

    for component in ServiceComponent.objects.filter(service__in=services):
        if object_configuration_has_issue(component):
            issue = create_issue(
                owner=CoreObjectDescriptor(id=component.id, type=ADCMCoreType.COMPONENT), cause=ConcernCause.CONFIG
            )
            new_concerns[ADCMCoreType.COMPONENT][component.pk].add(issue.pk)

    # remove gone concerns, which can be:
    #   1) ConcernCause.SERVICE of cluster
    #   2) ConcernCause.REQUIREMENT of already existing services (not added just now)
    existing_services_except_new: dict[ServiceName, ServiceID] = dict(
        cluster.clusterobject_set.exclude(pk__in=(service.pk for service in services)).values_list(
            "prototype__name", "pk"
        )
    )
    cluster_cod = CoreObjectDescriptor(id=cluster.pk, type=ADCMCoreType.CLUSTER)
    service_cods = [
        CoreObjectDescriptor(id=id_, type=ADCMCoreType.SERVICE) for id_ in existing_services_except_new.values()
    ]
    concerns_map = retrieve_related_concerns(objects=[cluster_cod, *service_cods], concern_type=ConcernType.ISSUE)

    required_service_issues: set[int] = {
        concern.id
        for concern in _filter_concerns_by_cause(concerns=concerns_map.get(cluster_cod, []), cause=ConcernCause.SERVICE)
    }
    if required_service_issues and not cluster_has_required_services_issue(
        bundle_restrictions=bundle_restrictions, existing_services=named_mapping
    ):
        ConcernItem.objects.filter(pk__in=required_service_issues).delete()

    unsatisfied_requirements_names = (
        req.dependant_object.service
        for req in find_unsatisfied_service_requirements(
            services_restrictions=bundle_restrictions.service_requires, named_mapping=named_mapping
        )
        if req.dependant_object.service in existing_services_except_new
    )
    existing_services_except_new_with_satisfied_requirements: set[ServiceID] = {
        service_id
        for service_name, service_id in existing_services_except_new.items()
        if service_name not in unsatisfied_requirements_names
    }

    services_concerns: dict[CoreObjectDescriptor, set[Concern]] = defaultdict(set)
    for service_cod in service_cods:
        if concerns := set(
            _filter_concerns_by_cause(concerns=concerns_map.get(service_cod, []), cause=ConcernCause.REQUIREMENT)
        ):
            services_concerns[service_cod].update(concerns)

    outdated_service_concerns: set[ConcernID] = set()
    for owner_cod, concerns in services_concerns.items():
        if owner_cod.id not in existing_services_except_new_with_satisfied_requirements:
            continue
        outdated_service_concerns.update(concern.id for concern in concerns)

    ConcernItem.objects.filter(pk__in=outdated_service_concerns).delete()

    return new_concerns


def recalculate_own_concerns_on_add_hosts(host: Host) -> OwnObjectConcernMap:
    if object_configuration_has_issue(host):
        issue = create_issue(owner=CoreObjectDescriptor(id=host.id, type=ADCMCoreType.HOST), cause=ConcernCause.CONFIG)
        return {ADCMCoreType.HOST: {host.id: {issue.id}}}

    return {}


def recalculate_concerns_on_cluster_upgrade(cluster: Cluster) -> None:
    cluster_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
    )

    existing_cluster_concern_causes = set(
        ConcernItem.objects.values_list("cause", flat=True).filter(
            owner_id=cluster.id,
            owner_type=ContentType.objects.get_for_model(Cluster),
            type=ConcernType.ISSUE,
            cause__in=map(itemgetter(0), cluster_checks),
        )
    )

    cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)
    for cause, has_issue in cluster_checks:
        if cause in existing_cluster_concern_causes:
            continue

        if has_issue(cluster):
            create_issue(owner=cluster_cod, cause=cause)

    named_mapping = named_mapping_from_topology(topology=retrieve_cluster_topology(cluster_id=cluster.pk))
    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=int(cluster.prototype.bundle_id))

    if ConcernCause.SERVICE not in existing_cluster_concern_causes and cluster_has_required_services_issue(
        bundle_restrictions=bundle_restrictions, existing_services=named_mapping
    ):
        create_issue(owner=cluster_cod, cause=ConcernCause.SERVICE)
    if ConcernCause.HOSTCOMPONENT not in existing_cluster_concern_causes and cluster_mapping_has_issue(
        cluster_id=cluster.pk, bundle_restrictions=bundle_restrictions
    ):
        create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)

    service_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
    )

    services = tuple(ClusterObject.objects.select_related("prototype").filter(cluster=cluster))
    existing_service_concern_causes = set(
        ConcernItem.objects.values_list("owner_id", "cause").filter(
            owner_id__in=map(attrgetter("id"), services),
            owner_type=ContentType.objects.get_for_model(ClusterObject),
            type=ConcernType.ISSUE,
            cause__in=map(itemgetter(0), service_checks),
        )
    )
    services_with_unsatisfied_requirements: set[ServiceName] = {
        req.dependant_object.service
        for req in find_unsatisfied_service_requirements(
            services_restrictions=bundle_restrictions.service_requires, named_mapping=named_mapping
        )
    }
    for service in services:
        service_cod = CoreObjectDescriptor(id=service.id, type=ADCMCoreType.SERVICE)
        for concern_cause, has_issue in service_checks:
            if (service.id, concern_cause) in existing_service_concern_causes:
                continue

            if has_issue(service):
                create_issue(owner=service_cod, cause=concern_cause)

        if (
            service.pk,
            ConcernCause.REQUIREMENT,
        ) not in existing_service_concern_causes and service.prototype.name in services_with_unsatisfied_requirements:
            create_issue(owner=service_cod, cause=ConcernCause.REQUIREMENT)

    components_with_config_concerns = set(
        ConcernItem.objects.values_list("owner_id", flat=True).filter(
            owner_id__in=ServiceComponent.objects.values_list("id", flat=True).filter(service__in=services),
            owner_type=ContentType.objects.get_for_model(ServiceComponent),
            type=ConcernType.ISSUE,
            cause=ConcernCause.CONFIG,
        )
    )
    for component in (
        ServiceComponent.objects.select_related("prototype")
        .filter(service__in=services)
        .exclude(id__in=components_with_config_concerns)
    ):
        if object_configuration_has_issue(component):
            create_issue(
                owner=CoreObjectDescriptor(id=component.id, type=ADCMCoreType.COMPONENT), cause=ConcernCause.CONFIG
            )
