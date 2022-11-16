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
# pylint: disable=redefined-outer-name, unused-argument, dangerous-default-value

"""Tests for config groups"""
import json
from collections import OrderedDict
from typing import Tuple, Type, Union

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    GroupConfig,
    Host,
    HostList,
    Provider,
    Service,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
    run_provider_action_and_assert_result,
    run_service_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage
from docker.models.containers import Container
from tests.library.errorcodes import (
    ATTRIBUTE_ERROR,
    GROUP_CONFIG_CHANGE_UNSELECTED_FIELD,
    GROUP_CONFIG_HOST_ERROR,
    GROUP_CONFIG_HOST_EXISTS,
    ADCMError,
)

CLUSTER_BUNDLE_PATH = get_data_dir(__file__, "cluster_simple")
CLUSTER_BUNDLE_WITH_GROUP_PATH = get_data_dir(__file__, "cluster_with_group_all_params")
CLUSTER_BUNDLE_WITH_CONFIG_GROUP_CUSTOM_PATH = get_data_dir(__file__, "cluster_with_config_group_custom")
PROVIDER_BUNDLE_PATH = get_data_dir(__file__, "hostprovider_bundle")
PROVIDER_BUNDLE_WITH_GROUP_PATH = get_data_dir(__file__, "provider_group_with_all_params")
PROVIDER_BUNDLE_WITH_CONFIG_GROUP_CUSTOM_PATH = get_data_dir(__file__, "provider_group_with_config_group_custom")
HOST_ERROR_MESSAGE = (
    "host is not available for this object, or host already is a member of another group of this object"
)
HOST_EXISTS_MESSAGE = "the host is already a member of this group"
ATTRIBUTE_ERROR_MESSAGE = "field cannot be changed, read-only"
GROUP_ERROR_MESSAGE = "field cannot be included in the group"
GROUP_CONFIG_CHANGE_UNSELECTED_ERROR_MESSAGE = "field is different in current and new config"
FIRST_COMPONENT_NAME = "first"
SECOND_COMPONENT_NAME = "second"
FIRST_GROUP = "test_group"
SECOND_GROUP = "test_group_2"
FIRST_HOST = "test-host-1"
SECOND_HOST = "test-host-2"
ACTION_NAME = "test_action"
ACTION_MULTIJOB_NAME = "test_action_multijob"


@pytest.fixture()
def provider_bundle(request, sdk_client_fs: ADCMClient):
    """Upload provider bundle"""
    bundle_path = request.param if hasattr(request, "param") else PROVIDER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster_bundle(request, sdk_client_fs: ADCMClient):
    """Upload cluster bundle"""
    bundle_path = request.param if hasattr(request, "param") else CLUSTER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster(cluster_bundle) -> Cluster:
    """Create cluster"""
    return cluster_bundle.cluster_create(name=utils.random_string())


@pytest.fixture()
def provider(provider_bundle) -> Provider:
    """Create provider"""
    return provider_bundle.provider_create(name=utils.random_string())


@pytest.fixture()
def create_two_hosts(provider) -> Tuple[Host, Host]:
    """Create two hosts"""
    with allure.step("Create host for config groups"):
        test_host_1 = provider.host_create(fqdn=FIRST_HOST)
    with allure.step("Create host for host candidate check"):
        test_host_2 = provider.host_create(fqdn=SECOND_HOST)
    return test_host_1, test_host_2


@pytest.fixture()
def cluster_with_two_hosts_on_it(create_two_hosts, cluster: Cluster, provider: Provider) -> Tuple[Host, Host, Cluster]:
    """Add service, two hosts and create components to check intersection in config groups"""
    test_host_1, test_host_2 = create_two_hosts
    cluster.host_add(test_host_1)
    cluster.host_add(test_host_2)
    return test_host_1, test_host_2, cluster


@pytest.fixture()
def cluster_with_components(cluster_with_two_hosts_on_it) -> Tuple[Service, Host, Host]:
    """Add service, two hosts and create components to check intersection in config groups"""
    test_host_1, test_host_2, cluster = cluster_with_two_hosts_on_it
    service = cluster.service_add(name='test_service_1')
    cluster.hostcomponent_set(
        (test_host_1, service.component(name=FIRST_COMPONENT_NAME)),
        (test_host_2, service.component(name=FIRST_COMPONENT_NAME)),
        (test_host_2, service.component(name=SECOND_COMPONENT_NAME)),
    )
    return service, test_host_1, test_host_2


@pytest.fixture()
def cluster_with_components_on_first_host(
    create_two_hosts, cluster: Cluster, provider: Provider
) -> Tuple[Service, Host, Host]:
    """Add service, two hosts and create components to check config groups"""
    service = cluster.service_add(name='test_service_1')
    test_host_1, test_host_2 = create_two_hosts
    cluster.host_add(test_host_1)
    cluster.hostcomponent_set(
        (test_host_1, service.component(name=FIRST_COMPONENT_NAME)),
        (test_host_1, service.component(name=SECOND_COMPONENT_NAME)),
    )
    return service, test_host_1, test_host_2


