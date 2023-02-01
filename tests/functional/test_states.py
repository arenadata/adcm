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

"""Tests for ADCM objects states and related stuff"""

# todo add new DSL variant for job and multijob

# pylint:disable=redefined-outer-name
from typing import Callable, Tuple

import allure
from adcm_client.objects import ADCMClient, Cluster, Provider
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_host_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import fixture_parametrized_by_data_subdirs
from tests.functional.plugin_utils import build_objects_checker

ACTION_NAME = 'state_changing_action'
ACTION_SET_MULTISTATE_NAME = "set_multistate"


@fixture_parametrized_by_data_subdirs(__file__, 'cluster_and_service')
def cluster_and_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Cluster, Callable]:
    """Create cluster and states checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    name = bundle.name.replace('_', ' ')
    cluster = bundle.cluster_create(name=name)
    bundle.cluster_create(name=f"{name} second")
    check_objects_state_changed = build_objects_checker(
        field_name='State',
        changed=cluster.name.replace(' ', '_'),
        extractor=lambda obj: obj.state,
    )
    return cluster, check_objects_state_changed


@fixture_parametrized_by_data_subdirs(__file__, 'cluster_and_service_multistate')
def cluster_and_multi_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Cluster, Callable]:
    """Create cluster and multi states checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    name = bundle.name.replace('_', ' ')
    cluster = bundle.cluster_create(name=name)
    bundle.cluster_create(name=f"{name} second")
    check_objects_state_changed = build_objects_checker(
        field_name='Multi state',
        # as set in actions
        changed=[cluster.name.replace(' ', '_')],
        extractor=lambda obj: sorted(obj.multi_state),
    )
    return cluster, check_objects_state_changed


