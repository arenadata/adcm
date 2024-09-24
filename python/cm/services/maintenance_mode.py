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
from rest_framework.serializers import Serializer
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT

from cm.models import (
    Action,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    Service,
    ServiceComponent,
)
from cm.services.job.action import ActionRunPayload, run_action
from cm.services.status.notify import reset_objects_in_mm
from cm.status_api import send_object_update_event


def _change_mm_via_action(
    prototype: Prototype,
    action_name: str,
    obj: Host | Service | ServiceComponent,
    serializer: Serializer,
) -> Serializer:
    action = Action.objects.filter(prototype=prototype, name=action_name).first()
    if action:
        run_action(
            action=action,
            obj=obj,
            payload=ActionRunPayload(conf={}, attr={}, hostcomponent=[], verbose=False),
        )
        serializer.validated_data["maintenance_mode"] = MaintenanceMode.CHANGING

    return serializer


def get_maintenance_mode_response(
    obj: Host | Service | ServiceComponent,
    serializer: Serializer,
) -> Response:
    if obj.maintenance_mode_attr == MaintenanceMode.CHANGING:
        return Response(
            data={
                "code": "MAINTENANCE_MODE",
                "level": "error",
                "desc": "Maintenance mode is changing now",
            },
            status=HTTP_409_CONFLICT,
        )

    turn_on_action_name = settings.ADCM_TURN_ON_MM_ACTION_NAME
    turn_off_action_name = settings.ADCM_TURN_OFF_MM_ACTION_NAME
    prototype = obj.prototype

    if isinstance(obj, Host):
        obj_name = "host"
        turn_on_action_name = settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME
        turn_off_action_name = settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME

        if not obj.cluster:
            return Response(
                data={
                    "code": "MAINTENANCE_MODE_NOT_AVAILABLE",
                    "level": "error",
                    "desc": "Maintenance mode is not available",
                },
                status=HTTP_409_CONFLICT,
            )

        prototype = obj.cluster.prototype
    elif isinstance(obj, Service):
        obj_name = "service"
    elif isinstance(obj, ServiceComponent):
        obj_name = "component"
    else:
        obj_name = "obj"

    service_has_hc = None
    if obj_name == "service":
        service_has_hc = HostComponent.objects.filter(service=obj).exists()

    component_has_hc = None
    if obj_name == "component":
        component_has_hc = HostComponent.objects.filter(component=obj).exists()

    if obj.maintenance_mode_attr == MaintenanceMode.OFF:
        if serializer.validated_data["maintenance_mode"] == MaintenanceMode.OFF:
            return Response(
                data={
                    "code": "MAINTENANCE_MODE",
                    "level": "error",
                    "desc": "Maintenance mode already off",
                },
                status=HTTP_409_CONFLICT,
            )

        if obj_name == "host" or service_has_hc or component_has_hc:
            serializer = _change_mm_via_action(
                prototype=prototype,
                action_name=turn_on_action_name,
                obj=obj,
                serializer=serializer,
            )
        else:
            obj.maintenance_mode = MaintenanceMode.ON
            serializer.validated_data["maintenance_mode"] = MaintenanceMode.ON

        serializer.save()
        reset_objects_in_mm()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})

        return Response()

    if obj.maintenance_mode_attr == MaintenanceMode.ON:
        if serializer.validated_data["maintenance_mode"] == MaintenanceMode.ON:
            return Response(
                data={
                    "code": "MAINTENANCE_MODE",
                    "level": "error",
                    "desc": "Maintenance mode already on",
                },
                status=HTTP_409_CONFLICT,
            )

        if obj_name == "host" or service_has_hc or component_has_hc:
            serializer = _change_mm_via_action(
                prototype=prototype,
                action_name=turn_off_action_name,
                obj=obj,
                serializer=serializer,
            )
        else:
            obj.maintenance_mode = MaintenanceMode.OFF
            serializer.validated_data["maintenance_mode"] = MaintenanceMode.OFF

        serializer.save()
        reset_objects_in_mm()
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})

        return Response()

    return Response(
        data={"error": f'Unknown {obj_name} maintenance mode "{obj.maintenance_mode}"'},
        status=HTTP_400_BAD_REQUEST,
    )
