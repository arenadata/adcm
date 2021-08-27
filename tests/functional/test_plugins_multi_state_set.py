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

# pylint: disable=redefined-outer-name

from typing import Collection, Optional, Set, Union, Tuple, List, Callable

import pytest
import allure

from _pytest.mark.structures import ParameterSet
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_service_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_host_action_and_assert_result,
)
from adcm_pytest_plugin.utils import catch_failed
from adcm_client.objects import ADCMClient, Cluster, Service, Component, Host, Provider, TaskFailed

# same for cluster, service, component (when only 2 of each)
NAMES = ('first', 'second')

# type of function to get particular ADCM cluster objects using Client
ADCMClusterObjectGetter = Callable[[ADCMClient], Union[Cluster, Service, Component]]
# same for provider
ADCMProviderObjectGetter = Callable[[ADCMClient], Union[Provider, Host]]


@pytest.fixture()
def two_clusters(request, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Cluster]:
    """Get two clusters with both services"""
    bundle_dir = "cluster" if not hasattr(request, 'param') else request.param
    uploaded_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, bundle_dir))
    first_cluster = uploaded_bundle.cluster_create(name=NAMES[0])
    second_cluster = uploaded_bundle.cluster_create(name=NAMES[1])
    clusters = (first_cluster, second_cluster)
    for cluster in clusters:
        for name in NAMES:
            cluster.service_add(name=name)
    return clusters


@pytest.fixture()
def two_providers(sdk_client_fs: ADCMClient) -> Tuple[Provider, Provider]:
    """Get two providers with two hosts"""
    uploaded_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "provider"))
    first_provider, second_provider, *_ = [uploaded_bundle.provider_create(name=name) for name in NAMES]
    providers = (first_provider, second_provider)
    for provider in providers:
        for suffix in NAMES:
            provider.host_create(fqdn=f'{provider.name}-{suffix}')
    return providers


# !===== Prepare test params =====!


def _prepare_get_cluster_object_func(
    service: Optional[str] = None, component: Optional[str] = None
) -> ADCMClusterObjectGetter:
    """
    Get function to get one of ADCM cluster objects:

    - Cluster (when all args are None)
    - Service (when only service argument is not None)
    - Component (when both arguments are not None)

    All objects comes from "first" cluster
    """
    cluster_name = "first"
    if service is None and component is None:
        return lambda client: client.cluster(name=cluster_name)
    if service and component is None:
        return lambda client: client.cluster(name=cluster_name).service(name=service)
    if service and component:
        return lambda client: client.cluster(name=cluster_name).service(name=service).component(name=component)
    raise AttributeError('You can provide either only "service" argument or both "service" and "component" argument')


def _prepare_get_provider_object_func(host: Optional[str] = None) -> ADCMProviderObjectGetter:
    """
    Get function to get one of ADCM provider objects:

    - Provider (host is None)
    - Host (host FQDN is provided)

    All objects comes from "first" provider
    """
    provider_name = "first"
    if host is None:
        return lambda client: client.provider(name=provider_name)
    return lambda client: client.provider(name=provider_name).host(fqdn=host)


def generate_cluster_success_params() -> List[ParameterSet]:
    """
    Generate successful multi_state_set params for cluster objects:

    - Action name (as string)
    - Object that is going to change multi state
    - Object that is going to run action
    """
    get_cluster = _prepare_get_cluster_object_func()

    get_first_service = _prepare_get_cluster_object_func('first')
    get_first_component = _prepare_get_cluster_object_func('first', 'first')
    get_second_component = _prepare_get_cluster_object_func('first', 'second')

    get_second_service = _prepare_get_cluster_object_func('second')
    get_second_service_first_component = _prepare_get_cluster_object_func('second', 'first')
    return [
        *[
            pytest.param('set_cluster', get_cluster, from_obj_func, id=f'cluster_from_{from_obj_id}')
            for from_obj_func, from_obj_id in (
                (get_cluster, 'self'),
                (get_first_service, 'service'),
                (get_first_component, 'component'),
            )
        ],
        *[
            pytest.param('set_service', get_first_service, from_obj_func, id=f'service_from_{from_obj_id}')
            for from_obj_func, from_obj_id in ((get_first_service, 'self'), (get_first_component, 'component'))
        ],
        pytest.param('set_component', get_first_component, get_first_component, id='component_from_self'),
        *[
            pytest.param('set_first_service', get_first_service, from_obj_func, id=f'service_from_{from_obj_id}')
            for from_obj_func, from_obj_id in (
                (get_first_service, 'self_by_name'),
                (get_cluster, 'cluster'),
                (get_second_service, 'another_service'),
                (get_second_service_first_component, 'another_service_component'),
            )
        ],
        *[
            pytest.param('set_first_component', get_first_component, from_obj_func, id=f'component_from_{from_obj_id}')
            for from_obj_func, from_obj_id in (
                (get_first_component, 'self_by_name'),
                (get_first_service, 'service'),
                (get_second_component, 'another_component'),
            )
        ],
        *[
            pytest.param(
                'set_first_service_first_component',
                get_first_component,
                from_obj_func,
                id=f'component_from_{from_obj_id}',
            )
            for from_obj_func, from_obj_id in (
                (get_first_component, 'self_by_service_component_name'),
                (get_cluster, 'cluster'),
                (get_second_service, 'another_service'),
                (get_second_service_first_component, 'component_from_another_service'),
            )
        ],
    ]


