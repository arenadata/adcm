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
from typing import Generator

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.fixtures import _adcm
from adcm_pytest_plugin.plugin import parametrized_by_adcm_version
from adcm_pytest_plugin.utils import get_data_dir, random_string


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


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr)
def test_upgrade_adcm(adcm_fs: ADCM, sdk_client_fs: ADCMClient, adcm_api_credentials):
    sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_bundle"))
    with allure.step("Create cluster"):
        cluster_name = f"test_{random_string()}"
        sdk_client_fs.cluster_prototype().cluster_create(name=cluster_name)
    adcm_fs.upgrade(("hub.arenadata.io/adcm/adcm", "latest"))
    sdk_client_fs.auth(**adcm_api_credentials)
    with allure.step("Check that cluster is present"):
        assert len(sdk_client_fs.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = sdk_client_fs.cluster_list()[0]
        assert cluster.name == cluster_name, "Unexpected cluster name"


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr)
def test_pass_in_cluster_config_encryption_after_upgrade(
    adcm_fs: ADCM, sdk_client_fs: ADCMClient, adcm_api_credentials
):
    hostprovider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "hostprovider"))
    hostprovider = hostprovider_bundle.provider_create(name=f"test_{random_string()}")
    host = hostprovider.host_create(fqdn=f"test_host_{random_string()}")
    cluster_bundle = sdk_client_fs.upload_from_fs(
        get_data_dir(__file__, "cluster_with_cluster_pass_verify")
    )
    cluster = cluster_bundle.cluster_prototype().cluster_create(name=f"test_{random_string()}")
    cluster.host_add(host)
    cluster.config_set_diff(dict(password="q1w2e3r4"))
    adcm_fs.upgrade(("hub.arenadata.io/adcm/adcm", "latest"))
    sdk_client_fs.auth(**adcm_api_credentials)
    with allure.step("Check that cluster is present"):
        assert len(sdk_client_fs.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = sdk_client_fs.cluster_list()[0]
        assert cluster.action(name="check-password").run().wait() == "success"


@pytest.mark.parametrize("image", old_adcm_images(), ids=repr)
def test_pass_in_service_config_encryption_after_upgrade(
    adcm_fs: ADCM, sdk_client_fs: ADCMClient, adcm_api_credentials
):
    hostprovider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, 'hostprovider'))
    hostprovider = hostprovider_bundle.provider_create(name=f"test_{random_string()}")
    host = hostprovider.host_create(fqdn=f"test_host_{random_string()}")
    cluster_bundle = sdk_client_fs.upload_from_fs(
        get_data_dir(__file__, 'cluster_with_service_pass_verify')
    )
    cluster = cluster_bundle.cluster_prototype().cluster_create(name=f"test_{random_string()}")
    cluster.host_add(host)
    service = cluster.service_add(name="PassChecker")
    service.config_set_diff(dict(password="q1w2e3r4"))
    adcm_fs.upgrade(("hub.arenadata.io/adcm/adcm", "latest"))
    sdk_client_fs.auth(**adcm_api_credentials)
    with allure.step('Check cluster'):
        assert len(sdk_client_fs.cluster_list()) == 1, "There is no clusters. Expecting one"
        cluster = sdk_client_fs.cluster_list()[0]
        assert len(cluster.service_list()) == 1, "There is no services. Expecting one"
        service = cluster.service_list()[0]
        assert service.action(name="check-password").run().wait() == "success"
