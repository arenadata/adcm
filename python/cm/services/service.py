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

from itertools import chain

from core.cluster.types import ClusterTopology
from core.concern.checks import find_not_added_required_services, find_unsatisfied_service_requirements
from core.converters import named_mapping_from_topology
from core.types import ComponentNameKey, ServiceID, ServiceNameKey
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from cm.api import cancel_locking_tasks, delete_service
from cm.errors import AdcmEx
from cm.models import Action, ClusterBind, JobStatus, Service, TaskLog
from cm.services.bundle import retrieve_bundle_restrictions
from cm.services.cluster import retrieve_cluster_topology
from cm.services.job.action import ActionRunPayload, run_action


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
        owner_id=service_id,
        owner_type=ContentType.objects.get_for_model(Service),
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


def delete_service_from_api(service: Service) -> Response:
    delete_action = Action.objects.filter(
        prototype_id=service.prototype_id,
        name=settings.ADCM_DELETE_SERVICE_ACTION_NAME,
    ).first()
    topology_without_service = retrieve_cluster_topology(service.cluster_id)
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
        run_action(
            action=delete_action,
            obj=service,
            payload=ActionRunPayload(conf={}, attr={}, hostcomponent=set(), verbose=False),
        )
    else:
        delete_service(service=service)

    return Response(status=HTTP_204_NO_CONTENT)
