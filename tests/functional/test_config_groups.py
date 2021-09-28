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
# pylint: disable=redefined-outer-name, unused-argument, duplicate-code, no-self-use

from collections import OrderedDict
from typing import Tuple

import allure
import pytest
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Provider,
    HostList,
    Service,
    Host,
    GroupConfig,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage

from tests.library.errorcodes import (
    GROUP_CONFIG_HOST_ERROR,
    GROUP_CONFIG_HOST_EXISTS,
)

CLUSTER_BUNDLE_PATH = get_data_dir(__file__, "cluster_simple")
CLUSTER_BUNDLE_WITH_GROUP_PATH = get_data_dir(__file__, "cluster_with_group_all_params")
PROVIDER_BUNDLE_PATH = get_data_dir(__file__, "hostprovider_bundle")

HOST_ERROR_MESSAGE = (
    "host is not available for this object, or host already is a member of another group of this object"
)
HOST_EXISTS_MESSAGE = "the host is already a member of this group"
FIRST_COMPONENT_NAME = "first"
SECOND_COMPONENT_NAME = "second"
FIRST_GROUP = "test_group"
SECOND_GROUP = "test_group_2"
FIRST_HOST = "test_host_1"
SECOND_HOST = "test_host_2"


@pytest.fixture()
def provider_bundle(request, sdk_client_fs: ADCMClient):
    bundle_path = request.param if hasattr(request, "param") else PROVIDER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster_bundle(request, sdk_client_fs: ADCMClient):
    bundle_path = request.param if hasattr(request, "param") else CLUSTER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster(cluster_bundle) -> Cluster:
    return cluster_bundle.cluster_create(name=utils.random_string())


@pytest.fixture()
def provider(provider_bundle) -> Provider:
    return provider_bundle.provider_create(name=utils.random_string())


@pytest.fixture()
def create_two_hosts(provider) -> Tuple[Host, Host]:
    with allure.step("Create host for config groups"):
        test_host_1 = provider.host_create(fqdn=FIRST_HOST)
    with allure.step("Create host for host candidate check"):
        test_host_2 = provider.host_create(fqdn=SECOND_HOST)
    return test_host_1, test_host_2


@pytest.fixture()
def cluster_with_components(create_two_hosts, cluster: Cluster, provider: Provider) -> Tuple[Service, Host, Host]:
    """Add service, two hosts and create components to check intersection in config groups"""

    service = cluster.service_add(name='test_service_1')
    test_host_1, test_host_2 = create_two_hosts
    cluster.host_add(test_host_1)
    cluster.host_add(test_host_2)
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
def assert_that_host_add_is_unavailable(service_group: GroupConfig, host: Host):
    with allure.step(f'Check that error is "{GROUP_CONFIG_HOST_ERROR.code}"'):
        with pytest.raises(ErrorMessage) as e:
            service_group.host_add(host)
        GROUP_CONFIG_HOST_ERROR.equal(e)
    with allure.step(f'Check error message is "{HOST_ERROR_MESSAGE}"'):
        assert HOST_ERROR_MESSAGE in e.value.error['desc'], f"Should be error message '{HOST_ERROR_MESSAGE}'"


@allure.step('Check that host exists')
def assert_that_host_exists(group: GroupConfig, host: Host):
    with allure.step(f'Check that error is "{GROUP_CONFIG_HOST_EXISTS.code}"'):
        with pytest.raises(ErrorMessage) as e:
            group.host_add(host)
        GROUP_CONFIG_HOST_EXISTS.equal(e)
    with allure.step(f'Check error message is "{HOST_EXISTS_MESSAGE}"'):
        assert HOST_EXISTS_MESSAGE in e.value.error['desc'], f"Should be error message '{HOST_EXISTS_MESSAGE}'"


@allure.step('Check that host is in the group')
def assert_host_is_in_group(group: GroupConfig, host: Host):
    assert host.fqdn in [h.fqdn for h in group.hosts().data], f'Host "{host.fqdn}" should be in group "{group.name}"'


@allure.step("Check that the only second host is present in candidates on second group")
def assert_host_candidate_equal_expected(group: HostList, expected_hosts_names: [str]):
    expected_hosts_amount = len(expected_hosts_names)
    with allure.step(f"Check that {expected_hosts_amount} hosts are available in group"):
        assert len(group) == expected_hosts_amount, f"{expected_hosts_amount} hosts should be available in group"
    with allure.step(f"Check that host '{SECOND_HOST}' is available in group"):
        assert [g.fqdn for g in group] == expected_hosts_names, f"Should be available hosts '{expected_hosts_names}'"


