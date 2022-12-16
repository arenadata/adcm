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
from typing import Iterable

import requests
from django.conf import settings

from cm.logger import logger
from cm.models import (
    ADCMEntity,
    Cluster,
    ClusterObject,
    Host,
    HostComponent,
    ServiceComponent,
)

API_URL = "http://localhost:8020/api/v1"
TIMEOUT = 0.01


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

    def set_object_state(self, obj_type, obj_id, state):
        self.events.append((set_obj_state, (obj_type, obj_id, state)))

    def change_object_multi_state(self, obj_type, obj_id, multi_state):
        self.events.append((change_obj_multi_state, (obj_type, obj_id, multi_state)))

    def set_job_status(self, job_id, status):
        self.events.append((set_job_status, (job_id, status)))

    def set_task_status(self, task_id, status):
        self.events.append((set_task_status, (task_id, status)))


def api_request(method, url, data=None):
    url = API_URL + url
    kwargs = {
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Token {settings.ADCM_TOKEN}",
        },
        "timeout": TIMEOUT,
    }
    if data is not None:
        kwargs["data"] = json.dumps(data)
    try:
        request = requests.request(method, url, **kwargs)
        if request.status_code not in (200, 201):
            logger.error("%s %s error %d: %s", method, url, request.status_code, request.text)
        return request
    except requests.exceptions.Timeout:
        logger.error("%s request to %s timed out", method, url)
        return None
    except requests.exceptions.ConnectionError:
        logger.error("%s request to %s connection failed", method, url)
        return None


def post_event(event, obj_type, obj_id, det_type=None, det_val=None):
    details = {"type": det_type, "value": det_val}
    if det_type and not det_val:
        details = det_type
    data = {
        "event": event,
        "object": {
            "type": obj_type,
            "id": int(obj_id),
            "details": details,
        },
    }
    logger.debug("post_event %s", data)
    return api_request("post", "/event/", data)


def set_job_status(job_id, status):
    return post_event("change_job_status", "job", job_id, "status", status)


def set_task_status(task_id, status):
    return post_event("change_job_status", "task", task_id, "status", status)


def set_obj_state(obj_type, obj_id, state):
    if obj_type == "adcm":
        return None
    if obj_type not in ("cluster", "service", "host", "provider", "component"):
        logger.error("Unknown object type: '%s'", obj_type)
        return None
    return post_event("change_state", obj_type, obj_id, "state", state)


def change_obj_multi_state(obj_type, obj_id, multi_state):
    if obj_type == "adcm":
        return None
    if obj_type not in ("cluster", "service", "host", "provider", "component"):
        logger.error("Unknown object type: '%s'", obj_type)
        return None
    return post_event("change_state", obj_type, obj_id, "multi_state", multi_state)


def get_raw_status(url):
    r = api_request("get", url)
    if r is None:
        return 32
    try:
        js = r.json()
    except ValueError:
        return 8
    if "status" in js:
        return js["status"]
    else:
        return 4


def get_status(obj: ADCMEntity, url: str):
    if obj.prototype.monitoring == "passive":
        return 0
    return get_raw_status(url)


def get_cluster_status(cluster):
    return get_raw_status(f"/cluster/{cluster.id}/")


def get_service_status(service):
    return get_status(service, f"/cluster/{service.cluster.id}/service/{service.id}/")


def get_host_status(host):
    return get_status(host, f"/host/{host.id}/")


def get_hc_status(hc):
    return get_status(hc.component, f"/host/{hc.host_id}/component/{hc.component_id}/")


def get_host_comp_status(host, component):
    return get_status(component, f"/host/{host.id}/component/{component.id}/")


def get_component_status(comp: ServiceComponent):
    return get_status(comp, f"/component/{comp.id}/")


def get_object_map(obj: ADCMEntity, url_type: str):
    if url_type == "service":
        r = api_request("get", f"/cluster/{obj.cluster.id}/service/{obj.id}/?view=interface")
    else:
        r = api_request("get", f"/{url_type}/{obj.id}/?view=interface")
    if r is None:
        return None
    return r.json()


def make_ui_single_host_status(host: Host) -> dict:
    return {
        "id": host.id,
        "name": host.fqdn,
        "status": get_host_status(host),
    }


def make_ui_component_status(component: ServiceComponent, host_components: Iterable[HostComponent]) -> dict:
    """Make UI representation of component's status per host"""
    host_list = []
    for hc in host_components:
        host_list.append(
            {
                "id": hc.host.id,
                "name": hc.host.fqdn,
                "status": get_host_comp_status(hc.host, hc.component),
            }
        )
    return {
        "id": component.id,
        "name": component.display_name,
        "status": get_component_status(component),
        "hosts": host_list,
    }


def make_ui_service_status(service: ClusterObject, host_components: Iterable[HostComponent]) -> dict:
    """Make UI representation of service and its children statuses"""
    component_hc_map = defaultdict(list)
    for hc in host_components:
        component_hc_map[hc.component].append(hc)

    comp_list = []
    for component, hc_list in component_hc_map.items():
        comp_list.append(make_ui_component_status(component, hc_list))

    service_map = get_object_map(service, "service")
    return {
        "id": service.id,
        "name": service.display_name,
        "status": 32 if service_map is None else service_map.get("status", 0),
        "hc": comp_list,
    }


def make_ui_cluster_status(cluster: Cluster, host_components: Iterable[HostComponent]) -> dict:
    """Make UI representation of cluster and its children statuses"""
    service_hc_map = defaultdict(list)
    for hc in host_components:
        service_hc_map[hc.service].append(hc)

    service_list = []
    for service, hc_list in service_hc_map.items():
        service_list.append(make_ui_service_status(service, hc_list))

    host_list = []
    for host in Host.obj.filter(cluster=cluster):
        host_list.append(make_ui_single_host_status(host))

    cluster_map = get_object_map(cluster, "cluster")
    return {
        "name": cluster.name,
        "status": 32 if cluster_map is None else cluster_map.get("status", 0),
        "chilren": {  # backward compatibility typo
            "hosts": host_list,
            "services": service_list,
        },
    }


def make_ui_host_status(host: Host, host_components: Iterable[HostComponent]) -> dict:
    """Make UI representation of host and its children statuses"""
    comp_list = []
    for hc in host_components:
        comp_list.append(
            {
                "id": hc.component.id,
                "name": hc.component.display_name,
                "status": get_component_status(hc.component),
                "service_id": hc.service.id,
            }
        )

    host_map = get_object_map(host, "host")
    return {
        "id": host.id,
        "name": host.fqdn,
        "status": 32 if host_map is None else host_map.get("status", 0),
        "hc": comp_list,
    }
