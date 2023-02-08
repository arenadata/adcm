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

"""Tests for actions"""

# pylint: disable=redefined-outer-name
import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Provider
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import fixture_parametrized_by_data_subdirs

from tests.functional.tools import (
    AnyADCMObject,
    actions_in_objects_are_absent,
    actions_in_objects_are_present,
)


def check_verbosity(log, verbose_state):
    """Assert action verbosity by log content"""
    assert ("verbosity: 4" in log.content) is verbose_state


@pytest.mark.parametrize("verbose_state", [True, False], ids=["verbose_state_true", "verbose_state_false"])
def test_check_verbose_option_of_action_run(sdk_client_fs: ADCMClient, verbose_state):
    """Test action run with verbose switch"""
    bundle_dir = utils.get_data_dir(__file__, "verbose_state")
    bundle = sdk_client_fs.upload_from_fs(bundle_dir)
    cluster = bundle.cluster_create(utils.random_string())
    task = cluster.action(name="dummy_action").run(verbose=verbose_state)
    with allure.step(f"Check if verbosity is {verbose_state}"):
        task.wait()
        log = task.job().log()
        check_verbosity(log, verbose_state)


ACTION = "some_action"
ACTION_STATE_INSTALLED = "some_action_state_installed"
ACTION_STATE_CREATED = "some_action_state_created"
ACTION_UNAVAILABLE = "some_action_unavailable"
FIRST_SERVICE = "First service"
SECOND_SERVICE = "Second service"
FIRST_COMPONENT = "first"
SECOND_COMPONENT = "second"
SWITCH_SERVICE_STATE = "switch_service_state"
SWITCH_CLUSTER_STATE = "switch_cluster_state"
SWITCH_HOST_STATE = "switch_host_state"
SWITCH_COMPONENT_STATE = "switch_component_state"
SWITCH_PROVIDER_STATE = "switch_provider_state"


@allure.title("Create cluster")
@fixture_parametrized_by_data_subdirs(__file__, "cluster")
def cluster(sdk_client_fs: ADCMClient, request) -> Cluster:
    """Create cluster"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    return bundle.cluster_prototype().cluster_create(name="Cluster")


@allure.title("Create a cluster with service")
@fixture_parametrized_by_data_subdirs(__file__, "cluster_with_service")
def cluster_with_service(sdk_client_fs: ADCMClient, request) -> Cluster:
    """Create cluster with service"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    cluster = bundle.cluster_prototype().cluster_create(name="Cluster with services")
    return cluster


@allure.title("Create a cluster with service and components")
@fixture_parametrized_by_data_subdirs(__file__, "cluster_with_components")
def cluster_with_components(sdk_client_fs: ADCMClient, request) -> Cluster:
    """Create cluster with components"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    cluster = bundle.cluster_prototype().cluster_create(name="Cluster with components")
    return cluster


@allure.title("Create provider")
@fixture_parametrized_by_data_subdirs(__file__, "provider")
def provider(sdk_client_fs: ADCMClient, request) -> Provider:
    """Create provider"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    return bundle.provider_prototype().provider_create("Some provider")


def test_cluster_action_availability_at_state(cluster: Cluster):
    """
    Test that cluster host action is available on a specific cluster state
    """
    _assert_actions_state_created(cluster)
    run_cluster_action_and_assert_result(cluster, SWITCH_CLUSTER_STATE)
    _assert_actions_state_installed(cluster)
    run_cluster_action_and_assert_result(cluster, ACTION_STATE_INSTALLED)


def test_service_action_availability_at_state(cluster_with_service: Cluster):
    """
    Test that service action is available on specific service state
    """
    service_1 = cluster_with_service.service_add(name=FIRST_SERVICE)
    service_2 = cluster_with_service.service_add(name=SECOND_SERVICE)

    _assert_actions_state_created(service_1)
    run_cluster_action_and_assert_result(cluster_with_service, SWITCH_CLUSTER_STATE)
    _assert_actions_state_created(service_1)
    run_service_action_and_assert_result(service_1, SWITCH_SERVICE_STATE)
    _assert_actions_state_installed(service_1)
    _assert_actions_state_created(service_2)
    run_service_action_and_assert_result(service_1, ACTION_STATE_INSTALLED)


