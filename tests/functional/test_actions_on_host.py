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

"""Test actions on host"""

# pylint: disable=redefined-outer-name
import allure
import pytest

from adcm_client.objects import Cluster, Provider
from adcm_pytest_plugin.steps.actions import (
    run_host_action_and_assert_result,
    run_cluster_action_and_assert_result,
    run_service_action_and_assert_result,
    run_component_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir
from tests.functional.tools import action_in_object_is_absent, action_in_object_is_present
from tests.functional.test_actions import (
    FIRST_SERVICE,
    SECOND_SERVICE,
    FIRST_COMPONENT,
    SECOND_COMPONENT,
    SWITCH_SERVICE_STATE,
    SWITCH_CLUSTER_STATE,
    SWITCH_HOST_STATE,
    SWITCH_COMPONENT_STATE,
)

ACTION_ON_HOST = "action_on_host"
ACTION_ON_HOST_MULTIJOB = "action_on_host_multijob"
ACTION_ON_HOST_STATE_REQUIRED = "action_on_host_state_installed"


@allure.title("Create cluster")
@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    """Create cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    return bundle.cluster_prototype().cluster_create(name="Cluster")


@allure.title("Create a cluster with service")
@pytest.fixture()
def cluster_with_service(sdk_client_fs) -> Cluster:
    """Create cluster with service"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_service"))
    cluster = bundle.cluster_prototype().cluster_create(name="Cluster with services")
    return cluster


@allure.title("Create a cluster with service and components")
@pytest.fixture()
def cluster_with_components(sdk_client_fs) -> Cluster:
    """Create cluster with component"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_components"))
    cluster = bundle.cluster_prototype().cluster_create(name="Cluster with components")
    return cluster


@allure.title("Create a cluster with target group action")
@pytest.fixture()
def cluster_with_target_group_action(sdk_client_fs) -> Cluster:
    """Create cluster with target group action"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_target_group"))
    cluster = bundle.cluster_prototype().cluster_create(name="Target group test")
    return cluster


