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

"""Tests extracted from test_stacks"""

import os

import allure
import pytest
from adcm_pytest_plugin import utils

# pylint: disable=redefined-outer-name, protected-access
from adcm_pytest_plugin.docker_utils import ADCM


@allure.step('Load default stack')
def load_default_stack(client):
    client.stack.load.update()
    return client.stack.host.list()


@pytest.fixture()
def client(adcm_fs: ADCM):
    return adcm_fs.api.objects


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_cluster_proto_and_update(client):
    volumes = {
        utils.get_data_dir(__file__) + 'add_param_in_cluster_proto': {
            'bind': '/adcm/stack/', 'mode': 'rw'}
    }

    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'
    proto_list = load_default_stack(client)
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    with allure.step('Updated cluster'):
        updated_cluster = client.stack.cluster.read(prototype_id=proto_list[0]['id'])
    with allure.step('Check updated cluster'):
        expected = [d['name'] for d in updated_cluster['config']]
        assert ('test_key' in expected) is True


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_host_proto_and_update(client):
    volumes = {
        utils.get_data_dir(__file__) + 'add_param_in_host_proto': {
            'bind': '/adcm/stack/', 'mode': 'rw'}
    }

    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'
    proto_list = load_default_stack(client)
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    with allure.step('Updated host'):
        updated_proto = client.stack.host.read(prototype_id=proto_list[0]['id'])
    with allure.step('Check updated host'):
        expected = [d['name'] for d in updated_proto['config']]
        assert ('test_key' in expected) is True


@pytest.mark.skip(reason="no way of currently testing this")
def test_add_config_parameter_in_service_prototype_and_update(client):
    volumes = {
        utils.get_data_dir(__file__) + 'add_param_in_service_proto': {
            'bind': '/adcm/stack/', 'mode': 'rw'}
    }
    path = next(iter(volumes))
    config = path + '/config.yaml'
    updated = path + '/updated_config.yaml'
    proto_list = load_default_stack(client)
    os.rename(config, path + '/config.bak')
    os.rename(updated, config)
    client.stack.load.update()
    with allure.step('Update service'):
        updated_proto = client.stack.service.read(service_id=proto_list[0]['id'])
    with allure.step('Check updated service'):
        expected = [d['name'] for d in updated_proto['config']]
        assert ('test_key' in expected) is True