@fixture_parametrized_by_data_subdirs(__file__, 'cluster_and_service_state_and_multistate')
def cluster_and_multi_states_plus_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Cluster, Callable]:
    """Create cluster and multi states + states checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    name = bundle.name.replace('_', ' ')
    cluster = bundle.cluster_create(name=name)
    bundle.cluster_create(name=f"{name} second")
    expected = cluster.name.replace(' ', '_')
    check_objects_state_changed = build_objects_checker(
        field_name='Multi states and states',
        changed=dict(state=expected, multi_states=[expected]),
        extractor=lambda obj: dict(state=obj.state, multi_states=sorted(obj.multi_state)),
    )
    return cluster, check_objects_state_changed


class TestClusterRelatedObjects:
    """Tests for cluster-related objects states"""

    def test_cluster_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_states_checker):
        """Test cluster state after action"""
        cluster_obj, check_objects_state_changed = cluster_and_states_checker
        object_to_be_changed = cluster_obj
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run cluster action: {ACTION_NAME}'
        ):
            run_cluster_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_service_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_states_checker):
        """Test service state after action"""
        cluster_obj, check_objects_state_changed = cluster_and_states_checker
        object_to_be_changed = cluster_obj.service_add(name='first_srv')
        cluster_obj.service_add(name='second_srv')
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run service action: {ACTION_NAME}'
        ):
            run_service_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_component_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_states_checker):
        """Test component state after action"""
        cluster_obj, check_objects_state_changed = cluster_and_states_checker
        cluster_obj.service_add(name='first_srv')
        object_to_be_changed = cluster_obj.service(name='first_srv').component(name='first_cmp')
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run component action: {ACTION_NAME}'
        ):
            run_component_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_cluster_multi_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_multi_states_checker):
        """
        Test cluster and multi states after action
        Before action add multi state that should be unset via action
        """
        object_to_be_changed, check_objects_multi_state_changed = cluster_and_multi_states_checker
        run_cluster_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_multi_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run cluster action: {ACTION_NAME}'
        ):
            run_cluster_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in object_to_be_changed.name else "failed",
            )

    def test_service_multi_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_multi_states_checker):
        """
        Test service and multi states after action
        Before action add multi state that should be unset via action
        """
        cluster_obj, check_objects_multi_state_changed = cluster_and_multi_states_checker
        object_to_be_changed = cluster_obj.service_add(name='first_srv')
        cluster_obj.service_add(name='second_srv')
        run_service_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_multi_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run service action: {ACTION_NAME}'
        ):
            run_service_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_component_multi_state_after_action(self, sdk_client_fs: ADCMClient, cluster_and_multi_states_checker):
        """
        Test components and multi states after action
        Before action add multi state that should be unset via action
        """
        cluster_obj, check_objects_state_changed = cluster_and_multi_states_checker
        cluster_obj.service_add(name='first_srv')
        object_to_be_changed = cluster_obj.service(name='first_srv').component(name='first_cmp')
        run_component_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run component action: {ACTION_NAME}'
        ):
            run_component_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_cluster_multi_state_plus_states_after_action(
        self, sdk_client_fs: ADCMClient, cluster_and_multi_states_plus_states_checker
    ):
        """
        Test cluster and multi states and states after action
        Before action add multi state that should be unset via action
        """

        object_to_be_changed, check_objects_multi_state_changed = cluster_and_multi_states_plus_states_checker
        run_cluster_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_multi_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run cluster action: {ACTION_NAME}'
        ):
            run_cluster_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in object_to_be_changed.name else "failed",
            )

    def test_service_multi_state_plus_state_after_action(
        self, sdk_client_fs: ADCMClient, cluster_and_multi_states_plus_states_checker
    ):
        """
        Test service and multi states and states after action
        Before action add multi state that should be unset via action
        """
        cluster_obj, check_objects_multi_state_changed = cluster_and_multi_states_plus_states_checker
        object_to_be_changed = cluster_obj.service_add(name='first_srv')
        cluster_obj.service_add(name='second_srv')
        run_service_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_multi_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run service action: {ACTION_NAME}'
        ):
            run_service_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )

    def test_component_multi_state_plus_state_after_action(
        self, sdk_client_fs: ADCMClient, cluster_and_multi_states_plus_states_checker
    ):
        """
        Test components and multi states and states after action
        Before action add multi state that should be unset via action
        """
        cluster_obj, check_objects_state_changed = cluster_and_multi_states_plus_states_checker
        cluster_obj.service_add(name='first_srv')
        object_to_be_changed = cluster_obj.service(name='first_srv').component(name='first_cmp')
        run_component_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run component action: {ACTION_NAME}'
        ):
            run_component_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in cluster_obj.name else "failed",
            )


@fixture_parametrized_by_data_subdirs(__file__, 'provider_and_host')
def provider_and_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Provider, Callable]:
    """Create provider and states checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    cleaned_name = bundle.name.replace("_", "-")
    provider = bundle.provider_create(name=cleaned_name)
    bundle.provider_create(name=f"{cleaned_name}-second")
    provider.host_create(fqdn=cleaned_name)
    provider.host_create(fqdn=f"{cleaned_name}-second")
    check_objects_state_changed = build_objects_checker(
        field_name='State',
        changed=bundle.name,
        extractor=lambda obj: obj.state,
    )
    return provider, check_objects_state_changed