class TestGroupsIntersection:
    def test_that_groups_not_allowed_to_intersect_in_cluster(self, sdk_client_fs, cluster, create_two_hosts):
        """Test that groups are not allowed to intersect in cluster"""

        test_host_1, test_host_2 = create_two_hosts
        cluster.host_add(test_host_1)
        cluster.host_add(test_host_2)
        with allure.step("Create config group for cluster and add the first host"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
            cluster_group.host_add(test_host_1)
        with allure.step("Create the second group for cluster and check that not allowed to add the first host to it"):
            cluster_group_2 = cluster.group_config_create(name=SECOND_GROUP)
            assert_that_host_add_is_unavailable(cluster_group_2, test_host_1)
            assert_host_candidate_equal_expected(cluster_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_provider(self, sdk_client_fs, create_two_hosts, provider):
        """Test that groups are not allowed to intersect in provider"""

        test_host_1, _ = create_two_hosts
        with allure.step("Create config group for provider and add the first host"):
            provider_group = provider.group_config_create(name=FIRST_GROUP)
            provider_group.host_add(test_host_1)
        with allure.step("Create the second group for provider and check that not allowed to add the first host to it"):
            provider_group_2 = provider.group_config_create(name=SECOND_GROUP)
            assert_that_host_add_is_unavailable(provider_group_2, test_host_1)
            assert_host_candidate_equal_expected(provider_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_service(self, sdk_client_fs, cluster, cluster_with_components):
        """Test that groups are not allowed to intersect in service"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create group for service and add the first host"):
            service_group = service.group_config_create(name=FIRST_GROUP)
            service_group.host_add(test_host_1)
        with allure.step("Create the second group for service and check that not allowed to add the first host to it"):
            service_group_2 = service.group_config_create(name=SECOND_GROUP)
            assert_that_host_add_is_unavailable(service_group_2, test_host_1)
            assert_host_candidate_equal_expected(service_group_2.host_candidate(), [SECOND_HOST])

    def test_that_groups_not_allowed_to_intersect_in_component(self, sdk_client_fs, cluster_with_components):
        """Test that groups are not allowed to intersect"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create config group for component and add the first host"):
            component_group = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=FIRST_GROUP)
            component_group.host_add(test_host_1)
        with allure.step(
            "Create the second group for component and check that not allowed to add the first host to it"
        ):
            component_group_2 = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=SECOND_GROUP)
        assert_that_host_add_is_unavailable(component_group_2, test_host_1)
        assert_host_candidate_equal_expected(component_group_2.host_candidate(), [SECOND_HOST])


class TestIncorrectHostInGroups:
    """Test for incorrect hosts in group caused errors like GROUP_CONFIG_HOST_ERROR or GROUP_CONFIG_HOST_EXISTS"""

    def test_add_incorrect_host_to_provider_group(self, sdk_client_fs, provider_bundle, provider):
        """Test exception rise when we try to add incorrect host to provider group"""
        with allure.step("Create host from first provider"):
            correct_host = provider.host_create(fqdn=utils.random_string())
        with allure.step("Create second provider"):
            provider_2 = provider_bundle.provider_create(name="Second test provider")
        with allure.step("Create host from second provider"):
            incorrect_host = provider_2.host_create(fqdn=utils.random_string())
        with allure.step("Create config group for first provider and try to add the first host"):
            provider_group = provider.group_config_create(name=incorrect_host.fqdn)
            assert_that_host_add_is_unavailable(provider_group, incorrect_host)
            assert_host_candidate_equal_expected(provider_group.host_candidate(), [correct_host.fqdn])
        with allure.step("Add first host to provider group and check that second add is not available"):
            provider_group.host_add(correct_host)
            assert_that_host_exists(provider_group, correct_host)
            assert_host_candidate_equal_expected(provider_group.host_candidate(), [])

    def test_add_incorrect_host_to_service_group(self, cluster_with_components_on_first_host):
        """Test exception rise when we try to add incorrect host to service group"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for service"):
            service_group = service.group_config_create(name=FIRST_GROUP)
        with allure.step("Try to add the second host not from service and check group hosts list"):
            assert_that_host_add_is_unavailable(service_group, test_host_2)
            assert_host_candidate_equal_expected(service_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to service group and check that second add is not available"):
            service_group.host_add(test_host_1)
            assert_that_host_exists(service_group, test_host_1)
            assert_host_candidate_equal_expected(service_group.host_candidate(), [])

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
            assert_that_host_add_is_unavailable(cluster_group, test_host_2)
            assert_host_candidate_equal_expected(cluster_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to cluster group and check that second add is not available"):
            cluster_group.host_add(test_host_1)
            assert_that_host_exists(cluster_group, test_host_1)
            assert_host_candidate_equal_expected(cluster_group.host_candidate(), [])

    def test_add_incorrect_host_to_component_group(self, cluster_with_components_on_first_host):
        """Test exception rise when we try to add incorrect host to component group"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for component"):
            component_group = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=FIRST_GROUP)
        with allure.step("Try to add host not from cluster to component group"):
            assert_that_host_add_is_unavailable(component_group, test_host_2)
            assert_host_candidate_equal_expected(component_group.host_candidate(), [FIRST_HOST])
        with allure.step("Add first host to component group and check that second add is not available"):
            component_group.host_add(test_host_1)
            assert_that_host_exists(component_group, test_host_1)
            assert_host_candidate_equal_expected(component_group.host_candidate(), [])