def generate_provider_success_params() -> List[ParameterSet]:
    """
    Generate successful multi_state_set params for provider objects:

    - Action name (as string)
    - Object that is going to change multi state
    - Object that is going to run action
    """
    get_provider = _prepare_get_provider_object_func()
    get_host = _prepare_get_provider_object_func('first-first')

    return [
        pytest.param('set_provider', get_provider, get_provider, id='provider_from_self'),
        pytest.param('set_provider', get_provider, get_host, id='provider_from_host'),
        pytest.param('set_host', get_host, get_host, id='host_from_self'),
    ]


# !===== Tests =====!


@pytest.mark.parametrize(
    ('action_name', 'get_object_to_be_changed', 'get_action_owner_object'), generate_cluster_success_params()
)
@pytest.mark.usefixtures("two_clusters")
def test_cluster_successful_multi_state_set(
    action_name: str,
    get_object_to_be_changed: ADCMClusterObjectGetter,
    get_action_owner_object: ADCMClusterObjectGetter,
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct multi_state_set calls can run successfully
        with Cluster, Service, Component
        and change only the objects that must be changed
    """
    _test_successful_multi_state_set(
        action_name, get_object_to_be_changed, get_action_owner_object, sdk_client_fs, check_clusters_multi_state
    )


@pytest.mark.parametrize(
    ('action_name', 'get_object_to_be_changed', 'get_action_owner_object'), generate_provider_success_params()
)
@pytest.mark.usefixtures("two_providers")
def test_provider_successful_multi_state_set(
    action_name: str,
    get_object_to_be_changed: ADCMProviderObjectGetter,
    get_action_owner_object: ADCMProviderObjectGetter,
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct multi_state_set calls can run successfully
        with Provider and Host
        and change only the objects that must be changed
    """
    _test_successful_multi_state_set(
        action_name, get_object_to_be_changed, get_action_owner_object, sdk_client_fs, check_providers_multi_state
    )


@pytest.mark.parametrize("two_clusters", ["cluster_double_call"], indirect=True)
def test_double_call_to_multi_state_set(two_clusters: Tuple[Cluster, Cluster], sdk_client_fs: ADCMClient):
    """Test that double call to plugin from two files doesn't fail"""
    cluster = two_clusters[0]
    run_cluster_action_and_assert_result(cluster, 'double_call_two_playbooks')
    with allure.step(f'Check only state of Cluster "{cluster.name}" was changed'):
        check_clusters_multi_state(
            sdk_client_fs, {cluster}, changed_multi_state={'much', 'better', 'actually', 'the best'}
        )


@pytest.mark.usefixtures('two_clusters', 'two_providers')
def test_forbidden_multi_state_set_actions(sdk_client_fs: ADCMClient):
    """
    Check that forbidden caller-context combinations fail as actions
        and don't affect any ADCM objects
    """
    name = "first"
    with allure.step('Check forbidden from cluster "{name}" context actions'):
        cluster = sdk_client_fs.cluster(name=name)
        for forbidden_action in ('set_service', 'set_component'):
            run_cluster_action_and_assert_result(cluster, forbidden_action, status='failed')
            check_clusters_multi_state(sdk_client_fs)
    with allure.step('Check forbidden from service "{name}" context actions'):
        service = cluster.service(name=name)
        for forbidden_action in ('set_component',):
            run_service_action_and_assert_result(service, forbidden_action, status='failed')
            check_clusters_multi_state(sdk_client_fs)
    with allure.step(f'Check forbidden from provider "{name}" context actions'):
        provider = sdk_client_fs.provider(name=name)
        for forbidden_action in ('set_host',):
            run_provider_action_and_assert_result(provider, forbidden_action, status='failed')
            check_providers_multi_state(sdk_client_fs)


# pylint: disable-next=possibly-unused-variable
def test_multi_state_from_host_actions(
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
            check_clusters_multi_state(sdk_client_fs, affected_objects)


def _test_successful_multi_state_set(
    action_name: str,
    get_object_to_be_changed: Union[ADCMClusterObjectGetter, ADCMProviderObjectGetter],
    get_action_owner_object: Union[ADCMClusterObjectGetter, ADCMProviderObjectGetter],
    sdk_client_fs: ADCMClient,
    check_multi_state_func: Callable,
):
    """Test successful multi state set"""
    object_to_be_changed = get_object_to_be_changed(sdk_client_fs)
    changed_object_type = object_to_be_changed.__class__.__name__
    changed_object_name = (
        object_to_be_changed.name if not isinstance(object_to_be_changed, Host) else object_to_be_changed.fqdn
    )
    action_owner_object = get_action_owner_object(sdk_client_fs)
    action_owner_type = action_owner_object.__class__.__name__
    action_owner_name = (
        action_owner_object.name if not isinstance(action_owner_object, Host) else action_owner_object.fqdn
    )
    with allure.step(
        f'Change multi state of {changed_object_type} "{changed_object_name}" with action '
        f'from {action_owner_type} "{action_owner_name}"'
    ):
        task = action_owner_object.action(name=action_name).run()
        with catch_failed(
            TaskFailed,
            f'Action {action_name} should have succeeded when ran on {action_owner_type} "{action_owner_name}"',
        ):
            task.try_wait()
    with allure.step(f'Check only state of {changed_object_type} "{changed_object_name}" was changed'):
        check_multi_state_func(sdk_client_fs, {object_to_be_changed})


# !===== Steps and Helpers =====!


@allure.step('Check that multi_state_set affected correct ADCM objects')
def check_clusters_multi_state(
    adcm_client: ADCMClient,
    changed_adcm_objects: Collection[Union[Cluster, Service, Component]] = (),
    changed_multi_state: Optional[Set[str]] = None,
    unchanged_multi_state: Optional[Set[str]] = None,
):
    """
    Check that multi state changed correctly in objects that were plugin's targets
    and those that weren't targets has *default* multi state
    """
    changed_multi_state = changed_multi_state or {'ifeelgood!'}
    for adcm_object in changed_adcm_objects:
        _compare_multi_states(adcm_object, changed_multi_state)

    unchanged_multi_state = unchanged_multi_state or set()
    cluster_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Cluster)}
    service_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Service)}
    component_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Component)}
    for cluster in adcm_client.cluster_list():
        if cluster.id not in cluster_ids:
            _compare_multi_states(cluster, unchanged_multi_state)
        for service in cluster.service_list():
            if service.id not in service_ids:
                _compare_multi_states(service, unchanged_multi_state)
            for component in service.component_list():
                if component.id not in component_ids:
                    _compare_multi_states(component, unchanged_multi_state)


