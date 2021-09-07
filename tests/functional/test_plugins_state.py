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

# pylint:disable=redefined-outer-name, duplicate-code
from typing import Tuple, Union

import allure
import pytest

from adcm_client.objects import ADCMClient, Cluster, Provider, TaskFailed, Action
from adcm_pytest_plugin.utils import catch_failed
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_service_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_host_action_and_assert_result,
)

from tests.functional.plugin_utils import (
    build_objects_comparator,
    build_objects_checker,
    generate_cluster_success_params,
    get_cluster_related_object,
    compose_name,
    generate_provider_success_params,
    get_provider_related_object,
    AnyADCMObject,
    ADCMObjectField,
    create_two_providers,
    create_two_clusters,
)

NAMES = ('first', 'second')


def compare_cluster_states(
    adcm_object: AnyADCMObject, expected_value: Union[ADCMObjectField, Tuple[ADCMObjectField, ...]]
):
    """
    As we have objects in different states from start (with dummy objects)
    we need to check if "start" state is "one of" dummy states
    """
    adcm_object_name = compose_name(adcm_object)
    adcm_object.reread()
    actual_value = adcm_object.state
    if isinstance(expected_value, Tuple):
        assert (
            actual_value in expected_value
        ), f'State of {adcm_object_name} should be on of {expected_value}, not {actual_value}'
    else:
        assert (
            actual_value == expected_value
        ), f'State of {adcm_object_name} should be {expected_value}, not {actual_value}'


compare_provider_states = build_objects_comparator(lambda obj: obj.state, 'State')
check_cluster_related_objects_state = build_objects_checker(
    Cluster,
    compare_cluster_states,
    changed='ifeelgood!',
    unchanged=('created', 'installed'),
    allure_message='Check state of cluster related objects changed correctly',
)
check_provider_related_objects_state = build_objects_checker(
    Provider,
    compare_provider_states,
    changed='ifeelgood!',
    unchanged='created',
    allure_message='Check state of provider related objects changed correctly',
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
        sdk_client_fs, caller_file=__file__, bundle_dir="cluster" if not hasattr(request, 'param') else request.param
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
    with allure.step(f'Set state of {changed_object_name} with action from {action_owner_name}'):
        _run_successful_task(action_owner_object.action(name=action_name), action_owner_name)
    with allure.step(f'Check only state of {changed_object_name} was changed'):
        check_cluster_related_objects_state(sdk_client_fs, {object_to_be_changed})


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
    with allure.step(f'Set state of {changed_object_name} with action from {action_owner_name}'):
        _run_successful_task(action_owner_object.action(name=action_name), action_owner_name)
    with allure.step(f'Check only state of {changed_object_name} was changed'):
        check_provider_related_objects_state(sdk_client_fs, {object_to_be_changed})


def test_host_from_provider(two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient):
    """Change host state from provider"""
    provider = two_providers[0]
    host = provider.host_list()[0]
    provider_name = compose_name(provider)
    host_name = compose_name(host)
    with allure.step(f'Set state of {host_name} with action from {provider_name}'):
        run_provider_action_and_assert_result(provider, 'set_host_from_provider', config={'host_id': host.id})
    with allure.step(f'Check only state of {host_name} was changed'):
        check_provider_related_objects_state(sdk_client_fs, {host})


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
            run_cluster_action_and_assert_result(cluster, forbidden_action, status='failed')
            check_cluster_related_objects_state(sdk_client_fs)
    with allure.step(f'Check forbidden from service "{name}" context actions'):
        service = cluster.service(name=name)
        for forbidden_action in ('set_component',):
            run_service_action_and_assert_result(service, forbidden_action, status='failed')
            check_cluster_related_objects_state(sdk_client_fs)
    with allure.step(f'Check forbidden from provider "{name}" context actions'):
        provider = sdk_client_fs.provider(name=name)
        for forbidden_action in ('set_host',):
            run_provider_action_and_assert_result(provider, forbidden_action, status='failed')
            check_provider_related_objects_state(sdk_client_fs)
    with allure.step(f'Check forbidden from host "{first_first_fqdn}" context actions'):
        host_first = sdk_client_fs.host(fqdn=first_first_fqdn)
        host_second = sdk_client_fs.host(fqdn=first_second_fqdn)
        run_host_action_and_assert_result(
            host_first, 'set_host_from_provider', config={'host_id': host_second.id}, status='failed'
        )
        check_provider_related_objects_state(sdk_client_fs)


@pytest.mark.parametrize("two_clusters", ["cluster_double_call"], indirect=True)
def test_double_call_to_state_set(two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient):
    """Test that double call to plugin from two files doesn't fail"""
    cluster = two_clusters[0]
    run_cluster_action_and_assert_result(cluster, 'double_call_two_playbooks')
    with allure.step(f'Check only state of Cluster "{cluster.name}" was changed'):
        check_cluster_related_objects_state(sdk_client_fs, {cluster})


# pylint: disable-next=possibly-unused-variable
def test_state_set_from_host_actions(
    two_providers: Tuple[Provider, Provider], two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient
):
    """Test that host actions actually change state"""
    name = "first"
    with allure.step('Bind component to host'):
        host = two_providers[0].host_list()[0]
        component = (service := (cluster := two_clusters[0]).service(name=name)).component(name=name)
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
    affected_objects = set()
    for object_type in ('cluster', 'service', 'component'):
        with allure.step(f'Check change {object_type} state from host action'):
            run_host_action_and_assert_result(host, f'set_{object_type}_host_action')
            affected_objects.add(locals()[object_type])
            check_cluster_related_objects_state(sdk_client_fs, affected_objects)


# !===== Steps and Helpers =====!


def _run_successful_task(action: Action, action_owner_name: str):
    """Run action and expect it succeeds"""
    task = action.run()
    with catch_failed(TaskFailed, f'Action {action.name} should have succeeded when ran on {action_owner_name}'):
        task.try_wait()
