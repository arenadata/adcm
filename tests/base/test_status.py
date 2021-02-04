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


class TestStatusAPI(unittest.TestCase):
    # debug = False
    _TOKEN_FILENAME = "/adcm/data/var/secrets.json"
    debug = True
    url = 'http://localhost:8020/api/v1'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._read_key()

    def _read_key(self):
        with open(self._TOKEN_FILENAME) as f:
            data = json.load(f)
            self.token = data['token']

    def api(self, path, res, data=''):
        self.print_result(path, res, data)
        return res

    def token_hdr(self):
        return {"Authorization": "Token " + self.token}

    def api_get(self, path):
        return self.api(path, requests.get(self.url + path, headers=self.token_hdr()))

    def api_delete(self, path):
        return self.api(path, requests.delete(self.url + path, headers=self.token_hdr()))

    def api_post(self, path, data):
        return self.api(path, requests.post(
            self.url + path,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json', 'Authorization': 'Token ' + self.token},
            timeout=0.1
        ), data)

    def ws_connect(self, url):
        return websocket.create_connection(url, subprotocols=["adcm", self.token])

    def ws_recv(self, ws):
        r1 = ws.recv()
        if self.debug:
            print('WS IN: {}'.format(r1))
        return json.loads(r1)

    def print_result(self, path, r, data=''):
        if self.debug:
            print("IN:  {}".format(path))
            if data:
                print("DATA:{}".format(data))
            print("OUT: {} {}".format(r.status_code, r.text))
            # print("HDR: {}".format(r.headers))
            print("")

    def smap(self):
        return {
            'service': {
                "1": [5]
            },
            'host': {
                "1": [1, 2]
            },
            'hostservice': {
                "1.7": {"cluster": 1, "service": 5},
                "2.7": {"cluster": 1, "service": 5},
            },
            'component': {
                "1": {
                    "5": ["1.7", "2.7"]
                }
            }
        }

    def test_post_access(self):
        api = ('servicemap', 'event', 'host/1/component/2')
        for path in api:
            url = self.url + '/' + path + '/'
            r1 = self.api(url, requests.post(url, {}))
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['code'], 'AUTH_ERROR')

    def test_get_access(self):
        api = ('servicemap', 'host/1/component/2')
        for path in api:
            url = self.url + '/' + path + '/'
            r1 = self.api(url, requests.get(url))
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['code'], 'AUTH_ERROR')

    def test_service_map(self):
        sm_in = self.smap()
        r1 = self.api_post('/servicemap/', sm_in)
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/servicemap/')
        self.assertEqual(r1.status_code, 200)
        sm_out = r1.json()
        self.assertEqual(sm_in['host'], sm_out['host'])
        self.assertEqual(sm_in['service'], sm_out['service'])
        self.assertEqual(sm_in['component'], sm_out['component'])
        self.assertEqual(sm_in['hostservice'], sm_out['hostservice'])

    def test_host(self):
        sm = self.smap()
        r1 = self.api_post('/servicemap/', sm)
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_post('/host/1/', {'status': 0})
        self.assertTrue(r1.status_code in (200, 201))

        r1 = self.api_get('/host/1/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 0)

        r1 = self.api_post('/host/1/', {'status': 42})
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/host/1/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 42)

    def test_service(self):
        sm = self.smap()
        r1 = self.api_post('/servicemap/', sm)
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/cluster/1/service/5/')
        if r1.status_code == 409:
            self.assertEqual(r1.json()['code'], 'STATUS_UNDEFINED')
        else:
            self.assertEqual(r1.status_code, 200)
            self.api_post('/host/1/component/7/', {'status': 1})
            self.assertEqual(r1.status_code, 200)

        r1 = self.api_post('/host/2/component/7/', {'status': 0})
        self.assertIn(r1.status_code, (200, 201))

        r1 = self.api_get('/cluster/1/service/5/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 1)

        r1 = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(r1.status_code, (200, 201))

        r1 = self.api_get('/cluster/1/service/5/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 0)

        r1 = self.api_post('/host/1/component/7/', {'status': 1})
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/cluster/1/service/5/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 1)

        r1 = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertEqual(r1.status_code, 200)

    def check_event(self, ev, event, obj_type, obj_id, det_type, det_val, det_id=None):
        # pylint: disable=too-many-arguments
        self.assertEqual(ev['event'], event)
        self.assertEqual(ev['object']['type'], obj_type)
        self.assertEqual(ev['object']['id'], obj_id)
        self.assertEqual(ev['object']['details']['type'], det_type)
        self.assertEqual(ev['object']['details']['value'], str(det_val))
        if det_id:
            self.assertEqual(ev['object']['details']['id'], str(det_id))

    def test_status_ws(self):   # pylint: disable=too-many-statements
        ws = self.ws_connect("ws://localhost:8020/ws/event/")

        r1 = self.api_post('/servicemap/', self.smap())
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/cluster/1/service/5/')
        if r1.status_code == 200:
            if r1.json()['status'] == 0:
                r1 = self.api_post('/host/1/component/7/', {'status': 42})
                self.assertIn(r1.status_code, (200, 201))

        r1 = self.api_get('/cluster/1/service/5/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['status'], 42)

        r1 = self.api_post('/host/2/component/7/', {'status': 0})
        self.assertIn(r1.status_code, (200, 201))

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "hostcomponent", 1, "status", 42, 7)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "component", 7, "status", 42)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "service", 5, "status", 42)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "cluster", 1, "status", 42)

        r1 = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(r1.status_code, (200, 201))

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "hostcomponent", 1, "status", 0, 7)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "component", 7, "status", 0)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "service", 5, "status", 0)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "cluster", 1, "status", 0)

        r1 = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertIn(r1.status_code, (200, 201))

        r1 = self.api_post('/host/1/component/7/', {'status': 1})
        self.assertEqual(r1.status_code, 200)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "hostcomponent", 1, "status", 1, 7)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "component", 7, "status", 1)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "service", 5, "status", 1)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "cluster", 1, "status", 1)

        r1 = self.api_post('/host/1/component/7/', {'status': 0})
        self.assertEqual(r1.status_code, 200)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "hostcomponent", 1, "status", 0, 7)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "component", 7, "status", 0)

        j1 = self.ws_recv(ws)
        self.check_event(j1, "change_status", "service", 5, "status", 0)

        ws.close()

    def test_state(self):
        obj_id = 4
        st = 'installed'
        ws = self.ws_connect("ws://localhost:8020/ws/event/")

        url = '/event/'
        for obj_type in ('cluster', 'service', 'host'):
            data = {
                'event': 'change_state',
                'object': {
                    'type': obj_type,
                    'id': int(obj_id),
                    'details': {
                        'type': 'state',
                        'value': st,
                    }
                }
            }
            r1 = self.api_post(url, data)
            self.assertEqual(r1.status_code, 200)

            j1 = self.ws_recv(ws)
            self.assertEqual(j1['event'], 'change_state')
            self.assertEqual(j1['object']['id'], obj_id)
            self.assertEqual(j1['object']['type'], obj_type)
            self.assertEqual(j1['object']['details']['value'], st)

        ws.close()


if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