@allure.step('Check that multi_state_set affected correct ADCM objects')
def check_providers_multi_state(
    adcm_client: ADCMClient,
    changed_adcm_objects: Collection[Union[Provider, Host]] = (),
    changed_multi_state: Optional[Set[str]] = None,
    unchanged_multi_state: Optional[Set[str]] = None,
):
    changed_multi_state = changed_multi_state or {'ifeelgood!'}
    for adcm_object in changed_adcm_objects:
        _compare_multi_states(adcm_object, changed_multi_state)

    unchanged_multi_state = unchanged_multi_state or set()
    provider_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Provider)}
    host_ids = {obj.id for obj in changed_adcm_objects if isinstance(obj, Host)}
    for provider in adcm_client.provider_list():
        if provider.id not in provider_ids:
            _compare_multi_states(provider, unchanged_multi_state)
        for host in provider.host_list():
            if host.id not in host_ids:
                _compare_multi_states(host, unchanged_multi_state)


def _compare_multi_states(
    adcm_object: Union[Cluster, Service, Component, Provider, Host], expected_multi_state: Set[str]
):
    """Compare multi state of ADCM object with expected one"""
    adcm_object_name = adcm_object.name if not isinstance(adcm_object, Host) else adcm_object.fqdn
    adcm_object_type = adcm_object.__class__.__name__
    adcm_object.reread()
    assert (multi_state := set(adcm_object.multi_state)) == expected_multi_state, (
        f'Multi state of {adcm_object_type} "{adcm_object_name}" '
        f'should be {expected_multi_state}, not {multi_state}'
    )
