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

"""Tests for bundle upgrades"""

import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin import utils

from tests.library.errorcodes import (
    INVALID_VERSION_DEFINITION,
    UPGRADE_ERROR,
    UPGRADE_NOT_FOUND,
)

# pylint: disable=redefined-outer-name


@pytest.fixture()
def cluster_bundles():
    """Prepare cluster bundle paths"""
    bundle = utils.get_data_dir(__file__, "cluster_bundle_before_upgrade")
    upgrade_bundle = utils.get_data_dir(__file__, "upgradable_cluster_bundle")
    return bundle, upgrade_bundle


@pytest.fixture()
def host_bundles():
    """Prepare hostprovider bundle paths"""
    bundle = utils.get_data_dir(__file__, "hostprovider_bundle_before_upgrade")
    upgrade_bundle = utils.get_data_dir(__file__, "upgradable_hostprovider_bundle")
    return bundle, upgrade_bundle


def test_cluster_bundle_upgrade_will_ends_successfully(sdk_client_fs: ADCMClient, cluster_bundles):
    """Test successful cluster bundle upgrade"""
    bundle, upgrade_bundle = cluster_bundles
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle)
    cluster = cluster_bundle.cluster_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = cluster.upgrade(name="upgrade to 1.6")
    upgr.do()
    cluster.reread()
    with allure.step("Check if state is upgradable"):
        assert cluster.state == "upgradable"


def test_shouldnt_upgrade_upgrated_cluster(sdk_client_fs: ADCMClient, cluster_bundles):
    """Test unavailable cluster bundle upgrade"""
    bundle, upgrade_bundle = cluster_bundles
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle)
    cluster = cluster_bundle.cluster_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = cluster.upgrade(name="upgrade to 1.6")
    upgr.do()
    cluster.reread()
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    with allure.step("Check if cluster version is more than upgrade max version"):
        UPGRADE_ERROR.equal(e, "cluster version", "is more than upgrade max version")


def test_that_check_nonexistent_cluster_upgrade(sdk_client_fs: ADCMClient, cluster_bundles):
    """Test nonexisting cluster bundle upgrade"""
    bundle, _ = cluster_bundles
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle)
    cluster = cluster_bundle.cluster_create("test")
    sdk_client_fs.upload_from_fs(_)
    upgr = cluster.upgrade(name="upgrade to 1.6")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do(upgrade_id=5555, cluster_id=cluster.id)
    with allure.step("Check if upgrade is not found"):
        UPGRADE_NOT_FOUND.equal(e, "Upgrade", "does not exist")


def test_that_check_nonexistent_hostprovider_upgrade(sdk_client_fs: ADCMClient, host_bundles):
    """Test nonexisting hostprovider bundle upgrade"""
    bundle, _ = host_bundles
    hostprovider_bundle = sdk_client_fs.upload_from_fs(bundle)
    hostprovider = hostprovider_bundle.provider_create("test")
    sdk_client_fs.upload_from_fs(_)
    upgr = hostprovider.upgrade(name="upgrade to 2.0")
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do(upgrade_id=5555, provider_id=hostprovider.id)
    with allure.step("Check if upgrade is not found"):
        UPGRADE_NOT_FOUND.equal(e, "Upgrade", "does not exist")


def test_hostprovider_bundle_upgrade_will_ends_successfully(sdk_client_fs: ADCMClient, host_bundles):
    """Test successful hostprovider bundle upgrade"""
    bundle, upgrade_bundle = host_bundles
    hostprovider_bundle = sdk_client_fs.upload_from_fs(bundle)
    hostprovider = hostprovider_bundle.provider_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = hostprovider.upgrade(name="upgrade to 2.0")
    upgr.do()
    hostprovider.reread()
    with allure.step("Check if state is upgradable"):
        assert hostprovider.state == "upgradable"


def test_shouldnt_upgrade_upgrated_hostprovider(sdk_client_fs: ADCMClient, host_bundles):
    """Test unavailable hostprovider bundle upgrade"""
    bundle, upgrade_bundle = host_bundles
    hostprovider_bundle = sdk_client_fs.upload_from_fs(bundle)
    hostprovider = hostprovider_bundle.provider_create("test")
    sdk_client_fs.upload_from_fs(upgrade_bundle)
    upgr = hostprovider.upgrade(name="upgrade to 2.0")
    upgr.do()
    hostprovider.reread()
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        upgr.do()
    UPGRADE_ERROR.equal(e)
    with allure.step("Check errors"):
        assert "provider version" in e.value.error["desc"], e.value.error["desc"]
        assert "is more than upgrade max version" in e.value.error["desc"], e.value.error["desc"]


def test_upgrade_cluster_without_old_config(sdk_client_fs: ADCMClient):
    """Test upgrade cluster without old config"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster_without_old_config", "old"))
    cluster = bundle.cluster_create(utils.random_string())
    sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster_without_old_config", "upgrade"))
    upgrade = cluster.upgrade()
    upgrade.do()
    cluster.reread()
    with allure.step("Check if version is 2-config"):
        assert cluster.prototype().version == "2-config"


@pytest.mark.parametrize(
    ("boundary", "expected"),
    [
        ("min_cluster", "can not be used simultaneously"),
        ("max_cluster", "should be present"),
        ("min_hostprovider", "can not be used simultaneously"),
        ("max_hostprovider", "can not be used simultaneously"),
    ],
)
def test_upgrade_contains_strict_and_nonstrict_value(sdk_client_fs: ADCMClient, boundary, expected):
    """Test upgrade contains strict and nonstrict value"""
    bundledir = utils.get_data_dir(__file__, "strict_and_non_strict_upgrade", boundary)
    with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
        sdk_client_fs.upload_from_fs(bundledir)
    with allure.step(f"Check if error is {expected}"):
        INVALID_VERSION_DEFINITION.equal(e, expected)
