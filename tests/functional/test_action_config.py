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

"""Tests for actions config"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Host, Provider, Service
from adcm_pytest_plugin import utils as plugin_utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from coreapi.exceptions import ErrorMessage
from tests.library.errorcodes import CONFIG_KEY_ERROR, CONFIG_VALUE_ERROR

# pylint: disable=redefined-outer-name


ACTION_MAP = {
    Cluster: run_cluster_action_and_assert_result,
    Service: run_service_action_and_assert_result,
    Component: run_component_action_and_assert_result,
    Provider: run_provider_action_and_assert_result,
    Host: run_host_action_and_assert_result,
}


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """Create cluster"""
    uploaded_bundle = sdk_client_fs.upload_from_fs(plugin_utils.get_data_dir(__file__, "cluster"))
    cluster = uploaded_bundle.cluster_create("test cluster")
    cluster.service_add(name="test_service")
    return cluster


@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Create provider"""
    uploaded_bundle = sdk_client_fs.upload_from_fs(plugin_utils.get_data_dir(__file__, "provider"))
    provider = uploaded_bundle.provider_create("test_cluster")
    provider.host_create(fqdn="test-host")
    return provider


def test_config_not_presented(cluster: Cluster, provider: Provider, sdk_client_fs: ADCMClient):
    """
    Action's configuration not presented
    Run action with config
    """
    job_count = len(sdk_client_fs.job_list())
    component = (service := cluster.service()).component()
    host = provider.host()
    for obj in (cluster, service, component, provider, host):
        with allure.step(f"Check no config with action on {obj.__class__.__name__}"):
            with allure.step("Run action without config and expect it to fail with ansible error"):
                try:
                    ACTION_MAP[obj.__class__](obj, "no_config", "failed", config={"some_param": "1"})
                except ErrorMessage as e:
                    CONFIG_VALUE_ERROR.equal(e)
                else:
                    raise AssertionError("Action run request should've failed")
            with allure.step("Check that job wasn't launched"):
                _check_job_count_equal_to(job_count, sdk_client_fs)


def test_incorrect_config(cluster: Cluster, provider: Provider, sdk_client_fs: ADCMClient):
    """
    Action's configuration not presented
    Run action with "incorrect" config
    """
    job_count = len(sdk_client_fs.job_list())
    component = (service := cluster.service()).component()
    host = provider.host()
    for obj in (cluster, service, component, provider, host):
        with allure.step(f'Check "incorrect" config with action on {obj.__class__.__name__}'):
            with allure.step('Run action with "incorrect" config and expect ADCM response with non 500 status code'):
                try:
                    ACTION_MAP[obj.__class__](obj, "with_config", "failed", config={"no_such_param": "1"})
                except ErrorMessage as e:
                    CONFIG_KEY_ERROR.equal(e)
                else:
                    raise AssertionError("Action should've failed")
            with allure.step("Check that job wasn't launched"):
                _check_job_count_equal_to(job_count, sdk_client_fs)


def test_pass_no_config(cluster: Cluster, provider: Provider, sdk_client_fs: ADCMClient):
    """
    Action has config
    Run action without config
    """
    job_count = len(sdk_client_fs.job_list())
    component = (service := cluster.service()).component()
    host = provider.host()
    for obj in (cluster, service, component, provider, host):
        with allure.step(f"Check run action that require config with on {obj.__class__.__name__}"):
            with allure.step(
                "Run action that require config without config and expect ADCM to response with non 500 status code"
            ):
                try:
                    ACTION_MAP[obj.__class__](obj, "with_config", "failed")
                except ErrorMessage as e:
                    CONFIG_VALUE_ERROR.equal(e)
                else:
                    raise AssertionError("Action run should've failed")
            with allure.step("Check that job wasn't launched"):
                _check_job_count_equal_to(job_count, sdk_client_fs)


def _check_job_count_equal_to(count: int, adcm_client: ADCMClient):
    """Check that job count is equal to expected"""
    assert (
        job_count := len(adcm_client.job_list())
    ) == count, f"Amount of jobs expected is {count}, but {job_count} was found"
