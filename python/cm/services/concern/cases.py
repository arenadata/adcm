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
from typing import Iterable

from core.types import ADCMCoreType, CoreObjectDescriptor
from django.contrib.contenttypes.models import ContentType

from cm.models import Cluster, ConcernCause, ConcernItem, ConcernType, Host, Service, ServiceComponent
from cm.services.concern import create_issue, delete_issue, retrieve_issue
from cm.services.concern.checks import (
    cluster_mapping_has_issue,
    object_configuration_has_issue,
    object_has_required_services_issue,
    object_imports_has_issue,
    service_requirements_has_issue,
)
from cm.services.concern.distribution import OwnObjectConcernMap


def recalculate_own_concerns_on_add_clusters(cluster: Cluster) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    cluster_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
        (ConcernCause.HOSTCOMPONENT, cluster_mapping_has_issue),
        (ConcernCause.SERVICE, object_has_required_services_issue),
    )

    cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)
    for cause, has_issue in cluster_checks:
        if has_issue(cluster):
            issue = create_issue(owner=cluster_cod, cause=cause)
            new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    return new_concerns


def recalculate_own_concerns_on_add_services(cluster: Cluster, services: Iterable[Service]) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))
    cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)

    # create new concerns
    cluster_own_hc_issue = retrieve_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
    if cluster_own_hc_issue is None and cluster_mapping_has_issue(cluster=cluster):
        issue = create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    service_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
        (ConcernCause.REQUIREMENT, service_requirements_has_issue),
    )
    for service in services:
        service_cod = CoreObjectDescriptor(id=service.id, type=ADCMCoreType.SERVICE)
        for concern_cause, has_issue in service_checks:
            if has_issue(service):
                issue = create_issue(owner=service_cod, cause=concern_cause)
                new_concerns[ADCMCoreType.SERVICE][service.pk].add(issue.pk)

    for component in ServiceComponent.objects.filter(service__in=services):
        if object_configuration_has_issue(component):
            issue = create_issue(
                owner=CoreObjectDescriptor(id=component.id, type=ADCMCoreType.COMPONENT), cause=ConcernCause.CONFIG
            )
            new_concerns[ADCMCoreType.COMPONENT][component.pk].add(issue.pk)

    # remove gone concerns
    if not object_has_required_services_issue(cluster=cluster):
        delete_issue(owner=CoreObjectDescriptor(type=ADCMCoreType.CLUSTER, id=cluster.pk), cause=ConcernCause.SERVICE)

    for service in cluster.services.exclude(pk__in=(service.pk for service in services)):
        if not service_requirements_has_issue(service=service):
            delete_issue(
                owner=CoreObjectDescriptor(type=ADCMCoreType.SERVICE, id=service.pk), cause=ConcernCause.REQUIREMENT
            )

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
        (ConcernCause.HOSTCOMPONENT, cluster_mapping_has_issue),
        (ConcernCause.SERVICE, object_has_required_services_issue),
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

    service_checks = (
        (ConcernCause.CONFIG, object_configuration_has_issue),
        (ConcernCause.IMPORT, object_imports_has_issue),
        (ConcernCause.REQUIREMENT, service_requirements_has_issue),
    )

    services = tuple(Service.objects.select_related("prototype").filter(cluster=cluster))
    existing_service_concern_causes = set(
        ConcernItem.objects.values_list("owner_id", "cause").filter(
            owner_id__in=map(attrgetter("id"), services),
            owner_type=ContentType.objects.get_for_model(Service),
            type=ConcernType.ISSUE,
            cause__in=map(itemgetter(0), service_checks),
        )
    )
    for service in services:
        service_cod = CoreObjectDescriptor(id=service.id, type=ADCMCoreType.SERVICE)
        for concern_cause, has_issue in service_checks:
            if (service.id, concern_cause) in existing_service_concern_causes:
                continue

            if has_issue(service):
                create_issue(owner=service_cod, cause=concern_cause)

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
