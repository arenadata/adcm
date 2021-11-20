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

from typing import Tuple, Callable

import allure
import pytest
from adcm_client.objects import Cluster, Provider, ADCMClient, Service, Host, Component
from adcm_pytest_plugin.utils import get_data_dir
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_service_action_and_assert_result,
    run_component_action_and_assert_result,
)

from tests.functional.tools import ClusterRelatedObject

# pylint: disable=redefined-outer-name

EXPECTED_HC_MAP = {
    ('test-service-host', 'test_service', 'test_component'),
    ('another-service-host', 'another_service', 'test_component'),
}

CLUSTER_NAME = 'Best Cluster Ever'
PROVIDER_NAME = 'Best Provider Ever'
HC_CHANGE_ACTION_NAME = 'change_hc_map'


@pytest.fixture()
def cluster_with_services(sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service, Service]:
    """Return cluster and two services connected to cluster"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster"))
    cluster = bundle.cluster_create(CLUSTER_NAME)
    test_service = cluster.service_add(name='test_service')
    another_service = cluster.service_add(name='another_service')
    return cluster, test_service, another_service


@pytest.fixture()
def provider_with_hosts(sdk_client_fs: ADCMClient) -> Tuple[Provider, Host, Host]:
    """Return provider and two hosts"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    provider = bundle.provider_create(PROVIDER_NAME)
    test_host = provider.host_create('test-service-host')
    another_host = provider.host_create('another-service-host')
    return provider, test_host, another_host


@pytest.fixture()
def set_hc_map(cluster_with_services, provider_with_hosts):
    """Set HC map for test"""
    cluster, test_service, another_service = cluster_with_services
    _, test_host, another_host = provider_with_hosts
    cluster.host_add(test_host)
    cluster.host_add(another_host)
    return cluster.hostcomponent_set(
        (test_host, test_service.component(name='another_component')),
        (another_host, another_service.component(name='another_component')),
    )


def _get_cluster(adcm_client: ADCMClient) -> Cluster:
    """Get cluster object"""
    return adcm_client.cluster(name=CLUSTER_NAME)


def _get_service(adcm_client: ADCMClient) -> Service:
    """Get test_service from cluster"""
    return _get_cluster(adcm_client).service(name='test_service')


def _get_component(adcm_client: ADCMClient) -> Component:
    """Get test_component from test_service from cluster"""
    return _get_service(adcm_client).component(name='test_component')


@pytest.mark.parametrize(
    ('get_object', 'run_action_and_wait_result'),
    [
        (_get_cluster, run_cluster_action_and_assert_result),
        (_get_service, run_service_action_and_assert_result),
        (_get_component, run_component_action_and_assert_result),
    ],
    ids=['on_cluster', 'on_service', 'on_component'],
)
@pytest.mark.usefixtures('set_hc_map', 'cluster_with_services', 'provider_with_hosts')
def test_hc_map_change_by_adcm_hc_plugin(
    get_object: Callable[[ADCMClient], ClusterRelatedObject],
    run_action_and_wait_result: Callable,
    sdk_client_fs: ADCMClient,
):
    """Check that hc_map works as expected on cluster/service/component"""
    action_owner_object = get_object(sdk_client_fs)
    with allure.step(f'Change Host-Component map from action on {action_owner_object.__class__.__name__}'):
        run_action_and_wait_result(action_owner_object, HC_CHANGE_ACTION_NAME)
    _check_hc_map_is_correct(sdk_client_fs)


@allure.step('Check Host-Component map was changed correctly')
def _check_hc_map_is_correct(adcm_client: ADCMClient):
    """Check that hc map is correct after adcm_hc action"""
    actual_hc_map = {
        (hc['host'], hc['service_name'], hc['component'])
        for hc in adcm_client.cluster(name=CLUSTER_NAME).hostcomponent()
    }
    assert (
        actual_hc_map == EXPECTED_HC_MAP
    ), f"Host-Component map isn't the same as expected. Got: {actual_hc_map}. Expected: {EXPECTED_HC_MAP}"
