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

import os
import json
import string
import time
import unittest
import requests

token = None


class TestAPI(unittest.TestCase):  # pylint: disable=too-many-public-methods
    debug = os.environ.get('BASE_DEBUG', False)
    # debug = True
    url = 'http://localhost:8040/api/v1'
    cluster = 'adh42'
    host = 'test.host.net'
    service = 'ZOOKEEPER'
    service_id = 1
    component = 'ZOOKEEPER_SERVER'
    adh_bundle = 'adh.1.5.tar'
    ssh_bundle = 'ssh.1.0.tar'

    def setUp(self):
        global token  # pylint: disable=global-statement
        if token is not None:
            return
        r1 = requests.post(
            self.url + '/token/',
            data=json.dumps({'username': 'admin', 'password': 'admin'}),
            headers={'Content-Type': 'application/json'},
        )
        self.print_result('/token/', r1)
        self.assertEqual(r1.status_code, 200)
        token = r1.json()['token']

    def api(self, path, res, data=''):
        self.print_result(path, res, data)
        return res

    def token_hdr(self):
        return {'Authorization': 'Token ' + token}

    def api_get(self, path):
        return self.api(path, requests.get(self.url + path, headers=self.token_hdr()))

    def api_delete(self, path):
        return self.api(path, requests.delete(self.url + path, headers=self.token_hdr()))

    def api_post(self, path, data):
        return self.api(
            path,
            requests.post(
                self.url + path,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json', 'Authorization': 'Token ' + token},
            ),
            data,
        )

    def api_put(self, path, data):
        return self.api(
            path,
            requests.put(
                self.url + path,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json', 'Authorization': 'Token ' + token},
            ),
            data,
        )

    def api_patch(self, path, data):
        return self.api(
            path,
            requests.patch(
                self.url + path,
                data=json.dumps(data),
                headers={'Content-Type': 'application/json', 'Authorization': 'Token ' + token},
            ),
            data,
        )

    def print_result(self, path, r, data=''):
        if self.debug:
            print("IN:  {}".format(path))
            if data:
                print("DATA:{}".format(data))
            print("OUT: {} {}".format(r.status_code, r.text))
            # print("HDR: {}".format(r.headers))
            print("")

    def get_service_proto_id(self):
        r1 = self.api_get('/stack/service/')
        self.assertEqual(r1.status_code, 200)
        for service in r1.json():
            if service['name'] == self.service:
                return service['id']
        return 0

    def get_action_id(self, service_id, action_name):
        r1 = self.api_get('/stack/service/' + str(service_id) + '/action/')
        self.assertEqual(r1.status_code, 200)
        for action in r1.json():
            if action['name'] == action_name:
                return action['id']
        return 0

    def get_component_id(self, cluster_id, service_id, component_name):
        r1 = self.api_get('/cluster/{}/service/{}/component/'.format(cluster_id, service_id))
        self.assertEqual(r1.status_code, 200)
        for comp in r1.json():
            if comp['name'] == component_name:
                return comp['id']
        return 0

    def get_cluster_proto_id(self):
        r1 = self.api_get('/stack/cluster/')
        self.assertEqual(r1.status_code, 200)
        for cluster in r1.json():
            return (cluster['bundle_id'], cluster['id'])

    def get_host_proto_id(self):
        r1 = self.api_get('/stack/host/')
        self.assertEqual(r1.status_code, 200)
        for host in r1.json():
            return (host['bundle_id'], host['id'])

    def get_host_provider_proto_id(self):
        r1 = self.api_get('/stack/provider/')
        self.assertEqual(r1.status_code, 200)
        for provider in r1.json():
            return (provider['bundle_id'], provider['id'])

    def create_host(self, fqdn, name='DF1'):
        ssh_bundle_id, host_proto = self.get_host_proto_id()
        _, provider_proto = self.get_host_provider_proto_id()
        r1 = self.api_post('/provider/', {'name': name, 'prototype_id': provider_proto})
        self.assertEqual(r1.status_code, 201)
        provider_id = r1.json()['id']
        r1 = self.api_post(
            '/host/', {'fqdn': fqdn, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(r1.status_code, 201)
        host_id = r1.json()['id']
        return (ssh_bundle_id, provider_id, host_id)

    def test_access(self):
        api = ['cluster', 'host', 'job', 'task', 'stack', 'user', 'profile']
        for path in api:
            r1 = requests.get(self.url + '/' + path + '/')
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['detail'], 'Authentication credentials were not provided.')

        for path in api:
            r1 = requests.post(self.url + '/' + path + '/', {})
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['detail'], 'Authentication credentials were not provided.')

        for path in api:
            r1 = requests.put(self.url + '/' + path + '/', {})
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['detail'], 'Authentication credentials were not provided.')

        for path in api:
            r1 = requests.delete(self.url + '/' + path + '/')
            self.assertEqual(r1.status_code, 401)
            self.assertEqual(r1.json()['detail'], 'Authentication credentials were not provided.')

    def test_schema(self):
        r1 = self.api_get('/schema/')
        self.assertEqual(r1.status_code, 200)

    def test_cluster(self):  # pylint: disable=too-many-statements
        cluster = 'test_cluster'
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        bundle_id, proto_id = self.get_cluster_proto_id()

        r1 = self.api_post('/cluster/', {})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['name'], ['This field is required.'])

        r1 = self.api_post('/cluster/', {'name': ''})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['name'], ['This field may not be blank.'])

        r1 = self.api_post('/cluster/', {'name': cluster})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['prototype_id'], ['This field is required.'])

        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': ''})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['prototype_id'], ['A valid integer is required.'])

        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': 'some-string'})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['prototype_id'], ['A valid integer is required.'])

        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': 100500})
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'PROTOTYPE_NOT_FOUND')

        r1 = self.api_post(
            '/cluster/', {'name': cluster, 'prototype_id': proto_id, 'description': ''}
        )
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['description'], ['This field may not be blank.'])

        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': proto_id})
        self.assertEqual(r1.status_code, 201)
        cluster_id = r1.json()['id']

        r2 = self.api_get('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()['name'], cluster)

        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': proto_id})
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'CLUSTER_CONFLICT')

        r1 = self.api_put('/cluster/' + str(cluster_id) + '/', {})
        self.assertEqual(r1.status_code, 405)
        self.assertEqual(r1.json()['detail'], 'Method "PUT" not allowed.')

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_get('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'CLUSTER_NOT_FOUND')

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'CLUSTER_NOT_FOUND')

        r1 = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_cluster_patching(self):
        name = 'test_cluster'
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        bundle_id, proto_id = self.get_cluster_proto_id()

        r1 = self.api_post('/cluster/', {'name': name, 'prototype_id': proto_id})
        self.assertEqual(r1.status_code, 201)
        cluster_id = r1.json()['id']

        patched_name = 'patched_cluster'
        r1 = self.api_patch('/cluster/' + str(cluster_id) + '/', {'name': patched_name})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['name'], patched_name)

        description = 'cluster_description'
        r1 = self.api_patch(
            '/cluster/' + str(cluster_id) + '/', {'name': patched_name, 'description': description}
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['description'], description)

        r1 = self.api_post('/cluster/', {'name': name, 'prototype_id': proto_id})
        self.assertEqual(r1.status_code, 201)
        second_cluster_id = r1.json()['id']

        r1 = self.api_patch('/cluster/' + str(second_cluster_id) + '/', {'name': patched_name})
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'CLUSTER_CONFLICT')

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_delete('/cluster/' + str(second_cluster_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_host(self):  # pylint: disable=too-many-statements
        host = 'test.server.net'

        r1 = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_post('/host/', {})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['fqdn'], ['This field is required.'])

        ssh_bundle_id, host_proto = self.get_host_proto_id()
        r1 = self.api_post('/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': 0})
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'PROVIDER_NOT_FOUND')

        _, provider_proto = self.get_host_provider_proto_id()
        r1 = self.api_post('/provider/', {'name': 'DF1', 'prototype_id': provider_proto})
        self.assertEqual(r1.status_code, 201)
        provider_id = r1.json()['id']

        r1 = self.api_post('/host/', {'fqdn': host, 'prototype_id': 42, 'provider_id': provider_id})
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'PROTOTYPE_NOT_FOUND')

        r1 = self.api_post('/host/', {'fqdn': host, 'provider_id': provider_id})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['prototype_id'], ['This field is required.'])

        r1 = self.api_post('/host/', {'fqdn': host, 'prototype_id': host_proto})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['provider_id'], ['This field is required.'])

        r1 = self.api_post(
            '/host/',
            {
                'fqdn': 'x' + 'deadbeef' * 32,  # 257 chars
                'prototype_id': host_proto,
                'provider_id': provider_id,
            },
        )
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['desc'], 'Host name is too long. Max length is 256')

        r1 = self.api_post(
            '/host/',
            {
                'fqdn': 'x' + string.punctuation,
                'prototype_id': host_proto,
                'provider_id': provider_id,
            },
        )
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], 'WRONG_NAME')

        r1 = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(r1.status_code, 201)
        host_id = r1.json()['id']

        r1 = self.api_get('/host/' + str(host_id) + '/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json()['fqdn'], host)

        r1 = self.api_put('/host/' + str(host_id) + '/', {})
        self.assertEqual(r1.status_code, 405)
        self.assertEqual(r1.json()['detail'], 'Method "PUT" not allowed.')

        r1 = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'HOST_CONFLICT')

        r1 = self.api_delete('/host/' + str(host_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_get('/host/' + str(host_id) + '/')
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'HOST_NOT_FOUND')

        r1 = self.api_delete('/host/' + str(host_id) + '/')
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'HOST_NOT_FOUND')

        r1 = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_cluster_host(self):
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        r1 = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(r1.status_code, 200)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        r1 = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = r1.json()['id']
        ssh_bundle_id, _, host_id = self.create_host(self.host)

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/host/', {})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['host_id'], ['This field is required.'])

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': 100500})
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'HOST_NOT_FOUND')

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()['id'], host_id)
        self.assertEqual(r1.json()['cluster_id'], cluster_id)

        r1 = self.api_post('/cluster/', {'name': 'qwe', 'prototype_id': cluster_proto})
        cluster_id2 = r1.json()['id']

        r1 = self.api_post('/cluster/' + str(cluster_id2) + '/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'FOREIGN_HOST')

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'HOST_CONFLICT')

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/host/' + str(host_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_post('/cluster/' + str(cluster_id2) + '/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()['cluster_id'], cluster_id2)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/cluster/' + str(cluster_id2) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        r1 = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)
        r1 = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_service(self):
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        service_id = self.get_service_proto_id()

        r1 = self.api_post('/stack/service/', {})
        self.assertEqual(r1.status_code, 405)

        r1 = self.api_get('/stack/service/' + str(service_id) + '/')
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_put('/stack/service/' + str(service_id) + '/', {})
        self.assertEqual(r1.status_code, 405)

        r1 = self.api_delete('/stack/service/' + str(service_id) + '/')
        self.assertEqual(r1.status_code, 405)

        r1 = self.api_get('/stack/service/' + str(service_id) + '/')
        self.assertEqual(r1.status_code, 200)
        bundle_id = r1.json()['bundle_id']

        r1 = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_cluster_service(self):
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)

        service_proto_id = self.get_service_proto_id()
        bundle_id, cluster_proto_id = self.get_cluster_proto_id()

        cluster = 'test_cluster'
        r1 = self.api_post('/cluster/', {'name': cluster, 'prototype_id': cluster_proto_id})
        self.assertEqual(r1.status_code, 201)
        cluster_id = r1.json()['id']

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': 'some-string',
            },
        )
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['prototype_id'], ['A valid integer is required.'])

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': -service_proto_id,
            },
        )
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'PROTOTYPE_NOT_FOUND')

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': service_proto_id,
            },
        )
        self.assertEqual(r1.status_code, 201)
        service_id = r1.json()['id']

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': service_proto_id,
            },
        )
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'SERVICE_CONFLICT')

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/service/' + str(service_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(r1.status_code, 204)

        r1 = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_hostcomponent(self):  # pylint: disable=too-many-statements,too-many-locals
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        r1 = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(r1.status_code, 200)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        ssh_bundle_id, _, host_id = self.create_host(self.host)
        service_proto_id = self.get_service_proto_id()
        r1 = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = r1.json()['id']

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/', {'prototype_id': service_proto_id}
        )
        self.assertEqual(r1.status_code, 201)
        service_id = r1.json()['id']

        HS_URL = '/cluster/' + str(cluster_id) + '/hostcomponent/'
        r1 = self.api_post(HS_URL, {'hc': {}})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], "INVALID_INPUT")
        self.assertEqual(r1.json()['desc'], "hc field is required")

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        r1 = self.api_post(
            HS_URL, {'hc': [{'service_id': service_id, 'host_id': 100500, 'component_id': comp_id}]}
        )
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], "HOST_NOT_FOUND")

        r1 = self.api_post(
            HS_URL, {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': 100500}]}
        )
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], "COMPONENT_NOT_FOUND")

        r1 = self.api_post(
            HS_URL,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], "FOREIGN_HOST")

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 201)

        r1 = self.api_post(HS_URL, {'hc': {'host_id': host_id, 'component_id': comp_id}})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], "INVALID_INPUT")
        self.assertEqual(r1.json()['desc'], "hc field should be a list")

        r1 = self.api_post(HS_URL, {'hc': [{'component_id': comp_id}]})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], "INVALID_INPUT")

        r1 = self.api_post(HS_URL, {'hc': [{'host_id': host_id}]})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], "INVALID_INPUT")

        r1 = self.api_post(
            HS_URL,
            {
                'hc': [
                    {'service_id': service_id, 'host_id': 1, 'component_id': comp_id},
                    {'service_id': service_id, 'host_id': 1, 'component_id': comp_id},
                ]
            },
        )
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], "INVALID_INPUT")
        self.assertEqual(r1.json()['desc'][0:9], "duplicate")

        r1 = self.api_post(
            HS_URL,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(r1.status_code, 201)
        hs_id = r1.json()[0]['id']

        r1 = self.api_get(HS_URL + str(hs_id) + '/')
        self.assertEqual(r1.status_code, 200)

        zclient_id = self.get_component_id(cluster_id, service_id, 'ZOOKEEPER_CLIENT')
        r1 = self.api_post(
            HS_URL,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': zclient_id}]},
        )
        self.assertEqual(r1.status_code, 201)

        r1 = self.api_post('/cluster/', {'name': 'qwe', 'prototype_id': cluster_proto})
        cluster_id2 = r1.json()['id']

        r1 = self.api_post(
            '/cluster/' + str(cluster_id2) + '/hostcomponent/',
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], "CLUSTER_SERVICE_NOT_FOUND")

        r1 = self.api_post(
            '/cluster/' + str(cluster_id2) + '/service/', {'prototype_id': service_proto_id}
        )
        service_id2 = r1.json()['id']
        self.assertEqual(r1.status_code, 201)
        comp_id2 = self.get_component_id(cluster_id2, service_id2, self.component)
        r1 = self.api_post(
            '/cluster/' + str(cluster_id2) + '/hostcomponent/',
            {'hc': [{'service_id': service_id2, 'host_id': host_id, 'component_id': comp_id2}]},
        )
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], "FOREIGN_HOST")

        r1 = self.api_delete(HS_URL + str(hs_id) + '/')
        self.assertEqual(r1.status_code, 405)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/cluster/' + str(cluster_id2) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        r1 = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)
        r1 = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(r1.status_code, 204)

    def test_task(self):
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        r1 = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(r1.status_code, 200)

        ssh_bundle_id, provider_id, host_id = self.create_host(self.host)
        config = {'config': {'entry': 'some value'}}
        r1 = self.api_post(f'/provider/{provider_id}/config/history/', config)
        self.assertEqual(r1.status_code, 201)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        service_id = self.get_service_proto_id()
        action_id = self.get_action_id(service_id, 'start')
        r1 = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = r1.json()['id']

        r1 = self.api_post(f'/cluster/{cluster_id}/host/', {'host_id': host_id})
        self.assertEqual(r1.status_code, 201)

        r1 = self.api_post(f'/cluster/{cluster_id}/service/', {'prototype_id': service_id})
        self.assertEqual(r1.status_code, 201)
        service_id = r1.json()['id']

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        r1 = self.api_post(
            f'/cluster/{cluster_id}/hostcomponent/',
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(r1.status_code, 201)

        r1 = self.api_post(f'/cluster/{cluster_id}/action/{action_id}/run/', {})
        self.assertEqual(r1.status_code, 409)
        self.assertEqual(r1.json()['code'], 'TASK_ERROR')
        self.assertEqual(r1.json()['desc'], 'object is locked')  # was 'action has issues'

        r1 = self.api_post(f'/cluster/{cluster_id}/config/history/', {'config': {'required': 42}})
        self.assertEqual(r1.status_code, 201)

        r1 = self.api_post(f'/cluster/{cluster_id}/action/{action_id}/run/', {})
        self.assertEqual(r1.status_code, 201)
        task_id = r1.json()['id']
        job_id = task_id

        r1 = self.api_get('/task/' + str(task_id) + '/')
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get('/job/' + str(job_id) + '/')
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_delete('/job/' + str(job_id) + '/')
        self.assertEqual(r1.status_code, 405)

        r1 = self.api_get('/job/' + str(job_id) + '/log/' + str(3))
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'LOG_NOT_FOUND')

        time.sleep(2)
        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        r1 = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        r1 = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')

    def test_config(self):  # pylint: disable=too-many-statements
        r1 = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(r1.status_code, 200)
        adh_bundle_id, proto_id = self.get_cluster_proto_id()
        service_proto_id = self.get_service_proto_id()
        r1 = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': proto_id})
        cluster_id = r1.json()['id']

        r1 = self.api_get('/cluster/' + str(cluster_id) + '/service/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.json(), [])

        r1 = self.api_post('/cluster/' + str(cluster_id) + '/service/', {'prototype_id': 100500})
        self.assertEqual(r1.status_code, 404)
        self.assertEqual(r1.json()['code'], 'PROTOTYPE_NOT_FOUND')

        r1 = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/', {'prototype_id': service_proto_id}
        )
        self.assertEqual(r1.status_code, 201)
        service_id = r1.json()['id']

        zurl = '/cluster/' + str(cluster_id) + '/service/' + str(service_id) + '/'
        r1 = self.api_get(zurl)
        self.assertEqual(r1.status_code, 200)

        r1 = self.api_get(zurl + 'config/current/')
        self.assertEqual(r1.status_code, 200)
        id1 = r1.json()['id']
        c1 = r1.json()['config']
        self.assertEqual(c1['zoo.cfg']['autopurge.purgeInterval'], 24)

        r1 = self.api_post(zurl + 'config/history/', {'config': 'qwe'})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['code'], 'JSON_ERROR')
        self.assertEqual(r1.json()['desc'], "config should not be just one string")

        r1 = self.api_post(zurl + 'config/history/', {'config': 42})
        self.assertEqual(r1.status_code, 400)
        self.assertEqual(r1.json()['desc'], "config should not be just one int or float")

        c1['zoo.cfg']['autopurge.purgeInterval'] = 42
        c1['zoo.cfg']['port'] = 80
        r1 = self.api_post(zurl + 'config/history/', {'config': c1})
        self.assertEqual(r1.status_code, 201)
        id2 = r1.json()['id']

        r1 = self.api_get(zurl + 'config/history/' + str(id2) + '/')
        self.assertEqual(r1.status_code, 200)
        c2 = r1.json()['config']
        self.assertEqual(c2['zoo.cfg']['autopurge.purgeInterval'], 42)

        r1 = self.api_patch(
            zurl + 'config/history/' + str(id1) + '/restore/', {'description': 'New config'}
        )
        self.assertEqual(r1.status_code, 200)
        r1 = self.api_get(zurl + 'config/current/')
        c3 = r1.json()['config']
        self.assertEqual(c3['zoo.cfg']['autopurge.purgeInterval'], 24)

        r1 = self.api_get(zurl + 'config/previous/')
        self.assertEqual(r1.status_code, 200)
        c4 = r1.json()['config']
        self.assertEqual(c4['zoo.cfg']['autopurge.purgeInterval'], 42)

        r1 = self.api_get(zurl + 'config/history/')
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(len(r1.json()), 2)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        r1 = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')


if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