@allure.step('Check error')
def _assert_that_host_add_is_unavailable(service_group: GroupConfig, host: Host):
    with allure.step(f'Check that error is "{GROUP_CONFIG_HOST_ERROR.code}"'):
        with pytest.raises(ErrorMessage) as e:
            service_group.host_add(host)
        GROUP_CONFIG_HOST_ERROR.equal(e)
    with allure.step(f'Check error message is "{HOST_ERROR_MESSAGE}"'):
        assert HOST_ERROR_MESSAGE in e.value.error['desc'], f"Should be error message '{HOST_ERROR_MESSAGE}'"


@allure.step('Check that host exists')
def _assert_that_host_exists(group: GroupConfig, host: Host):
    with allure.step(f'Check that error is "{GROUP_CONFIG_HOST_EXISTS.code}"'):
        with pytest.raises(ErrorMessage) as e:
            group.host_add(host)
        GROUP_CONFIG_HOST_EXISTS.equal(e)
    with allure.step(f'Check error message is "{HOST_EXISTS_MESSAGE}"'):
        assert HOST_EXISTS_MESSAGE in e.value.error['desc'], f"Should be error message '{HOST_EXISTS_MESSAGE}'"


@allure.step('Check that host is in the group')
def _assert_host_is_in_group(group: GroupConfig, host: Host):
    assert host.fqdn in [h.fqdn for h in group.hosts().data], f'Host "{host.fqdn}" should be in group "{group.name}"'


@allure.step('Check that host is not in group')
def _assert_host_is_not_in_group(group: GroupConfig, host: Host):
    assert host.fqdn not in (
        h.fqdn for h in group.hosts().data
    ), f'Host "{host.fqdn}" should be in group "{group.name}"'


@allure.step("Check that the only second host is present in candidates on second group")
def _assert_host_candidate_equal_expected(group: HostList, expected_hosts_names: [str]):
    expected_hosts_amount = len(expected_hosts_names)
    with allure.step(f"Check that {expected_hosts_amount} hosts are available in group"):
        assert len(group) == expected_hosts_amount, f"{expected_hosts_amount} hosts should be available in group"
    with allure.step(f"Check that host '{SECOND_HOST}' is available in group"):
        assert [g.fqdn for g in group] == expected_hosts_names, f"Should be available hosts '{expected_hosts_names}'"


@allure.step("Create config group and add host")
def _create_group_and_add_host(
    object_with_group: Union[Cluster, Service, Component, Provider], host: Host
) -> GroupConfig:
    group = object_with_group.group_config_create(name=FIRST_GROUP)
    group.host_add(host)
    return group


