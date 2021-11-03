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

"""Tests for actions inventory"""

import json

from uuid import uuid4

import allure
import pytest

from _pytest.fixtures import SubRequest
from adcm_client.objects import Provider, ADCMClient, Cluster, ADCM
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import get_file_from_container
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

from tests.functional.tools import create_config_group_and_add_host
from tests.functional.conftest import only_clean_adcm

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]


HOST_FQDN = 'awesome-future'
CLUSTER_NAME = 'dumMxpQA'
GROUP_COMPONENT_NAME = 'GROUP_BUDDY'

CONFIG_TO_CHANGE = {
    'config': {
        'json_field': {'there_is': 'no one'},
        'map_field': {'here': 'but me'},
        '__main_info': "I'm a very important string, don't touch me",
        'simple_field': 1,
    },
    'attr': {
        'group_keys': {'json_field': True, 'map_field': True, 'simple_field': False, '__main_info': False},
        'custom_group_keys': {'json_field': True, 'map_field': True, 'simple_field': True, '__main_info': False},
    },
}


@allure.title('Create provider')
@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Get dummy provider"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'provider'))
    return bundle.provider_create(name='test_provider')


@allure.title('Create cluster')
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """Get cluster for inventory check"""
    cluster_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, 'cluster_inventory_tests'))
    return cluster_bundle.cluster_prototype().cluster_create(CLUSTER_NAME)


def test_check_inventories_file(cluster: Cluster, provider: Provider, adcm_fs: ADCM, request: SubRequest):
    """Assert inventory file contents for the action"""
    host = provider.host_create(fqdn=HOST_FQDN)
    with allure.step('Configure cluster'):
        service = cluster.service_add(name="zookeeper")
        cluster.host_add(host)
        component = service.component(name=GROUP_COMPONENT_NAME)
        cluster.hostcomponent_set((host, component))
    with allure.step(f'Create config group with {GROUP_COMPONENT_NAME} and change it'):
        config_group = create_config_group_and_add_host('group_name', component, host)
        config_group.config_set(CONFIG_TO_CHANGE)
    with allure.step('Run actions on cluster'):
        run_cluster_action_and_assert_result(cluster, "set_multi_states")
        run_cluster_action_and_assert_result(cluster, "install")
    with allure.step('Get inventory file from container'):
        text = get_file_from_container(adcm_fs, '/adcm/data/run/2/', 'inventory.json')
        inventory_content = text.read().decode('utf8')
        inventory = json.loads(inventory_content)
        _attach_inventory_file(request, inventory_content, 'Actual content of inventory.json')
    with allure.step('Get expected inventory file'):
        with open(utils.get_data_dir(__file__, 'cluster-inventory.json'), 'rb') as template:
            expected_content = template.read().decode('utf8')
            expected = json.loads(expected_content)
        _attach_inventory_file(request, expected_content, 'Expected content of inventory.json')
    with allure.step('Compare actual and expected config'):
        assert (
            inventory == expected
        ), "Content of file inventory.json doesn't match expected. See attachments for more info."


def _attach_inventory_file(request: SubRequest, inventory_content: str, name: str):
    """Attach inventory file on top level of allure report"""
    reporter = utils.allure_reporter(request.config)
    if not reporter:
        return
    test_result = reporter.get_test(uuid=None)
    reporter.attach_data(
        uuid=uuid4(),
        body=inventory_content,
        name=name,
        attachment_type=allure.attachment_type.JSON,
        parent_uuid=test_result.uuid,
    )
