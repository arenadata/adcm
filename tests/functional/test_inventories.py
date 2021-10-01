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

import allure
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.docker_utils import get_file_from_container
from adcm_pytest_plugin.utils import random_string

from tests.functional.conftest import only_clean_adcm

pytestmark = [only_clean_adcm]


def test_check_inventories_file(adcm_fs, sdk_client_fs):
    """Assert inventory file contents for the action"""
    bundledir = utils.get_data_dir(__file__, 'cluster_inventory_tests')
    cluster_bundle = sdk_client_fs.upload_from_fs(bundledir)
    with allure.step('Create cluster'):
        cluster_name = "dumMxpQA"
        cluster = cluster_bundle.cluster_prototype().cluster_create(cluster_name)
        cluster.service_add(name="zookeeper")
        cluster.action(name="install").run().try_wait()
    with allure.step('Get inventory file from container'):
        text = get_file_from_container(adcm_fs, '/adcm/data/run/1/', 'inventory.json')
        inventory = json.loads(text.read().decode('utf8'))
    with allure.step('Check inventory file'):
        with open(utils.get_data_dir(__file__, 'cluster-inventory.json'), 'rb') as template:
            expected = json.loads(template.read().decode('utf8'))
            assert inventory == expected
