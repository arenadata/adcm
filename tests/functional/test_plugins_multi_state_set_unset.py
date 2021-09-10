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

from typing import Tuple, List, Callable

import pytest
import allure

from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_service_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_host_action_and_assert_result,
    wait_for_task_and_assert_result,
    run_component_action_and_assert_result,
)
from adcm_client.objects import ADCMClient, Cluster, Provider, Action

# pylint: disable=redefined-outer-name, duplicate-code

# same for cluster, service, component (when only 2 of each)
from tests.functional.plugin_utils import (
    generate_cluster_success_params,
    generate_provider_success_params,
    compose_name,
    build_objects_checker,
    build_objects_comparator,
    AnyADCMObject,
    get_cluster_related_object,
    get_provider_related_object,
    create_two_clusters,
    create_two_providers,
)

# default *solo* multi state value
MULTI_STATE = ['ifeelgood!']


# Prepare common functions for working with ADCM objects state


def _prepare_multi_state(multi_state: List[str]) -> List[str]:
    """Ensures multi state is sorted"""
    multi_state.sort()
    return multi_state


multi_state_comparator = build_objects_comparator(lambda obj: obj.multi_state, 'Multi state', _prepare_multi_state)

check_cluster_related_objects_multi_state = build_objects_checker(
    Cluster,
    multi_state_comparator,
    changed=MULTI_STATE,
    unchanged=[],
    allure_message='Check multi state of cluster related objects changed correctly',
)

check_provider_related_objects_multi_state = build_objects_checker(
    Provider,
    multi_state_comparator,
    changed=MULTI_STATE,
    unchanged=[],
    allure_message='Check multi state of provider related objects changed correctly',
)


# !===== Fixtures =====!


@pytest.fixture()
def two_clusters(request, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Cluster]:
    """Get two clusters with both services"""
    return create_two_clusters(
        sdk_client_fs, caller_file=__file__, bundle_dir="cluster" if not hasattr(request, 'param') else request.param
    )


@pytest.fixture()
def two_providers(sdk_client_fs: ADCMClient) -> Tuple[Provider, Provider]:
    """Get two providers with two hosts"""
    return create_two_providers(sdk_client_fs, __file__, "provider")


# !===== Tests =====!


