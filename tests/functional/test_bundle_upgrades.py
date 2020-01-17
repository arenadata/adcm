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
import os

import coreapi
import pytest
from adcm_pytest_plugin import utils

# pylint: disable=W0611, W0621
from adcm_client.objects import ADCMClient
from tests.library.errorcodes import (INVALID_UPGRADE_DEFINITION,
                                      UPGRADE_ERROR)

BUNDLES = os.path.join(os.path.dirname(__file__), "stacks/")


@pytest.fixture(scope="module")
def cluster_bundles():
    bundle = os.path.join(BUNDLES, "cluster_bundle_before_upgrade")
    upgrade_bundle = os.path.join(BUNDLES, "upgradable_cluster_bundle")
    return bundle, upgrade_bundle


@pytest.fixture(scope="module")
def host_bundles():
    bundle = os.path.join(BUNDLES, "host_bundle_before_upgrade")
    upgrade_bundle = os.path.join(BUNDLES, "upgradable_host_bundle")
    return bundle, upgrade_bundle


def test_a_cluster_bundle_upgrade_will_ends_successfully(sdk_client_fs: ADCMClient, cluster_bundles):
    bundle, upgrade_bundle = cluster_bundles
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle)
    cluster = cluster_bundle.cluster_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    assert cluster.state == 'upgradable'


def test_shouldnt_upgrade_upgrated_cluster(sdk_client_fs: ADCMClient, cluster_bundles):
    bundle, upgrade_bundle = cluster_bundles
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle)
    cluster = cluster_bundle.cluster_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = cluster.upgrade(name='upgrade to 1.6')
    upgr.do()
    cluster.reread()
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    UPGRADE_ERROR.equal(e, 'cluster version', 'is more than upgrade max version')


@pytest.mark.skip(reason="Test must be changed for provider's upgrade procedure")
def test_a_host_bundle_upgrade_will_ends_successfully(sdk_client_fs: ADCMClient, host_bundles):
    bundle, upgrade_bundle = host_bundles
    hostprovider_bundle = sdk_client_fs.upload_from_fs(bundle)
    hostprovider = hostprovider_bundle.provider_create("test")
    host = hostprovider.host_create("localhost")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = host.upgrade(name='upgrade to 2.0')
    upgr.do()
    host.reread()
    assert host.state == 'upgradable'


@pytest.mark.skip(reason="Test must be changed for provider's upgrade procedure")
def test_shouldnt_upgrade_upgrated_host(sdk_client_fs: ADCMClient, host_bundles):
    bundle, upgrade_bundle = host_bundles
    hostprovider_bundle = sdk_client_fs.upload_from_fs(bundle)
    hostprovider = hostprovider_bundle.provider_create("test")
    host = hostprovider.host_create("localhost")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = host.upgrade(name='upgrade to 2.0')
    upgr.do()
    host.reread()
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    UPGRADE_ERROR.equal(e)
    assert 'host version' in e.value.error['desc']
    assert 'is more than upgrade max version' in e.value.error['desc']


def test_upgrade_cluster_without_old_config(sdk_client_fs: ADCMClient):
    bundledir = os.path.join(BUNDLES, 'cluster_without_old_config')
    bundle = sdk_client_fs.upload_from_fs(os.path.join(bundledir, 'old'))
    cluster = bundle.cluster_create(utils.random_string())
    sdk_client_fs.upload_from_fs(os.path.join(bundledir, 'upgrade'))
    upgrade = cluster.upgrade()
    upgrade.do()
    cluster.reread()
    assert cluster.prototype().version == '2-config'


@pytest.mark.parametrize("boundary, expected", [
    ("min_cluster", "min and min_strict"), ("max_cluster", "max and max_strict"),
    ("min_hostprovider", "min and min_strict"), ("max_hostprovider", "max and max_strict")
])
def test_upgrade_contains_strict_and_nonstrict_value(sdk_client_fs: ADCMClient, boundary, expected):
    bundledir = os.path.join(BUNDLES, 'strict_and_non_strict_upgrade/' + boundary)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundledir)
    INVALID_UPGRADE_DEFINITION.equal(e, expected, 'can not be used simultaneously')
