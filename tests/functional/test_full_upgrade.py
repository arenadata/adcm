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

"""Tests for full update of objects"""

import allure
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.utils import get_data_dir


def test_full_upgrade_hostprovider_first(sdk_client_fs: ADCMClient):
    """Create cluster and hostprovider with host and components
     and upgrade cluster and host with provider after that
    and check that all was upgraded.
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster"))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    comp = service.component(name="master")
    hp_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider"))
    hostprovider = hp_bundle.provider_create("test")
    host = hostprovider.host_create(fqdn="localhost")
    cluster.host_add(host)
    cluster.hostcomponent_set((host, comp))
    upgr_hp = hostprovider.upgrade(name="upgrade to 2.0")
    upgr_hp.do()
    upgr_cl = cluster.upgrade(name="upgrade to 1.6")
    upgr_cl.do()
    cluster.reread()
    service.reread()
    hostprovider.reread()
    host.reread()
    with allure.step("Check cluster, service, hostprovider, host were upgraded"):
        assert cluster.prototype().version == "1.6"
        assert service.prototype().version == "3.4.11"
        assert hostprovider.prototype().version == "2.0"
        assert host.prototype().version == "00.10"


def test_full_upgrade_cluster_first(sdk_client_fs: ADCMClient):
    """Create cluster and hostprovider with host and components
     and upgrade cluster and host with provider after that
    and check that all was upgraded.
    """
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_cluster"))
    cluster = bundle.cluster_create("test")
    service = cluster.service_add(name="zookeeper")
    comp = service.component(name="master")
    hp_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgradable_hostprovider"))
    hostprovider = hp_bundle.provider_create("test")
    host = hostprovider.host_create(fqdn="localhost")
    cluster.host_add(host)
    cluster.hostcomponent_set((host, comp))
    upgr_cl = cluster.upgrade(name="upgrade to 1.6")
    upgr_cl.do()
    upgr_hp = hostprovider.upgrade(name="upgrade to 2.0")
    upgr_hp.do()
    cluster.reread()
    service.reread()
    hostprovider.reread()
    host.reread()
    with allure.step("Check cluster, service, hostprovider, host were upgraded"):
        assert cluster.prototype().version == "1.6"
        assert service.prototype().version == "3.4.11"
        assert hostprovider.prototype().version == "2.0"
        assert host.prototype().version == "00.10"