class TestGroupsIntersection:
    """Tests for config groups intersections"""

    def test_that_groups_not_allowed_to_intersect_in_cluster(self, cluster_with_two_hosts_on_it):
        """Test that groups are not allowed to intersect in cluster"""

        test_host_1, _, cluster = cluster_with_two_hosts_on_it
        _create_group_and_add_host(cluster, test_host_1)
        with allure.step("Create the second group for cluster and check that not allowed to add the first host to it"):
            cluster_group_2 = cluster.group_config_create(name=SECOND_GROUP)
            _assert_that_host_add_is_unavailable(cluster_group_2, test_host_1)
            _assert_host_candidate_equal_expected(cluster_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_provider(self, create_two_hosts, provider):
        """Test that groups are not allowed to intersect in provider"""

        test_host_1, _ = create_two_hosts
        _create_group_and_add_host(provider, test_host_1)
        with allure.step("Create the second group for provider and check that not allowed to add the first host to it"):
            provider_group_2 = provider.group_config_create(name=SECOND_GROUP)
            _assert_that_host_add_is_unavailable(provider_group_2, test_host_1)
            _assert_host_candidate_equal_expected(provider_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_service(self, cluster_with_components):
        """Test that groups are not allowed to intersect in service"""

        service, test_host_1, _ = cluster_with_components
        _create_group_and_add_host(service, test_host_1)
        with allure.step("Create the second group for service and check that not allowed to add the first host to it"):
            service_group_2 = service.group_config_create(name=SECOND_GROUP)
            _assert_that_host_add_is_unavailable(service_group_2, test_host_1)
            _assert_host_candidate_equal_expected(service_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_component(self, cluster_with_components):
        """Test that groups are not allowed to intersect"""

        service, test_host_1, _ = cluster_with_components
        _create_group_and_add_host(service.component(name=FIRST_COMPONENT_NAME), test_host_1)
        with allure.step(
            "Create the second group for component and check that not allowed to add the first host to it"
        ):
            component_group_2 = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=SECOND_GROUP)
        _assert_that_host_add_is_unavailable(component_group_2, test_host_1)
        _assert_host_candidate_equal_expected(component_group_2.host_candidate(), [SECOND_HOST])


class TestIncorrectHostInGroups:
    """Test for incorrect hosts in group caused errors like GROUP_CONFIG_HOST_ERROR or GROUP_CONFIG_HOST_EXISTS"""

    def test_add_incorrect_host_to_provider_group(self, provider_bundle, provider):
        """Test exception rise when we try to add incorrect host to provider group"""
        with allure.step("Create host from first provider"):
            correct_host = provider.host_create(fqdn=utils.random_string())
        with allure.step("Create second provider"):
            provider_2 = provider_bundle.provider_create(name="Second test provider")
        with allure.step("Create host from second provider"):
            incorrect_host = provider_2.host_create(fqdn=utils.random_string())
        with allure.step("Create config group for first provider and try to add the first host"):
            provider_group = provider.group_config_create(name=incorrect_host.fqdn)
            _assert_that_host_add_is_unavailable(provider_group, incorrect_host)
            _assert_host_candidate_equal_expected(provider_group.host_candidate(), [correct_host.fqdn])
        with allure.step("Add first host to provider group and check that second add is not available"):
            provider_group.host_add(correct_host)
            _assert_that_host_exists(provider_group, correct_host)
            _assert_host_candidate_equal_expected(provider_group.host_candidate(), [])

    def test_add_incorrect_host_to_service_group(self, cluster_with_components_on_first_host):
        """Test exception rise when we try to add incorrect host to service group"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for service"):
            service_group = service.group_config_create(name=FIRST_GROUP)
        with allure.step("Try to add the second host not from service and check group hosts list"):
            _assert_that_host_add_is_unavailable(service_group, test_host_2)
            _assert_host_candidate_equal_expected(service_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to service group and check that second add is not available"):
            service_group.host_add(test_host_1)
            _assert_that_host_exists(service_group, test_host_1)
            _assert_host_candidate_equal_expected(service_group.host_candidate(), [])

    def test_add_incorrect_host_to_cluster_group(self, cluster_bundle, cluster, create_two_hosts):
        """Test exception rise when we try to add incorrect host to cluster group"""

        test_host_1, test_host_2 = create_two_hosts
        with allure.step("Create second cluster"):
            cluster_2 = cluster_bundle.cluster_create(name=utils.random_string())
        with allure.step("Add hosts to clusters"):
            cluster.host_add(test_host_1)
            cluster_2.host_add(test_host_2)
        with allure.step("Create group for first cluster"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
        with allure.step("Try to add host from second cluster to first cluster group"):
            _assert_that_host_add_is_unavailable(cluster_group, test_host_2)
            _assert_host_candidate_equal_expected(cluster_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to cluster group and check that second add is not available"):
            cluster_group.host_add(test_host_1)
            _assert_that_host_exists(cluster_group, test_host_1)
            _assert_host_candidate_equal_expected(cluster_group.host_candidate(), [])

    def test_add_incorrect_host_to_component_group(self, cluster_with_components_on_first_host):
        """Test exception rise when we try to add incorrect host to component group"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for component"):
            component_group = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=FIRST_GROUP)
        with allure.step("Try to add host not from cluster to component group"):
            _assert_that_host_add_is_unavailable(component_group, test_host_2)
            _assert_host_candidate_equal_expected(component_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to component group and check that second add is not available"):
            component_group.host_add(test_host_1)
            _assert_that_host_exists(component_group, test_host_1)
            _assert_host_candidate_equal_expected(component_group.host_candidate(), [])


class TestDeleteHostInGroups:
    """Test deleting host related to conf group"""

    @allure.step("Check that there are no hosts in conf group")
    def _check_no_hosts_in_group(self, group: GroupConfig):
        assert len(group.hosts()) == 0, "Should not be any hosts in conf group"

    def test_delete_host_from_group_after_deleting_in_cluster(self, cluster, provider):
        """Test that host removed from conf group after removing from cluster"""

        test_host = provider.host_create(fqdn=FIRST_HOST)
        cluster.host_add(test_host)
        with allure.step("Create config group for cluster and add the host"):
            cluster_group = _create_group_and_add_host(cluster, test_host)
            _assert_host_is_in_group(cluster_group, test_host)
        cluster.host_delete(test_host)
        self._check_no_hosts_in_group(cluster_group)
        with allure.step("Check that there are no hosts available to add in cluster group"):
            _assert_host_candidate_equal_expected(cluster_group.host_candidate(), [])

    def test_delete_host_from_group_after_deleting_in_service(self, cluster, cluster_with_components_on_first_host):
        """Test that host removed from conf group after removing from service"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for service and add the host"):
            service_group = _create_group_and_add_host(service, test_host_1)
            _assert_host_is_in_group(service_group, test_host_1)
        with allure.step("Change host in service"):
            cluster.host_add(test_host_2)
            cluster.hostcomponent_set(
                (test_host_2, service.component(name=FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=SECOND_COMPONENT_NAME)),
            )
        self._check_no_hosts_in_group(service_group)

    def test_delete_host_from_group_after_delete_in_component(self, cluster, cluster_with_components_on_first_host):
        """Test that host removed from conf group after removing from component"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create config group for component and add the first host"):
            component_group = _create_group_and_add_host(service.component(name=FIRST_COMPONENT_NAME), test_host_1)
            _assert_host_is_in_group(component_group, test_host_1)
        with allure.step("Change host in component"):
            cluster.host_add(test_host_2)
            cluster.hostcomponent_set(
                (test_host_2, service.component(name=FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=SECOND_COMPONENT_NAME)),
            )
        self._check_no_hosts_in_group(component_group)

    def test_delete_host_from_group_after_it_deleted(self, provider):
        """Test that host removed from provider conf group after deleting"""

        with allure.step("Create config group for provider and add host"):
            test_host = provider.host_create(fqdn=FIRST_HOST)
            provider_group = _create_group_and_add_host(provider, test_host)
        _assert_host_is_in_group(provider_group, test_host)
        with allure.step("Delete host"):
            test_host.delete()
        self._check_no_hosts_in_group(provider_group)

    @allure.link(url="https://arenadata.atlassian.net/browse/ADCM-2176")
    def test_host_in_service_group_after_hc_change(
        self, cluster_with_components_on_first_host: Tuple[Service, Host, Host]
    ):
        """
        Check that host stays in cluster and service config groups
            after components were moved to another host
            during hostcomponent map change
        """
        service, first_host, second_host = cluster_with_components_on_first_host
        cluster = service.cluster()
        cluster.host_add(second_host)
        first_component = service.component(name=FIRST_COMPONENT_NAME)
        second_component = service.component(name=SECOND_COMPONENT_NAME)
        cluster.hostcomponent_set((first_host, first_component), (first_host, second_component))
        cluster_group = _create_group_and_add_host(cluster, first_host)
        service_group = _create_group_and_add_host(service, first_host)
        component_group = _create_group_and_add_host(first_component, first_host)
        cluster.hostcomponent_set((second_host, first_component), (first_host, second_component))
        with allure.step(f'Check host "{first_host.fqdn}" is still presented in cluster config group'):
            _assert_host_is_in_group(cluster_group, first_host)
        with allure.step(f'Check host "{first_host.fqdn}" is still presented in service config group'):
            _assert_host_is_in_group(service_group, first_host)
        with allure.step(f'Check host "{first_host.fqdn}" is not presented in component config group'):
            _assert_host_is_not_in_group(component_group, first_host)


