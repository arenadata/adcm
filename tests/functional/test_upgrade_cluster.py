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
# pylint: disable=W0611, W0621
import coreapi
import pytest

from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir

from tests.library.errorcodes import UPGRADE_ERROR


def test_check_config(sdk_client_fs: ADCMClient):
    """Check default service and cluster config fields after upgrade
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert cluster.prototype().version == '1.6'
    for variable in cluster_config_before:
        assert cluster_config_before[variable] == cluster_config_after[variable]
    for variable in service_config_before:
        assert service_config_before[variable] == service_config_after[variable]


def test_with_new_default_values(sdk_client_fs: ADCMClient):
    """Upgrade cluster with new default fields. Old and new config values should be presented
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    upgr_bundle = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_new_default_values'))
    upgr_cluster_prototype = upgr_bundle.cluster_prototype().config
    upgr_service_prototype = upgr_bundle.service_prototype().config
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    for variable in upgr_cluster_prototype:
        assert variable['value'] == cluster_config_after[variable['name']]
    for variable in upgr_service_prototype:
        assert variable['value'] == service_config_after[variable['name']]


def test_with_new_default_variables(sdk_client_fs: ADCMClient):
    """Upgrade cluster with new default fields. Old and new config variables should be presented
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    upgr_bundle = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_new_default_variables'))
    upgr_cluster_prototype = upgr_bundle.cluster_prototype().config
    upgr_service_prototype = upgr_bundle.service_prototype().config
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    for variable in upgr_cluster_prototype:
        assert variable['name'] in cluster_config_after.keys()
    for variable in upgr_service_prototype:
        assert variable['name'] in service_config_after.keys()


def test_decrase_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with config without old values in config. Deleted lines not presented
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_decrase_variables'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert len(cluster_config_after.keys()) == 1
    assert len(service_config_after.keys()) == 1
    for key in cluster_config_after:
        assert cluster_config_before[key] == cluster_config_after[key]
    for key in service_config_after:
        assert service_config_before[key] == service_config_after[key]


def test_changed_variable_type(sdk_client_fs: ADCMClient):
    """Change config variable type for upgrade

    :param sdk_client_fs:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_cluster_change_variable_type'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert isinstance(cluster_config_after['required'], str)
    assert isinstance(service_config_after['required_service'], str)
    assert int(cluster_config_after['required']) == cluster_config_before['required']
    assert int(service_config_after[
                   'required_service']) == service_config_before['required_service']


def test_multiple_upgrade_bundles(sdk_client_fs: ADCMClient):
    """Upgrade cluster multiple time from version to another

    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster'))
    cluster = bundle.cluster_create("test")
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    upgr = cluster.upgrade(name='upgrade 2')
    upgr.do()
    cluster.reread()
    assert cluster.state == 'upgradated'


def test_change_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with other config
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_new_change_values'))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    cluster_config_before = cluster.config()
    service_config_before = service.config()
    cluster_config_before['required'] = 25
    cluster_config_before['int_key'] = 245
    cluster_config_before['str-key'] = "new_value"
    service_config_before['required_service'] = 20
    service_config_before['int_key_service'] = 333
    cluster.config_set(cluster_config_before)
    service.config_set(service_config_before)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    service.reread()
    cluster_config_after = cluster.config()
    service_config_after = service.config()
    assert len(cluster_config_before.keys()) == len(cluster_config_after.keys())
    for key in cluster_config_before:
        assert cluster_config_before[key] == cluster_config_after[key]
    for key in service_config_before:
        assert service_config_before[key] == service_config_after[key]


def test_cannot_upgrade_with_state(sdk_client_fs: ADCMClient):
    """

    :param sdk_client_fs:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'cluster'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_cluster_unsupported_state'))
    cluster = bundle.cluster_create("test")
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    upgr = cluster.upgrade(name='upgrade 2')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    UPGRADE_ERROR.equal(e, 'cluster state', 'is not in available states list')


