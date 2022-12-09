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

"""Test concerns with hosts in MM"""

from typing import Tuple

import allure
import pytest
from adcm_client.objects import Cluster, Host, Provider
from tests.functional.maintenance_mode.conftest import (
    BUNDLES_DIR,
    turn_mm_off,
    turn_mm_on,
)
from tests.functional.tools import AnyADCMObject

# pylint: disable=redefined-outer-name


@pytest.fixture()
def provider_host_with_concerns(sdk_client_fs) -> Tuple[Provider, Host]:
    """Create provider and host with concerns about their configs"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'provider_with_issues')
    provider = bundle.provider_create('Provider with issues')
    return provider, provider.host_create('host-with-issues')


@pytest.fixture()
def _set_provider_config(provider_host_with_concerns) -> None:
    provider, _ = provider_host_with_concerns
    provider.config_set_diff({'param': 'it is not important actually'})


@pytest.fixture()
def _set_host_config(provider_host_with_concerns) -> None:
    _, host = provider_host_with_concerns
    host.config_set_diff({'param': 'it is not important actually'})


@pytest.mark.usefixtures('_set_provider_config')
def test_mm_host_with_concern_not_raising_issue_on_cluster_objects(
    api_client, cluster_with_mm, provider_host_with_concerns
):
    """
    Test that when there's a concern on host that is in MM and mapped to a cluster,
    cluster objects don't have issues, but host does
    """
    _, host = provider_host_with_concerns
    service = cluster_with_mm.service()
    component = service.component()

    cluster_with_mm.host_add(host)
    _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
    _check_no_concerns_on_cluster_objects(cluster_with_mm)

    with allure.step('Map component to host with a concern and check concern appeared on cluster objects'):
        cluster_with_mm.hostcomponent_set((host, component))
        _check_concerns_are_presented_on_cluster_objects(cluster_with_mm)

    with allure.step('Turn MM on and check that concerns are gone'):
        turn_mm_on(api_client, host)
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_no_concerns_on_cluster_objects(cluster_with_mm)

    with allure.step('Turn MM off and check that concerns have returned'):
        turn_mm_off(api_client, host)
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_concerns_are_presented_on_cluster_objects(cluster_with_mm)


@pytest.mark.usefixtures('_set_host_config')
def test_host_from_provider_with_concern_not_raising_issue_on_cluster_objects(
    api_client, cluster_with_mm, provider_host_with_concerns
):
    """
    Test that when there's a concern on provider, but not on host,
    and component is mapped on host,
    cluster objects aren't affected when host is in MM
    """
    provider, host = provider_host_with_concerns
    service = cluster_with_mm.service()
    component = service.component()

    with allure.step(
        'Add host to a cluster and check that concern from provider affects host, provider, but not cluster objects'
    ):
        cluster_with_mm.host_add(host)
        # since host own config is set, provider's concern should affect the host
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_concern_is_presented_on_object(provider, f'provider {provider.name}')
        _check_no_concerns_on_cluster_objects(cluster_with_mm)

    with allure.step(
        'Map component to host with a concern and check concern from provider appeared on cluster objects'
    ):
        cluster_with_mm.hostcomponent_set((host, component))
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_concern_is_presented_on_object(provider, f'provider {provider.name}')
        _check_concerns_are_presented_on_cluster_objects(cluster_with_mm)

    with allure.step('Turn MM on and check that concerns are gone'):
        turn_mm_on(api_client, host)
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_concern_is_presented_on_object(provider, f'provider {provider.name}')
        _check_no_concerns_on_cluster_objects(cluster_with_mm)

    with allure.step('Turn MM off and check that concerns have returned'):
        turn_mm_off(api_client, host)
        _check_concern_is_presented_on_object(host, f'host {host.fqdn}')
        _check_concern_is_presented_on_object(provider, f'provider {provider.name}')
        _check_concerns_are_presented_on_cluster_objects(cluster_with_mm)


def _check_no_concerns_on_cluster_objects(cluster: Cluster):
    with allure.step(f'Check there is 0 concerns on objects from cluster {cluster.name}'):
        _check_no_concerns_on_object(cluster, f'cluster {cluster.name}')
        for service in cluster.service_list():
            _check_no_concerns_on_object(service, f'service {service.name}')
            for component in service.component_list():
                _check_no_concerns_on_object(service, f'component {component.name} of {service.name}')


def _check_no_concerns_on_object(obj: AnyADCMObject, verbose_name: str):
    obj.reread()
    concerns = obj.concerns()
    assert len(concerns) == 0, f'There should not be any concerns on {verbose_name}.\nActual are: {concerns}'


def _check_concerns_are_presented_on_cluster_objects(cluster: Cluster):
    with allure.step(f'Check there at least 1 concern on objects from cluster {cluster.name}'):
        _check_concern_is_presented_on_object(cluster, f'cluster {cluster.name}')
        for service in cluster.service_list():
            _check_concern_is_presented_on_object(service, f'service {service.name}')
            for component in service.component_list():
                _check_concern_is_presented_on_object(service, f'component {component.name} of {service.name}')


def _check_concern_is_presented_on_object(obj: AnyADCMObject, verbose_name: str):
    obj.reread()
    concerns = obj.concerns()
    assert len(concerns) != 0, f'There should be at least one concern on {verbose_name}.\nActual are: {concerns}'
