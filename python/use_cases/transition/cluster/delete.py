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
from dataclasses import dataclass
from functools import partial
from itertools import chain

from cm.errors import AdcmEx
from cm.legacy.api import cancel_locking_tasks
from cm.legacy.services.bundle import retrieve_bundle_restrictions
from cm.legacy.services.cluster import retrieve_cluster_topology
from cm.legacy.services.concern import create_issue, delete_concerns_of_removed_objects, delete_issue, retrieve_issue
from cm.legacy.services.concern.checks import (
    cluster_mapping_has_issue_orm_version,
)
from cm.legacy.services.concern.distribution import (
    distribute_concern_on_related_objects,
)
from cm.legacy.services.status.notify import reset_hc_map
from cm.legacy.status_api import (
    notify_about_new_concern,
    send_delete_service_event,
)
from cm.logger import logger
from cm.models import (
    Action,
    ClusterBind,
    Component,
    ConcernCause,
    JobStatus,
    Service,
    TaskLog,
)
from core.converters import named_mapping_from_topology
from core.legacy.cluster.types import ClusterTopology
from core.legacy.concern.checks import find_not_added_required_services, find_unsatisfied_service_requirements
from core.types import ADCMCoreType, ComponentNameKey, CoreObjectDescriptor, ServiceID, ServiceNameKey
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.db.transaction import atomic, on_commit
from rbac.models import re_apply_object_policy
import core

from use_cases.dto import RunActionDTO
from use_cases.transition.job.schedule import ScheduleTask


@dataclass(slots=True)
class DeleteService:
    # copied from cm.legacy.api.delete_service

    def do(self, service: Service) -> None:
        service_pk = service.pk

        delete_concerns_of_removed_objects(
            objects={
                ADCMCoreType.SERVICE: (service_pk,),
                ADCMCoreType.COMPONENT: tuple(
                    Component.objects.values_list("id", flat=True).filter(service_id=service_pk)
                ),
            }
        )

        service.delete()

        cluster = service.cluster
        cluster_cod = CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER)
        concern_id = None
        related_objects = {}
        if not cluster_mapping_has_issue_orm_version(cluster=cluster):
            delete_issue(
                owner=CoreObjectDescriptor(id=cluster.id, type=ADCMCoreType.CLUSTER), cause=ConcernCause.HOSTCOMPONENT
            )
        elif retrieve_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT) is None:
            concern = create_issue(owner=cluster_cod, cause=ConcernCause.HOSTCOMPONENT)
            concern_id = concern.pk
            related_objects = distribute_concern_on_related_objects(owner=cluster_cod, concern_id=concern_id)

        keep_objects = defaultdict(set)
        for task in TaskLog.objects.filter(
            object_type=ContentType.objects.get_for_model(Service), object_id=service_pk
        ).prefetch_related("joblog_set", "joblog_set__logstorage_set"):
            keep_objects[task.__class__].add(task.pk)
            for job in task.joblog_set.all():  # pyright: ignore[reportAttributeAccessIssue]
                keep_objects[job.__class__].add(job.pk)
                for log in job.logstorage_set.all():
                    keep_objects[log.__class__].add(log.pk)

        re_apply_object_policy(apply_object=cluster, keep_objects=keep_objects)

        reset_hc_map()
        on_commit(func=partial(send_delete_service_event, service_id=service_pk))
        if concern_id:
            on_commit(func=partial(notify_about_new_concern, concern_id=concern_id, related_objects=related_objects))
        logger.info("service #%s is deleted", service_pk)


