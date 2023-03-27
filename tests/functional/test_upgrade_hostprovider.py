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

"""Tests for hostprovider update"""

import allure
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


@allure.step("Create host")
def create_host(hostprovider):
    """Create host"""
    return hostprovider.host_create("localhost")


# pylint: disable=too-many-locals
def test_upgrade_with_two_hostproviders(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider when we have two created hostproviders with hosts from one bundle
    Scenario:
    1. Create two hostproviders from one bundle
    2. Upload upgradable bundle
    3. Create host for each hostprovider
    4. Upgrade first hostprovider
    5. Check that only first hostprovider and hosts was upgraded
    """
    with allure.step("Create two hostproviders from one bundle. Upload upgradable bundle"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider"))
        hostprovider_first = bundle.provider_create("hp_first")
        hostprovider_first_proto_before = hostprovider_first.prototype()
        hostprovider_first_id_before = hostprovider_first.id
        hostprovider_second = bundle.provider_create("hp_second")
        hostprovider_second_proto_before = hostprovider_second.prototype()
        hostprovider_second_id_before = hostprovider_second.id
    with allure.step("Create host for each hostprovider"):
        hp1_host1 = hostprovider_first.host_create(fqdn="localhost")
        hp1_host1_id_before = hp1_host1.id
        hp1_host1_proto_before = hp1_host1.prototype()
        hp1_host2 = hostprovider_first.host_create(fqdn="localhost2")
        hp1_host3 = hostprovider_first.host_create(fqdn="localhost3")
        hp2_host1 = hostprovider_second.host_create(fqdn="hp2-localhost")
        hp2_host1_proto_before = hp2_host1.prototype()
        hp2_host1_id_before = hp2_host1.id
        hp2_host2 = hostprovider_second.host_create(fqdn="hp2-localhost2")
        hp2_host3 = hostprovider_second.host_create(fqdn="hp2-localhost3")
    with allure.step("Upgrade first hostprovider"):
        upgr = hostprovider_first.upgrade(name="upgrade to 2.0")
        upgr.do()
    with allure.step("Check that only first hostprovider and hosts was upgraded"):
        hostprovider_first.reread()
        hostprovider_second.reread()
        hp1_host1.reread()
        hp1_host2.reread()
        hp1_host3.reread()
        hp2_host1.reread()
        hp2_host2.reread()
        hp2_host3.reread()
        hp_first_proto_after = hostprovider_first.prototype()
        hp1_host_proto_after = hp1_host1.prototype()
        hp_second_proto_after = hostprovider_second.prototype()
        hp2_host1_proto_after = hp2_host1.prototype()
        assert hostprovider_first.prototype().version == "2.0"
        assert hp1_host1.prototype().version == "00.10"
        assert hostprovider_second.prototype().version == "1.0"
        assert hp2_host1.prototype().version == "00.09"
        assert hostprovider_first_id_before == hostprovider_first.id
        assert hp1_host1_id_before == hp1_host1.id
        assert hostprovider_first_proto_before.id != hp_first_proto_after.id
        assert hp1_host1_proto_before.id != hp1_host_proto_after.id

        assert hostprovider_second_id_before == hostprovider_second.id
        assert hp2_host1_id_before == hp2_host1.id
        assert hostprovider_second_proto_before.id == hp_second_proto_after.id
        assert hp2_host1_proto_before.id == hp2_host1_proto_after.id


def test_check_prototype(sdk_client_fs: ADCMClient):
    """Check prototype for provider and host after upgrade"""
    with allure.step("Create upgradable hostprovider and get id"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider"))
        hostprovider = bundle.provider_create("test")
        host = hostprovider.host_create(fqdn="localhost")
        hostprovider_proto_before = hostprovider.prototype()
        hp_id_before = hostprovider.id
        host_proto_before = host.prototype()
        ht_id_before = host.id
    with allure.step("Upgrade hostprovider to 2.0"):
        upgr = hostprovider.upgrade(name="upgrade to 2.0")
        upgr.do()
    with allure.step("Check prototype for provider and host after upgrade"):
        hostprovider.reread()
        host.reread()
        hostprovider_proto_after = hostprovider.prototype()
        host_proto_after = host.prototype()
        assert hp_id_before == hostprovider.id
        assert ht_id_before == host.id
        assert hostprovider_proto_before.id != hostprovider_proto_after.id
        assert host_proto_before.id != host_proto_after.id


def test_multiple_upgrade_bundles(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider multiple time from version to another"""
    with allure.step("Create upgradable hostprovider"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider"))
        hostprovider = bundle.provider_create("test")
    with allure.step("First upgrade hostprovider to 2.0"):
        upgr = hostprovider.upgrade(name="upgrade to 2.0")
        upgr.do()
        hostprovider.reread()
    with allure.step("Second upgrade hostprovider to 2"):
        upgr = hostprovider.upgrade(name="upgrade 2")
        upgr.do()
    with allure.step("Check hostprovider state"):
        hostprovider.reread()
        assert hostprovider.state == "ver2.4"


def test_change_config(sdk_client_fs: ADCMClient):
    """Upgrade hostprovider with other config"""
    with allure.step("Create upgradable hostprovider with new change values"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider_new_change_values"))
        hostprovider = bundle.provider_create("test")
    host = create_host(hostprovider)
    hostprovider_config_before = hostprovider.config()
    host_config_before = host.config()
    hostprovider_config_before["required"] = 25
    hostprovider_config_before["str-key"] = "new_value"
    host_config_before["str_param"] = "str_param_new"
    with allure.step("Set config"):
        hostprovider.config_set(hostprovider_config_before)
        host.config_set(host_config_before)
    with allure.step("Upgrade hostprovider with other config"):
        upgr = hostprovider.upgrade(name="upgrade to 2.0")
        upgr.do()
    with allure.step("Check hostprovider config"):
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
    """Upgrade hostprovider from unsupported state"""
    with allure.step("Create hostprovider with unsupported state"):
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider_unsupported_state"))
        hostprovider = bundle.provider_create("test")
    with allure.step("Upgrade hostprovider from unsupported state"):
        upgr = hostprovider.upgrade(name="upgrade to 2.0")
        upgr.do()
        hostprovider.reread()
        assert len(hostprovider.upgrade_list()) == 0, "No upgrade should be available at new state"
