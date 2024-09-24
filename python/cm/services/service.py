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

from django.conf import settings
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from cm.api import cancel_locking_tasks, delete_service
from cm.errors import AdcmEx
from cm.models import Action, ClusterBind, HostComponent, JobStatus, Service, ServiceComponent, TaskLog
from cm.services.job.action import ActionRunPayload, run_action


def delete_service_from_api(service: Service) -> Response:
    delete_action = Action.objects.filter(
        prototype=service.prototype,
        name=settings.ADCM_DELETE_SERVICE_ACTION_NAME,
    ).first()
    host_components_exists = HostComponent.objects.filter(cluster=service.cluster, service=service).exists()

    if not delete_action:
        if service.state != "created":
            raise AdcmEx(code="SERVICE_DELETE_ERROR")

        if host_components_exists:
            raise AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{service.display_name}" has component(s) on host(s)')

    cluster = service.cluster

    if cluster.state == "upgrading" and service.prototype.name in cluster.before_upgrade.get("services", ()):
        raise AdcmEx(code="SERVICE_CONFLICT", msg="Can't remove service when upgrading cluster")

    if ClusterBind.objects.filter(source_service=service).exists():
        raise AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{service.display_name}" has exports(s)')

    if service.prototype.required:
        raise AdcmEx(code="SERVICE_CONFLICT", msg=f'Service "{service.display_name}" is required')

    if TaskLog.objects.filter(action=delete_action, status__in={JobStatus.CREATED, JobStatus.RUNNING}).exists():
        raise AdcmEx(code="SERVICE_DELETE_ERROR", msg="Service is deleting now")

    for component in ServiceComponent.objects.filter(cluster=service.cluster).exclude(service=service):
        if component.requires_service_name(service_name=service.name):
            raise AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f'Component "{component.name}" of service "{component.service.display_name}'
                f" requires this service or its component",
            )

    for another_service in Service.objects.filter(cluster=service.cluster):
        if another_service.requires_service_name(service_name=service.name):
            raise AdcmEx(
                code="SERVICE_CONFLICT",
                msg=f'Service "{another_service.display_name}" requires this service or its component',
            )

    cancel_locking_tasks(obj=service, obj_deletion=True)
    if delete_action and (host_components_exists or service.state != "created"):
        run_action(
            action=delete_action,
            obj=service,
            payload=ActionRunPayload(conf={}, attr={}, hostcomponent=[], verbose=False),
        )
    else:
        delete_service(service=service)

    return Response(status=HTTP_204_NO_CONTENT)