@dataclass(slots=True)
class DeleteServiceFromAPI:
    # moved from cm.legacy.services.service without major changes

    delete_service: DeleteService
    schedule_task: ScheduleTask

    @atomic
    def do(self, service: Service) -> None:
        # comment below was copied too
        #
        # Technical debt:
        #   in some cases service deletion comes with updating hc mapping (ansible plugin adcm_delete_service)
        #   Here we rely only on CASCADE deletion of HostComponent entries (if not deleting by action)

        delete_action = Action.objects.filter(
            prototype_id=service.prototype_id,  # pyright: ignore[reportAttributeAccessIssue]
            name=core.bundle.constants.ADCM_DELETE_SERVICE_ACTION_NAME,
        ).first()

        topology_without_service = retrieve_cluster_topology(service.cluster_id)  # pyright: ignore[reportAttributeAccessIssue]

        service_topology = topology_without_service.services.pop(service.pk)
        related_mapping_exists = any(
            chain.from_iterable(
                component_topology.hosts.keys() for component_topology in service_topology.components.values()
            )
        )

        if error := _get_error_on_service_deletion(
            service_id=service.pk,
            cluster_topology=topology_without_service,
            delete_action_exists=delete_action is not None,
            related_mapping_exists=related_mapping_exists,
        ):
            raise error

        cancel_locking_tasks(obj=service, obj_deletion=True)

        if delete_action and (related_mapping_exists or service.state != "created"):
            self.schedule_task.do(action_orm=delete_action, target=service, payload=RunActionDTO())
            return

        self.delete_service.do(service)


def _get_error_on_service_deletion(
    service_id: ServiceID, cluster_topology: ClusterTopology, delete_action_exists: bool, related_mapping_exists: bool
) -> AdcmEx | None:
    service_data = Service.objects.values(
        "cluster_id",
        "prototype_id",
        "state",
        bundle_id=F("prototype__bundle_id"),
        name=F("prototype__name"),
        display_name=F("prototype__display_name"),
        cluster_state=F("cluster__state"),
        cluster_before_upgrade=F("cluster__before_upgrade"),
    ).get(pk=service_id)

    display_name = service_data["display_name"]

    if not delete_action_exists:
        if service_data["state"] != "created":
            return AdcmEx(code="SERVICE_DELETE_ERROR")

        if related_mapping_exists:
            return AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{display_name}" has component(s) on host(s)')

    if service_data["cluster_state"] == "upgrading" and service_data["name"] in service_data[
        "cluster_before_upgrade"
    ].get("services", ()):
        return AdcmEx(code="SERVICE_CONFLICT", msg="Can't remove service when upgrading cluster")

    if ClusterBind.objects.filter(source_service_id=service_id).exists():
        return AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{display_name}" has exports(s)')

    bundle_restrictions = retrieve_bundle_restrictions(bundle_id=service_data["bundle_id"])
    if service_data["name"] in find_not_added_required_services(
        bundle_restrictions=bundle_restrictions,
        existing_services={service.info.name for service in cluster_topology.services.values()},
    ):
        return AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{display_name}" is required')

    if TaskLog.objects.filter(
        object_id=service_id,
        object_type=ContentType.objects.get_for_model(Service),
        action__name=settings.ADCM_DELETE_SERVICE_ACTION_NAME,
        status__in={JobStatus.CREATED, JobStatus.RUNNING},
    ).exists():
        return AdcmEx(code="SERVICE_DELETE_ERROR", msg="Service is deleting now")

    unsatisfied_service_requirements = find_unsatisfied_service_requirements(
        services_restrictions={
            # we can't delete service, that is specified in other existing service's or component's requires
            # merge requirements from services with requirements from components (mapping)
            **bundle_restrictions.service_requires,
            **bundle_restrictions.mapping.required_services,
            **{
                key: {v.service for v in value}
                for key, value in bundle_restrictions.mapping.required_components.items()
            },
        },
        named_mapping=named_mapping_from_topology(topology=cluster_topology),
    )
    for violation in unsatisfied_service_requirements:
        if service_data["name"] != violation.required_service:
            continue

        service_display_name = Service.objects.values_list("prototype__display_name", flat=True).get(
            cluster_id=service_data["cluster_id"], prototype__name=violation.dependant_object.service
        )

        if isinstance(violation.dependant_object, ServiceNameKey):
            error_msg = f'Service "{service_display_name}" requires this service or its component'
            return AdcmEx(code="SERVICE_CONFLICT", msg=error_msg)

        elif isinstance(violation.dependant_object, ComponentNameKey):
            error_msg = (
                f'Component "{violation.dependant_object.component}" of service '
                f'"{service_display_name} requires this service or its component'
            )
            return AdcmEx(code="SERVICE_CONFLICT", msg=error_msg)
