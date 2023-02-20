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

"""Test plugin adcm_hc"""

from collections.abc import Callable

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    Host,
    Job,
    Provider,
    Service,
)
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir

# pylint: disable=redefined-outer-name


CLUSTER_NAME = "Best Cluster Ever"
PROVIDER_NAME = "Best Provider Ever"


class TestPluginWorksFromAllADCMObjects:
    """
    Check that adcm_hc plugin works correctly
    when it is called from Cluster, Service and Component context
    """

    HC_CHANGE_ACTION_NAME = "change_hc_map"
    EXPECTED_HC_MAP = {
        ("test-service-host", "test_service", "test_component"),
        ("another-service-host", "another_service", "test_component"),
    }

    @pytest.fixture()
    def cluster_with_services(self, sdk_client_fs: ADCMClient) -> tuple[Cluster, Service, Service]:
        """Return cluster and two services connected to cluster"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "clusters", "different_objects"))
        cluster = bundle.cluster_create(CLUSTER_NAME)
        test_service = cluster.service_add(name="test_service")
        another_service = cluster.service_add(name="another_service")
        return cluster, test_service, another_service

    @pytest.fixture()
    def provider_with_hosts(self, sdk_client_fs: ADCMClient) -> tuple[Provider, Host, Host]:
        """Return provider and two hosts"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
        provider = bundle.provider_create(PROVIDER_NAME)
        test_host = provider.host_create("test-service-host")
        another_host = provider.host_create("another-service-host")
        return provider, test_host, another_host

    @pytest.fixture()
    def set_hc_map(self, cluster_with_services, provider_with_hosts):
        """Set HC map for test"""
        cluster, test_service, another_service = cluster_with_services
        _, test_host, another_host = provider_with_hosts
        cluster.host_add(test_host)
        cluster.host_add(another_host)
        return cluster.hostcomponent_set(
            (test_host, test_service.component(name="another_component")),
            (another_host, another_service.component(name="another_component")),
        )

    def _get_cluster(self, adcm_client: ADCMClient) -> Cluster:
        """Get cluster object"""
        return adcm_client.cluster(name=CLUSTER_NAME)

    def _get_service(self, adcm_client: ADCMClient) -> Service:
        """Get test_service from cluster"""
        return self._get_cluster(adcm_client).service(name="test_service")

    def _get_component(self, adcm_client: ADCMClient) -> Component:
        """Get test_component from test_service from cluster"""
        return self._get_service(adcm_client).component(name="test_component")

    @pytest.mark.parametrize(
        ("get_object", "run_action_and_wait_result"),
        [
            (_get_cluster, run_cluster_action_and_assert_result),
            (_get_service, run_service_action_and_assert_result),
            (_get_component, run_component_action_and_assert_result),
        ],
        ids=["on_cluster", "on_service", "on_component"],
    )
    @pytest.mark.usefixtures("set_hc_map", "cluster_with_services", "provider_with_hosts")
    def test_hc_map_change_by_adcm_hc_plugin(
        self,
        get_object: Callable,
        run_action_and_wait_result: Callable,
        sdk_client_fs: ADCMClient,
    ):
        """Check that hc_map works as expected on cluster/service/component"""
        action_owner_object = get_object(self, sdk_client_fs)
        with allure.step(f"Change Host-Component map from action on {action_owner_object.__class__.__name__}"):
            run_action_and_wait_result(action_owner_object, self.HC_CHANGE_ACTION_NAME)
        self._check_hc_map_is_correct(sdk_client_fs)

    @allure.step("Check Host-Component map was changed correctly")
    def _check_hc_map_is_correct(self, adcm_client: ADCMClient):
        """Check that hc map is correct after adcm_hc action"""
        actual_hc_map = {
            (hc["host"], hc["service_name"], hc["component"])
            for hc in adcm_client.cluster(name=CLUSTER_NAME).hostcomponent()
        }
        assert (
            actual_hc_map == self.EXPECTED_HC_MAP
        ), f"Host-Component map isn't the same as expected. Got: {actual_hc_map}. Expected: {self.EXPECTED_HC_MAP}"


class TestPluginCanBreakConstraints:
    """
    Check that action that uses adcm_hc plugin can "break" component constraints
    during execution if "in the end" constraints are satisfied
    """

    @pytest.fixture()
    def cluster_with_service(self, sdk_client_fs: ADCMClient) -> tuple[Cluster, Service]:
        """Return cluster with service"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "clusters", "constraints"))
        cluster = bundle.cluster_create(CLUSTER_NAME)
        test_service = cluster.service_add(name="test_service")
        return cluster, test_service

    @pytest.fixture()
    def provider_with_hosts(self, sdk_client_fs: ADCMClient) -> tuple[Provider, Host, Host, Host]:
        """Return provider and three hosts"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
        provider = bundle.provider_create(PROVIDER_NAME)
        hosts = tuple(provider.host_create(f"{prefix}-host") for prefix in ("first", "second", "third"))
        return provider, *hosts

    @pytest.fixture()
    def set_hc_map(self, cluster_with_service, provider_with_hosts):
        """Set HC map for test"""
        cluster, test_service = cluster_with_service
        _, first_host, second_host, third_host = provider_with_hosts
        cluster.host_add(first_host)
        cluster.host_add(second_host)
        cluster.host_add(third_host)
        return cluster.hostcomponent_set(
            (first_host, test_service.component(name="test_component")),
            (second_host, test_service.component(name="test_component")),
        )

    @pytest.mark.usefixtures("set_hc_map")
    def test_correct_hc_change(self, cluster_with_service: tuple[Cluster, Service]):
        """
        Check that correct "break" of HC constraints works.
        Correct "break" is when constraints are satisfied after the action's end
        but was "broken" during action execution.
        """
        cluster, _ = cluster_with_service
        run_cluster_action_and_assert_result(cluster, "correct_hc_map_change")

    @pytest.mark.usefixtures("set_hc_map")
    def test_incorrect_hc_change(self, cluster_with_service: tuple[Cluster, Service]):
        """
        Check that incorrect "break" of HC constraints if forbidden.
        Incorrect "break" is when constraints are "broken" during action's execution
        and wasn't restored after all operations.
        """
        error = "COMPONENT_CONSTRAINT_ERROR"
        cluster, _ = cluster_with_service
        task = run_cluster_action_and_assert_result(cluster, "incorrect_hc_map_change", status="failed")
        job: Job = task.job_list()[0]
        with allure.step(f'Check "{error}" is in log'):
            assert error in job.log(type="stdout").content, f"Error message in log should contain {error}"