@fixture_parametrized_by_data_subdirs(__file__, 'provider_and_host_state_and_multistate')
def provider_and_multi_states_plus_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Provider, Callable]:
    """Create provider and multi state plus state checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    cleaned_name = bundle.name.replace("_", "-")
    provider = bundle.provider_create(name=cleaned_name)
    bundle.provider_create(name=f"{cleaned_name}-second".replace("_", "-"))
    provider.host_create(fqdn=cleaned_name)
    provider.host_create(fqdn=f"{cleaned_name}-second".replace("_", "-"))
    check_objects_state_changed = build_objects_checker(
        field_name='Multi states and states',
        changed=dict(state=bundle.name, multi_states=[bundle.name]),
        extractor=lambda obj: dict(state=obj.state, multi_states=sorted(obj.multi_state)),
    )
    return provider, check_objects_state_changed


@fixture_parametrized_by_data_subdirs(__file__, 'provider_and_host_multistate')
def provider_and_multi_states_checker(sdk_client_fs: ADCMClient, request) -> Tuple[Provider, Callable]:
    """Create provider and multi state checker"""
    bundle = sdk_client_fs.upload_from_fs(request.param)
    clean_name = bundle.name.replace("_", "-")
    provider = bundle.provider_create(name=clean_name)
    bundle.provider_create(name=f"{clean_name}-second")
    provider.host_create(fqdn=clean_name)
    provider.host_create(fqdn=f"{clean_name}-second")
    check_objects_state_changed = build_objects_checker(
        field_name='Multi state',
        changed=[bundle.name],
        extractor=lambda obj: sorted(obj.multi_state),
    )
    return provider, check_objects_state_changed


class TestProviderRelatedObjects:
    """Tests for provider-related objects states"""

    def test_provider_state_after_action(self, sdk_client_fs: ADCMClient, provider_and_states_checker):
        """Test provider state after action"""
        provider_obj, check_objects_state_changed = provider_and_states_checker
        object_to_be_changed = provider_obj
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run provider action: {ACTION_NAME}'
        ):
            run_provider_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )

    def test_host_state_after_action(self, sdk_client_fs: ADCMClient, provider_and_states_checker):
        """Test host state after action"""
        provider_obj, check_objects_state_changed = provider_and_states_checker
        object_to_be_changed = provider_obj.host(fqdn=provider_obj.name)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run host action: {ACTION_NAME}'
        ):
            run_host_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )

    def test_provider_multi_state_after_action(self, sdk_client_fs: ADCMClient, provider_and_multi_states_checker):
        """
        Test provider and multi states after action
        Before action add multi state that should be unset via action
        """
        provider_obj, check_objects_state_changed = provider_and_multi_states_checker
        object_to_be_changed = provider_obj
        run_provider_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run provider action: {ACTION_NAME}'
        ):
            run_provider_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )

    def test_host_multi_state_after_action(self, sdk_client_fs: ADCMClient, provider_and_multi_states_checker):
        """
        Test host and multi states after action
        Before action add multi state that should be unset via action
        """
        provider_obj, check_objects_state_changed = provider_and_multi_states_checker
        object_to_be_changed = provider_obj.host(fqdn=provider_obj.name)
        run_host_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run host action: {ACTION_NAME}'
        ):
            run_host_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )

    def test_provider_multi_state_plus_state_after_action(
        self, sdk_client_fs: ADCMClient, provider_and_multi_states_plus_states_checker
    ):
        """
        Test provider and multi states and states after action
        Before action add multi state that should be unset via action
        """
        provider_obj, check_objects_state_changed = provider_and_multi_states_plus_states_checker
        object_to_be_changed = provider_obj
        run_provider_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run provider action: {ACTION_NAME}'
        ):
            run_provider_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )

    def test_host_multi_state_plus_state_after_action(
        self, sdk_client_fs: ADCMClient, provider_and_multi_states_plus_states_checker
    ):
        """
        Test host and multi states and states after action
        Before action add multi state that should be unset via action
        """
        provider_obj, check_objects_state_changed = provider_and_multi_states_plus_states_checker
        object_to_be_changed = provider_obj.host(fqdn=provider_obj.name)
        run_host_action_and_assert_result(object_to_be_changed, ACTION_SET_MULTISTATE_NAME)
        with check_objects_state_changed(sdk_client_fs, {object_to_be_changed}), allure.step(
            f'Run host action: {ACTION_NAME}'
        ):
            run_host_action_and_assert_result(
                object_to_be_changed,
                action=ACTION_NAME,
                status="success" if "fail" not in provider_obj.name else "failed",
            )
