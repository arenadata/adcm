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
import random

import allure
import coreapi
import pytest
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker import DockerWrapper
from jsonschema import validate

# pylint: disable=E0401, W0601, W0611, W0621
from tests.library import errorcodes as err
from tests.library import steps

BUNDLES = os.path.join(os.path.dirname(__file__), "../stack/")
SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")


@pytest.fixture(scope="module")
def adcm(image, request):
    repo, tag = image
    dw = DockerWrapper()
    adcm = dw.run_adcm(image=repo, tag=tag, pull=False)
    adcm.api.auth(username='admin', password='admin')

    def fin():
        adcm.stop()

    request.addfinalizer(fin)
    return adcm


@pytest.fixture(scope="module")
def client(adcm):
    steps.upload_bundle(adcm.api.objects, BUNDLES + "cluster_bundle")
    steps.upload_bundle(adcm.api.objects, BUNDLES + "hostprovider_bundle")
    return adcm.api.objects


class TestHost:
    # *** Basic tests for hosts ***

    def test_validate_host_prototype(self, client):
        host_prototype = json.loads(json.dumps(client.stack.host.list()[0]))
        schema = json.load(
            open(SCHEMAS + '/stack_list_item_schema.json')
        )
        with allure.step('Match prototype with schema'):
            assert validate(host_prototype, schema) is None
        steps.delete_all_data(client)

    def test_create_host(self, client):
        actual = steps.create_host_w_default_provider(client, utils.random_string())
        expected = steps.read_host(client, actual['id'])

        # status is a variable, so it is no good to compare it
        assert 'status' in actual
        assert 'status' in expected
        del actual['status']
        del expected['status']
        with allure.step('Check created host with the data from the API'):
            assert actual == expected
        steps.delete_all_data(client)

    def test_shouldnt_create_duplicate_host(self, client):
        steps.create_host_w_default_provider(client, 'duplicate')
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.create_host_w_default_provider(client, 'duplicate')
        err.HOST_CONFLICT.equal(e, 'duplicate host')
        steps.delete_all_data(client)

    def test_shouldnt_create_host_with_unknown_prototype(self, client):
        provider_id = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                             name=utils.random_string())['id']
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.host.create(prototype_id=random.randint(100, 500),
                               provider_id=provider_id,
                               fqdn=utils.random_string())
        err.PROTOTYPE_NOT_FOUND.equal(e, 'prototype doesn\'t exist')
        steps.delete_all_data(client)

    def test_shouldnt_create_host_wo_prototype(self, client):
        provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                          name=utils.random_string())
        with allure.step('Try to create host without prototype'):
            with pytest.raises(coreapi.exceptions.ParameterError) as e:
                client.host.create(provider_id=provider['id'], fqdn=utils.random_string())
            assert str(e.value) == "{'prototype_id': 'This parameter is required.'}"
        steps.delete_all_data(client)

    def test_shouldnt_create_host_wo_provider(self, client):
        proto = utils.get_random_host_prototype(client)
        with pytest.raises(coreapi.exceptions.ParameterError) as e:
            client.host.create(prototype_id=proto['id'], fqdn=utils.random_string())
        assert str(e.value) == "{'provider_id': 'This parameter is required.'}"
        steps.delete_all_data(client)

    def test_create_host_with_max_length_plus_1(self, client):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.create_host_w_default_provider(client, utils.random_string(257))
        err.LONG_NAME.equal(e, 'Host name is too long. Max length is 256')
        steps.delete_all_data(client)

    def test_shouldnt_create_host_with_wrong_name(self, client):
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            steps.create_host_w_default_provider(
                client, utils.random_string() + utils.random_special_chars())
        err.WRONG_NAME.equal(e, 'Host name is incorrect. Only latin characters, digits, dots (.)')
        steps.delete_all_data(client)

    def test_get_host_list(self, client):
        expected_list = []
        actual_list = []
        for fqdn in utils.random_string_list():
            steps.create_host_w_default_provider(client, fqdn)
            expected_list.append(fqdn)
        for host in client.host.list():
            actual_list.append(host['fqdn'])
        with allure.step('Check created hosts with the data from the API'):
            assert actual_list == expected_list
        steps.delete_all_data(client)

    def test_get_host_info(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        actual = steps.read_host(client, host['id'])
        with allure.step('Check created host with the data from the API'):
            del actual['status']
            del host['status']
            assert actual == host
        steps.delete_all_data(client)

    def test_delete_host(self, client):
        expected = None
        host = steps.create_host_w_default_provider(client, utils.random_string())
        with allure.step('Delete host'):
            actual = client.host.delete(host_id=host['id'])
        with allure.step('Check that answer is equals None'):
            assert actual == expected
        steps.delete_all_data(client)

    def test_should_return_correct_error_when_read_deleted(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        steps.delete_all_hosts(client)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            with allure.step('Try to get info about deleted host'):
                steps.read_host(client, host['id'])
            err.HOST_NOT_FOUND.equal(e)
        steps.delete_all_data(client)

    def test_should_return_correct_error_when_delete_nonexist_host(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        steps.delete_all_hosts(client)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            client.host.delete(host_id=host['id'])
        err.HOST_NOT_FOUND.equal(e, 'host doesn\'t exist')

    # *** Basic tests for hostcomponent ***
    def test_create_hostcomponent(self, client):
        cluster = steps.create_cluster(client)
        host = steps.create_host_w_default_provider(client, utils.random_string())
        steps.add_host_to_cluster(client, host, cluster)
        service_proto = steps.read_service(client, utils.get_random_service(client)['id'])
        cluster_svc = client.cluster.service.create(cluster_id=cluster['id'],
                                                    prototype_id=service_proto['id'])
        component = client.cluster.service.component.list(cluster_id=cluster['id'],
                                                          service_id=cluster_svc['id'])[0]
        actual = client.cluster.hostcomponent.create(cluster_id=cluster['id'],
                                                     hc=[{"host_id": host['id'],
                                                          "service_id": cluster_svc['id'],
                                                          "component_id": component['id']}])
        expected = client.cluster.hostcomponent.read(cluster_id=cluster['id'],
                                                     hs_id=actual[0]['id'])
        assert actual[0] == expected
        steps.delete_all_data(client)

    def test_get_hostcomponent_list(self, client):  # invalid case, random component takes in circle
        cluster = steps.create_cluster(client)
        service = steps.read_service(client, utils.get_random_service(client)['id'])
        cluster_svc = client.cluster.service.create(cluster_id=cluster['id'],
                                                    prototype_id=service['id'])
        components = client.cluster.service.component.list(cluster_id=cluster['id'],
                                                           service_id=cluster_svc['id'])
        # create mapping between cluster and hosts, then create hostcomponent on host
        expected_hostcomponent_list = []
        hostcomponent_list = []
        for fqdn in utils.random_string_list():
            host = steps.create_host_w_default_provider(client, fqdn)
            steps.add_host_to_cluster(client, host, cluster)
            component = random.choice(components)['id']
            hostcomponent_list.append({"host_id": host['id'], "service_id": cluster_svc['id'],
                                       "component_id": component})
        expected_hostcomponent_list = client.cluster.hostcomponent.create(
            cluster_id=cluster['id'], hc=hostcomponent_list)
        actual_hs_list = client.cluster.hostcomponent.list(cluster_id=cluster['id'])
        with allure.step('Check created data with data from API'):
            assert actual_hs_list == expected_hostcomponent_list
        steps.delete_all_data(client)


class TestHostConfig:

    def test_config_history_url_must_point_to_the_host_config(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = {"str-key": "{1bbb}", "required": 158, "option": 8080, "sub": {"sub1": 2},
                  "credentials": {"sample_string": "txt", "read_only_initiated": {}}}
        i = 0
        while i < random.randint(0, 10):
            client.host.config.history.create(host_id=host['id'],
                                              description=utils.random_string(),
                                              config=config)
            i += 1
        history = client.host.config.history.list(host_id=host['id'])
        for conf in history:
            assert ('host/{0}/config/'.format(host['id']) in conf['url']) is True
        steps.delete_all_data(client)

    def test_get_default_host_config(self, client):
        # Get a default host config and validate it with json schema
        host = steps.create_host_w_default_provider(client, utils.random_string())
        with allure.step('Get default configuration from host'):
            config = client.host.config.current.list(host_id=host['id'])
        if config:
            config_json = json.loads(json.dumps(config))
        schema = json.load(open(SCHEMAS + '/config_item_schema.json'))
        assert validate(config_json, schema) is None
        steps.delete_all_data(client)

    def test_get_config_from_nonexistant_host(self, client):
        # Get the configuration from a non existant host
        with allure.step('Get host config from a non existant host'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.list(host_id=random.randint(100, 500))
            err.HOST_NOT_FOUND.equal(e, 'host doesn\'t exist')
        steps.delete_all_data(client)

    def test_shouldnt_create_host_config_when_config_not_json_string(self, client):
        # Should not create host configuration when config string is not json
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = utils.random_string()
        with allure.step('Try to create the host config from non-json string'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'], config=config)
            err.JSON_ERROR.equal(e, 'config should not be just one string')

    def test_shouldnt_create_host_config_when_config_is_number(self, client):
        # Should not create host configuration when config string is number
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = random.randint(100, 999)
        with allure.step('Try to create the host configuration with a number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'], config=config)
                err.JSON_ERROR.equal(e, 'should not be just one int or float')

    def test_shouldnt_create_host_config_when_parameter_is_not_integer(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config_w_illegal_param = {"str-key": "{1bbb}",
                                  "required": "158",
                                  "option": "my.host",
                                  "sub": {"sub1": 3},
                                  "credentials": {
                                      "sample_string": "test",
                                      "read_only_initiated": 1}}
        with allure.step('Try to create config when parameter is not integer'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'],
                                                  description=utils.random_string(),
                                                  config=config_w_illegal_param)
            err.CONFIG_VALUE_ERROR.equal(e, 'should be integer')

    def test_should_create_host_config_when_parameter_is_integer_and_not_float(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config_w_illegal_param = {"str-key": "{1bbb}",
                                  "required": 158,
                                  "fkey": 18,
                                  "option": "my.host",
                                  "sub": {"sub1": 3},
                                  "credentials": {"sample_string": "txt",
                                                  "read_only_initiated": {}
                                                  }
                                  }

        client.host.config.history.create(host_id=host['id'],
                                          description=utils.random_string(),
                                          config=config_w_illegal_param)

    def test_shouldnt_create_host_config_when_parameter_is_not_string(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config_w_illegal_param = {"str-key": 61, "required": 158, "fkey": 18.3,
                                  "option": "my.host", "sub": {"sub1": 3},
                                  "credentials": {"sample_string": "txt",
                                                  "read_only_initiated": {}}}
        with allure.step('Try to create config when param is not float'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'],
                                                  description=utils.random_string(),
                                                  config=config_w_illegal_param)
            err.CONFIG_VALUE_ERROR.equal(e, 'should be string')

    def test_shouldnt_create_host_config_when_parameter_is_not_in_option_list(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config_w_illegal_param = {"str-key": "{1bbb}", "required": 158, "fkey": 18.3,
                                  "option": "my.host", "sub": {"sub1": 9}}
        with allure.step('Try to create config has not option in a list'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'],
                                                  description=utils.random_string(),
                                                  config=config_w_illegal_param)
            err.CONFIG_VALUE_ERROR.equal(e, 'not in option list')

    def test_shouldnt_create_host_config_when_subkey_has_dict_value(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        broken_config = {"str-key": "{1bbb}", "required": 158, "option": 8080,
                         "sub": {"sub1": {"foo": "bar"}}}
        with allure.step('Try to create config that has a subkey with dict value'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'],
                                                  description=utils.random_string(),
                                                  config=broken_config)
            err.CONFIG_VALUE_ERROR.equal(e, 'should be flat')
