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
# pylint: disable=W0611, W0621, W0404, W0212, C1801
import coreapi
import logging
import requests

try:
    # pylint: disable=unused-import
    from pytest import allure
    # pylint: disable=unused-import
    import pytest
    IS_ALLURE = True
except ImportError:
    IS_ALLURE = False


logging.getLogger("urllib3").setLevel(logging.ERROR)


class APINode():
    pass


class ADCMApiError(Exception):
    pass


class ADCMApiWrapper():
    """Thin wrapper over ADCM API with coreapi (search django rest framework)
    Quick start:

    api =  ADCMApiWrapper()
    api.auth(username='admin', password='admin')

    Following function are equal and returns OrderedDict with API response:
    api.action(['cluster', 'list'])
    api.objects.cluster.list()

    Create and remove object:
    cluster = api.objects.cluster.create(name="test")
    api.objects.cluster.delete(cluster_id=cluster['id'])
    """

    def _fabric_function(self, node, path=None):
        if path is None:
            path = []

        def result(**kvargs):
            return self.action(path, params=kvargs)

        return result

    def _fabric_function_allure(self, node, path=None):
        # pylint: disable=no-member
        if path is None:
            path = []

        @pytest.allure.step(path[-1].title() + ' ' + path[-2])
        def result(**kvargs):
            return self.action(path, params=kvargs)

        return result

    def _parse_schema(self, node, is_allure=False, path=None):
        if path is None:
            path = []

        result = APINode()
        for funcname in node.links.keys():
            if is_allure:
                func = self._fabric_function_allure(node.links[funcname], path + [funcname])
            else:
                func = self._fabric_function(node.links[funcname], path + [funcname])
            setattr(result, funcname, func)

        for subnodename in node.data.keys():
            setattr(result,
                    subnodename,
                    self._parse_schema(node.data[subnodename], is_allure, path + [subnodename]))
        return result

    def __init__(self, url):
        """
        Init class with ADCM url.

        Example:
        api = ADCMApiWrapper('http://127.0.0.1:8000')
        """
        self.api_url = "/api/v1/"
        self.url = url
        self.client = None
        self.schema = None
        self.objects = None
        self.api_token = None

    def _check_for_error(self, data):
        if data is not None:
            if 'level' in data and data['level'] == 'error':
                raise ADCMApiError(data['code'], data['desc'])

    def auth(self, username, password):
        """Auth api client in ADCM and get schema"""

        result = requests.request(
            'POST', self.url + '/api/v1/token/',
            data={'username': username, 'password': password})
        token = result.json()
        self._check_for_error(token)
        auth = coreapi.auth.TokenAuthentication(
            scheme='Token',
            token=token['token']
        )
        self.client = coreapi.Client(auth=auth)
        self.schema = self.client.get("{}{}schema/".format(self.url, self.api_url))
        self.objects = self._parse_schema(self.schema, is_allure=IS_ALLURE)
        self.api_token = token['token']

    def action(self, *args, **kvargs):
        """
        Do operation over api. For information see coreapi documentation.

        Example:
        api.action(['cluster', 'create'], name='testcluster')
        """
        data = self.client.action(self.schema, *args, **kvargs)
        self._check_for_error(data)
        return data