@pytest.mark.parametrize(
    ('set_action_name', 'object_to_be_changed', 'action_owner'),
    generate_cluster_success_params(action_prefix='set', id_template='set_{}_multi_state'),
)
@pytest.mark.usefixtures("two_clusters")
def test_cluster_related_objects(
    set_action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct multi_state_set calls can run successfully
        with Cluster, Service, Component
        and change only the objects that must be changed
    Then unset state and check that none of objects has multi state
    """
    _test_successful_multi_state_set_unset(
        set_action_name,
        object_to_be_changed,
        action_owner,
        sdk_client_fs,
        check_cluster_related_objects_multi_state,
        get_cluster_related_object,
    )


@pytest.mark.parametrize(
    ('set_action_name', 'object_to_be_changed', 'action_owner'),
    generate_provider_success_params(action_prefix='set', id_template='set_{}_multi_state'),
)
@pytest.mark.usefixtures("two_providers")
def test_provider_related_objects(
    set_action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct multi_state_set calls can run successfully
        with Provider and Host
        and change only the objects that must be changed
    Then unset state and check that none of objects has multi state
    """
    _test_successful_multi_state_set_unset(
        set_action_name,
        object_to_be_changed,
        action_owner,
        sdk_client_fs,
        check_provider_related_objects_multi_state,
        get_provider_related_object,
    )


def test_host_from_provider(two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient):
    """Change host multi state from provider"""
    provider = two_providers[0]
    host = provider.host_list()[0]
    provider_name = compose_name(provider)
    host_name = compose_name(host)
    with allure.step(f'Set multi state of {host_name} with action from {provider_name}'):
        run_provider_action_and_assert_result(provider, 'set_host_from_provider', config={'host_id': host.id})
    with allure.step(f'Check only state of {host_name} was changed'):
        check_provider_related_objects_multi_state(sdk_client_fs, {host})
    with allure.step(f'Unset multi state of {host_name} with action from {provider_name}'):
        run_provider_action_and_assert_result(provider, 'unset_host_from_provider', config={'host_id': host.id})
    with allure.step('Check state of every object is as it was before "set"'):
        check_provider_related_objects_multi_state(sdk_client_fs)


@pytest.mark.parametrize("two_clusters", ["cluster_double_call"], indirect=True)
def test_double_call_to_multi_state_set(two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient):
    """Test that double call to plugin from two files doesn't fail"""
    expected_after_set = _prepare_multi_state(['much', 'better', 'actually'])
    expected_after_unset = ['actually']
    cluster = two_clusters[0]
    run_cluster_action_and_assert_result(cluster, 'double_call_two_playbooks')
    with allure.step(f'Check only state of Cluster "{cluster.name}" was changed'):
        check_cluster_related_objects_multi_state(sdk_client_fs, {cluster}, alternative_changed=expected_after_set)
    run_cluster_action_and_assert_result(cluster, 'double_unset')
    with allure.step(f'Check state of Cluster "{cluster.name}" changed after unset'):
        check_cluster_related_objects_multi_state(sdk_client_fs, {cluster}, alternative_changed=expected_after_unset)


@pytest.mark.usefixtures('two_clusters', 'two_providers')
def test_forbidden_multi_state_set_actions(sdk_client_fs: ADCMClient):
    """
    Check that forbidden caller-context combinations fail as actions
        and don't affect any ADCM objects
    """
    name = "first"
    with allure.step(f'Check forbidden from cluster "{name}" context actions'):
        cluster = sdk_client_fs.cluster(name=name)
        # missing is used because it should fail for misconfiguration reasons, not because state not set
        for forbidden_action in ('set_service', 'set_component', 'unset_service_missing', 'unset_component_missing'):
            run_cluster_action_and_assert_result(cluster, forbidden_action, status='failed')
            check_cluster_related_objects_multi_state(sdk_client_fs)
    with allure.step(f'Check forbidden from service "{name}" context actions'):
        service = cluster.service(name=name)
        for forbidden_action in ('set_component', 'unset_component_missing'):
            run_service_action_and_assert_result(service, forbidden_action, status='failed')
            check_cluster_related_objects_multi_state(sdk_client_fs)
    with allure.step(f'Check forbidden from provider "{name}" context actions'):
        provider = sdk_client_fs.provider(name=name)
        for forbidden_action in ('set_host', 'unset_host_missing'):
            run_provider_action_and_assert_result(provider, forbidden_action, status='failed')
            check_provider_related_objects_multi_state(sdk_client_fs)


@pytest.mark.usefixtures('two_providers', 'two_clusters')
def test_missing_ok_multi_state_unset(sdk_client_fs: ADCMClient):
    """
    Checking behaviour of flag "missing_ok":
        - Job fails when flag is "false" and state is not in multi_state
        - Job succeed when flag is "true" and state is not in multi_state
    """
    provider = sdk_client_fs.provider()
    host = provider.host()
    cluster = sdk_client_fs.cluster()
    service = cluster.service()
    component = service.component()
    with allure.step('Check job fails with "missing_ok: false" and state not in multi_state'):
        for forbidden_action in ('unset_provider', 'unset_host'):
            run_host_action_and_assert_result(host, forbidden_action, 'failed')
            check_provider_related_objects_multi_state(sdk_client_fs)
        run_provider_action_and_assert_result(
            provider, 'unset_host_from_provider', status='failed', config={'host_id': host.id}
        )
        check_provider_related_objects_multi_state(sdk_client_fs)
        run_cluster_action_and_assert_result(cluster, 'unset_cluster', status='failed')
        check_cluster_related_objects_multi_state(sdk_client_fs)
        run_service_action_and_assert_result(service, 'unset_service', status='failed')
        check_cluster_related_objects_multi_state(sdk_client_fs)
        run_component_action_and_assert_result(component, 'unset_component', status='failed')
        check_cluster_related_objects_multi_state(sdk_client_fs)

    with allure.step('Check job succeed with "missing_ok: true" without changing multi_state of any object'):
        for allowed_action in ('unset_provider_missing', 'unset_host_missing'):
            run_host_action_and_assert_result(host, allowed_action)
            check_provider_related_objects_multi_state(sdk_client_fs)
        run_provider_action_and_assert_result(provider, 'unset_host_from_provider_missing', config={'host_id': host.id})
        run_cluster_action_and_assert_result(cluster, 'unset_cluster_missing')
        check_cluster_related_objects_multi_state(sdk_client_fs)
        run_service_action_and_assert_result(service, 'unset_service_missing')
        check_cluster_related_objects_multi_state(sdk_client_fs)
        run_component_action_and_assert_result(component, 'unset_component_missing')
        check_cluster_related_objects_multi_state(sdk_client_fs)


# pylint: disable-next=possibly-unused-variable
def test_multi_state_set_from_host_actions(
    two_clusters: Tuple[Cluster, Cluster], two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient
):
    """Test that host actions actually change multi state"""
    name = "first"
    with allure.step('Bind component to host'):
        component = (service := (cluster := two_clusters[0]).service(name=name)).component(name=name)
        host = two_providers[0].host_list()[0]
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
    affected_objects = set()
    for object_type in ('cluster', 'service', 'component'):
        with allure.step(f'Check change {object_type} multi state from host action'):
            run_host_action_and_assert_result(host, f'set_{object_type}_host_action')
            affected_objects.add(locals()[object_type])
            check_cluster_related_objects_multi_state(sdk_client_fs, affected_objects)


def test_multi_state_set_unset_from_different_objects(two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient):
    """
    Check that one object change multi-state of another object
        and another object can unset this multi-state
    """
    cluster = two_clusters[0]
    cluster_name = compose_name(cluster)
    service = cluster.service()
    service_name = compose_name(service)
    with allure.step(f'Set multi_state of {service_name} from {cluster_name}'):
        run_cluster_action_and_assert_result(cluster, f'set_{service.name}_service')
        check_cluster_related_objects_multi_state(sdk_client_fs, {service})
    with allure.step(f'Unset multi_state of {service_name} from itself'):
        run_service_action_and_assert_result(service, 'unset_service')
        check_cluster_related_objects_multi_state(sdk_client_fs)
    with allure.step(f'Set multi_state of {cluster_name} from itself'):
        run_cluster_action_and_assert_result(cluster, 'set_cluster')
        check_cluster_related_objects_multi_state(sdk_client_fs, {cluster})
    with allure.step(f'Unset multi_state of {cluster_name} from {service_name}'):
        run_service_action_and_assert_result(service, 'unset_cluster')
        check_cluster_related_objects_multi_state(sdk_client_fs)


# pylint: disable-next=too-many-arguments
def _test_successful_multi_state_set_unset(
    set_action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
    check_multi_state_func: Callable,
    get_object_func: Callable[..., AnyADCMObject],
):
    """Test successful multi state of one object set and then unset"""
    object_to_be_changed = get_object_func(sdk_client_fs, *object_to_be_changed)
    changed_object_name = compose_name(object_to_be_changed)
    action_owner_object = get_object_func(sdk_client_fs, *action_owner)
    action_owner_name = compose_name(action_owner_object)
    with allure.step(f'Set multi state of {changed_object_name} with action from {action_owner_name}'):
        _run_successful_task(action_owner_object.action(name=set_action_name), action_owner_name)
    with allure.step(f'Check only state of {changed_object_name} was changed'):
        check_multi_state_func(sdk_client_fs, {object_to_be_changed})
    with allure.step(f'Unset multi state of {changed_object_name} with action from {action_owner_name}'):
        _run_successful_task(action_owner_object.action(name=f'un{set_action_name}'), action_owner_name)
    with allure.step(f'Check state of {changed_object_name} returned to "before set" state'):
        check_multi_state_func(sdk_client_fs)


# !===== Steps and Helpers =====!


def _run_successful_task(action: Action, action_owner_name: str):
    """Run action and expect it succeeds"""
    task = action.run()
    try:
        wait_for_task_and_assert_result(task, status="success")
    except AssertionError as error:
        raise AssertionError(
            f'Action {action.name} should have succeeded when ran on {action_owner_name}:\n' f'{error}'
        ) from error