class TestChangeGroupsConfig:
    """Tests for changing group config"""

    ASSERT_TYPE = ["float", "boolean", "integer", "string", "list", "option", "text", "group", "structure", "map"]

    PARAMS_TO_CHANGE = {
        "float": 1.1,
        "boolean": False,
        "integer": 0,
        "string": "string2",
        "list": ["/dev/rdisk0s4", "/dev/rdisk0s5", "/dev/rdisk0s6"],
        "option": "WEEKLY",
        "text": "testtext",
        "group": OrderedDict([('port', 9100), ('transport_port', 9200)]),
        "structure": [{"code": 3, "country": "Test1"}, {"code": 4, "country": "Test2"}],
        "map": {"age": "20", "name": "Chloe", "hair_color": "blond"},
        "json": {"age": "20", "name": "Chloe", "hair_color": "blond"},
        "password": "123",
        "file": "file content test",
        "secrettext": "awesome\npa$$",
    }

    GROUP_KEYS_TO_CHANGE = {
        "float": True,
        "boolean": True,
        "integer": True,
        "password": True,
        "string": True,
        "list": True,
        "file": True,
        "option": True,
        "text": True,
        "group": {"value": True, "fields": {"port": True, "transport_port": True}},
        "structure": True,
        "map": True,
        "json": True,
        "secrettext": True,
    }

    CUSTOM_GROUP_KEYS_TO_CHANGE = {
        "float": False,
        "boolean": False,
        "integer": False,
        "password": False,
        "string": False,
        "list": False,
        "file": False,
        "option": False,
        "text": False,
        "group": {"value": False, "fields": {"port": False, "transport_port": False}},
        "structure": False,
        "map": False,
        "json": False,
        "secrettext": False,
    }

    CLUSTER_HOSTS_VARIANTS = [
        "all",
        "CLUSTER",
        "test_service_1",
        "test_service_1.first",
        "test_service_1.second",
        FIRST_HOST,
        SECOND_HOST,
    ]

    def _add_values_to_group_config_template(
        self, custom_group_keys: dict = None, group_keys: dict = None, config_attr: dict = PARAMS_TO_CHANGE
    ) -> dict:
        """
        Template for group configuration.
        attr and config are required even if this dicts are empty.
        """
        group_config_template = {"attr": {}, "config": {}}
        if custom_group_keys:
            group_config_template["attr"]["custom_group_keys"] = {**custom_group_keys}
        if group_keys:
            group_config_template["attr"]["group_keys"] = {**group_keys}
        if config_attr:
            group_config_template["config"] = {**config_attr}
        # dirty
        for key in group_config_template["attr"].get("group_keys", {}).keys():
            if "group" in key and key not in group_config_template["attr"]:
                group_config_template["attr"][key] = {"active": True}
        return group_config_template

    @allure.step("Check group config values are equal expected")
    def _check_values_in_group(self, actual_values: Union[OrderedDict, dict], expected_values: dict = None):
        """Checks that params in config group are equal to expected and password has been changed"""

        for item in self.ASSERT_TYPE:
            assert (
                actual_values[item] == expected_values[item]
            ), f'Value is "{actual_values[item]}", but should be {expected_values[item]}'
        if actual_values["file"]:
            assert actual_values["file"].strip() == expected_values["file"].strip(), "File has not changed"

    def _get_config_from_group(self, group: GroupConfig):
        """Get config from group and add custom values to password and file"""
        config_group = group.config()
        if "password" in config_group:
            config_group["password"] = "password"
        if "secrettext" in config_group:
            config_group["secrettext"] = "secret\npass\nword"
        if "file" in config_group:
            config_group["file"] = config_group["file"].replace("\n", "")
        return config_group

    @allure.step("Check error that group config can't change")
    def _check_error_with_adding_param_to_group(
        self, group: GroupConfig, params: dict, error_message: str, adcm_error: ADCMError
    ):
        with allure.step(f'Check that error is "{adcm_error.code}"'):
            with pytest.raises(ErrorMessage) as e:
                group.config_set_diff(params)
            adcm_error.equal(e)
        with allure.step(f'Check error message is "{error_message}"'):
            assert error_message in e.value.error['desc'], f"Should be error message '{error_message}'"

    def _check_error_about_changing_custom_group_keys(self, group: GroupConfig, config_before: dict):
        for param in config_before.keys():
            with allure.step(f"Assert that can't change read-only {param} custom_group_keys parameter"):
                invalid_config = {
                    "attr": {"custom_group_keys": {param: self.CUSTOM_GROUP_KEYS_TO_CHANGE[param]}},
                    "config": {param: self.PARAMS_TO_CHANGE[param]},
                }
                self._check_error_with_adding_param_to_group(
                    group,
                    invalid_config,
                    error_message=GROUP_CONFIG_CHANGE_UNSELECTED_ERROR_MESSAGE,
                    adcm_error=GROUP_CONFIG_CHANGE_UNSELECTED_FIELD,
                )

    def _check_error_about_group_keys(self, group: GroupConfig, config_before: dict):

        for param in config_before.keys():
            with allure.step(f"Assert that can't change '{param}' group_keys parameter"):
                invalid_config = {
                    "attr": {"group_keys": {param: self.GROUP_KEYS_TO_CHANGE[param]}},
                    "config": {param: self.PARAMS_TO_CHANGE[param]},
                }
                self._check_error_with_adding_param_to_group(
                    group, invalid_config, error_message=GROUP_ERROR_MESSAGE, adcm_error=ATTRIBUTE_ERROR
                )

    @pytest.fixture(
        params=[
            pytest.param(CLUSTER_BUNDLE_WITH_GROUP_PATH, id="cluster_with_group_customization"),
            pytest.param(CLUSTER_BUNDLE_WITH_CONFIG_GROUP_CUSTOM_PATH, id="cluster_with_config_group_customization"),
        ]
    )
    def cluster_bundle(self, request, sdk_client_fs):
        """Cluster bundle fixture"""
        return sdk_client_fs.upload_from_fs(request.param)

    def test_change_group_in_cluster(self, cluster_bundle, cluster_with_two_hosts_on_it):
        """Test that groups in cluster are allowed change"""

        test_host_1, test_host_2, cluster = cluster_with_two_hosts_on_it
        with allure.step("Create config group for cluster and add first host"):
            cluster_group = _create_group_and_add_host(cluster, test_host_1)
            config_before = self._get_config_from_group(cluster_group)
        with allure.step("Check that without cluster group keys values are not saved in cluster group"):
            config_expected_without_groups = self._add_values_to_group_config_template()
            with pytest.raises(ErrorMessage) as e:
                cluster_group.config_set(config_expected_without_groups)
            ATTRIBUTE_ERROR.equal(e)
            config_after = self._get_config_from_group(cluster_group)
            self._check_values_in_group(
                actual_values=config_after,
                expected_values=config_before,
            )
            config_previous = {"map": {test_host_1.fqdn: dict(config_before), test_host_2.fqdn: dict(config_before)}}
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_previous["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_cluster_action_and_assert_result(cluster, action=ACTION_NAME, config=config_previous)
                    run_cluster_action_and_assert_result(cluster, action=ACTION_MULTIJOB_NAME, config=config_previous)
        with allure.step("Check that with cluster group keys values are saved in cluster group"):
            config_expected_with_groups = self._add_values_to_group_config_template(
                custom_group_keys=cluster_group.config(full=True)["attr"]["custom_group_keys"],
                group_keys=self.GROUP_KEYS_TO_CHANGE,
            )
            config_after = cluster_group.config_set(config_expected_with_groups)
            self._check_values_in_group(
                actual_values=config_after['config'],
                expected_values=config_expected_with_groups['config'],
            )
            config_updated = {
                "map": {test_host_1.fqdn: config_expected_with_groups['config'], test_host_2.fqdn: dict(config_before)}
            }
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_updated["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_cluster_action_and_assert_result(cluster, action=ACTION_NAME, config=config_updated)
                    run_cluster_action_and_assert_result(cluster, action=ACTION_MULTIJOB_NAME, config=config_updated)

    @pytest.mark.full()
    def test_change_group_in_service(self, cluster_bundle, cluster_with_components):
        """Test that groups in service are allowed change"""

        service, test_host_1, test_host_2 = cluster_with_components
        with allure.step("Create config group for service and add first host"):
            service_group = _create_group_and_add_host(service, test_host_1)
            config_before = self._get_config_from_group(service_group)
        with allure.step("Check that without group keys values are not saved in service group"):
            config_expected_without_groups = self._add_values_to_group_config_template()
            with pytest.raises(ErrorMessage) as e:
                service_group.config_set(config_expected_without_groups)
            ATTRIBUTE_ERROR.equal(e)
            config_after = service_group.config()
            self._check_values_in_group(
                actual_values=config_after,
                expected_values=config_before,
            )
            config_previous = {"map": {test_host_1.fqdn: dict(config_before), test_host_2.fqdn: dict(config_before)}}
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_previous["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_service_action_and_assert_result(service, action=ACTION_NAME, config=config_previous)
                    run_service_action_and_assert_result(service, action=ACTION_MULTIJOB_NAME, config=config_previous)
        with allure.step("Check that with group keys values are saved in service group"):
            config_expected_with_groups = self._add_values_to_group_config_template(
                custom_group_keys=service_group.config(full=True)["attr"]["custom_group_keys"],
                group_keys=self.GROUP_KEYS_TO_CHANGE,
            )
            config_after = service_group.config_set(config_expected_with_groups)
            self._check_values_in_group(
                actual_values=config_after['config'],
                expected_values=config_expected_with_groups['config'],
            )
            config_updated = {
                "map": {test_host_1.fqdn: config_expected_with_groups['config'], test_host_2.fqdn: dict(config_before)}
            }
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_updated["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_service_action_and_assert_result(service, action=ACTION_NAME, config=config_updated)
                    run_service_action_and_assert_result(service, action=ACTION_MULTIJOB_NAME, config=config_updated)

    @pytest.mark.full()  # pylint: disable-next=too-many-locals
    def test_change_group_in_component(self, cluster_bundle, cluster_with_components):
        """Test that groups in component are allowed change"""

        service, test_host_1, test_host_2 = cluster_with_components
        component = service.component(name=FIRST_COMPONENT_NAME)
        with allure.step("Create config group for components and add first host"):
            component_group = _create_group_and_add_host(component, test_host_1)
            config_before = self._get_config_from_group(component_group)
        with allure.step("Check that without group keys values are not saved in component group"):
            config_expected_without_groups = self._add_values_to_group_config_template()
            with pytest.raises(ErrorMessage) as e:
                component_group.config_set(config_expected_without_groups)
            ATTRIBUTE_ERROR.equal(e)
            config_after = component_group.config()
            self._check_values_in_group(
                actual_values=config_after,
                expected_values=config_before,
            )
            config_previous = {"map": {test_host_1.fqdn: dict(config_before), test_host_2.fqdn: dict(config_before)}}
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_previous["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_component_action_and_assert_result(component, action=ACTION_NAME, config=config_previous)
                    run_component_action_and_assert_result(
                        component, action=ACTION_MULTIJOB_NAME, config=config_previous
                    )
        with allure.step("Check that with group keys values are saved in component group"):
            config_expected_with_groups = self._add_values_to_group_config_template(
                custom_group_keys=component_group.config(full=True)["attr"]["custom_group_keys"],
                group_keys=self.GROUP_KEYS_TO_CHANGE,
            )
            config_after = component_group.config_set(config_expected_with_groups)
            self._check_values_in_group(
                actual_values=config_after['config'],
                expected_values=config_expected_with_groups['config'],
            )
            config_updated = {
                "map": {test_host_1.fqdn: config_expected_with_groups['config'], test_host_2.fqdn: dict(config_before)}
            }
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_updated["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_component_action_and_assert_result(component, action=ACTION_NAME, config=config_updated)
                    run_component_action_and_assert_result(
                        component, action=ACTION_MULTIJOB_NAME, config=config_updated
                    )

    @pytest.mark.full()
    @pytest.mark.parametrize(
        "provider_bundle",
        [
            pytest.param(PROVIDER_BUNDLE_WITH_GROUP_PATH, id="provider_with_group_customization"),
            pytest.param(PROVIDER_BUNDLE_WITH_CONFIG_GROUP_CUSTOM_PATH, id="provider_with_config_group_customization"),
        ],
        indirect=True,
    )
    def test_change_group_in_provider(self, provider_bundle, provider, create_two_hosts):
        """Test that groups in provider are allowed change"""

        test_host_1, test_host_2 = create_two_hosts
        with allure.step("Create config group for provider and add first host"):
            provider_group = _create_group_and_add_host(provider, test_host_1)
            config_before = self._get_config_from_group(provider_group)
        with allure.step("Check that without group keys values are not saved in provider group"):
            config_expected_without_groups = self._add_values_to_group_config_template()
            with pytest.raises(ErrorMessage) as e:
                provider_group.config_set(config_expected_without_groups)
            ATTRIBUTE_ERROR.equal(e)
            config_after = provider_group.config()
            self._check_values_in_group(
                actual_values=config_after,
                expected_values=config_before,
            )
            config_previous = {"map": {test_host_1.fqdn: dict(config_before), test_host_2.fqdn: dict(config_before)}}
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_previous["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_provider_action_and_assert_result(provider, action=ACTION_NAME, config=config_previous)
                    run_provider_action_and_assert_result(provider, action=ACTION_MULTIJOB_NAME, config=config_previous)
        with allure.step("Check that with group keys values are saved in provider group"):
            config_expected_with_groups = self._add_values_to_group_config_template(
                custom_group_keys=provider_group.config(full=True)["attr"]["custom_group_keys"],
                group_keys=self.GROUP_KEYS_TO_CHANGE,
            )
            config_after = provider_group.config_set(config_expected_with_groups)
            self._check_values_in_group(
                actual_values=config_after['config'],
                expected_values=config_expected_with_groups['config'],
            )
            config_updated = {
                "map": {test_host_1.fqdn: config_expected_with_groups['config'], test_host_2.fqdn: dict(config_before)}
            }
            for hosts in self.CLUSTER_HOSTS_VARIANTS:
                config_updated["hosts"] = hosts
                with allure.step(f"Assert that config values is fine on inventory hosts: {hosts}"):
                    run_provider_action_and_assert_result(provider, action=ACTION_NAME, config=config_updated)
                    run_provider_action_and_assert_result(provider, action=ACTION_MULTIJOB_NAME, config=config_updated)

    def test_error_with_changing_custom_group_keys_in_cluster_group(self, cluster_bundle, cluster):
        """Test error with changing group_customization in cluster group"""

        with allure.step("Create config group for cluster"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(cluster_group)
        self._check_error_about_changing_custom_group_keys(cluster_group, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "cluster_with_all_group_keys_false"), id="cluster_with_all_group_keys_false"
            )
        ],
        indirect=True,
    )
    def test_changing_params_in_cluster_group_without_group_customization(self, cluster, cluster_with_two_hosts_on_it):
        """Test changing params in cluster group without group_customization"""

        with allure.step("Create config group for cluster"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(cluster_group)
        self._check_error_about_group_keys(cluster_group, config_before)

    def test_error_with_changing_custom_group_keys_in_service_group(self, cluster_bundle, cluster):
        """Test error with changing group_customization"""

        with allure.step("Create config group for service"):
            service = cluster.service_add(name='test_service_1')
            service_group = service.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(service_group)
        self._check_error_about_changing_custom_group_keys(service_group, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "cluster_with_all_group_keys_false"), id="cluster_with_all_group_keys_false"
            )
        ],
        indirect=True,
    )
    def test_change_params_in_service_group_without_group_customization(self, cluster_bundle, cluster_with_components):
        """Test changing params in service group without group_customization"""

        service, _, _ = cluster_with_components
        with allure.step("Create config group for service"):
            service_group = service.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(service_group)
        self._check_error_about_group_keys(service_group, config_before)

    def test_error_with_changing_custom_group_keys_in_component_group(self, cluster_bundle, cluster_with_components):
        """Test changing params in component group without group_customization"""

        service, _, _ = cluster_with_components
        component = service.component(name=FIRST_COMPONENT_NAME)
        with allure.step("Create config group for component"):
            component_group = component.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(component_group)
        self._check_error_about_changing_custom_group_keys(component_group, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "cluster_with_all_group_keys_false"), id="cluster_with_all_group_keys_false"
            )
        ],
        indirect=True,
    )
    def test_change_params_in_component_group_without_group_customization(
        self, cluster_bundle, cluster_with_components
    ):
        """Test changing params in component group without group_customization"""

        service, test_host_1, _ = cluster_with_components
        component = service.component(name=FIRST_COMPONENT_NAME)
        with allure.step("Create config group for components and add first host"):
            component_group = _create_group_and_add_host(component, test_host_1)
            config_before = self._get_config_from_group(component_group)
        self._check_error_about_group_keys(component_group, config_before)

    @pytest.mark.parametrize(
        "provider_bundle",
        [
            pytest.param(PROVIDER_BUNDLE_WITH_GROUP_PATH, id="provider_with_group_customization"),
            pytest.param(PROVIDER_BUNDLE_WITH_CONFIG_GROUP_CUSTOM_PATH, id="provider_with_config_group_customization"),
        ],
        indirect=True,
    )
    def test_error_with_changing_custom_group_keys_in_provider_group(self, provider_bundle, provider):
        """Test changing params in provider group without group_customization"""

        with allure.step("Create config group for provider and add first host"):
            provider_group = provider.group_config_create(name=FIRST_GROUP)
            config_before = self._get_config_from_group(provider_group)
        self._check_error_about_changing_custom_group_keys(provider_group, config_before)

    @pytest.mark.parametrize(
        "provider_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "provider_group_with_all_group_keys_false"),
                id="provider_with_all_group_keys_false",
            )
        ],
        indirect=True,
    )
    def test_change_params_in_provider_group_without_group_customization(
        self, provider_bundle, provider, create_two_hosts
    ):
        """Test changing params in provider group without group_customization"""

        test_host_1, _ = create_two_hosts
        with allure.step("Create config group for provider and add first host"):
            provider_group = _create_group_and_add_host(provider, test_host_1)
            config_before = self._get_config_from_group(provider_group)
        self._check_error_about_group_keys(provider_group, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [pytest.param(get_data_dir(__file__, "cluster_simple"), id="cluster_with_group_subs")],
        indirect=True,
    )
    def test_changing_params_in_cluster_group_subs(self, cluster_bundle, cluster_with_two_hosts_on_it):
        """Test changing params in cluster group subs with different group_customization"""

        test_host_1, test_host_2, cluster = cluster_with_two_hosts_on_it
        with allure.step("Create config group for cluster"):
            cluster_group = _create_group_and_add_host(cluster, test_host_1)
            config_before = self._get_config_from_group(cluster_group)
        with allure.step("Check changing sub with group_customization true"):
            config_expected = self._add_values_to_group_config_template(
                config_attr={"group": OrderedDict([('port', 9200), ('transport_port', 9100)])},
                group_keys={"group": {"value": False, "fields": {"port": False, "transport_port": True}}},
                custom_group_keys={"group": {"value": False, "fields": {"port": False, "transport_port": True}}},
            )
            config_expected['attr']['group'] = {'active': True}
            cluster_group.config_set(config_expected)
            config_updated = {
                "map": {test_host_1.fqdn: config_expected['config'], test_host_2.fqdn: dict(config_before)}
            }
            run_cluster_action_and_assert_result(cluster, action=ACTION_NAME, config=config_updated)
            run_cluster_action_and_assert_result(cluster, action=ACTION_MULTIJOB_NAME, config=config_updated)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [pytest.param(get_data_dir(__file__, "cluster_with_main_info"), id="main_info_check")],
        indirect=True,
    )
    @allure.issue("https://arenadata.atlassian.net/browse/ADCM-2235")
    def test_changing_group_with_main_info_key(self, cluster_bundle, cluster_with_two_hosts_on_it):
        """Test that __main_info key do not break action runner"""

        test_host_1, _, cluster = cluster_with_two_hosts_on_it
        with allure.step("Assert that action with __main_info key works fine without config group"):
            cluster.config_set({"float": 0.3})
            run_cluster_action_and_assert_result(cluster, action=ACTION_NAME)
            run_cluster_action_and_assert_result(cluster, action=ACTION_MULTIJOB_NAME)
        with allure.step("Create group and add host"):
            cluster_group = _create_group_and_add_host(cluster, test_host_1)
        with allure.step("Assert that action with __main_info key works fine with host in config group"):
            cluster_group.config_set(
                {
                    "config": {"__main_info": "This is cluster main info", "float": 0.1},
                    "attr": {
                        "group_keys": {"__main_info": False, "float": True},
                        "custom_group_keys": {"__main_info": False, "float": True},
                    },
                }
            )
            run_cluster_action_and_assert_result(cluster, action=ACTION_NAME, timeout=30)
            run_cluster_action_and_assert_result(cluster, action=ACTION_MULTIJOB_NAME, timeout=30)