def test_component_action_availability_at_state(cluster_with_components: Cluster):
    """
    Test that component action is available on specific component state
    """
    service = cluster_with_components.service_add(name=FIRST_SERVICE)
    component_1 = service.component(name=FIRST_COMPONENT)
    component_2 = service.component(name=SECOND_COMPONENT)

    _assert_actions_state_created(component_1)
    run_cluster_action_and_assert_result(cluster_with_components, SWITCH_CLUSTER_STATE)
    _assert_actions_state_created(component_1)
    run_service_action_and_assert_result(service, SWITCH_SERVICE_STATE)
    _assert_actions_state_created(component_1)
    run_component_action_and_assert_result(component_1, SWITCH_COMPONENT_STATE)
    _assert_actions_state_installed(component_1)
    _assert_actions_state_created(component_2)
    run_component_action_and_assert_result(component_1, ACTION_STATE_INSTALLED)


def test_provider_action_availability_at_state(provider: Provider):
    """
    Test that provider action is available on specific provider state
    """
    _assert_actions_state_created(provider)
    run_provider_action_and_assert_result(provider, SWITCH_PROVIDER_STATE)
    _assert_actions_state_installed(provider)
    run_provider_action_and_assert_result(provider, ACTION_STATE_INSTALLED)


def test_host_action_availability_at_state(provider: Provider):
    """
    Test that host action is available on specific host state
    """
    host_1 = provider.host_create("host-1-fqdn")
    host_2 = provider.host_create("host-2-fqdn")
    _assert_actions_state_created(host_1)
    run_provider_action_and_assert_result(provider, SWITCH_PROVIDER_STATE)
    _assert_actions_state_created(host_1)
    run_host_action_and_assert_result(host_1, SWITCH_HOST_STATE)
    _assert_actions_state_installed(host_1)
    _assert_actions_state_created(host_2)
    run_host_action_and_assert_result(host_1, ACTION_STATE_INSTALLED)


def _assert_actions_state_created(obj: AnyADCMObject):
    actions_in_objects_are_absent(
        [
            (ACTION_UNAVAILABLE, obj),
            (ACTION_STATE_INSTALLED, obj),
        ]
    )
    actions_in_objects_are_present(
        [
            (ACTION, obj),
            (ACTION_STATE_CREATED, obj),
        ]
    )


def _assert_actions_state_installed(obj: AnyADCMObject):
    actions_in_objects_are_absent(
        [
            (ACTION_UNAVAILABLE, obj),
            (ACTION_STATE_CREATED, obj),
        ]
    )
    actions_in_objects_are_present(
        [
            (ACTION, obj),
            (ACTION_STATE_INSTALLED, obj),
        ]
    )


AVAILABLE_ACTIONS_SPECIAL_CASE_CREATED = [
    "action_available_any_1",
    "action_available_any_2",
    "action_available_any_3",
    "action_available_state_created",
    "action_available_state_created_and_installed",
    "action_unavailable_state_installed",
]

UNAVAILABLE_ACTIONS_SPECIAL_CASE_CREATED = [
    "action_unavailable",
    "action_unavailable_state_installed_and_created",
]

AVAILABLE_ACTIONS_SPECIAL_CASE_INSTALLED = [
    "action_available_any_1",
    "action_available_any_2",
    "action_available_any_3",
    "action_available_state_created_and_installed",
]

UNAVAILABLE_ACTIONS_SPECIAL_CASE_INSTALLED = [
    "action_unavailable",
    "action_unavailable_state_installed_and_created",
    "action_available_state_created",
    "action_unavailable_state_installed",
]


@allure.title("Create cluster")
@pytest.fixture()
def cluster_special(sdk_client_fs: ADCMClient) -> Cluster:
    """Create special cluster"""
    bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster_special_new_dsl"))
    return bundle.cluster_prototype().cluster_create(name="Cluster")


def test_cluster_action_availability_at_state_new_dsl_special(cluster_special: Cluster):
    """
    Test that cluster host action is available on a specific cluster state (special availability cases)
    """
    actions_in_objects_are_absent([(action, cluster_special) for action in UNAVAILABLE_ACTIONS_SPECIAL_CASE_CREATED])
    actions_in_objects_are_present([(action, cluster_special) for action in AVAILABLE_ACTIONS_SPECIAL_CASE_CREATED])
    run_cluster_action_and_assert_result(cluster_special, SWITCH_CLUSTER_STATE)
    actions_in_objects_are_absent([(action, cluster_special) for action in UNAVAILABLE_ACTIONS_SPECIAL_CASE_INSTALLED])
    actions_in_objects_are_present([(action, cluster_special) for action in AVAILABLE_ACTIONS_SPECIAL_CASE_INSTALLED])
