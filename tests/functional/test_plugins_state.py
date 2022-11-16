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

"""Tests for adcm_state plugin"""

# pylint:disable=redefined-outer-name
from typing import Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Host, Provider, Service
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from tests.functional.plugin_utils import (
    TestImmediateChange,
    build_objects_checker,
    compose_name,
    create_two_clusters,
    create_two_providers,
    generate_cluster_success_params,
    generate_provider_success_params,
    get_cluster_related_object,
    get_provider_related_object,
    run_successful_task,
)

check_objects_state_changed = build_objects_checker(
    field_name='State',
    changed='ifeelgood!',
    extractor=lambda obj: obj.state,
)

# !===== Fixtures =====!


@pytest.fixture()
def two_providers(sdk_client_fs: ADCMClient) -> Tuple[Provider, Provider]:
    """Get two providers with two hosts"""
    return create_two_providers(sdk_client_fs, __file__, "hostprovider")


@pytest.fixture()
def two_clusters(request, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Cluster]:
    """Get two clusters with both services"""
    return create_two_clusters(
        sdk_client_fs,
        caller_file=__file__,
        bundle_dir="cluster" if not hasattr(request, 'param') else request.param,
    )


# !===== Tests =====!


@pytest.mark.parametrize(
    ('action_name', 'object_to_be_changed', 'action_owner'),
    generate_cluster_success_params(action_prefix='set', id_template='set_{}_state'),
)
@pytest.mark.usefixtures("two_clusters")
def test_cluster_related_objects(
    action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct set state calls can run successfully
        with Cluster, Service, Component
        and change only the objects that must be changed
    """
    object_to_be_changed = get_cluster_related_object(sdk_client_fs, *object_to_be_changed)
    changed_object_name = compose_name(object_to_be_changed)
    action_owner_object = get_cluster_related_object(sdk_client_fs, *action_owner)
    action_owner_name = compose_name(action_owner_object)
    with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
        f'Set state of {changed_object_name} with action from {action_owner_name}'
    ):
        run_successful_task(action_owner_object.action(name=action_name), action_owner_name)


@pytest.mark.parametrize(
    ('action_name', 'object_to_be_changed', 'action_owner'),
    generate_provider_success_params(action_prefix='set', id_template='set_{}_state'),
)
@pytest.mark.usefixtures("two_providers")
def test_provider_related_objects(
    action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct set state calls can run successfully
        with Provider and Host
        and change only the objects that must be changed
    """
    object_to_be_changed = get_provider_related_object(sdk_client_fs, *object_to_be_changed)
    changed_object_name = compose_name(object_to_be_changed)
    action_owner_object = get_provider_related_object(sdk_client_fs, *action_owner)
    action_owner_name = compose_name(action_owner_object)
    with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
        f'Set state of {changed_object_name} with action from {action_owner_name}'
    ):
        run_successful_task(action_owner_object.action(name=action_name), action_owner_name)


def test_host_from_provider(two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient):
    """Change host state from provider"""
    provider = two_providers[0]
    host = provider.host_list()[0]
    provider_name = compose_name(provider)
    host_name = compose_name(host)
    with check_objects_state_changed(sdk_client_fs, {host}), allure.step(
        f'Set state of {host_name} with action from {provider_name}'
    ):
        run_provider_action_and_assert_result(provider, 'set_host_from_provider', config={'host_id': host.id})


# pylint: disable-next=possibly-unused-variable
@pytest.mark.usefixtures('two_clusters', 'two_providers')
def test_forbidden_state_set_actions(sdk_client_fs: ADCMClient):
    """
    Check that forbidden caller-context combinations fail as actions
        and don't affect any ADCM objects
    """
    name = "first"
    first_first_fqdn = "first-first"
    first_second_fqdn = "first-second"
    with allure.step(f'Check forbidden from cluster "{name}" context actions'):
        cluster = sdk_client_fs.cluster(name=name)
        for forbidden_action in ('set_service', 'set_component'):
            with check_objects_state_changed(sdk_client_fs):
                run_cluster_action_and_assert_result(cluster, forbidden_action, status='failed')
    with allure.step(f'Check forbidden from service "{name}" context actions'):
        service = cluster.service(name=name)
        with check_objects_state_changed(sdk_client_fs):
            run_service_action_and_assert_result(service, 'set_component', status='failed')
    with allure.step(f'Check forbidden from provider "{name}" context actions'):
        provider = sdk_client_fs.provider(name=name)
        with check_objects_state_changed(sdk_client_fs):
            run_provider_action_and_assert_result(provider, 'set_host', status='failed')
    with allure.step(f'Check forbidden from host "{first_first_fqdn}" context actions'):
        host_first = sdk_client_fs.host(fqdn=first_first_fqdn)
        host_second = sdk_client_fs.host(fqdn=first_second_fqdn)
        with check_objects_state_changed(sdk_client_fs):
            run_host_action_and_assert_result(
                host_first,
                'set_host_from_provider',
                config={'host_id': host_second.id},
                status='failed',
            )


@pytest.mark.parametrize("two_clusters", ["cluster_double_call"], indirect=True)
def test_double_call_to_state_set(two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient):
    """Test that double call to plugin from two files doesn't fail"""
    cluster = two_clusters[0]
    run_cluster_action_and_assert_result(cluster, 'double_call_two_playbooks')
    with allure.step(f'Check only state of Cluster "{cluster.name}" was changed'):
        check_objects_state_changed(sdk_client_fs, {cluster})


def test_state_set_from_host_actions(
    two_providers: Tuple[Provider, Provider],
    two_clusters: Tuple[Cluster, Cluster],
    sdk_client_fs: ADCMClient,
):
    """Test that host actions actually change state"""
    name = "first"
    with allure.step('Bind component to host'):
        host = two_providers[0].host_list()[0]
        component = (service := (cluster := two_clusters[0]).service(name=name)).component(name=name)
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
    affected_objects = set()
    for obj in (cluster, service, component):
        classname = obj.__class__.__name__.lower()
        affected_objects.add(obj)
        with check_objects_state_changed(sdk_client_fs, affected_objects), allure.step(
            f'Check change {compose_name(obj)} state from host action'
        ):
            run_host_action_and_assert_result(host, f'set_{classname}_host_action')


class TestImmediateStateChange(TestImmediateChange):
    """Test that state changed immediately"""

    _file = __file__

    @allure.issue(url='https://arenadata.atlassian.net/browse/ADCM-2116')
    def test_immediate_state_change(
        self,
        provider_host: Tuple[Provider, Host],
        cluster_service_component: Tuple[Cluster, Service, Component],
    ):
        """Test that state is changed right after adcm_state step in multijob action"""
        self.run_immediate_change_test(provider_host, cluster_service_component)