class TestActivatableGroupInGroupConfig:
    """Test cases with activatable group manipulations in group config"""

    @pytest.mark.parametrize(
        'cluster_bundle', [get_data_dir(__file__, 'cluster_with_activatable_group')], indirect=True
    )
    def test_activatable_group(self, adcm_fs, cluster_with_two_hosts_on_it):
        """Test activatable group in config groups"""
        NoneType = type(None)
        first_host, _, cluster = cluster_with_two_hosts_on_it

        with allure.step('Activate group in cluster config'):
            self._change_attrs(cluster, True)
        with allure.step('Create config group for the cluster with one host'):
            group = _create_group_and_add_host(cluster, first_host)

        with allure.step('Do not include anything in config group and expect "main_group" to be dict'):
            self.check_new_inventory(dict, cluster, adcm_fs.container)

        with allure.step('Deactivate "main_group", include it in config group, expect "null" in inventory'):
            self._change_attrs(group, False, True, False)
            self.check_new_inventory(NoneType, cluster, adcm_fs.container)

        with allure.step(
            'Deactivate "main_group", exclude from config group, include one of its children, expect dict in inventory'
        ):
            self._change_attrs(group, False, False, True)
            self.check_new_inventory(dict, cluster, adcm_fs.container)

        with allure.step('Deactivate "main_group", exclude it from config group, expect dict in inventory'):
            self._change_attrs(group, False, False, False)
            self.check_new_inventory(dict, cluster, adcm_fs.container)

        with allure.step('Deactivate "main_group" in cluster config and expect None in inventory'):
            self._change_attrs(cluster, False)
            self.check_new_inventory(NoneType, cluster, adcm_fs.container)

    @allure.step('Generate new inventory and expect "main_group" to be of type {expected_group_type}')
    def check_new_inventory(self, expected_group_type: Type, cluster: Cluster, container: Container):
        """Run action and check inventory"""
        task = cluster.action().run()
        task.wait()
        inventory = self._get_task_inventory(task.id, container)
        main_group = inventory['all']['children']['CLUSTER']['hosts'][FIRST_HOST]['cluster']['config']['main_group']
        assert isinstance(main_group, expected_group_type), (
            f'"main_group" should be of type "{expected_group_type}" in the inventory.\n'
            f'Actual type is "{type(main_group)}"'
        )

    def _get_task_inventory(self, task_id: int, container: Container):
        return json.loads(container.exec_run(['cat', f'/adcm/data/run/{task_id}/inventory.json']).output)

    def _change_attrs(self, obj, group_is_on, group_is_included=None, group_element_is_included=None):
        config = {
            'config': {},
            'attr': {
                'main_group': {
                    'active': group_is_on,
                },
            },
        }
        if group_is_included is not None and group_element_is_included is not None:
            config['attr']['group_keys'] = {
                'main_group': {
                    'value': group_is_included,
                    'fields': {'simple_value': group_element_is_included},
                }
            }
        obj.config_set_diff(config)
