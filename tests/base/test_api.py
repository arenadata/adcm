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


class ApiTestCase(unittest.TestCase):
    token = None
    url = None
    debug = os.environ.get('BASE_DEBUG', False)

    def api(self, path, res, data=''):
        self.print_result(path, res, data)
        return res

    def token_hdr(self):
        return {'Authorization': 'Token ' + self.token}

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
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Token ' + self.token,
                },
            ),
            data,
        )

    def api_put(self, path, data):
        return self.api(
            path,
            requests.put(
                self.url + path,
                data=json.dumps(data),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Token ' + self.token,
                },
            ),
            data,
        )

    def api_patch(self, path, data):
        return self.api(
            path,
            requests.patch(
                self.url + path,
                data=json.dumps(data),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Token ' + self.token,
                },
            ),
            data,
        )

    def print_result(self, path, response, data=''):
        if self.debug:
            print(f"IN:  {path}")
            if data:
                print(f"DATA:{data}")
            print(f"OUT: {response.status_code} {response.text}")
            # print("HDR: {}".format(r.headers))
            print("")


class TestAPI(ApiTestCase):  # pylint: disable=too-many-public-methods
    token = None
    url = 'http://localhost:8040/api/v1'
    cluster = 'adh42'
    host = 'test.host.net'
    service = 'ZOOKEEPER'
    service_id = 1
    component = 'ZOOKEEPER_SERVER'
    adh_bundle = 'adh.1.5.tar'
    ssh_bundle = 'ssh.1.0.tar'

    def setUp(self):
        if self.token is not None:
            return
        response = requests.post(
            self.url + '/token/',
            data=json.dumps({'username': 'admin', 'password': 'admin'}),
            headers={'Content-Type': 'application/json'},
        )
        self.print_result('/token/', response)
        self.assertEqual(response.status_code, 200)
        self.token = response.json()['token']

    def get_service_proto_id(self):
        response = self.api_get('/stack/service/')
        self.assertEqual(response.status_code, 200)
        for service in response.json():
            if service['name'] == self.service:
                return service['id']
        return 0

    def get_action_id(self, service_id, action_name):
        response = self.api_get('/stack/service/' + str(service_id) + '/action/')
        self.assertEqual(response.status_code, 200)
        for action in response.json():
            if action['name'] == action_name:
                return action['id']
        return 0

    def get_component_id(self, cluster_id, service_id, component_name):
        response = self.api_get('/cluster/{}/service/{}/component/'.format(cluster_id, service_id))
        self.assertEqual(response.status_code, 200)
        for comp in response.json():
            if comp['name'] == component_name:
                return comp['id']
        return 0

    def get_cluster_proto_id(self):
        response = self.api_get('/stack/cluster/')
        self.assertEqual(response.status_code, 200)
        for cluster in response.json():
            return (cluster['bundle_id'], cluster['id'])

    def get_host_proto_id(self):
        response = self.api_get('/stack/host/')
        self.assertEqual(response.status_code, 200)
        for host in response.json():
            return (host['bundle_id'], host['id'])

    def get_host_provider_proto_id(self):
        response = self.api_get('/stack/provider/')
        self.assertEqual(response.status_code, 200)
        for provider in response.json():
            return (provider['bundle_id'], provider['id'])

    def create_host(self, fqdn, name='DF1'):
        ssh_bundle_id, host_proto = self.get_host_proto_id()
        _, provider_proto = self.get_host_provider_proto_id()
        response = self.api_post('/provider/', {'name': name, 'prototype_id': provider_proto})
        self.assertEqual(response.status_code, 201)
        provider_id = response.json()['id']
        response = self.api_post(
            '/host/', {'fqdn': fqdn, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(response.status_code, 201)
        host_id = response.json()['id']
        return (ssh_bundle_id, provider_id, host_id)

    def test_access(self):
        api = ['cluster', 'host', 'job', 'task', 'stack', 'user', 'profile']
        for path in api:
            response = requests.get(self.url + '/' + path + '/')
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json()['detail'], 'Authentication credentials were not provided.'
            )

        for path in api:
            response = requests.post(self.url + '/' + path + '/', {})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json()['detail'], 'Authentication credentials were not provided.'
            )

        for path in api:
            response = requests.put(self.url + '/' + path + '/', {})
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json()['detail'], 'Authentication credentials were not provided.'
            )

        for path in api:
            response = requests.delete(self.url + '/' + path + '/')
            self.assertEqual(response.status_code, 401)
            self.assertEqual(
                response.json()['detail'], 'Authentication credentials were not provided.'
            )

    def test_schema(self):
        response = self.api_get('/schema/')
        self.assertEqual(response.status_code, 200)

    def test_cluster(self):  # pylint: disable=too-many-statements
        cluster = 'test_cluster'
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        bundle_id, proto_id = self.get_cluster_proto_id()

        response = self.api_post('/cluster/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['name'], ['This field is required.'])

        response = self.api_post('/cluster/', {'name': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['name'], ['This field may not be blank.'])

        response = self.api_post('/cluster/', {'name': cluster})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['prototype_id'], ['This field is required.'])

        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['prototype_id'], ['A valid integer is required.'])

        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': 'some-string'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['prototype_id'], ['A valid integer is required.'])

        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': 100500})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'PROTOTYPE_NOT_FOUND')

        response = self.api_post(
            '/cluster/', {'name': cluster, 'prototype_id': proto_id, 'description': ''}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['description'], ['This field may not be blank.'])

        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': proto_id})
        self.assertEqual(response.status_code, 201)
        cluster_id = response.json()['id']

        response = self.api_get('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], cluster)

        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': proto_id})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'CLUSTER_CONFLICT')

        response = self.api_put('/cluster/' + str(cluster_id) + '/', {})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()['detail'], 'Method "PUT" not allowed.')

        response = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_get('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'CLUSTER_NOT_FOUND')

        response = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'CLUSTER_NOT_FOUND')

        response = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_cluster_patching(self):
        name = 'test_cluster'
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        bundle_id, proto_id = self.get_cluster_proto_id()

        response = self.api_post('/cluster/', {'name': name, 'prototype_id': proto_id})
        self.assertEqual(response.status_code, 201)
        cluster_id = response.json()['id']

        patched_name = 'patched_cluster'
        response = self.api_patch('/cluster/' + str(cluster_id) + '/', {'name': patched_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['name'], patched_name)

        description = 'cluster_description'
        response = self.api_patch(
            '/cluster/' + str(cluster_id) + '/', {'name': patched_name, 'description': description}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['description'], description)

        response = self.api_post('/cluster/', {'name': name, 'prototype_id': proto_id})
        self.assertEqual(response.status_code, 201)
        second_cluster_id = response.json()['id']

        response = self.api_patch(
            '/cluster/' + str(second_cluster_id) + '/', {'name': patched_name}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'CLUSTER_CONFLICT')

        response = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_delete('/cluster/' + str(second_cluster_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_host(self):  # pylint: disable=too-many-statements
        host = 'test.server.net'

        response = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(response.status_code, 200)

        response = self.api_post('/host/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['fqdn'], ['This field is required.'])

        ssh_bundle_id, host_proto = self.get_host_proto_id()
        response = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': 0}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'PROVIDER_NOT_FOUND')

        _, provider_proto = self.get_host_provider_proto_id()
        response = self.api_post('/provider/', {'name': 'DF1', 'prototype_id': provider_proto})
        self.assertEqual(response.status_code, 201)
        provider_id = response.json()['id']

        response = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': 42, 'provider_id': provider_id}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'PROTOTYPE_NOT_FOUND')

        response = self.api_post('/host/', {'fqdn': host, 'provider_id': provider_id})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['prototype_id'], ['This field is required.'])

        response = self.api_post('/host/', {'fqdn': host, 'prototype_id': host_proto})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['provider_id'], ['This field is required.'])

        response = self.api_post(
            '/host/',
            {
                'fqdn': 'x' + 'deadbeef' * 32,  # 257 chars
                'prototype_id': host_proto,
                'provider_id': provider_id,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['desc'], 'Host name is too long. Max length is 256')

        response = self.api_post(
            '/host/',
            {
                'fqdn': 'x' + string.punctuation,
                'prototype_id': host_proto,
                'provider_id': provider_id,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'WRONG_NAME')

        response = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(response.status_code, 201)
        host_id = response.json()['id']

        response = self.api_get('/host/' + str(host_id) + '/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['fqdn'], host)

        response = self.api_put('/host/' + str(host_id) + '/', {})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json()['detail'], 'Method "PUT" not allowed.')

        response = self.api_post(
            '/host/', {'fqdn': host, 'prototype_id': host_proto, 'provider_id': provider_id}
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'HOST_CONFLICT')

        response = self.api_delete('/host/' + str(host_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_get('/host/' + str(host_id) + '/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'HOST_NOT_FOUND')

        response = self.api_delete('/host/' + str(host_id) + '/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'HOST_NOT_FOUND')

        response = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_cluster_host(self):
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        response = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(response.status_code, 200)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        response = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = response.json()['id']
        ssh_bundle_id, _, host_id = self.create_host(self.host)

        response = self.api_post('/cluster/' + str(cluster_id) + '/host/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['host_id'], ['This field is required.'])

        response = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': 100500})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'HOST_NOT_FOUND')

        response = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['id'], host_id)
        self.assertEqual(response.json()['cluster_id'], cluster_id)

        response = self.api_post('/cluster/', {'name': 'qwe', 'prototype_id': cluster_proto})
        cluster_id2 = response.json()['id']

        response = self.api_post('/cluster/' + str(cluster_id2) + '/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'FOREIGN_HOST')

        response = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'HOST_CONFLICT')

        response = self.api_delete('/cluster/' + str(cluster_id) + '/host/' + str(host_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_post('/cluster/' + str(cluster_id2) + '/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['cluster_id'], cluster_id2)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/cluster/' + str(cluster_id2) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        response = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        self.assertEqual(response.status_code, 204)
        response = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_service(self):
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        service_id = self.get_service_proto_id()

        response = self.api_post('/stack/service/', {})
        self.assertEqual(response.status_code, 405)

        response = self.api_get('/stack/service/' + str(service_id) + '/')
        self.assertEqual(response.status_code, 200)

        response = self.api_put('/stack/service/' + str(service_id) + '/', {})
        self.assertEqual(response.status_code, 405)

        response = self.api_delete('/stack/service/' + str(service_id) + '/')
        self.assertEqual(response.status_code, 405)

        response = self.api_get('/stack/service/' + str(service_id) + '/')
        self.assertEqual(response.status_code, 200)
        bundle_id = response.json()['bundle_id']

        response = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_cluster_service(self):
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)

        service_proto_id = self.get_service_proto_id()
        bundle_id, cluster_proto_id = self.get_cluster_proto_id()

        cluster = 'test_cluster'
        response = self.api_post('/cluster/', {'name': cluster, 'prototype_id': cluster_proto_id})
        self.assertEqual(response.status_code, 201)
        cluster_id = response.json()['id']

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': 'some-string',
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['prototype_id'], ['A valid integer is required.'])

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': -service_proto_id,
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'PROTOTYPE_NOT_FOUND')

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': service_proto_id,
            },
        )
        self.assertEqual(response.status_code, 201)
        service_id = response.json()['id']

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/',
            {
                'prototype_id': service_proto_id,
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'SERVICE_CONFLICT')

        response = self.api_delete(
            '/cluster/' + str(cluster_id) + '/service/' + str(service_id) + '/'
        )
        self.assertEqual(response.status_code, 204)

        response = self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.assertEqual(response.status_code, 204)

        response = self.api_delete('/stack/bundle/' + str(bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_hostcomponent(self):  # pylint: disable=too-many-statements,too-many-locals
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        response = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(response.status_code, 200)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        ssh_bundle_id, _, host_id = self.create_host(self.host)
        service_proto_id = self.get_service_proto_id()
        response = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = response.json()['id']

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/', {'prototype_id': service_proto_id}
        )
        self.assertEqual(response.status_code, 201)
        service_id = response.json()['id']

        hc_url = '/cluster/' + str(cluster_id) + '/hostcomponent/'
        response = self.api_post(hc_url, {'hc': {}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], "INVALID_INPUT")
        self.assertEqual(response.json()['desc'], "hc field is required")

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        response = self.api_post(
            hc_url, {'hc': [{'service_id': service_id, 'host_id': 100500, 'component_id': comp_id}]}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], "HOST_NOT_FOUND")

        response = self.api_post(
            hc_url, {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': 100500}]}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], "COMPONENT_NOT_FOUND")

        response = self.api_post(
            hc_url,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], "FOREIGN_HOST")

        response = self.api_post('/cluster/' + str(cluster_id) + '/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 201)

        response = self.api_post(hc_url, {'hc': {'host_id': host_id, 'component_id': comp_id}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], "INVALID_INPUT")
        self.assertEqual(response.json()['desc'], "hc field should be a list")

        response = self.api_post(hc_url, {'hc': [{'component_id': comp_id}]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], "INVALID_INPUT")

        response = self.api_post(hc_url, {'hc': [{'host_id': host_id}]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], "INVALID_INPUT")

        response = self.api_post(
            hc_url,
            {
                'hc': [
                    {'service_id': service_id, 'host_id': 1, 'component_id': comp_id},
                    {'service_id': service_id, 'host_id': 1, 'component_id': comp_id},
                ]
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], "INVALID_INPUT")
        self.assertEqual(response.json()['desc'][0:9], "duplicate")

        response = self.api_post(
            hc_url,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(response.status_code, 201)
        hs_id = response.json()[0]['id']

        response = self.api_get(hc_url + str(hs_id) + '/')
        self.assertEqual(response.status_code, 200)

        zclient_id = self.get_component_id(cluster_id, service_id, 'ZOOKEEPER_CLIENT')
        response = self.api_post(
            hc_url,
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': zclient_id}]},
        )
        self.assertEqual(response.status_code, 201)

        response = self.api_post('/cluster/', {'name': 'qwe', 'prototype_id': cluster_proto})
        cluster_id2 = response.json()['id']

        response = self.api_post(
            '/cluster/' + str(cluster_id2) + '/hostcomponent/',
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], "CLUSTER_SERVICE_NOT_FOUND")

        response = self.api_post(
            '/cluster/' + str(cluster_id2) + '/service/', {'prototype_id': service_proto_id}
        )
        service_id2 = response.json()['id']
        self.assertEqual(response.status_code, 201)
        comp_id2 = self.get_component_id(cluster_id2, service_id2, self.component)
        response = self.api_post(
            '/cluster/' + str(cluster_id2) + '/hostcomponent/',
            {'hc': [{'service_id': service_id2, 'host_id': host_id, 'component_id': comp_id2}]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], "FOREIGN_HOST")

        response = self.api_delete(hc_url + str(hs_id) + '/')
        self.assertEqual(response.status_code, 405)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/cluster/' + str(cluster_id2) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        response = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        self.assertEqual(response.status_code, 204)
        response = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')
        self.assertEqual(response.status_code, 204)

    def test_task(self):
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        response = self.api_post('/stack/load/', {'bundle_file': self.ssh_bundle})
        self.assertEqual(response.status_code, 200)

        ssh_bundle_id, provider_id, host_id = self.create_host(self.host)
        config = {'config': {'entry': 'some value'}}
        response = self.api_post(f'/provider/{provider_id}/config/history/', config)
        self.assertEqual(response.status_code, 201)

        adh_bundle_id, cluster_proto = self.get_cluster_proto_id()
        service_id = self.get_service_proto_id()
        action_id = self.get_action_id(service_id, 'start')
        response = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': cluster_proto})
        cluster_id = response.json()['id']

        response = self.api_post(f'/cluster/{cluster_id}/host/', {'host_id': host_id})
        self.assertEqual(response.status_code, 201)

        response = self.api_post(f'/cluster/{cluster_id}/service/', {'prototype_id': service_id})
        self.assertEqual(response.status_code, 201)
        service_id = response.json()['id']

        comp_id = self.get_component_id(cluster_id, service_id, self.component)
        response = self.api_post(
            f'/cluster/{cluster_id}/hostcomponent/',
            {'hc': [{'service_id': service_id, 'host_id': host_id, 'component_id': comp_id}]},
        )
        self.assertEqual(response.status_code, 201)

        response = self.api_post(f'/cluster/{cluster_id}/action/{action_id}/run/', {})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'TASK_ERROR')
        self.assertEqual(response.json()['desc'], 'action has issues')

        response = self.api_post(
            f'/cluster/{cluster_id}/config/history/', {'config': {'required': 42}}
        )
        self.assertEqual(response.status_code, 201)

        response = self.api_post(f'/cluster/{cluster_id}/action/{action_id}/run/', {})
        self.assertEqual(response.status_code, 201)
        task_id = response.json()['id']
        job_id = task_id

        response = self.api_get('/task/' + str(task_id) + '/')
        self.assertEqual(response.status_code, 200)

        response = self.api_get('/job/' + str(job_id) + '/')
        self.assertEqual(response.status_code, 200)

        response = self.api_delete('/job/' + str(job_id) + '/')
        self.assertEqual(response.status_code, 405)

        response = self.api_get('/job/' + str(job_id) + '/log/' + str(3))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'LOG_NOT_FOUND')

        time.sleep(2)
        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/host/' + str(host_id) + '/')
        response = self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')
        response = self.api_delete('/stack/bundle/' + str(ssh_bundle_id) + '/')

    def test_config(self):  # pylint: disable=too-many-statements
        response = self.api_post('/stack/load/', {'bundle_file': self.adh_bundle})
        self.assertEqual(response.status_code, 200)
        adh_bundle_id, proto_id = self.get_cluster_proto_id()
        service_proto_id = self.get_service_proto_id()
        response = self.api_post('/cluster/', {'name': self.cluster, 'prototype_id': proto_id})
        cluster_id = response.json()['id']

        response = self.api_get('/cluster/' + str(cluster_id) + '/service/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/', {'prototype_id': 100500}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['code'], 'PROTOTYPE_NOT_FOUND')

        response = self.api_post(
            '/cluster/' + str(cluster_id) + '/service/', {'prototype_id': service_proto_id}
        )
        self.assertEqual(response.status_code, 201)
        service_id = response.json()['id']

        zurl = '/cluster/' + str(cluster_id) + '/service/' + str(service_id) + '/'
        response = self.api_get(zurl)
        self.assertEqual(response.status_code, 200)

        response = self.api_get(zurl + 'config/current/')
        self.assertEqual(response.status_code, 200)
        id1 = response.json()['id']
        config = response.json()['config']
        self.assertEqual(config['zoo.cfg']['autopurge.purgeInterval'], 24)

        response = self.api_post(zurl + 'config/history/', {'config': 'qwe'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'JSON_ERROR')
        self.assertEqual(response.json()['desc'], "config should not be just one string")

        response = self.api_post(zurl + 'config/history/', {'config': 42})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['desc'], "config should not be just one int or float")

        config['zoo.cfg']['autopurge.purgeInterval'] = 42
        config['zoo.cfg']['port'] = 80
        response = self.api_post(zurl + 'config/history/', {'config': config})
        self.assertEqual(response.status_code, 201)
        id2 = response.json()['id']

        response = self.api_get(zurl + 'config/history/' + str(id2) + '/')
        self.assertEqual(response.status_code, 200)
        config = response.json()['config']
        self.assertEqual(config['zoo.cfg']['autopurge.purgeInterval'], 42)

        response = self.api_patch(
            zurl + 'config/history/' + str(id1) + '/restore/', {'description': 'New config'}
        )
        self.assertEqual(response.status_code, 200)
        response = self.api_get(zurl + 'config/current/')
        config = response.json()['config']
        self.assertEqual(config['zoo.cfg']['autopurge.purgeInterval'], 24)

        response = self.api_get(zurl + 'config/previous/')
        self.assertEqual(response.status_code, 200)
        config = response.json()['config']
        self.assertEqual(config['zoo.cfg']['autopurge.purgeInterval'], 42)

        response = self.api_get(zurl + 'config/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        self.api_delete('/cluster/' + str(cluster_id) + '/')
        self.api_delete('/stack/bundle/' + str(adh_bundle_id) + '/')


if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
