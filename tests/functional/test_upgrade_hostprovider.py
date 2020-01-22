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
    """Check default host and hostprovider config fields after upgrade
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_hostprovider'))
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create(fqdn="localhost")
    hostprovider_config_before = hostprovider.config()
    host_config_before = host.config()
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    host_config_after = host.config()
    assert hostprovider.prototype().version == '2.0'
    for variable in hostprovider_config_before:
        assert hostprovider_config_before[variable] == hostprovider_config_after[variable]
    for variable in host_config_before:
        assert host_config_before[variable] == host_config_after[variable]


def test_with_new_default_values(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider with new default fields. Old and new config values should be presented
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    upgr_bundle = sdk_client_fs.upload_from_fs(
        get_data_dir(__file__,
                     'upgradable_hostprovider_new_default_values'))
    upgr_hostprovider_prototype = upgr_bundle.provider_prototype().config
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create('localhost')
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    for variable in upgr_hostprovider_prototype:
        assert variable['value'] == hostprovider_config_after[variable['name']]


def test_with_new_default_variables(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider with new default fields.
     Old and new config variables should be presented
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    upgr_bundle = sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_hostprovider_new_default_variables'))
    upgr_hostprovider_prototype = upgr_bundle.provider_prototype().config
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create('localhost')
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    for variable in upgr_hostprovider_prototype:
        assert variable['name'] in hostprovider_config_after.keys()


def test_decrase_config(sdk_client_fs: ADCMClient):
    """Upgrade cluster with config without old values in config. Deleted lines not presented
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_hostprovider_decrase_variables'))
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create('localhost')
    hostprovider_config_before = hostprovider.config()
    host_config_before = host.config()
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    host_config_after = host.config()
    assert len(hostprovider_config_after.keys()) == 1
    assert len(host_config_after.keys()) == 1
    for key in hostprovider_config_after:
        assert hostprovider_config_before[key] == hostprovider_config_after[key]
    for key in host_config_after:
        assert host_config_before[key] == host_config_after[key]


def test_changed_variable_type(sdk_client_fs: ADCMClient):
    """Change config variable type for upgrade

    :param sdk_client_fs:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_hostprovider_change_variable_type'))
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create('localhost')
    hostprovider_config_before = hostprovider.config()
    host_config_before = host.config()
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    host_config_after = host.config()
    assert isinstance(hostprovider_config_after['required'], str)
    assert isinstance(hostprovider_config_after['int_key'], str)
    assert isinstance(host_config_after['str_param'], int)
    assert int(hostprovider_config_after['required']) == hostprovider_config_before['required']
    assert host_config_after['str_param'] == int(host_config_before['str_param'])


def test_multiple_upgrade_bundles(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider multiple time from version to another

    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'upgradable_hostprovider'))
    hostprovider = bundle.provider_create("test")
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    upgr = hostprovider.upgrade(name='upgrade 2')
    upgr.do()
    hostprovider.reread()
    assert hostprovider.state == 'ver2.4'


def test_change_config(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider with other config
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_hostprovider_new_change_values'))
    hostprovider = bundle.provider_create("test")
    host = hostprovider.host_create('localhost')
    hostprovider_config_before = hostprovider.config()
    host_config_before = host.config()
    hostprovider_config_before['required'] = 25
    hostprovider_config_before['str-key'] = "new_value"
    host_config_before['str_param'] = "str_param_new"
    hostprovider.config_set(hostprovider_config_before)
    host.config_set(host_config_before)
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    host.reread()
    hostprovider_config_after = hostprovider.config()
    host_config_after = host.config()
    assert len(hostprovider_config_before.keys()) == len(hostprovider_config_after.keys())
    for key in hostprovider_config_before:
        assert hostprovider_config_before[key] == hostprovider_config_after[key]
    for key in host_config_before:
        assert host_config_before[key] == host_config_after[key]


def test_cannot_upgrade_with_state(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider from unsupported state

    :param sdk_client_fs:
    :return:
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    sdk_client_fs.upload_from_fs(get_data_dir(
        __file__, 'upgradable_hostprovider_unsupported_state'))
    hostprovider = bundle.provider_create("test")
    upgr = hostprovider.upgrade(name='upgrade to 2.0')
    upgr.do()
    hostprovider.reread()
    upgr = hostprovider.upgrade(name='upgrade 2')
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    UPGRADE_ERROR.equal(e, 'provider state', 'is not in available states list')
