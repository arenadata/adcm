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

"""Tests for cluster upgrade"""
import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir

from tests.library.errorcodes import UPGRADE_ERROR


def test_upgrade_with_two_clusters(sdk_client_fs: ADCMClient):
    """Upgrade cluster when we have two created clusters from one bundle
    Scenario:
    1. Create two clusters from one bundle
    2. Upload upgradable bundle
    3. Upgrade first cluster
    4. Check that only first cluster was upgraded
    """
    with allure.step('Create two clusters from one bundle'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster_first = bundle.cluster_create("test")
        cluster_second = bundle.cluster_create("test2")
        service = cluster_first.service_add(name="zookeeper")
    with allure.step('Upgrade first cluster'):
        upgr_cl = cluster_first.upgrade(name='upgrade to 1.6')
        upgr_cl.do()
    with allure.step('Check that only first cluster was upgraded'):
        cluster_first.reread()
        service.reread()
        cluster_second.reread()
        assert cluster_first.prototype().version == '1.6'
        assert service.prototype().version == '3.4.11'
        assert cluster_second.prototype().version == '1.5'


def test_check_prototype(sdk_client_fs: ADCMClient):
    """Check prototype for service and cluster after upgrade"""
    with allure.step('Create test cluster'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster = bundle.cluster_create("test")
        cl_id_before = cluster.id
        service = cluster.service_add(name="zookeeper")
        serv_id_before = service.id
        cluster_proto_before = cluster.prototype()
        service_proto_before = service.prototype()
    with allure.step('Upgrade test cluster to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check prototype'):
        cluster.reread()
        service.reread()
        cluster_proto_after = cluster.prototype()
        service_proto_after = service.prototype()
        assert cl_id_before == cluster.id
        assert serv_id_before == service.id
        assert cluster_proto_before.id != cluster_proto_after.id
        assert service_proto_before.id != service_proto_after.id


def test_multiple_upgrade_bundles(sdk_client_fs: ADCMClient):
    """Upgrade cluster multiple time from version to another"""
    with allure.step('Create upgradable cluster for multiple upgrade'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
        cluster = bundle.cluster_create("test")
    with allure.step('Upgrade cluster multiple time from version to another to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Upgrade second time cluster to 2'):
        cluster.reread()
        upgr = cluster.upgrade(name='upgrade 2')
        upgr.do()
    with allure.step('Check upgraded cluster'):
        cluster.reread()
        assert cluster.state == 'upgradated'


def test_change_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with other config"""
    with allure.step('Create upgradable cluster with new change values'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_new_change_values'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Set cluster and service config'):
        cluster_config_before = cluster.config()
        service_config_before = service.config()
        cluster_config_before['required'] = 25
        cluster_config_before['int_key'] = 245
        cluster_config_before['str-key'] = "new_value"
        service_config_before['required_service'] = 20
        service_config_before['int_key_service'] = 333
        cluster.config_set(cluster_config_before)
        service.config_set(service_config_before)
    with allure.step('Upgrade cluster with new change values to 1.6'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
    with allure.step('Check upgraded cluster and service'):
        cluster.reread()
        service.reread()
        cluster_config_after = cluster.config()
        service_config_after = service.config()
        assert len(cluster_config_before.keys()) == len(cluster_config_after.keys())
        for key in cluster_config_before:
            assert cluster_config_before[key] == cluster_config_after[key]
        for key in service_config_before:
            assert service_config_before[key] == service_config_after[key]


@allure.issue("https://arenadata.atlassian.net/browse/ADCM-1971")
def test_upgrade_cluster_with_config_groups(sdk_client_fs):
    """Test upgrade cluster config groups"""
    with allure.step('Create cluster with different groups on config'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster_with_groups'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_with_groups'))
        cluster = bundle.cluster_create("test")
        service = cluster.service_add(name="zookeeper")
    with allure.step('Upgrade cluster with new change values to 1.6'):
        upgrade = cluster.upgrade(name='upgrade to 1.6')
        upgrade.do()
    with allure.step('Assert that configs save success after upgrade'):
        cluster.config_set(
            {
                **cluster.config(),
                "activatable_group_with_ro": {"readonly-key": "value"},
                "activatable_group": {"required": 10, "writable-key": "value"},
            }
        )
        service.config_set(
            {
                **cluster.config(),
                "activatable_group_with_ro": {"readonly-key": "value"},
                "activatable_group": {"required": 10, "writable-key": "value"},
            }
        )


def test_cannot_upgrade_with_state(sdk_client_fs: ADCMClient):
    """Test upgrade should not be available ant stater"""
    with allure.step('Create upgradable cluster with unsupported state'):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_unsupported_state'))
        cluster = bundle.cluster_create("test")
    with allure.step('Upgrade cluster to 1.6 and then to 2'):
        upgr = cluster.upgrade(name='upgrade to 1.6')
        upgr.do()
        cluster.reread()
        upgr = cluster.upgrade(name='upgrade 2')
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            upgr.do()
    with allure.step('Check error: cluster state is not in available states list'):
        UPGRADE_ERROR.equal(e, 'cluster state', 'is not in available states list')

