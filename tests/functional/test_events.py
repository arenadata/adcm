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
import os
import re

import allure
import pytest
import websocket
# pylint: disable=redefined-outer-name
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

DATADIR = utils.get_data_dir(__file__)
R_WWW_PREFIX = re.compile(r"https?://(www.\.)?")


def repr_template(event_type, obj_type, obj_id, dtype=None, value=None):
    return {
        'event': event_type,
        'object': {
            'type': obj_type,
            'id': obj_id,
            'details': {
                'type': dtype,
                'value': value
            }
        }
    }


def prep_url(url):
    return R_WWW_PREFIX.sub('', url).strip().strip('/')


def assert_events(ws, *expected_events):
    expected_list = list(expected_events)
    count = 1
    try:
        while expected_list != [] and count < 100:
            data = json.loads(ws.recv())
            for event in expected_list:
                if event == data:
                    expected_list.remove(event)
                    continue
            count = count + 1
    except websocket.WebSocketTimeoutException:
        pass
    assert expected_list == []


@pytest.fixture()
def ws(sdk_client_fs: ADCMClient, max_conn=10):
    while max_conn:
        try:
            ws_conn = websocket.create_connection(
                url="ws://" + prep_url(sdk_client_fs.url) + "/ws/event/",
                subprotocols=["adcm", sdk_client_fs.api_token()],
                timeout=15)
        except websocket.WebSocketBadStatusException:
            pass
        else:
            return ws_conn
        max_conn -= 1
        break


@pytest.fixture()
def cluster_with_svc_and_host(sdk_client_fs):
    cl = cluster(sdk_client_fs)
    svc = cl.service_add(name='zookeeper')
    hst = host(sdk_client_fs)
    cl.host_add(hst)
    components = svc.component_list()
    cl.hostcomponent_set(
        (hst, components[0]),
        (hst, components[1])
    )
    return cl, svc, hst


def cluster_bundle(sdk_client_fs):
    return sdk_client_fs.upload_from_fs(
        os.path.join(DATADIR, 'cluster_bundle'))


def cluster(sdk_client_fs, name=utils.random_string()):
    return cluster_bundle(sdk_client_fs).cluster_create(name=name)


def provider(sdk_client_fs, name=utils.random_string()):
    return sdk_client_fs.upload_from_fs(os.path.join(
        DATADIR, 'hostprovider')).provider_create(name=name)


def host(sdk_client_fs, fqdn=utils.random_string()):
    return provider(sdk_client_fs).host_create(fqdn=fqdn)


def service(sdk_client_fs, name='zookeeper'):
    return cluster(sdk_client_fs).service_add(name=name)


def cluster_action_run(sdk_client_fs, name):
    return cluster(sdk_client_fs).action_run(name=name)


def expected_success_task(obj, job):
    return (repr_template('change_job_status', 'task', obj.id, 'status', 'created'),
            repr_template('change_job_status', 'job', job.id, 'status', 'created'),
            repr_template('change_job_status', 'task', obj.id, 'status', 'running'),
            repr_template('change_job_status', 'job', job.id, 'status', 'running'),
            repr_template('change_job_status', 'job', job.id, 'status', 'success'),
            repr_template('change_job_status', 'task', obj.id, 'status', 'success'))


def expected_failed_task(obj, job):
    return (repr_template('change_job_status', 'task', obj.id, 'status', 'created'),
            repr_template('change_job_status', 'job', job.id, 'status', 'created'),
            repr_template('change_job_status', 'task', obj.id, 'status', 'running'),
            repr_template('change_job_status', 'job', job.id, 'status', 'running'),
            repr_template('change_job_status', 'job', job.id, 'status', 'failed'),
            repr_template('change_job_status', 'task', obj.id, 'status', 'failed'))


create_adcm_obj = [
    (cluster_bundle, 'create', 'bundle'),
    (cluster, 'create', 'cluster'),
    (provider, 'create', 'provider')
]

cluster_actions = [
    ('finish_successfully', 'install', expected_success_task),
    ('failed', 'run_fail', expected_failed_task),
]

svc_actions = [
    ('success_task', 'install', expected_success_task),
    ('failed_task', 'should_be_failed', expected_failed_task),
]


@pytest.mark.parametrize(('adcm_object', 'event_type', 'obj_type'), create_adcm_obj)
def test_event_when_create_(obj_type, adcm_object, event_type, sdk_client_fs, ws):
    with allure.step(f'Create {obj_type}'):
        obj = adcm_object(sdk_client_fs)
    with allure.step(f'Check created {obj_type}'):
        assert_events(
            ws,
            repr_template(event_type, obj_type, obj.id)
        )


def test_event_when_create_host(sdk_client_fs, ws):
    obj = host(sdk_client_fs, fqdn=utils.random_string())
    with allure.step('Check created host'):
        assert_events(ws, repr_template('create', 'host', obj.id, 'provider', str(obj.provider_id)))


def test_event_when_host_added_to_cluster(sdk_client_fs, ws):
    cl = cluster(sdk_client_fs)
    hst = host(sdk_client_fs)
    cl.host_add(hst)
    with allure.step('Check host'):
        assert_events(
            ws,
            repr_template('add', 'host', hst.host_id, 'cluster', str(cl.cluster_id))
        )


def test_event_when_add_service(sdk_client_fs, ws):
    obj = service(sdk_client_fs)
    assert_events(ws, repr_template('add', 'service', obj.id, 'cluster', str(obj.cluster_id)))


@pytest.mark.parametrize(('case', 'action_name', 'expected'), cluster_actions)
def test_events_when_cluster_action_(case, action_name, expected, ws, cluster_with_svc_and_host):
    cluster, _, _ = cluster_with_svc_and_host
    job = cluster.action_run(name=action_name)
    with allure.step('Check job'):
        assert_events(
            ws,
            *expected(cluster, job)
        )


@pytest.mark.parametrize(('case', 'action_name', 'expected'), svc_actions)
def test_events_when_service_(case, action_name, expected, ws, cluster_with_svc_and_host):
    _, zookeeper, _ = cluster_with_svc_and_host
    job = zookeeper.action_run(name=action_name)
    with allure.step('Check job'):
        assert_events(
            ws,
            *expected(zookeeper, job)
        )
