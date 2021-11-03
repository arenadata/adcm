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

import requests

from cm.config import STATUS_SECRET_KEY
from cm.logger import log
from cm.models import ADCMEntity

API_URL = "http://localhost:8020/api/v1"
TIMEOUT = 0.01


class Event:
    def __init__(self):
        self.events = []

    def __del__(self):
        self.send_state()

    def send_state(self):
        while self.events:
            try:
                func, args = self.events.pop(0)
                func.__call__(*args)
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


def api_post(path, data):
    url = API_URL + path
    try:
        r = requests.post(
            url,
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token ' + STATUS_SECRET_KEY,
            },
            timeout=TIMEOUT,
        )
        if r.status_code not in (200, 201):
            log.error("POST %s error %d: %s", url, r.status_code, r.text)
        return r
    except requests.exceptions.Timeout:
        log.error("POST request to %s timed out", url)
        return None
    except requests.exceptions.ConnectionError:
        log.error("POST request to %s connection failed", url)
        return None


def api_get(path):
    url = API_URL + path
    try:
        r = requests.get(
            url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token ' + STATUS_SECRET_KEY,
            },
            timeout=TIMEOUT,
        )
        if r.status_code not in (200, 201):
            log.error("GET %s error %d: %s", url, r.status_code, r.text)
        return r
    except requests.exceptions.Timeout:
        log.error("GET request to %s timed out", url)
        return None
    except requests.exceptions.ConnectionError:
        log.error("GET request to %s connection failed", url)
        return None


def post_event(event, obj_type, obj_id, det_type=None, det_val=None):
    details = {'type': det_type, 'value': det_val}
    if det_type and not det_val:
        details = det_type
    data = {
        'event': event,
        'object': {
            'type': obj_type,
            'id': int(obj_id),
            'details': details,
        },
    }
    log.debug('post_event %s', data)
    return api_post('/event/', data)


def set_job_status(job_id, status):
    return post_event('change_job_status', 'job', job_id, 'status', status)


def set_task_status(task_id, status):
    return post_event('change_job_status', 'task', task_id, 'status', status)


def set_obj_state(obj_type, obj_id, state):
    if obj_type == 'adcm':
        return None
    if obj_type not in ('cluster', 'service', 'host', 'provider', 'component'):
        log.error('Unknown object type: "%s"', obj_type)
        return None
    return post_event('change_state', obj_type, obj_id, 'state', state)


def change_obj_multi_state(obj_type, obj_id, multi_state):
    if obj_type == 'adcm':
        return None
    if obj_type not in ('cluster', 'service', 'host', 'provider', 'component'):
        log.error('Unknown object type: "%s"', obj_type)
        return None
    return post_event('change_state', obj_type, obj_id, 'multi_state', multi_state)


def get_raw_status(url):
    r = api_get(url)
    if r is None:
        return 32
    try:
        js = r.json()
    except ValueError:
        return 8
    if 'status' in js:
        return js['status']
    else:
        return 4


def get_status(obj, url):
    if obj.prototype.monitoring == 'passive':
        return 0
    return get_raw_status(url)


def get_cluster_status(cluster):
    return get_raw_status(f'/cluster/{cluster.id}/')


def get_service_status(service):
    return get_status(service, f'/cluster/{service.cluster.id}/service/{service.id}/')


def get_host_status(host):
    return get_status(host, f'/host/{host.id}/')


def get_hc_status(hc):
    return get_status(hc.component, f'/host/{hc.host_id}/component/{hc.component_id}/')


def get_host_comp_status(host, component):
    return get_status(component, f'/host/{host.id}/component/{component.id}/')


def get_component_status(comp):
    return get_status(comp, f'/component/{comp.id}/')


def get_object_map(obj: ADCMEntity, url_type: str):
    if url_type == 'service':
        r = api_get(f'/cluster/{obj.cluster.id}/service/{obj.id}/?view=interface')
    else:
        r = api_get(f'/{url_type}/{obj.id}/?view=interface')
    if r is None:
        return None
    return r.json()
