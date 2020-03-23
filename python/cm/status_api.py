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
import simplejson

from cm.logger import log
from cm.models import HostComponent, ServiceComponent, ClusterObject, Host
from cm.config import STATUS_SECRET_KEY

API_URL = "http://localhost:8020/api/v1"
TIMEOUT = 0.01


class Event:

    def __init__(self):
        self.events = []

    def send_state(self):
        for _ in range(len(self.events)):
            try:
                event = self.events.pop(0)
                func, args = event
                func.call(*args)
            except IndexError:
                pass


def api_post(path, data):
    url = API_URL + path
    try:
        r = requests.post(
            url,
            data=json.dumps(data),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token ' + STATUS_SECRET_KEY
            },
            timeout=TIMEOUT
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
                'Authorization': 'Token ' + STATUS_SECRET_KEY
            },
            timeout=TIMEOUT
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
    data = {
        'event': event,
        'object': {
            'type': obj_type,
            'id': int(obj_id),
            'details': {
                'type': det_type,
                'value': det_val,
            }
        }
    }
    return api_post('/event/', data)


def set_job_status(job_id, status):
    return post_event('change_job_status', 'job', job_id, 'status', status)


def set_task_status(task_id, status):
    return post_event('change_job_status', 'task', task_id, 'status', status)


def set_obj_state(obj_type, obj_id, state):
    if obj_type == 'adcm':
        return None
    if obj_type not in ('cluster', 'service', 'host', 'provider'):
        log.error('Unknown object type: "%s"', obj_type)
        return None
    return post_event('change_state', obj_type, obj_id, 'state', state)


def get_status(url):
    r = api_get(url)
    if r is None:
        return 32
    try:
        js = r.json()
    except simplejson.scanner.JSONDecodeError:
        return 8
    if 'status' in js:
        return js['status']
    else:
        return 4


def get_cluster_status(cluster_id):
    return get_status('/cluster/{}/'.format(cluster_id))


def get_service_status(cluster_id, service_id):
    return get_status('/cluster/{}/service/{}/'.format(cluster_id, service_id))


def get_host_status(host_id):
    return get_status('/host/{}/'.format(host_id))


def get_hc_status(host_id, comp_id):
    return get_status('/host/{}/component/{}/'.format(host_id, comp_id))


def get_component_status(comp_id):
    return get_status('/component/{}/'.format(comp_id))


def load_service_map():
    comps = {}
    hosts = {}
    hc_map = {}
    services = {}
    passive = {}
    for c in ServiceComponent.objects.filter(component__monitoring='passive'):
        passive[c.id] = True

    for hc in HostComponent.objects.all():
        if hc.component.id in passive:
            continue
        key = '{}.{}'.format(hc.host.id, hc.component.id)
        hc_map[key] = {'cluster': hc.cluster.id, 'service': hc.service.id}
        if str(hc.cluster.id) not in comps:
            comps[str(hc.cluster.id)] = {}
        if str(hc.service.id) not in comps[str(hc.cluster.id)]:
            comps[str(hc.cluster.id)][str(hc.service.id)] = []
        comps[str(hc.cluster.id)][str(hc.service.id)].append(key)

    for host in Host.objects.filter(prototype__monitoring='active'):
        if host.cluster:
            cluster_id = host.cluster.id
        else:
            cluster_id = 0
        if cluster_id not in hosts:
            hosts[cluster_id] = []
        hosts[cluster_id].append(host.id)

    for co in ClusterObject.objects.filter(prototype__monitoring='active'):
        if co.cluster.id not in services:
            services[co.cluster.id] = []
        services[co.cluster.id].append(co.id)

    m = {
        'hostservice': hc_map,
        'component': comps,
        'service': services,
        'host': hosts,
    }
    log.debug("service map: %s", m)
    return api_post('/servicemap/', m)
