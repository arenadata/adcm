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

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir
from adcm_pytest_plugin import utils
from jsonschema import validate

# pylint: disable=E0401, W0601, W0611, W0621, W0212
from tests.library import errorcodes as err
from tests.library import steps
from tests.library.utils import get_random_service, get_random_host_prototype

SCHEMAS = os.path.join(os.path.dirname(__file__), "schemas/")

host_bad_configs = (({"str-key": "{1bbb}", "required": "158", "option": "my.host",
                      "sub": {"sub1": 3}, "credentials": {"sample_string": "test",
                                                          "read_only_initiated": 1}},
                     "should be integer"),
                    ({"str-key": 61, "required": 158, "fkey": 18.3,
                      "option": "my.host", "sub": {"sub1": 3},
                      "credentials": {"sample_string": "txt",
                                      "read_only_initiated": {}}},
                     'should be string'),
                    ({"str-key": "{1bbb}", "required": 158, "fkey": 18.3,
                      "option": "my.host", "sub": {"sub1": 9}},
                     'not in option list'),
                    ({"str-key": "{1bbb}", "required": 158, "option": 8080,
                      "sub": {"sub1": {"foo": "bar"}}},
                     'should be flat')
                    )


@pytest.fixture(scope="module")
def hostprovider(sdk_client_ms: ADCMClient):
    bundle = sdk_client_ms.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
    return bundle.provider_create(utils.random_string())


@pytest.fixture(scope="module")
def host(sdk_client_ms: ADCMClient, hostprovider):
    return hostprovider.host_create(utils.random_string())


@pytest.fixture(scope="module")
def cluster(sdk_client_ms: ADCMClient):
    return sdk_client_ms.upload_from_fs(get_data_dir(__file__, 'cluster_bundle'))


@pytest.fixture(scope="module")
def client(sdk_client_ms: ADCMClient, cluster, hostprovider):
    return sdk_client_ms.adcm()._api.objects


