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

"""ADCM API tests fixtures"""
from itertools import chain
from typing import Generator

import allure
import pytest
from adcm_pytest_plugin.docker.steps import attach_adcm_data_dir

from tests.api.steps.asserts import BodyAssertionError
from tests.api.steps.common import assume_step
from tests.api.utils.api_objects import ADCMTestApiWrapper
from tests.api.utils.endpoints import Endpoints
from tests.conftest import GENERIC_BUNDLES_DIR


def pytest_addoption(parser):
    """
    Additional options for ADCM api testing
    """
    parser.addoption(
        "--disable-soft-assert",
        action="store_true",
        help="This option is needed to disable soft assert in 'flexible_assert_step' fixture",
    )


@pytest.fixture(scope="session")
def fill_adcm(sdk_client_ss):
    adcm_client = sdk_client_ss
    with allure.step("Create provider"):
        provider_bundle = adcm_client.upload_from_fs(GENERIC_BUNDLES_DIR / "simple_provider")
        provider = provider_bundle.provider_create(name="Pre-uploaded provider")
        second_provider = provider_bundle.provider_create(name="Pre-uploaded second provider")
        _ = [second_provider.host_create(fqdn=f"pre-uploaded-host-second-provider-{i}") for i in range(6)]
    with allure.step("Create cluster for the further import and add hosts to it"):
        cluster_to_import_bundle = adcm_client.upload_from_fs(GENERIC_BUNDLES_DIR / "cluster_to_import")
        cluster_to_import = cluster_to_import_bundle.cluster_prototype().cluster_create(
            name="Pre-uploaded cluster for the import"
        )
        for i in range(6):
            cluster_to_import.host_add(provider.host_create(fqdn=f"pre-uploaded-host-import-{i}"))
    with allure.step("Create a cluster with service"):
        cluster_bundle = adcm_client.upload_from_fs(GENERIC_BUNDLES_DIR / "cluster_with_service")
        cluster = cluster_bundle.cluster_create(name="Pre-uploaded cluster with services")
        cluster.bind(cluster_to_import)
    with allure.step("Create hosts and add them to cluster"):
        hosts = tuple((cluster.host_add(provider.host_create(fqdn=f"pre-uploaded-host-{i}")) for i in range(6)))
    with allure.step("Add services"):
        service_first = cluster.service_add(name="First service")
        service_second = cluster.service_add(name="Second service")
        components = (
            service_first.component(name="first"),
            service_first.component(name="second"),
            service_second.component(name="third"),
        )
    with allure.step("Add hosts to cluster and set hostcomponent map"):
        cluster.hostcomponent_set(*[(host, component) for host in hosts for component in components])
    with allure.step("Run task"):
        task = cluster.action(name="action_on_cluster").run()
        task.wait()


@pytest.fixture()
def adcm_api(
    request, launcher, sdk_client_ss, fill_adcm  # pylint: disable=redefined-outer-name,unused-argument
) -> Generator[ADCMTestApiWrapper, None, None]:
    """Runs ADCM container with previously initialized image.
    Returns authorized instance of ADCMTestApiWrapper object
    """
    yield ADCMTestApiWrapper(adcm_api_wrapper=sdk_client_ss._api)  # pylint: disable=protected-access

    attach_adcm_data_dir(launcher, request)

    for obj in chain(
        sdk_client_ss.policy_list(),
        filter(lambda r: not r.built_in, sdk_client_ss.role_list()),
        sdk_client_ss.group_list(),
    ):
        obj.delete()


@pytest.fixture()
def flexible_assert_step(cmd_opts):
    """
    Returns either allure.step or assume_step context manager
    depending on option '--disable-soft-assert'
    """

    def _flexible_assert_step(title, assertion_error=BodyAssertionError):
        if cmd_opts.disable_soft_assert is True:
            return allure.step(title)
        return assume_step(title, assertion_error)

    return _flexible_assert_step


@pytest.fixture(autouse=True)
def clear_endpoints_data():
    """
    Clear endpoint paths
    # TODO it could be done better
    """
    yield
    Endpoints.clear_endpoints_paths()
