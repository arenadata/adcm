#!/usr/bin/env python3
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
import unittest
import requests
import websocket

from .test_api import ApiTestCase


class TestStatusAPI(ApiTestCase):
    # debug = False
    _TOKEN_FILENAME = "/adcm/data/var/secrets.json"
    debug = True
    url = 'http://localhost:8020/api/v1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_key()

    def _read_key(self):
        with open(self._TOKEN_FILENAME, encoding='utf_8') as file:
            data = json.load(file)
            self.token = data['token']

    def ws_connect(self, url):
        return websocket.create_connection(url, subprotocols=["adcm", self.token])

    def ws_recv(self, socket):
        received = socket.recv()
        if self.debug:
            print(f'WS IN: {received}')
        return json.loads(received)

    def print_result(self, path, response, data=''):
        if self.debug:
            print(f"IN: {path}")
            if data:
                print(f"DATA:{data}")
            print(f"OUT: {response.status_code} {response.text}")
            # print("HDR: {}".format(r.headers))
            print("")

    @staticmethod
    def smap():
        return {
            'service': {"1": [5]},
            'host': {"1": [1, 2]},
            'hostservice': {
                "1.7": {"cluster": 1, "service": 5},
                "2.7": {"cluster": 1, "service": 5},
            },
            'component': {"1": {"5": ["1.7", "2.7"]}},
        }

    def test_post_access(self):
        api = ('servicemap', 'event', 'host/1/component/2')
        for path in api:
            url = self.url + '/' + path + '/'
            response = self.api(url, requests.post(url, {}))
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['code'], 'AUTH_ERROR')

    def test_get_access(self):
        api = ('servicemap', 'host/1/component/2')
        for path in api:
            url = self.url + '/' + path + '/'
            response = self.api(url, requests.get(url))
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()['code'], 'AUTH_ERROR')

    def test_service_map(self):
        sm_in = self.smap()
        response = self.api_post('/servicemap/', sm_in)
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/servicemap/')
        self.assertEqual(response.status_code, 200)
        sm_out = response.json()
        self.assertEqual(sm_in['host'], sm_out['host'])
        self.assertEqual(sm_in['service'], sm_out['service'])
        self.assertEqual(sm_in['component'], sm_out['component'])
        self.assertEqual(sm_in['hostservice'], sm_out['hostservice'])

    def test_host(self):
        servicemap = self.smap()
        response = self.api_post('/servicemap/', servicemap)
        self.assertEqual(response.status_code, 200)

        response = self.api_post('/host/1/', {'status': 0})
        self.assertTrue(response.status_code in (200, 201))

        response = self.api_get('/host/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 0)

        response = self.api_post('/host/1/', {'status': 42})
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/host/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 42)

    def test_service(self):
        servicemap = self.smap()
        response = self.api_post('/servicemap/', servicemap)
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/cluster/1/service/5/')
        if response.status_code == 409:
            self.assertEqual(response.json()['code'], 'STATUS_UNDEFINED')
        else:
            self.assertEqual(response.status_code, 200)
            self.api_post('/host/1/component/7/', {'status': 1})
            self.assertEqual(response.status_code, 200)

        response = self.api_post('/host/2/component/7/', {'status': 0})
        self.assertIn(response.status_code, (200, 201))

        response = self.api_get('/cluster/1/service/5/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 1)

        response = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(response.status_code, (200, 201))

        response = self.api_get('/cluster/1/service/5/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 0)

        response = self.api_post('/host/1/component/7/', {'status': 1})
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/cluster/1/service/5/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 1)

        response = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertEqual(response.status_code, 200)

    def check_event(
        self, received_event, event, obj_type, obj_id, det_type, det_val, det_id=None
    ):  # pylint: disable=too-many-arguments
        self.assertEqual(received_event['event'], event)
        self.assertEqual(received_event['object']['type'], obj_type)
        self.assertEqual(received_event['object']['id'], obj_id)
        self.assertEqual(received_event['object']['details']['type'], det_type)
        self.assertEqual(received_event['object']['details']['value'], str(det_val))
        if det_id:
            self.assertEqual(received_event['object']['details']['id'], str(det_id))

    def test_status_ws(self):  # pylint: disable=too-many-statements
        socket = self.ws_connect("ws://localhost:8020/ws/event/")

        response = self.api_post('/servicemap/', self.smap())
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/cluster/1/service/5/')
        if response.status_code == 200:
            if response.json()['status'] == 0:
                response = self.api_post('/host/1/component/7/', {'status': 42})
                self.assertIn(response.status_code, (200, 201))

        response = self.api_get('/cluster/1/service/5/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 42)

        response = self.api_post('/host/2/component/7/', {'status': 0})
        self.assertIn(response.status_code, (200, 201))

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "hostcomponent", 1, "status", 42, 7)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "component", 7, "status", 42)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "service", 5, "status", 42)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "cluster", 1, "status", 42)

        response = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(response.status_code, (200, 201))

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "hostcomponent", 1, "status", 0, 7)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "component", 7, "status", 0)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "service", 5, "status", 0)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "cluster", 1, "status", 0)

        response = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(response.status_code, (200, 201))

        response = self.api_post('/host/1/component/7/', {'status': 1})
        self.assertEqual(response.status_code, 200)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "hostcomponent", 1, "status", 1, 7)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "component", 7, "status", 1)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "service", 5, "status", 1)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "cluster", 1, "status", 1)

        response = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertEqual(response.status_code, 200)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "hostcomponent", 1, "status", 0, 7)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "component", 7, "status", 0)

        socket_received = self.ws_recv(socket)
        self.check_event(socket_received, "change_status", "service", 5, "status", 0)

        socket.close()

    def test_state(self):
        obj_id = 4
        state = 'installed'
        socket = self.ws_connect("ws://localhost:8020/ws/event/")

        url = '/event/'
        for obj_type in ('cluster', 'service', 'host'):
            data = {
                'event': 'change_state',
                'object': {
                    'type': obj_type,
                    'id': int(obj_id),
                    'details': {
                        'type': 'state',
                        'value': state,
                    },
                },
            }
            response = self.api_post(url, data)
            self.assertEqual(response.status_code, 200)

            socket_received = self.ws_recv(socket)
            self.assertEqual(socket_received['event'], 'change_state')
            self.assertEqual(socket_received['object']['id'], obj_id)
            self.assertEqual(socket_received['object']['type'], obj_type)
            self.assertEqual(socket_received['object']['details']['value'], state)

        socket.close()


if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
