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

"""Tests for service delete method"""
import allure
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


def test_delete_service(sdk_client_fs: ADCMClient):
    """
    If host has NO component, then we can simply remove it from cluster.
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster.reread()
    with allure.step("Ensure there's a concern on cluster from service's config"):
        assert len(cluster.concerns()) > 0, 'There should be a concern on cluster from config of the service'
    with allure.step('Delete service'):
        service.delete()
    with allure.step('Ensure that concern is gone from cluster after service removal'):
        cluster.reread()
        assert len(cluster.concerns()) == 0, 'Concern on cluster should be removed alongside with the service'
