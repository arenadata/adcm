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

from core.types import ADCMCoreType, CoreObjectDescriptor
from django.db.models import QuerySet

from cm.issue import (
    check_hc,
    check_required_import,
    check_required_services,
    check_requires,
    create_issue,
)
from cm.models import Cluster, ClusterObject, ConcernCause, ServiceComponent
from cm.services.concern import delete_issue
from cm.services.concern.checks import object_configuration_has_issue
from cm.services.concern.distribution import OwnObjectConcernMap


def recalculate_own_concerns_on_add_clusters(cluster: Cluster) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    cluster_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, check_required_import),
        (ConcernCause.HOSTCOMPONENT, check_hc),
        (ConcernCause.SERVICE, check_required_services),
    )

    for cause, check in cluster_checks:
        if not check(cluster):
            issue = create_issue(obj=cluster, issue_cause=cause)
            new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    return new_concerns


def recalculate_own_concerns_on_add_services(
    cluster: Cluster, services: QuerySet[ClusterObject]
) -> OwnObjectConcernMap:
    new_concerns: OwnObjectConcernMap = defaultdict(lambda: defaultdict(set))

    # create new concerns
    if not check_hc(cluster=cluster) and cluster.get_own_issue(cause=ConcernCause.HOSTCOMPONENT) is None:
        issue = create_issue(obj=cluster, issue_cause=ConcernCause.HOSTCOMPONENT)
        new_concerns[ADCMCoreType.CLUSTER][cluster.pk].add(issue.pk)

    service_checks = (
        (ConcernCause.CONFIG, lambda obj: not object_configuration_has_issue(obj)),
        (ConcernCause.IMPORT, check_required_import),
        (ConcernCause.REQUIREMENT, check_requires),
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
    if check_required_services(cluster=cluster):
        delete_issue(owner=CoreObjectDescriptor(type=ADCMCoreType.CLUSTER, id=cluster.pk), cause=ConcernCause.SERVICE)

    for service in cluster.clusterobject_set.exclude(pk__in=(service.pk for service in services)):
        if check_requires(service=service):
            delete_issue(
                owner=CoreObjectDescriptor(type=ADCMCoreType.SERVICE, id=service.pk), cause=ConcernCause.REQUIREMENT
            )

    return new_concerns