class TestDeleteHostInGroups:
    """Test deleting host related to conf group"""

    @allure.step("Check that there are no hosts in conf group")
    def check_no_hosts_in_group(self, group: GroupConfig):
        assert len(group.hosts()) == 0, "Should not be any hosts in conf group"

    def test_delete_host_from_group_after_deleting_in_cluster(self, sdk_client_fs, cluster, provider):
        """Test that host removed from conf group after removing from cluster"""

        test_host = provider.host_create(fqdn=FIRST_HOST)
        cluster.host_add(test_host)
        with allure.step("Create config group for cluster and add the host"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
            cluster_group.host_add(test_host)
            assert_host_is_in_group(cluster_group, test_host)
        cluster.host_delete(test_host)
        self.check_no_hosts_in_group(cluster_group)
        with allure.step("Check that there are no hosts available to add in cluster group"):
            assert_host_candidate_equal_expected(cluster_group.host_candidate(), [])

    def test_delete_host_from_group_after_deleting_in_service(
        self, cluster, sdk_client_fs, cluster_with_components_on_first_host
    ):
        """Test that host removed from conf group after removing from service"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create group for service and add the host"):
            service_group = service.group_config_create(name=FIRST_GROUP)
            service_group.host_add(test_host_1)
            assert_host_is_in_group(service_group, test_host_1)
        with allure.step("Change host in service"):
            cluster.host_add(test_host_2)
            cluster.hostcomponent_set(
                (test_host_2, service.component(name=FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=SECOND_COMPONENT_NAME)),
            )
        self.check_no_hosts_in_group(service_group)

    def test_delete_host_from_group_after_delete_in_component(
        self, cluster, sdk_client_fs, cluster_with_components_on_first_host
    ):
        """Test that host removed from conf group after removing from component"""

        service, test_host_1, test_host_2 = cluster_with_components_on_first_host
        with allure.step("Create config group for component and add the first host"):
            component_group = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=FIRST_GROUP)
            component_group.host_add(test_host_1)
            assert_host_is_in_group(component_group, test_host_1)
        with allure.step("Change host in component"):
            cluster.host_add(test_host_2)
            cluster.hostcomponent_set(
                (test_host_2, service.component(name=FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=SECOND_COMPONENT_NAME)),
            )
        self.check_no_hosts_in_group(component_group)

    def test_delete_host_from_group_after_it_deleted(self, sdk_client_fs, provider):
        """Test that host removed from provider conf group after deleting"""

        with allure.step("Create config group for provider and add host"):
            test_host = provider.host_create(fqdn=FIRST_HOST)
            provider_group = provider.group_config_create(name=FIRST_GROUP)
            provider_group.host_add(test_host)
            assert_host_is_in_group(provider_group, test_host)
        with allure.step("Delete host"):
            test_host.delete()
        self.check_no_hosts_in_group(provider_group)


class TestChangeGroupsConfig:
    """Tests for changing group config"""

    ASSERT_TYPE = ["float", "boolean", "integer", "string", "list", "file", "option", "text", "structure", "map"]

    PARAMS_TO_CHANGE = {
        "attr": {},
        "config": {
            "float": 1.1,
            "boolean": False,
            "integer": 0,
            "password": "123",
            "string": "string2",
            "list": ["/dev/rdisk0s4", "/dev/rdisk0s5", "/dev/rdisk0s6"],
            "file": "file content test",
            "option": "WEEKLY",
            "text": "testtext",
            "structure": [{"code": 3, "country": "Test1"}, {"code": 4, "country": "Test2"}],
            "map": {"age": "20", "name": "Chloe", "sex": "f"},
        },
    }

    def _check_changed_values_in_group(self, values_after: OrderedDict, values_before: OrderedDict):
        for item in self.ASSERT_TYPE:
            assert (
                values_after[item] == self.PARAMS_TO_CHANGE["config"][item]
            ), f'Value is "{values_after[item]}", but should be {self.PARAMS_TO_CHANGE["config"][item]}'
            assert values_after["password"] != values_before["password"], "Password has not changed"

    @pytest.mark.parametrize(
        "cluster_bundle",
        [pytest.param(get_data_dir(__file__, CLUSTER_BUNDLE_WITH_GROUP_PATH), id="cluster_with_group")],
        indirect=True,
    )
    def test_change_group_in_cluster(self, cluster_bundle, sdk_client_fs):
        """Test that groups in cluster are allowed chenge with group_customization: true"""

        cluster = cluster_bundle.cluster_create(name=utils.random_string())
        with allure.step("Create config group for cluster"):
            cluster_group = cluster.group_config_create(name=FIRST_GROUP)
            config_before = cluster_group.config()
        config_after = cluster_group.config_set_diff(self.PARAMS_TO_CHANGE)['config']
        with allure.step("Check group config"):
            self._check_changed_values_in_group(config_after, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [pytest.param(get_data_dir(__file__, CLUSTER_BUNDLE_WITH_GROUP_PATH), id="cluster_with_group")],
        indirect=True,
    )
    def test_change_group_in_service(self, cluster_bundle, sdk_client_fs, cluster_with_components):
        """Test that groups in service are allowed chenge with group_customization: true"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create group for service and add the first host"):
            service_group = service.group_config_create(name=FIRST_GROUP)
            service_group.host_add(test_host_1)
            config_before = service_group.config()
        config_after = service_group.config_set_diff(self.PARAMS_TO_CHANGE)['config']
        with allure.step("Check group config"):
            self._check_changed_values_in_group(config_after, config_before)

    @pytest.mark.parametrize(
        "cluster_bundle",
        [pytest.param(get_data_dir(__file__, CLUSTER_BUNDLE_WITH_GROUP_PATH), id="cluster_with_group")],
        indirect=True,
    )
    def test_change_group_in_component(self, cluster_bundle, sdk_client_fs, cluster_with_components):
        """Test that groups in component are allowed chenge with group_customization: true"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create config group for component and add the first host"):
            component_group = service.component(name=FIRST_COMPONENT_NAME).group_config_create(name=FIRST_GROUP)
            component_group.host_add(test_host_1)
            config_before = component_group.config()
        config_after = component_group.config_set_diff(self.PARAMS_TO_CHANGE)['config']
        with allure.step("Check group config"):
            self._check_changed_values_in_group(config_after, config_before)

    @pytest.mark.parametrize(
        "provider_bundle",
        [pytest.param(get_data_dir(__file__, "provider_group_with_all_params"), id="provider_with_group")],
        indirect=True,
    )
    def test_change_group_in_provider(self, sdk_client_fs, provider_bundle):
        """Test that groups in provider are allowed chenge with group_customization: true"""

        test_host_1, _ = create_two_hosts
        with allure.step("Create config group for provider and add the first host"):
            provider_group = provider.group_config_create(name=FIRST_GROUP)
            provider_group.host_add(test_host_1)
        with allure.step("Create the second group for provider and check that not allowed to add the first host to it"):
            provider_group_2 = provider.group_config_create(name=SECOND_GROUP)
            assert_that_host_add_is_unavailable(provider_group_2, test_host_1)
            assert_host_candidate_equal_expected(provider_group_2.host_candidate(), [SECOND_HOST])
