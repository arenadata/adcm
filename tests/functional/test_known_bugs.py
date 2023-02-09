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

"""Tests that known bugs aren't present anymore"""

import allure
import pytest
from adcm_client.objects import Bundle, Cluster, Provider
from adcm_pytest_plugin.steps.actions import run_service_action_and_assert_result
from adcm_pytest_plugin.utils import catch_failed, get_data_dir
from coreapi.exceptions import ErrorMessage

# pylint: disable=redefined-outer-name
from tests.functional.tools import create_config_group_and_add_host

pytestmark = [pytest.mark.regression]


def _cluster_bundle(sdk_client_fs) -> Bundle:
    """Get dummy cluster"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "dummy", "cluster"))


def _provider_bundle(sdk_client_fs) -> Bundle:
    """Get dummy provider"""
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, "dummy", "provider"))


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Get dummy cluster"""
    return _cluster_bundle(sdk_client_fs).cluster_create(name="Test Dummy Cluster")


@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    """Get dummy provider"""
    return _provider_bundle(sdk_client_fs).provider_create(name="Test Dummy Provider")


@pytest.fixture()
def cluster_with_services(sdk_client_fs) -> Cluster:
    """Create cluster and add two services"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_services"))
    cluster = bundle.cluster_create(name="Test Cluster")
    cluster.service_add(name="first_service")
    cluster.service_add(name="second_service")
    return cluster


@allure.issue(url="https://arenadata.atlassian.net/browse/ADCM-2659")
def test_database_is_locked_during_upload(sdk_client_fs, provider):
    """
    Test that known bug that occurs during bundle upload when actions are running is not presented anymore
    """
    with allure.step("Create a lot of hosts and run a lot of actions on them"):
        for i in range(200):
            provider.host_create(f"host-{i}").action(name="dummy").run()
    with allure.step("Try to upload cluster bundle"):
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "simple_cluster_from_dirty_upgrade"))


@allure.issue(url="https://arenadata.atlassian.net/browse/ADCM-2800")
def test_missing_service_outside_config_group(cluster_with_services, provider):
    """
    Test that all services' configs are available in inventory file when one of services has a config group
    """
    action_name = "check"
    cluster = cluster_with_services
    first_service, second_service = cluster.service(name="first_service"), cluster.service(name="second_service")
    component_1, component_2 = first_service.component(), second_service.component()
    host_1, host_2 = [cluster.host_add(provider.host_create(f"test-host-{i}")) for i in range(2)]

    cluster.hostcomponent_set((host_1, component_1), (host_1, component_2), (host_2, component_1))
    create_config_group_and_add_host("config-group", first_service, host_1)

    with allure.step("Run actions on services and check config dicts are available"):
        run_service_action_and_assert_result(first_service, action_name)
        run_service_action_and_assert_result(second_service, action_name)


def test_launch_action_with_activatable_config_group(sdk_client_fs):
    """Known bug caught when running action with at least one activatable group in action's config"""
    cluster = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "activatable_group_in_action_config")).cluster_create(
        "Test Cluster"
    )
    for param_1, param_2 in ((False, False), (True, False), (False, True)):
        with allure.step(f"Try to set active status of {param_1=} and {param_2=}"):
            with catch_failed(ErrorMessage, "Running cluster action should not raise exception"):
                cluster.action(name="enable_something").run(
                    config={
                        "param_1": {"somethingtwo": "jjj"},
                        "param_2": {"somethingone": ["ololo"]},
                    },
                    attr={"param_1": {"active": param_1}, "param_2": {"active": param_2}},
                ).wait()
