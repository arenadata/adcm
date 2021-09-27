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

# pylint:disable=redefined-outer-name
from typing import Tuple, Union, List, Any

import allure
import pytest

from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Cluster, Host, Service
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.utils import catch_failed, get_data_dir, random_string

from tests.upgrade_utils import upgrade_adcm_version
from tests.functional.plugin_utils import AnyADCMObject
from .conftest import only_clean_adcm

pytestmark = [only_clean_adcm]

AVAILABLE_ACTIONS = {
    "single_state-available",
    "state_list-available",
    "state_any-available",
}


def old_adcm_images() -> Tuple[List[Tuple[str, str]], Any]:
    return parametrized_by_adcm_version(adcm_min_version="2019.10.08")[0]


def _create_cluster(sdk_client_fs: ADCMClient, bundle_dir: str = "cluster_bundle") -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    cluster_name = f"test_{random_string()}"
    return bundle.cluster_prototype().cluster_create(name=cluster_name)


def _create_host(sdk_client_fs: ADCMClient, bundle_dir: str = "hostprovider") -> Host:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    provider = bundle.provider_create(name=f"test_{random_string()}")
    return provider.host_create(fqdn=f"test_host_{random_string()}")


@allure.step("Check actions availability")
def _assert_available_actions(obj: AnyADCMObject):
    obj.reread()
    actions = {action.name for action in obj.action_list()}
    assert (
        actions == AVAILABLE_ACTIONS
    ), f"Unexpected list of available actions!\nExpected: {AVAILABLE_ACTIONS}\nActual:{actions}"


@allure.step("Check that previously created cluster exists")
def _check_that_cluster_exists(sdk_client_fs: ADCMClient, cluster: Cluster) -> None:
    assert len(sdk_client_fs.cluster_list()) == 1, "Only one cluster expected to be"
    with catch_failed(ObjectNotFound, "Previously created cluster not found"):
        sdk_client_fs.cluster(name=cluster.name)


@allure.step("Check that previously created service exists")
def _check_that_host_exists(cluster: Cluster, host: Host) -> None:
    assert len(cluster.host_list()) == 1, "Only one host expected to be"
    with catch_failed(ObjectNotFound, "Previously created host not found"):
        cluster.host(fqdn=host.fqdn)


@allure.step("Check encryption")
def _check_encryption(obj: Union[Cluster, Service]) -> None:
    assert obj.action(name="check-password").run().wait() == "success"


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", old_adcm_images(), ids=repr, indirect=True)
def test_upgrade_adcm(
    adcm_fs: ADCM,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: Tuple[str, str],
) -> None:
    """Test adcm upgrade"""
    cluster = _create_cluster(sdk_client_fs)
    host = _create_host(sdk_client_fs)
    cluster.host_add(host)

    upgrade_adcm_version(adcm_fs, sdk_client_fs, adcm_api_credentials, adcm_image_tags)

    _check_that_cluster_exists(sdk_client_fs, cluster)
    _check_that_host_exists(cluster, host)


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", old_adcm_images(), ids=repr, indirect=True)
def test_pass_in_config_encryption_after_upgrade(
    adcm_fs: ADCM,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    adcm_image_tags: Tuple[str, str],
) -> None:
    """Test adcm upgrade with encrypted fields"""
    cluster = _create_cluster(sdk_client_fs, "cluster_with_pass_verify")
    service = cluster.service_add(name="PassCheckerService")

    config_diff = dict(password="q1w2e3r4")
    cluster.config_set_diff(config_diff)
    service.config_set_diff(config_diff)

    upgrade_adcm_version(adcm_fs, sdk_client_fs, adcm_api_credentials, adcm_image_tags)

    _check_encryption(cluster)
    _check_encryption(service)


@pytest.mark.parametrize("adcm_is_upgradable", [True], indirect=True)
@pytest.mark.parametrize("image", [["hub.arenadata.io/adcm/adcm", "2021.06.17.06"]], ids=repr, indirect=True)
def test_actions_availability_after_upgrade(
    adcm_fs: ADCM,
    sdk_client_fs: ADCMClient,
    adcm_api_credentials: dict,
    upgrade_target: Tuple[str, str],
) -> None:
    """Test that actions availability from old DSL remains the same after update"""
    cluster = _create_cluster(sdk_client_fs, "cluster_with_actions")

    _assert_available_actions(cluster)

    upgrade_adcm_version(adcm_fs, sdk_client_fs, adcm_api_credentials, upgrade_target)

    _assert_available_actions(cluster)
