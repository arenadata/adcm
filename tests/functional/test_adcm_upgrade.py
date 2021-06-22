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
# pylint: disable=W0621,R0914
from typing import Generator, Tuple, Union

import allure
import pytest
from adcm_client.base import ObjectNotFound
from adcm_client.objects import ADCMClient, Cluster, Host, Service
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.fixtures import _adcm
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.utils import catch_failed, get_data_dir, random_string
from version_utils import rpm


@pytest.fixture(scope="session")
def upgrade_target(cmd_opts) -> Tuple[str, str]:
    if not cmd_opts.adcm_image:
        pytest.fail("CLI parameter adcm_image should be provided")
    return tuple(cmd_opts.adcm_image.split(":", maxsplit=2))


def old_adcm_images():
    return parametrized_by_adcm_version(adcm_min_version="2019.10.08")[0]


@allure.title("[FS] Upgradable ADCM Container")
@pytest.fixture()
def adcm_fs(image, cmd_opts, request, adcm_api_credentials) -> Generator[ADCM, None, None]:
    """Runs adcm container from the previously initialized image.
    Operates '--dontstop' option.
    Returns authorized instance of ADCM object
    """
    yield from _adcm(image, cmd_opts, request, adcm_api_credentials, upgradable=True)


@allure.step("Check that version has been changed")
def _check_that_version_changed(before: str, after: str) -> None:
    if rpm.compare_versions(after, before) < 1:
        raise AssertionError("ADCM version after upgrade is older or equal to the version before")


def _upgrade_adcm(adcm: ADCM, sdk: ADCMClient, target: Tuple[str, str]):
    buf = sdk.adcm_version
    adcm.upgrade(target)
    sdk.reread()
    _check_that_version_changed(buf, sdk.adcm_version)


def _create_cluster(sdk_client_fs: ADCMClient, bundle_dir: str = "cluster_bundle") -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    cluster_name = f"test_{random_string()}"
    return bundle.cluster_prototype().cluster_create(name=cluster_name)


def _create_host(sdk_client_fs: ADCMClient, bundle_dir: str = "hostprovider") -> Host:
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, bundle_dir))
    provider = bundle.provider_create(name=f"test_{random_string()}")
    return provider.host_create(fqdn=f"test_host_{random_string()}")


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


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr)
def test_upgrade_adcm(adcm_fs: ADCM, sdk_client_fs: ADCMClient, upgrade_target: Tuple[str, str]):
    """Test adcm upgrade"""
    cluster = _create_cluster(sdk_client_fs)
    host = _create_host(sdk_client_fs)
    cluster.host_add(host)

    _upgrade_adcm(adcm_fs, sdk_client_fs, upgrade_target)

    _check_that_cluster_exists(sdk_client_fs, cluster)
    _check_that_host_exists(cluster, host)


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr)
def test_pass_in_config_encryption_after_upgrade(
    adcm_fs: ADCM, sdk_client_fs: ADCMClient, upgrade_target: Tuple[str, str]
):
    """Test adcm upgrade with encrypted fields"""
    cluster = _create_cluster(sdk_client_fs, "cluster_with_pass_verify")
    service = cluster.service_add(name="PassCheckerService")

    config_diff = dict(password="q1w2e3r4")
    cluster.config_set_diff(config_diff)
    service.config_set_diff(config_diff)

    _upgrade_adcm(adcm_fs, sdk_client_fs, upgrade_target)

    _check_encryption(cluster)
    _check_encryption(service)
