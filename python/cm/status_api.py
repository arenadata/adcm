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
from collections.abc import Iterable
from urllib.parse import urljoin
import json

from api_v2.concern.serializers import ConcernSerializer
from core.types import ADCMCoreType, ClusterID, ConcernID, CoreObjectDescriptor, ObjectID
from django.conf import settings
from djangorestframework_camel_case.util import camelize
from requests import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
import requests

from cm.converters import core_type_to_model
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Cluster,
    Component,
    ConcernItem,
    Host,
    HostComponent,
    Service,
)
from cm.services.concern.distribution import AffectedObjectConcernMap, ConcernRelatedObjects


class EventTypes:
    CREATE_CONCERN = "create_{}_concern"
    DELETE_CONCERN = "delete_{}_concern"
    DELETE_SERVICE = "delete_service"
    UPDATE_HOSTCOMPONENTMAP = "update_hostcomponentmap"
    CREATE_CONFIG = "create_{}_config"
    UPDATE = "update_{}"


def api_request(method: str, url: str, data: dict = None) -> Response | None:
    url = urljoin(settings.API_URL, url)
    kwargs = {
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Token {settings.ADCM_TOKEN}",
        },
        "timeout": settings.STATUS_REQUEST_TIMEOUT,
    }

    if data is not None:
        kwargs["data"] = json.dumps(data)

    try:
        response = requests.request(method, url, **kwargs)
        if response.status_code not in {HTTP_200_OK, HTTP_201_CREATED}:
            logger.error("%s %s error %d: %s", method, url, response.status_code, response.text)
        return response  # noqa: TRY300
    except requests.exceptions.Timeout:
        logger.error("%s request to %s timed out", method, url)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("%s request to %s connection failed", method, url)
        return None


def post_event(event: str, object_id: int | None, changes: dict | None = None) -> Response | None:
    if object_id is None:
        return None

    data = {
        "event": event,
        "object": {"id": object_id, **({"changes": changes} if changes else {})},
    }

    return api_request(method="post", url="event/", data=data)


def fix_object_type(type_: str) -> str:
    if type_ == "provider":
        return "hostprovider"

    return type_


def send_concern_creation_event(object_: ADCMEntity, concern: dict) -> None:
    post_event(
        event=EventTypes.CREATE_CONCERN.format(fix_object_type(type_=object_.prototype.type)),
        object_id=object_.pk,
        changes=concern,
    )


def send_concern_delete_event(object_id: int, object_type: str, concern_id: int) -> None:
    post_event(
        event=EventTypes.DELETE_CONCERN.format(fix_object_type(type_=object_type)),
        object_id=object_id,
        changes={"id": concern_id},
    )


def send_delete_service_event(service_id: int) -> Response | None:
    return post_event(
        event=EventTypes.DELETE_SERVICE,
        object_id=service_id,
    )


def send_host_component_map_update_event(cluster_id: ClusterID) -> None:
    post_event(event=EventTypes.UPDATE_HOSTCOMPONENTMAP, object_id=cluster_id)


def send_config_creation_event(object_: ADCMEntity) -> None:
    post_event(
        event=EventTypes.CREATE_CONFIG.format(fix_object_type(type_=object_.prototype.type)), object_id=object_.pk
    )


def send_update_event(object_: CoreObjectDescriptor, changes: dict) -> None:
    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(type_=object_.type.value)), object_id=object_.id, changes=changes
    )


def send_object_update_event(object_: ADCMEntity, changes: dict) -> None:
    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(type_=object_.prototype.type)),
        object_id=object_.pk,
        changes=changes,
    )


def send_task_status_update_event(task_id: int, status: str) -> None:
    post_event(event=EventTypes.UPDATE.format("task"), object_id=task_id, changes={"status": status})


def send_prototype_update_event(object_: CoreObjectDescriptor) -> None:
    # todo inplace request, no need in the whole object
    send_prototype_and_state_update_event(
        core_type_to_model(core_type=object_.type).objects.select_related("prototype").get(id=object_.id)
    )


def send_prototype_and_state_update_event(object_: ADCMEntity) -> None:
    changes = {
        "state": object_.state,
        "prototype": {
            "id": object_.prototype.pk,
            "name": object_.prototype.name,
            "displayName": object_.prototype.display_name,
            "version": object_.prototype.version,
        },
    }

    post_event(
        event=EventTypes.UPDATE.format(fix_object_type(type_=object_.prototype.type)),
        object_id=object_.pk,
        changes=changes,
    )


def get_raw_status(url: str) -> int:
    response = api_request(method="get", url=url)
    if response is None:
        return settings.EMPTY_REQUEST_STATUS_CODE

    try:
        json_data = response.json()
    except ValueError:
        return settings.VALUE_ERROR_STATUS_CODE

    if "status" in json_data:
        return json_data["status"]
    return settings.EMPTY_STATUS_STATUS_CODE


def get_status(obj: ADCMEntity, url: str) -> int:
    if obj.prototype.monitoring == "passive":
        return 0

    return get_raw_status(url=url)


def get_cluster_status(cluster: Cluster) -> int:
    return get_raw_status(url=f"cluster/{cluster.id}/")


def get_service_status(service: Service) -> int:
    return get_status(obj=service, url=f"cluster/{service.cluster.id}/service/{service.id}/")


def get_host_status(host: Host) -> int:
    return get_status(obj=host, url=f"host/{host.id}/")


