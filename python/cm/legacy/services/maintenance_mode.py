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

from core.types import (
    ADCMCoreType,
    MMReason,
    ObjectMaintenanceModeState,
)
from django.conf import settings
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_409_CONFLICT
from use_cases.dto import RunActionDTO
from use_cases.transition.job.schedule import ScheduleMMChangingTask

from cm.converters import orm_object_to_core_type
from cm.legacy.services.status.notify import reset_objects_in_mm
from cm.legacy.status_api import send_object_update_event
from cm.models import (
    Action,
    Component,
    Host,
    HostComponent,
    MaintenanceMode,
    Prototype,
    Service,
)


def _change_mm_via_action(
    prototype: Prototype,
    action_name: str,
    obj: Host | Service | Component,
    serializer: Serializer,
    schedule_task: ScheduleMMChangingTask,
) -> Serializer:
    action = Action.objects.filter(prototype=prototype, name=action_name).first()
    if action:
        schedule_task.do(action_orm=action, target=obj, payload=RunActionDTO())

        serializer.validated_data["maintenance_mode"] = MaintenanceMode.CHANGING

    return serializer


def get_maintenance_mode_response(
    obj: Host | Service | Component,
    own_mm: ObjectMaintenanceModeState,
    calculated_mm: tuple[ObjectMaintenanceModeState, MMReason],
    serializer: Serializer,
    schedule_task: ScheduleMMChangingTask,
) -> Response:
    if own_mm == ObjectMaintenanceModeState.CHANGING:
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
    elif isinstance(obj, Component):
        obj_name = "component"
    else:
        raise NotImplementedError(f"Unexpected object: {obj}")

    service_has_hc = None
    if obj_name == "service":
        service_has_hc = HostComponent.objects.filter(service=obj).exists()

    component_has_hc = None
    if obj_name == "component":
        component_has_hc = HostComponent.objects.filter(component=obj).exists()

    calculated_mm, mm_reason = calculated_mm
    object_type = orm_object_to_core_type(obj)
    if own_mm == ObjectMaintenanceModeState.OFF:
        if serializer.validated_data["maintenance_mode"] == MaintenanceMode.OFF:
            error_desc = _build_disable_mm_error_response_description(reason=mm_reason, object_type=object_type)
            return Response(
                data={
                    "code": "MAINTENANCE_MODE",
                    "level": "error",
                    "desc": error_desc,
                },
                status=HTTP_409_CONFLICT,
            )

        if obj_name == "host" or service_has_hc or component_has_hc:
            serializer = _change_mm_via_action(
                prototype=prototype,
                action_name=turn_on_action_name,
                obj=obj,
                serializer=serializer,
                schedule_task=schedule_task,
            )
        else:
            obj.maintenance_mode = MaintenanceMode.ON
            serializer.validated_data["maintenance_mode"] = MaintenanceMode.ON

        serializer.save()
        reset_objects_in_mm()
        send_object_update_event(
            obj_id=obj.pk,
            obj_type=orm_object_to_core_type(obj).value,
            changes={"maintenanceMode": obj.maintenance_mode},
        )

        return Response()

    if own_mm == ObjectMaintenanceModeState.ON:
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
                schedule_task=schedule_task,
            )
        else:
            obj.maintenance_mode = MaintenanceMode.OFF
            serializer.validated_data["maintenance_mode"] = MaintenanceMode.OFF

        serializer.save()
        reset_objects_in_mm()
        send_object_update_event(
            obj_id=obj.pk,
            obj_type=orm_object_to_core_type(obj).value,
            changes={"maintenanceMode": obj.maintenance_mode},
        )

        return Response()

    return Response(
        data={"error": f'Unknown {obj_name} maintenance mode "{obj.maintenance_mode}"'},
        status=HTTP_400_BAD_REQUEST,
    )


def _build_disable_mm_error_response_description(reason: MMReason, object_type: ADCMCoreType) -> str:
    template = (
        "The {object_type} is in maintenance mode because {mm_source} in maintenance mode. "
        "To turn it off, disable maintenance mode on related {mm_source_type}."
    )

    match reason:
        case MMReason.ALL_HOSTS_IN_MM if object_type in {ADCMCoreType.SERVICE, ADCMCoreType.COMPONENT}:
            mm_source = "the hosts where it is installed are"
            mm_source_type = "hosts"
        case MMReason.ALL_COMPONENTS_IN_MM if object_type == ADCMCoreType.SERVICE:
            mm_source = "all it's components are"
            mm_source_type = "components"
        case MMReason.SERVICE_IN_MM if object_type == ADCMCoreType.COMPONENT:
            mm_source = "it's service is"
            mm_source_type = "service"
        case MMReason.SELF:
            return "Maintenance mode already off."
        case _:
            raise NotImplementedError(f"Unknown {reason=} for {object_type=}")

    return template.format(object_type=object_type.value, mm_source=mm_source, mm_source_type=mm_source_type)
