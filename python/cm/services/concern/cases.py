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

from cm.issue import check_hc, check_required_services, create_issue
from cm.models import Cluster, ClusterObject, ConcernCause, ConcernItem, ConcernType, Host, ServiceComponent
from cm.services.concern import delete_issue
from cm.services.concern.checks import (
    object_configuration_has_issue,
    object_has_required_services_issue,
    object_imports_has_issue,
    service_requirements_has_issue,
)
from cm.services.concern.distribution import OwnObjectConcernMap


def recalculate_own_concerns_on_add_clusters(cluster: Cluster) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    cluster_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, lambda obj: not object_imports_has_issue(obj)),
        (ConcernCause.HOSTCOMPONENT, check_hc),
        (ConcernCause.SERVICE, lambda obj: not object_has_required_services_issue(obj)),
    )

    for cause, check in cluster_checks:
        if not check(cluster):
            issue = create_issue(obj=cluster, issue_cause=cause)
            new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    return new_concerns


def recalculate_own_concerns_on_add_services(
    cluster: Cluster, services: Iterable[ClusterObject]
) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    # create new concerns
    if not check_hc(cluster=cluster) and cluster.get_own_issue(cause=ConcernCause.HOSTCOMPONENT) is None:
        issue = create_issue(obj=cluster, issue_cause=ConcernCause.HOSTCOMPONENT)
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    service_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, lambda obj: not object_imports_has_issue(obj)),
        (ConcernCause.REQUIREMENT, lambda obj: not service_requirements_has_issue(obj)),
    )
    for service in services:
        for concern_cause, func in service_checks:
            if not func(service):
                issue = create_issue(obj=service, issue_cause=concern_cause)
                new_concerns[ADCMCoreType.SERVICE][service.pk].add(issue.pk)

    for component in ServiceComponent.objects.filter(service__in=services):
        if object_configuration_has_issue(component):
            issue = create_issue(obj=component, issue_cause=ConcernCause.CONFIG)
            new_concerns[ADCMCoreType.COMPONENT][component.pk].add(issue.pk)

    # remove gone concerns
    if not object_has_required_services_issue(cluster=cluster):
        delete_issue(owner=CoreObjectDescriptor(type=ADCMCoreType.CLUSTER, id=cluster.pk), cause=ConcernCause.SERVICE)

    for service in cluster.clusterobject_set.exclude(pk__in=(service.pk for service in services)):
        if not service_requirements_has_issue(service=service):
            delete_issue(
                owner=CoreObjectDescriptor(type=ADCMCoreType.SERVICE, id=service.pk), cause=ConcernCause.REQUIREMENT
            )

    return new_concerns


def recalculate_own_concerns_on_add_hosts(host: Host) -> OwnObjectConcernMap:
    if object_configuration_has_issue(host):
        issue = create_issue(obj=host, issue_cause=ConcernCause.CONFIG)
        return {ADCMCoreType.HOST: {host.id: issue.id}}

    return {}


def recalculate_concerns_on_cluster_upgrade(cluster: Cluster) -> None:
    cluster_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, lambda obj: not object_imports_has_issue(obj)),
        (ConcernCause.HOSTCOMPONENT, check_hc),
        (ConcernCause.SERVICE, check_required_services),
    )

    existing_cluster_concern_causes = set(
        ConcernItem.objects.values_list("cause", flat=True).filter(
            owner_id=cluster.id,
            owner_type=ContentType.objects.get_for_model(Cluster),
            type=ConcernType.ISSUE,
            cause__in=map(itemgetter(0), cluster_checks),
        )
    )

    for cause, check in cluster_checks:
        if cause in existing_cluster_concern_causes:
            continue

        if not check(cluster):
            create_issue(obj=cluster, issue_cause=cause)

    service_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, lambda obj: not object_imports_has_issue(obj)),
        (ConcernCause.REQUIREMENT, lambda obj: not service_requirements_has_issue(obj)),
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
    for service in services:
        for concern_cause, func in service_checks:
            if (service.id, concern_cause) in existing_service_concern_causes:
                continue

            if not func(service):
                create_issue(obj=service, issue_cause=concern_cause)

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
            create_issue(obj=component, issue_cause=ConcernCause.CONFIG)