def get_hc_status(hostcomponent: HostComponent) -> int:
    return get_status(
        obj=hostcomponent.component,
        url=f"host/{hostcomponent.host_id}/component/{hostcomponent.component_id}/",
    )


def get_host_comp_status(host: Host, component: Component) -> int:
    return get_status(obj=component, url=f"host/{host.id}/component/{component.id}/")


def get_component_status(component: Component) -> int:
    return get_status(obj=component, url=f"component/{component.id}/")


def get_object_map(obj: ADCMEntity, url_type: str) -> dict | None:
    if url_type == "service":
        response = api_request(method="get", url=f"cluster/{obj.cluster.id}/service/{obj.id}/?view=interface")
    else:
        response = api_request(method="get", url=f"{url_type}/{obj.id}/?view=interface")

    if response is None:
        return None

    return response.json()


def make_ui_single_host_status(host: Host) -> dict:
    return {
        "id": host.id,
        "name": host.fqdn,
        "status": get_host_status(host=host),
    }


def make_ui_component_status(component: Component, host_components: Iterable[HostComponent]) -> dict:
    host_list = []
    for hostcomponent in host_components:
        host_list.append(
            {
                "id": hostcomponent.host.id,
                "name": hostcomponent.host.fqdn,
                "status": get_host_comp_status(host=hostcomponent.host, component=hostcomponent.component),
            },
        )

    return {
        "id": component.id,
        "name": component.display_name,
        "status": get_component_status(component=component),
        "hosts": host_list,
    }


def make_ui_service_status(service: Service, host_components: Iterable[HostComponent]) -> dict:
    component_hc_map = defaultdict(list)
    for hostcomponent in host_components:
        component_hc_map[hostcomponent.component].append(hostcomponent)

    comp_list = []
    for component, hc_list in component_hc_map.items():
        comp_list.append(make_ui_component_status(component=component, host_components=hc_list))

    service_map = get_object_map(obj=service, url_type="service")
    return {
        "id": service.id,
        "name": service.display_name,
        "status": 32 if service_map is None else service_map.get("status", 0),
        "hc": comp_list,
    }


def make_ui_cluster_status(cluster: Cluster, host_components: Iterable[HostComponent]) -> dict:
    service_hc_map = defaultdict(list)
    for hostcomponent in host_components:
        service_hc_map[hostcomponent.service].append(hostcomponent)

    service_list = []
    for service, hc_list in service_hc_map.items():
        service_list.append(make_ui_service_status(service=service, host_components=hc_list))

    host_list = []
    for host in Host.obj.filter(cluster=cluster):
        host_list.append(make_ui_single_host_status(host=host))

    cluster_map = get_object_map(obj=cluster, url_type="cluster")

    return {
        "name": cluster.name,
        "status": 32 if cluster_map is None else cluster_map.get("status", 0),
        "chilren": {  # backward compatibility typo
            "hosts": host_list,
            "services": service_list,
        },
    }


def make_ui_host_status(host: Host, host_components: Iterable[HostComponent]) -> dict:
    comp_list = []

    for hostcomponent in host_components:
        comp_list.append(
            {
                "id": hostcomponent.component.id,
                "name": hostcomponent.component.display_name,
                "status": get_component_status(component=hostcomponent.component),
                "service_id": hostcomponent.service.id,
            },
        )

    host_map = get_object_map(obj=host, url_type="host")

    return {
        "id": host.id,
        "name": host.fqdn,
        "status": 32 if host_map is None else host_map.get("status", 0),
        "hc": comp_list,
    }


def notify_about_redistributed_concerns(
    added: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
    removed: Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]],
) -> None:
    added_concerns = tuple(added)
    serialized_concerns = {
        concern.id: camelize(data=ConcernSerializer(instance=concern).data)
        for concern in ConcernItem.objects.filter(id__in=(id_ for _, _, id_ in added_concerns)).prefetch_related(
            "owner"
        )
    }

    for core_type, object_id, concern_id in removed:
        post_event(
            event=f"delete_{fix_object_type(type_=core_type.value)}_concern",
            object_id=object_id,
            changes={"id": concern_id},
        )

    for core_type, object_id, concern_id in added_concerns:
        concern = serialized_concerns.get(concern_id)
        if concern:
            post_event(
                event=f"create_{fix_object_type(type_=core_type.value)}_concern", object_id=object_id, changes=concern
            )


def notify_about_new_concern(concern_id: ConcernID, related_objects: ConcernRelatedObjects) -> None:
    notify_about_redistributed_concerns(
        added=(
            (core_type, object_id, concern_id)
            for core_type, object_ids in related_objects.items()
            for object_id in object_ids
        ),
        removed=(),
    )


def notify_about_redistributed_concerns_from_maps(
    added: AffectedObjectConcernMap,
    removed: AffectedObjectConcernMap,
):
    """
    Convenience function to call `notify_about_redistributed_concerns` based on input of `redistribute_issues_and_flags`
    """
    return notify_about_redistributed_concerns(
        added=_flatten_concerns_map(added),
        removed=_flatten_concerns_map(removed),
    )


def _flatten_concerns_map(concerns_map: AffectedObjectConcernMap) -> Iterable[tuple[ADCMCoreType, ObjectID, ConcernID]]:
    return (
        (core_type, object_id, concern_id)
        for core_type, objects in concerns_map.items()
        for object_id, concerns in objects.items()
        for concern_id in concerns
    )
