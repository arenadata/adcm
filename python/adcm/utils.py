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

from typing import Any, Iterable

from cm.adcm_config.ansible import ansible_decrypt
from cm.api import cancel_locking_tasks, delete_service, load_mm_objects
from cm.errors import AdcmEx
from cm.flag import update_flags
from cm.issue import update_hierarchy_issues, update_issue_after_deleting
from cm.job import ActionRunPayload, run_action
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    ClusterBind,
    ClusterObject,
    ConcernType,
    ConfigLog,
    Host,
    HostComponent,
    JobStatus,
    MaintenanceMode,
    Prototype,
    PrototypeConfig,
    ServiceComponent,
    TaskLog,
)
from cm.status_api import send_object_update_event
from django.conf import settings
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_409_CONFLICT,
)

OBJECT_TYPES_DICT = {
    "adcm": "adcm",
    "cluster": "cluster",
    "service": "clusterobject",
    "cluster object": "service",
    "component": "servicecomponent",
    "service component": "servicecomponent",
    "provider": "hostprovider",
    "host provider": "hostprovider",
    "host": "host",
}


def _change_mm_via_action(
    prototype: Prototype,
    action_name: str,
    obj: Host | ClusterObject | ServiceComponent,
    serializer: Serializer,
) -> Serializer:
    action = Action.objects.filter(prototype=prototype, name=action_name).first()
    if action:
        run_action(
            action=action,
            obj=obj,
            payload=ActionRunPayload(conf={}, attr={}, hostcomponent=[], verbose=False),
            hosts=[],
        )
        serializer.validated_data["maintenance_mode"] = MaintenanceMode.CHANGING

    return serializer


def _update_mm_hierarchy_issues(obj: Host | ClusterObject | ServiceComponent) -> None:
    if isinstance(obj, Host):
        update_hierarchy_issues(obj.provider)

    providers = {host_component.host.provider for host_component in HostComponent.objects.filter(cluster=obj.cluster)}
    for provider in providers:
        update_hierarchy_issues(provider)

    update_hierarchy_issues(obj.cluster)
    update_issue_after_deleting()
    update_flags()
    load_mm_objects()


def process_requires(
    proto: Prototype, comp_dict: dict, checked_object: list | None = None, adding_service: bool = False
) -> dict:
    if checked_object is None:
        checked_object = []
    checked_object.append(proto)

    for require in proto.requires:
        req_service = Prototype.obj.get(type="service", name=require["service"], bundle=proto.bundle)

        if req_service.name not in comp_dict:
            comp_dict[req_service.name] = {"components": {}, "service": req_service}

        req_comp = None
        if require.get("component"):
            req_comp = Prototype.obj.get(
                type="component",
                name=require["component"],
                parent=req_service,
            )
            comp_dict[req_service.name]["components"][req_comp.name] = req_comp

        if req_service.requires and req_service not in checked_object:
            process_requires(
                proto=req_service, comp_dict=comp_dict, checked_object=checked_object, adding_service=adding_service
            )

        if req_comp and req_comp.requires and req_comp not in checked_object and not adding_service:
            process_requires(proto=req_comp, comp_dict=comp_dict, checked_object=checked_object)

    return comp_dict


def get_obj_type(obj_type: str) -> str:
    object_names_to_object_types = {
        "adcm": "adcm",
        "cluster": "cluster",
        "cluster object": "service",
        "service component": "component",
        "host provider": "provider",
    }
    return object_names_to_object_types[obj_type]


def str_remove_non_alnum(value: str) -> str:
    result = "".join(ch.lower().replace(" ", "-") for ch in value if (ch.isalnum() or ch == " "))
    while result.find("--") != -1:
        result = result.replace("--", "-")
    return result


def get_oauth(oauth_key: str) -> tuple[str | None, str | None]:
    adcm = ADCM.objects.filter().first()
    if not adcm:
        return None, None

    config_log = ConfigLog.objects.get(obj_ref=adcm.config, id=adcm.config.current)
    if not config_log:
        return None, None

    if not config_log.config.get(oauth_key):
        return None, None

    if "client_id" not in config_log.config[oauth_key] or "secret" not in config_log.config[oauth_key]:
        return None, None

    secret = config_log.config[oauth_key]["secret"]
    if not secret:
        return None, None

    return (
        config_log.config[oauth_key]["client_id"],
        ansible_decrypt(secret),
    )


def get_yandex_oauth() -> tuple[str, str]:
    return get_oauth(oauth_key="yandex_oauth")


def get_google_oauth() -> tuple[str, str]:
    return get_oauth(oauth_key="google_oauth")


def has_yandex_oauth() -> bool:
    return all(get_yandex_oauth())


def has_google_oauth() -> bool:
    return all(get_google_oauth())


def get_requires(
    prototype: Prototype,
    adding_service: bool = False,
) -> list[dict[str, list[dict[str, Any]] | Any]] | None:
    if not prototype.requires:
        return None

    proto_dict = {}
    proto_dict = process_requires(proto=prototype, comp_dict=proto_dict, adding_service=adding_service)

    out = []

    for service_name, params in proto_dict.items():
        comp_out = []
        service = params["service"]
        for comp_name in params["components"]:
            comp = params["components"][comp_name]
            comp_out.append(
                {
                    "prototype_id": comp.id,
                    "name": comp_name,
                    "display_name": comp.display_name,
                },
            )

        out.append(
            {
                "prototype_id": service.id,
                "name": service_name,
                "display_name": service.display_name,
                "components": comp_out,
            },
        )

    return out


def get_maintenance_mode_response(
    obj: Host | ClusterObject | ServiceComponent,
    serializer: Serializer,
) -> Response:
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
    elif isinstance(obj, ClusterObject):
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

    if obj.maintenance_mode_attr == MaintenanceMode.CHANGING:
        return Response(
            data={
                "code": "MAINTENANCE_MODE",
                "level": "error",
                "desc": "Maintenance mode is changing now",
            },
            status=HTTP_409_CONFLICT,
        )

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
        _update_mm_hierarchy_issues(obj=obj)
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
        _update_mm_hierarchy_issues(obj=obj)
        send_object_update_event(object_=obj, changes={"maintenanceMode": obj.maintenance_mode})

        return Response()

    return Response(
        data={"error": f'Unknown {obj_name} maintenance mode "{obj.maintenance_mode}"'},
        status=HTTP_400_BAD_REQUEST,
    )


def delete_service_from_api(service: ClusterObject) -> Response:
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

    if cluster.state == "upgrading" and service.prototype.name in cluster.before_upgrade["services"]:
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

    for another_service in ClusterObject.objects.filter(cluster=service.cluster):
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
            hosts=[],
        )
    else:
        delete_service(service=service)

    return Response(status=HTTP_204_NO_CONTENT)


def filter_actions(obj: ADCMEntity, actions: Iterable[Action]):
    """Filter out actions that are not allowed to run on object at that moment"""
    if obj.concerns.filter(type=ConcernType.LOCK).exists():
        return []

    allowed = []
    for action in actions:
        if action.allowed(obj):
            allowed.append(action)
            action.config = PrototypeConfig.objects.filter(prototype=action.prototype, action=action).order_by("id")

    return allowed