@allure.title("Create provider")
@pytest.fixture()
def provider(sdk_client_fs) -> Provider:
    """Create provider"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    return bundle.provider_prototype().provider_create("Some provider")


class TestClusterActionsOnHost:
    """Tests for cluster actions on host"""

    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_availability(self, cluster: Cluster, provider: Provider, action_name):
        """
        Test that cluster host action is available on cluster host and is absent on cluster
        """
        host1 = provider.host_create("host-in-cluster")
        host2 = provider.host_create("host-not-in-cluster")
        cluster.host_add(host1)
        action_in_object_is_present(action_name, host1)
        action_in_object_is_absent(action_name, host2)
        action_in_object_is_absent(action_name, cluster)
        run_host_action_and_assert_result(host1, action_name, status="success")

    def test_availability_at_state(self, cluster: Cluster, provider: Provider):
        """
        Test that cluster host action is available on specify cluster state
        """
        host = provider.host_create("host-in-cluster")
        cluster.host_add(host)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_cluster_action_and_assert_result(cluster, SWITCH_CLUSTER_STATE)
        action_in_object_is_present(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, ACTION_ON_HOST_STATE_REQUIRED)

    def test_availability_at_host_state(self, cluster: Cluster, provider: Provider):
        """
        Test that cluster host action isn't available on specify host state
        """
        host = provider.host_create("host-in-cluster")
        cluster.host_add(host)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, SWITCH_HOST_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_cluster_action_and_assert_result(cluster, SWITCH_CLUSTER_STATE)
        action_in_object_is_present(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, ACTION_ON_HOST_STATE_REQUIRED)

    @allure.issue("https://arenadata.atlassian.net/browse/ADCM-1799")
    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_two_clusters(self, action_name, cluster: Cluster, provider: Provider):
        """
        Test that cluster actions on host works fine on two clusters
        """
        second_cluster = cluster.bundle().cluster_prototype().cluster_create(name="Second cluster")
        first_host = provider.host_create("host-in-first-cluster")
        second_host = provider.host_create("host-in-second-cluster")
        cluster.host_add(first_host)
        second_cluster.host_add(second_host)
        action_in_object_is_present(action_name, first_host)
        action_in_object_is_present(action_name, second_host)
        run_host_action_and_assert_result(first_host, action_name, status="success")
        run_host_action_and_assert_result(second_host, action_name, status="success")


class TestServiceActionOnHost:
    """Tests for service actions on host"""

    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_availability(self, cluster_with_service: Cluster, provider: Provider, action_name):
        """
        Test that service host action is available on a service host and is absent on cluster
        """
        service = cluster_with_service.service_add(name=FIRST_SERVICE)
        second_service = cluster_with_service.service_add(name=SECOND_SERVICE)
        host_with_two_components = provider.host_create("host-with-two-components")
        host_with_one_component = provider.host_create("host-with-one-component")
        host_without_component = provider.host_create("host-without-component")
        host_with_different_services = provider.host_create("host-with-different-services")
        host_outside_cluster = provider.host_create("host-outside-cluster")
        for host in [
            host_with_two_components,
            host_with_one_component,
            host_without_component,
            host_with_different_services,
        ]:
            cluster_with_service.host_add(host)
        cluster_with_service.hostcomponent_set(
            (host_with_two_components, service.component(name=FIRST_COMPONENT)),
            (host_with_two_components, service.component(name=SECOND_COMPONENT)),
            (host_with_one_component, service.component(name=FIRST_COMPONENT)),
            (host_with_different_services, service.component(name=SECOND_COMPONENT)),
            (host_with_different_services, second_service.component(name=FIRST_COMPONENT)),
        )

        action_in_object_is_present(action_name, host_with_one_component)
        action_in_object_is_present(action_name, host_with_two_components)
        action_in_object_is_present(action_name, host_with_different_services)
        action_in_object_is_absent(action_name, host_without_component)
        action_in_object_is_absent(action_name, host_outside_cluster)
        action_in_object_is_absent(action_name, cluster_with_service)
        action_in_object_is_absent(action_name, service)
        run_host_action_and_assert_result(host_with_one_component, action_name)
        run_host_action_and_assert_result(host_with_two_components, action_name)
        run_host_action_and_assert_result(host_with_different_services, action_name)

    def test_availability_at_state(self, cluster_with_service: Cluster, provider: Provider):
        """
        Test that service host action is available on specify service state
        """
        service = cluster_with_service.service_add(name=FIRST_SERVICE)
        host = provider.host_create("host-in-cluster")
        cluster_with_service.host_add(host)
        cluster_with_service.hostcomponent_set((host, service.component(name=FIRST_COMPONENT)))

        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_cluster_action_and_assert_result(cluster_with_service, SWITCH_CLUSTER_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_service_action_and_assert_result(service, SWITCH_SERVICE_STATE)
        action_in_object_is_present(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, ACTION_ON_HOST_STATE_REQUIRED)

    def test_availability_at_host_state(self, cluster_with_service: Cluster, provider: Provider):
        """
        Test that service host action isn't available on specify host state
        """
        service = cluster_with_service.service_add(name=FIRST_SERVICE)
        host = provider.host_create("host-in-cluster")
        cluster_with_service.host_add(host)
        cluster_with_service.hostcomponent_set((host, service.component(name=FIRST_COMPONENT)))

        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, SWITCH_HOST_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_service_action_and_assert_result(service, SWITCH_SERVICE_STATE)
        action_in_object_is_present(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, ACTION_ON_HOST_STATE_REQUIRED)

    @allure.issue("https://arenadata.atlassian.net/browse/ADCM-1799")
    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_two_clusters(self, action_name, cluster_with_service: Cluster, provider: Provider):
        """
        Test that service actions on host works fine on two clusters
        """
        second_cluster = cluster_with_service.bundle().cluster_prototype().cluster_create(name="Second cluster")
        service_on_first_cluster = cluster_with_service.service_add(name=FIRST_SERVICE)
        service_on_second_cluster = second_cluster.service_add(name=FIRST_SERVICE)
        first_host = provider.host_create("host-in-first-cluster")
        second_host = provider.host_create("host-in-second-cluster")
        cluster_with_service.host_add(first_host)
        second_cluster.host_add(second_host)
        cluster_with_service.hostcomponent_set((first_host, service_on_first_cluster.component(name=FIRST_COMPONENT)))
        second_cluster.hostcomponent_set((second_host, service_on_second_cluster.component(name=FIRST_COMPONENT)))

        action_in_object_is_present(action_name, first_host)
        action_in_object_is_present(action_name, second_host)
        run_host_action_and_assert_result(first_host, action_name, status="success")
        run_host_action_and_assert_result(second_host, action_name, status="success")


class TestComponentActionOnHost:
    """Tests for component actions on host"""

    @allure.issue(
        url="https://arenadata.atlassian.net/browse/ADCM-1948", name="Infinite host action on ADCM with pre-filled data"
    )
    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_availability(self, cluster_with_components: Cluster, provider: Provider, action_name):
        """
        Test that component host action is available on a component host
        """
        service = cluster_with_components.service_add(name=FIRST_SERVICE)
        component_with_action = service.component(name=FIRST_COMPONENT)
        component_without_action = service.component(name=SECOND_COMPONENT)

        host_single_component = provider.host_create("host-with-single-component")
        host_two_components = provider.host_create("host-with-two-components")
        host_component_without_action = provider.host_create("host-component-without-action")
        host_without_components = provider.host_create("host-without-components")
        host_outside_cluster = provider.host_create("host-outside-cluster")
        for host in [
            host_single_component,
            host_two_components,
            host_component_without_action,
            host_without_components,
        ]:
            cluster_with_components.host_add(host)
        cluster_with_components.hostcomponent_set(
            (host_single_component, component_with_action),
            (host_two_components, component_with_action),
            (host_two_components, component_without_action),
            (host_component_without_action, component_without_action),
        )
        action_in_object_is_present(action_name, host_single_component)
        action_in_object_is_present(action_name, host_two_components)
        action_in_object_is_absent(action_name, host_component_without_action)
        action_in_object_is_absent(action_name, host_without_components)
        action_in_object_is_absent(action_name, host_outside_cluster)
        action_in_object_is_absent(action_name, cluster_with_components)
        action_in_object_is_absent(action_name, service)
        action_in_object_is_absent(action_name, component_with_action)
        action_in_object_is_absent(action_name, component_without_action)
        run_host_action_and_assert_result(host_single_component, action_name)
        run_host_action_and_assert_result(host_two_components, action_name)

    def test_availability_at_state(self, cluster_with_components: Cluster, provider: Provider):
        """
        Test that component host action is available on specify service state
        """
        service = cluster_with_components.service_add(name=FIRST_SERVICE)
        component = service.component(name=FIRST_COMPONENT)
        adjacent_component = service.component(name=SECOND_COMPONENT)
        host = provider.host_create("host-in-cluster")
        cluster_with_components.host_add(host)
        cluster_with_components.hostcomponent_set((host, component))

        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_cluster_action_and_assert_result(cluster_with_components, SWITCH_CLUSTER_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_service_action_and_assert_result(service, SWITCH_SERVICE_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, SWITCH_HOST_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_component_action_and_assert_result(adjacent_component, SWITCH_COMPONENT_STATE)
        action_in_object_is_absent(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_component_action_and_assert_result(component, SWITCH_COMPONENT_STATE)
        action_in_object_is_present(ACTION_ON_HOST_STATE_REQUIRED, host)
        run_host_action_and_assert_result(host, ACTION_ON_HOST_STATE_REQUIRED)

    @allure.issue("https://arenadata.atlassian.net/browse/ADCM-1799")
    @pytest.mark.parametrize("action_name", [ACTION_ON_HOST, ACTION_ON_HOST_MULTIJOB])
    def test_two_clusters(self, action_name, cluster_with_components: Cluster, provider: Provider):
        """
        Test that component actions on host works fine on two clusters
        """
        second_cluster = cluster_with_components.bundle().cluster_prototype().cluster_create(name="Second cluster")
        service_on_first_cluster = cluster_with_components.service_add(name=FIRST_SERVICE)
        component_on_first_cluster = service_on_first_cluster.component(name=FIRST_COMPONENT)
        service_on_second_cluster = second_cluster.service_add(name=FIRST_SERVICE)
        component_on_second_cluster = service_on_second_cluster.component(name=FIRST_COMPONENT)
        first_host = provider.host_create("host-in-first-cluster")
        second_host = provider.host_create("host-in-second-cluster")
        cluster_with_components.host_add(first_host)
        second_cluster.host_add(second_host)
        cluster_with_components.hostcomponent_set((first_host, component_on_first_cluster))
        second_cluster.hostcomponent_set((second_host, component_on_second_cluster))

        action_in_object_is_present(action_name, first_host)
        action_in_object_is_present(action_name, second_host)
        run_host_action_and_assert_result(first_host, action_name, status="success")
        run_host_action_and_assert_result(second_host, action_name, status="success")


def test_target_group_in_inventory(cluster_with_target_group_action: Cluster, provider: Provider, sdk_client_fs):
    """
    Test that target group action has inventory_hostname info
    """
    hostname = "host-in-cluster"
    host = provider.host_create(hostname)
    cluster_with_target_group_action.host_add(host)
    action_in_object_is_present(ACTION_ON_HOST, host)
    run_host_action_and_assert_result(host, ACTION_ON_HOST)
    with allure.step("Assert that hostname in job log is present"):
        assert (
            f"We are on host: {hostname}" in sdk_client_fs.job().log(type="stdout").content
        ), "No hostname info in the job log"