class TestHost:
    """
    Basic tests for host
    """
    def test_validate_host_prototype(self, client):
        host_prototype = json.loads(json.dumps(client.stack.host.list()[0]))
        schema = json.load(
            open(SCHEMAS + '/stack_list_item_schema.json')
        )
        with allure.step('Match prototype with schema'):
            assert validate(host_prototype, schema) is None
        steps.delete_all_data(client)

    def test_create_host(self, sdk_client_fs: ADCMClient):
        """Check that host have same fqdn and status after reread config
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        hp = bundle.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        host_status_before = host.status
        host_fqdn_before = host.fqdn
        with allure.step('Reread host'):
            host.reread()
            host_status_after = host.status
            host_fqdn_after = host.fqdn
        with allure.step('Check states and fqdn'):
            assert host_fqdn_before == host_fqdn_after
            assert host_status_before == host_status_after

    def test_shouldnt_create_duplicate_host(self, sdk_client_fs: ADCMClient):
        """We have restriction for create duplicated hosts (wuth the same fqdn).
        Scenario:
        1. Create hostprovider
        2. Create first host
        3. Create second host with the same FQDN
        4. Check that we've got 409 error for second host creation
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        hp.host_create("duplicate")
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            hp.host_create('duplicate')
        with allure.step('Check host conflict'):
            err.HOST_CONFLICT.equal(e, 'duplicate host')

    def test_shouldnt_create_host_with_unknown_prototype(self, client):
        with allure.step('Create provider'):
            provider_id = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                                 name=utils.random_string())['id']
        with allure.step('Create host'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.create(prototype_id=random.randint(100, 500),
                                   provider_id=provider_id,
                                   fqdn=utils.random_string())
        with allure.step('Check PROTOTYPE_NOT_FOUND error'):
            err.PROTOTYPE_NOT_FOUND.equal(e, 'prototype doesn\'t exist')

    def test_shouldnt_create_host_wo_prototype(self, client):
        with allure.step('Create provider'):
            provider = client.provider.create(prototype_id=client.stack.provider.list()[0]['id'],
                                              name=utils.random_string())
        with allure.step('Try to create host without prototype'):
            with pytest.raises(coreapi.exceptions.ParameterError) as e:
                client.host.create(provider_id=provider['id'], fqdn=utils.random_string())
        with allure.step('Check prototype_id error'):
            assert str(e.value) == "{'prototype_id': 'This parameter is required.'}"

    def test_shouldnt_create_host_wo_provider(self, client):
        with allure.step('Create prototype'):
            proto = get_random_host_prototype(client)
            with pytest.raises(coreapi.exceptions.ParameterError) as e:
                client.host.create(prototype_id=proto['id'], fqdn=utils.random_string())
        with allure.step('Check provider_id error'):
            assert str(e.value) == "{'provider_id': 'This parameter is required.'}"

    def test_create_host_with_max_length_plus_1(self, sdk_client_fs: ADCMClient):
        """We cannot create host with name more then max length
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            hp.host_create(utils.random_string(257))
        with allure.step('Check LONG_NAME error'):
            err.LONG_NAME.equal(e, 'Host name is too long. Max length is 256')

    def test_shouldnt_create_host_with_wrong_name(self, sdk_client_fs: ADCMClient):
        """Check  that host name cannot contain special characters
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            hp.host_create(utils.random_string() + utils.random_special_chars())
        with allure.step('Check WRONG_NAME error'):
            err.WRONG_NAME.equal(e, 'Host name is incorrect. '
                                    'Only latin characters, digits, dots (.)')

    def test_get_host_list(self, sdk_client_fs: ADCMClient):
        """Create multiple hosts and check that all hosts was created
        """
        expected_list = set()
        actual_list = set()
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        for fqdn in utils.random_string_list():
            hp.host_create(fqdn)
            expected_list.add(fqdn)
        for host in sdk_client_fs.host_list():
            actual_list.add(host.fqdn)
        with allure.step('Check created hosts with the data from the API'):
            assert actual_list == expected_list

    def test_get_host_info(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        actual = steps.read_host(client, host['id'])
        with allure.step('Check created host with the data from the API'):
            del actual['status']
            del host['status']
            assert actual == host

    def test_delete_host(self, sdk_client_fs: ADCMClient):
        """Check that we can delete host"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        host = hp.host_create("deletion_host")
        with allure.step('delete host'):
            deletion_result = host.delete()
        with allure.step('Check that host is deleted'):
            assert deletion_result is None

    def test_should_return_correct_error_when_read_deleted(self, sdk_client_fs: ADCMClient):
        """Check that we have 409 error if host not found"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        with allure.step('delete host'):
            host.delete()
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            host.reread()
        with allure.step('Check HOST_NOT_FOUND'):
            err.HOST_NOT_FOUND.equal(e)

    def test_should_return_correct_error_when_delete_nonexist_host(
            self, sdk_client_fs: ADCMClient):
        """If we try to delete deleted host we've got 409 error.
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        hp = bundle.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        with allure.step('delete host'):
            host.delete()
        with allure.step('delete host second time'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                host.delete()
        with allure.step('Check HOST_NOT_FOUND'):
            err.HOST_NOT_FOUND.equal(e, 'host doesn\'t exist')

    # *** Basic tests for hostcomponent ***
    def test_create_hostcomponent(self, sdk_client_fs: ADCMClient):
        """Check that hostcomponent id the same in component list and for service
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(
            __file__, 'cluster_service_hostcomponent'))
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_simple'))
        cluster = bundle.cluster_create(utils.random_string())
        hp = bundle_hp.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        cluster.host_add(host)
        service = cluster.service_add(name="ZOOKEEPER")
        component_list = service.component_list()
        component = service.component(name='ZOOKEEPER_CLIENT')
        with allure.step('Check component id and name'):
            assert component.component_id == component_list[0].component_id
            assert component.name == component_list[0].name

    def test_get_hostcomponent_list(self, client):  # invalid case, random component takes in circle
        cluster = steps.create_cluster(client)
        service = steps.read_service(client, get_random_service(client)['id'])
        cluster_svc = client.cluster.service.create(cluster_id=cluster['id'],
                                                    prototype_id=service['id'])
        components = client.cluster.service.component.list(cluster_id=cluster['id'],
                                                           service_id=cluster_svc['id'])
        # create mapping between cluster and hosts, then create hostcomponent on host
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


class TestHostConfig:
    """Class for test host configuration"""

    def test_config_history_url_must_point_to_the_host_config(self, client):
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = {"str-key": "{1bbb}", "required": 158, "option": 8080, "sub": {"sub1": 2},
                  "credentials": {"sample_string": "txt", "read_only_initiated": {}}}
        i = 0
        with allure.step('Create host history'):
            while i < random.randint(0, 10):
                client.host.config.history.create(host_id=host['id'],
                                                  description=utils.random_string(),
                                                  config=config)
                i += 1
            history = client.host.config.history.list(host_id=host['id'])
        with allure.step('Check host history'):
            for conf in history:
                assert ('host/{0}/config/'.format(host['id']) in conf['url']) is True
        steps.delete_all_data(client)

    def test_get_default_host_config(self, client):
        # Get a default host config and validate it with json schema
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config_json = {}
        with allure.step('Get default configuration from host'):
            config = client.host.config.current.list(host_id=host['id'])
        if config:
            config_json = json.loads(json.dumps(config))
        schema = json.load(open(SCHEMAS + '/config_item_schema.json'))
        with allure.step('Check config'):
            assert validate(config_json, schema) is None
        steps.delete_all_data(client)

    def test_get_config_from_nonexistant_host(self, sdk_client_fs: ADCMClient):
        """Get configuration for non exist host.
        """
        bundle_hp = sdk_client_fs.upload_from_fs(get_data_dir(
            __file__, 'hostprovider_simple'))
        hp = bundle_hp.provider_create(utils.random_string())
        with allure.step('Get host config from a non existant host'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                hp.host(host_id=random.randint(100, 500))
        with allure.step('Check error host doesn\'t exist'):
            err.HOST_NOT_FOUND.equal(e, 'host doesn\'t exist')

    def test_shouldnt_create_host_config_when_config_not_json_string(self, client):
        """Should not create host configuration when config string is not json
        """
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = utils.random_string()
        with allure.step('Try to create the host config from non-json string'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'], config=config)
        with allure.step('Check error config should not be just one string'):
            err.JSON_ERROR.equal(e, 'config should not be just one string')

    def test_shouldnt_create_host_config_when_config_is_number(self, client):
        """Should not create host configuration when config string is number
        """
        host = steps.create_host_w_default_provider(client, utils.random_string())
        config = random.randint(100, 999)
        with allure.step('Try to create the host configuration with a number'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                client.host.config.history.create(host_id=host['id'], config=config)
        with allure.step('Check error should not be just one int or float'):
            err.JSON_ERROR.equal(e, 'should not be just one int or float')

    @pytest.mark.parametrize(('config', 'error'), host_bad_configs)
    def test_change_host_config_negative(self, host, config, error):
        """Check that we have error if try to update host config with bad configuration
        :param host: host object
        :param config: dict with bad config
        :param error: expected error
        """
        with allure.step('Try to create config when parameter is not integer'):
            with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
                host.config_set(config)
        with allure.step(f'Check error {error}'):
            err.CONFIG_VALUE_ERROR.equal(e, error)

    def test_should_create_host_config_when_parameter_is_integer_and_not_float(
            self, sdk_client_fs: ADCMClient):
        """Create host config for float parameter with integer
        """
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider_bundle'))
        hp = bundle.provider_create(utils.random_string())
        host = hp.host_create(utils.random_string())
        config = {"str-key": "{1bbb}", "required": 158, "fkey": 18, "option": "my.host",
                  "sub": {"sub1": 3},
                  "credentials": {"sample_string": "txt", "read_only_initiated": {}}}
        host.config_set(config)
