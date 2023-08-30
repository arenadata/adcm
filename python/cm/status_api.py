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

import json
from collections import defaultdict
from collections.abc import Iterable
from urllib.parse import urljoin

import requests
from cm.logger import logger
from cm.models import (
    ADCMEntity,
    ADCMEntityStatus,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    JobLog,
    ServiceComponent,
    TaskLog,
)
from django.conf import settings
from requests import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class Event:
    def __init__(self):
        self.events = []

    def __del__(self):
        self.send_state()

    def clear_state(self):
        self.events = []

    def send_state(self):
        while self.events:
            try:
                func, args = self.events.pop(0)
                func(*args)
            except IndexError:
                pass

    def set_object_state(self, obj, state):
        self.events.append((set_obj_state, (obj, state)))

    def change_object_multi_state(self, obj, multi_state):
        self.events.append((change_obj_multi_state, (obj, multi_state)))

    def set_job_status(self, job, status):
        self.events.append((set_job_status, (job, status)))

    def set_task_status(self, task, status):
        self.events.append((set_task_status, (task, status)))


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
        return response
    except requests.exceptions.Timeout:
        logger.error("%s request to %s timed out", method, url)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("%s request to %s connection failed", method, url)
        return None


def post_event(event: str, object_id: int | None, object_type: str, details: dict = None) -> Response | None:
    if object_id is None:
        return None

    if details is None:
        details = {"type": None, "value": None}

    data = {
        "event": event,
        "object": {
            "type": object_type,
            "id": object_id,
            "details": details,
        },
    }

    return api_request(method="post", url="event/", data=data)


def set_job_status(job: JobLog, status: str) -> Response | None:
    return post_event(
        event="change_job_status", object_id=job.pk, object_type="job", details={"type": "status", "value": status}
    )


def set_task_status(task: TaskLog, status: str) -> Response | None:
    return post_event(
        event="change_job_status", object_id=task.pk, object_type="task", details={"type": "status", "value": status}
    )


def set_obj_state(obj: ADCMEntity, state: str) -> Response | None:
    if not hasattr(obj, "prototype"):
        return None

    object_type = obj.prototype.type
    if object_type == "adcm":
        return None

    if object_type not in {"cluster", "service", "host", "provider", "component"}:
        logger.error("Unknown object type: '%s'", object_type)
        return None

    return post_event(
        event="change_state", object_id=obj.pk, object_type=object_type, details={"type": "state", "value": state}
    )


def change_obj_multi_state(obj: ADCMEntity, multi_state: str) -> Response | None:
    if not hasattr(obj, "prototype"):
        return None

    object_type = obj.prototype.type
    if object_type == "adcm":
        return None

    if object_type not in {"cluster", "service", "host", "provider", "component"}:
        logger.error("Unknown object type: '%s'", object_type)
        return None

    return post_event(
        event="change_state",
        object_id=obj.pk,
        object_type=object_type,
        details={"type": "multi_state", "value": multi_state},
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
    else:
        return settings.EMPTY_STATUS_STATUS_CODE


def get_status(obj: ADCMEntity, url: str) -> int:
    if obj.prototype.monitoring == "passive":
        return 0

    return get_raw_status(url=url)


def get_cluster_status(cluster: Cluster) -> int:
    return get_raw_status(url=f"cluster/{cluster.id}/")


def get_service_status(service: ClusterObject) -> int:
    return get_status(obj=service, url=f"cluster/{service.cluster.id}/service/{service.id}/")


def get_host_status(host: Host) -> int:
    return get_status(obj=host, url=f"host/{host.id}/")


def get_hc_status(hostcomponent: HostComponent) -> int:
    return get_status(
        obj=hostcomponent.component,
        url=f"host/{hostcomponent.host_id}/component/{hostcomponent.component_id}/",
    )


def get_host_comp_status(host: Host, component: ServiceComponent) -> int:
    return get_status(obj=component, url=f"host/{host.id}/component/{component.id}/")


def get_component_status(component: ServiceComponent) -> int:
    return get_status(obj=component, url=f"component/{component.id}/")


def get_obj_status(obj: Cluster | ClusterObject | Host | HostComponent | ServiceComponent) -> str:
    match obj.__class__.__name__:
        case Cluster.__name__:
            url = f"cluster/{obj.pk}/"
        case ClusterObject.__name__:
            url = f"cluster/{obj.cluster.pk}/service/{obj.pk}/"
        case Host.__name__:
            url = f"host/{obj.pk}/"
        case HostComponent.__name__:
            url = f"host/{obj.host_id}/component/{obj.component_id}/"
            obj = obj.component
        case ServiceComponent.__name__:
            url = f"component/{obj.pk}/"
        case _:
            raise ValueError("Wrong obj type")

    int_status = get_status(obj=obj, url=url)

    if int_status == 0:
        return ADCMEntityStatus.UP

    return ADCMEntityStatus.DOWN


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


def make_ui_component_status(component: ServiceComponent, host_components: Iterable[HostComponent]) -> dict:
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


def make_ui_service_status(service: ClusterObject, host_components: Iterable[HostComponent]) -> dict:
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
