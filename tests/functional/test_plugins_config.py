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

"""Tests for adcm_config plugin"""

from typing import Callable, Tuple

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
from tests.functional.tools import AnyADCMObject, get_config

# pylint:disable=redefined-outer-name

INITIAL_CONFIG = {
    "int": 1,
    "float": 1.0,
    "text": "xxx\nxxx\n",
    "file": "yyyy\nyyyy\n",
    "string": "zzz",
    "json": [{"x": "y"}, {"y": "z"}],
    'dummy': 'donthurtme',
    "map": {"one": "two", "two": "three"},
    "list": ["one", "two", "three"],
}
CHANGED_CONFIG = {
    "int": 2,
    "float": 4.0,
    "text": "new new\nxxx\n",
    "file": "new new new\nyyyy\n",
    "string": "double new",
    "json": [{"x": "new"}, {"y": "z"}],
    'dummy': 'donthurtme',
    "map": {"one": "two", "two": "new"},
    "list": ["one", "new", "three"],
}
CONFIG_KEYS = set(CHANGED_CONFIG.keys())


check_config_changed = build_objects_checker(
    field_name='Config',
    changed=CHANGED_CONFIG,
    extractor=get_config,
)


@pytest.fixture()
def two_clusters(request, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Cluster]:
    """Get two clusters with both services"""
    bundle_dir = "cluster" if not hasattr(request, 'param') else request.param
    return create_two_clusters(sdk_client_fs, __file__, bundle_dir)


@pytest.fixture()
def two_providers(sdk_client_fs: ADCMClient) -> Tuple[Provider, Provider]:
    """Get two providers with two hosts"""
    return create_two_providers(sdk_client_fs, __file__, "provider")


@pytest.mark.parametrize(
    ('change_action_name', 'object_to_be_changed', 'action_owner'),
    generate_cluster_success_params(action_prefix='change', id_template='change_{}_config'),
)
@pytest.mark.usefixtures("two_clusters")
def test_cluster_related_objects(
    change_action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct adcm_config calls can run successfully
        with Cluster, Service, Component
        and change only the objects that must be changed
    """
    _test_successful_config_change(
        change_action_name,
        object_to_be_changed,
        action_owner,
        sdk_client_fs,
        get_cluster_related_object,
    )


@pytest.mark.parametrize(
    ('change_action_name', 'object_to_be_changed', 'action_owner'),
    generate_provider_success_params(action_prefix='change', id_template='change_{}_config'),
)
@pytest.mark.usefixtures("two_providers")
def test_provider_related_objects(
    change_action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
):
    """
    Check that correct adcm_config calls can run successfully
        with Provider and Host
        and change only the objects that must be changed
    """
    _test_successful_config_change(
        change_action_name,
        object_to_be_changed,
        action_owner,
        sdk_client_fs,
        get_provider_related_object,
    )


def test_host_from_provider(two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient):
    """Change host config from provider"""
    provider = two_providers[0]
    host = provider.host()
    provider_name = compose_name(provider)
    host_name = compose_name(host)
    with check_config_changed(sdk_client_fs, {host}), allure.step(
        f'Set config of {host_name} with action from {provider_name}'
    ):
        run_provider_action_and_assert_result(provider, 'change_host_from_provider', config={'host_id': host.id})


def test_multijob(
    two_clusters: Tuple[Cluster, Cluster], two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient
):
    """Check that multijob actions change config or object itself"""
    component = (service := (cluster := two_clusters[0]).service()).component()
    host = (provider := two_providers[0]).host()
    affected_objects = set()
    for obj in (cluster, service, component, provider, host):
        classname = obj.__class__.__name__.lower()
        affected_objects.add(obj)
        object_name = compose_name(obj)
        with check_config_changed(sdk_client_fs, affected_objects), allure.step(
            f'Change {object_name} state with multijob action'
        ):
            run_successful_task(obj.action(name=f'change_{classname}_multijob'), object_name)


@pytest.mark.usefixtures('two_clusters', 'two_providers')
def test_forbidden_actions(sdk_client_fs: ADCMClient):
    """
    Check that forbidden caller-context combinations fail as actions
        and don't affect any ADCM objects
    """
    name = "first"
    with allure.step(f'Check forbidden from cluster "{name}" context actions'):
        cluster = sdk_client_fs.cluster(name=name)
        for forbidden_action in ('change_service', 'change_component'):
            with check_config_changed(sdk_client_fs):
                run_cluster_action_and_assert_result(cluster, forbidden_action, status='failed')
    with allure.step(f'Check forbidden from service "{name}" context actions'):
        service = cluster.service(name=name)
        with check_config_changed(sdk_client_fs):
            run_service_action_and_assert_result(service, 'change_component', status='failed')
    with allure.step(f'Check forbidden from provider "{name}" context actions'):
        provider = sdk_client_fs.provider(name=name)
        with check_config_changed(sdk_client_fs):
            run_provider_action_and_assert_result(provider, 'change_host', status='failed')
        first_host, second_host, *_ = provider.host_list()
        with check_config_changed(sdk_client_fs):
            run_host_action_and_assert_result(
                first_host, 'change_host_from_provider', status='failed', config={'host_id': second_host.id}
            )


def test_from_host_actions(
    two_clusters: Tuple[Cluster, Cluster], two_providers: Tuple[Provider, Provider], sdk_client_fs: ADCMClient
):
    """Test that host actions actually change config"""
    name = "first"
    affected_objects = set()
    check_config_changed_local = build_objects_checker(
        extractor=get_config, changed={**INITIAL_CONFIG, 'int': CHANGED_CONFIG['int']}, field_name='Config'
    )
    with allure.step('Bind component to host'):
        component = (service := (cluster := two_clusters[0]).service(name=name)).component(name=name)
        host = two_providers[0].host_list()[0]
        cluster.host_add(host)
        cluster.hostcomponent_set((host, component))
    for obj in (cluster, service, component):
        affected_objects.add(obj)
        classname = obj.__class__.__name__.lower()
        with check_config_changed_local(sdk_client_fs, affected_objects), allure.step(
            f'Check change {compose_name(obj)} config from host action'
        ):
            run_host_action_and_assert_result(host, f'change_{classname}_host')


class TestImmediateConfigChange(TestImmediateChange):
    """Test that config changed immediately"""

    _file = __file__

    @allure.issue(url='https://arenadata.atlassian.net/browse/ADCM-2116')
    def test_immediate_config_change(
        self,
        provider_host: Tuple[Provider, Host],
        cluster_service_component: Tuple[Cluster, Service, Component],
    ):
        """Test that config is changed right after adcm_config step in multijob action"""
        self.run_immediate_change_test(provider_host, cluster_service_component)


def _test_successful_config_change(
    action_name: str,
    object_to_be_changed: Tuple[str, ...],
    action_owner: Tuple[str, ...],
    sdk_client_fs: ADCMClient,
    get_object_func: Callable[..., AnyADCMObject],
):
    """Test successful change of config of one object"""
    object_to_be_changed = get_object_func(sdk_client_fs, *object_to_be_changed)
    changed_object_name = compose_name(object_to_be_changed)
    action_owner_object = get_object_func(sdk_client_fs, *action_owner)
    action_owner_name = compose_name(action_owner_object)
    with check_config_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
        f'Change config of {changed_object_name} with action from {action_owner_name}'
    ):
        run_successful_task(action_owner_object.action(name=action_name), action_owner_name)
