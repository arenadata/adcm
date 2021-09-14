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
# pylint: disable=redefined-outer-name, unused-argument, duplicate-code

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
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage

from tests.library.errorcodes import GROUP_CONFIG_HOST_ERROR

CLUSTER_BUNDLE_PATH = get_data_dir(__file__, "cluster_simple")
PROVIDER_BUNDLE_PATH = get_data_dir(__file__, "hostprovider_bundle")


@pytest.fixture()
def cluster(request, sdk_client_fs: ADCMClient) -> Cluster:
    bundle_path = request.param if hasattr(request, "param") else CLUSTER_BUNDLE_PATH
    cluster_bundle = sdk_client_fs.upload_from_fs(bundle_path)
    return cluster_bundle.cluster_create(name=utils.random_string())


@pytest.fixture()
def provider(request, sdk_client_fs: ADCMClient) -> Provider:
    bundle_path = request.param if hasattr(request, "param") else PROVIDER_BUNDLE_PATH
    provider_bundle = sdk_client_fs.upload_from_fs(bundle_path)
    return provider_bundle.provider_create(name=utils.random_string())


class TestGroupsIntersection:

    HOST_ERROR_MESSAGE = (
        "host is not available for this object, or host already is a member of another group of this object"
    )
    FIRST_COMPONENT_NAME = "first"
    SECOND_COMPONENT_NAME = "second"
    FIRST_GROUP = "test_group"
    SECOND_GROUP = "test_group_2"
    FIRST_HOST = "test_host_1"
    SECOND_HOST = "test_host_2"

    @pytest.fixture()
    def create_two_hosts(self, provider) -> Tuple[Host, Host]:
        with allure.step("Create host for config groups"):
            test_host_1 = provider.host_create(fqdn=self.FIRST_HOST)
        with allure.step("Create host for host candidate check"):
            test_host_2 = provider.host_create(fqdn=self.SECOND_HOST)
        return test_host_1, test_host_2

    @allure.step('Check error')
    def assert_that_host_add_is_unavaliable(self, error):
        with allure.step(f"Check that error is '{GROUP_CONFIG_HOST_ERROR.code}'"):
            GROUP_CONFIG_HOST_ERROR.equal(error)
        with allure.step(f"Check error message is '{self.HOST_ERROR_MESSAGE}'"):
            assert (
                self.HOST_ERROR_MESSAGE in error.value.error['desc']
            ), f"Should be error message '{self.HOST_ERROR_MESSAGE}'"

    @allure.step("Check that the only second host is present in candidates on second provider group")
    def assert_host_candidate_equal_expected(self, group: HostList, expected_hosts: int):
        with allure.step(f"Check that {expected_hosts} hosts are available in group"):
            assert len(group) == expected_hosts, f"{expected_hosts} hosts should be available in group"
        with allure.step(f"Check that host '{self.SECOND_HOST}' is available in group"):
            assert group[0].fqdn == self.SECOND_HOST, f"Should be available host '{self.SECOND_HOST}'"

    @pytest.fixture()
    def cluster_with_components(
        self, create_two_hosts, cluster: Cluster, provider: Provider
    ) -> Tuple[Service, Host, Host]:
        """Add service, two hosts and create components to check intersection in config groups"""

        service = cluster.service_add(name='test_service_1')
        test_host_1, test_host_2 = create_two_hosts
        cluster.host_add(test_host_1)
        cluster.host_add(test_host_2)
        cluster.hostcomponent_set(
            (test_host_1, service.component(name=self.FIRST_COMPONENT_NAME)),
            (test_host_2, service.component(name=self.FIRST_COMPONENT_NAME)),
            (test_host_2, service.component(name=self.SECOND_COMPONENT_NAME)),
        )
        return service, test_host_1, test_host_2

    def test_that_groups_not_allowed_to_intersect_in_cluster(self, sdk_client_fs, cluster, create_two_hosts):
        """Test that groups are not allowed to intersect in cluster"""

        test_host_1, test_host_2 = create_two_hosts
        cluster.host_add(test_host_1)
        cluster.host_add(test_host_2)
        with allure.step("Create config group for cluster and add the first host"):
            cluster_group = cluster.group_config_create(name=self.FIRST_GROUP)
            cluster_group.host_add(test_host_1)
        with allure.step("Create the second group for cluster and check that not allowed to add the first host to it"):
            cluster_group_2 = cluster.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                cluster_group_2.host_add(test_host_1)
            self.assert_that_host_add_is_unavaliable(e)
            self.assert_host_candidate_equal_expected(cluster_group_2.host_candidate(), 1)

    def test_that_groups_not_allowed_to_intersect_in_provider(self, sdk_client_fs, create_two_hosts, provider):
        """Test that groups are not allowed to intersect in provider"""

        test_host_1, _ = create_two_hosts
        with allure.step("Create config group for provider and add the first host"):
            provider_group = provider.group_config_create(name=self.FIRST_GROUP)
            provider_group.host_add(test_host_1)
        with allure.step("Create the second group for provider and check that not allowed to add the first host to it"):
            provider_group_2 = provider.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                provider_group_2.host_add(test_host_1)
            self.assert_that_host_add_is_unavaliable(e)
            self.assert_host_candidate_equal_expected(provider_group_2.host_candidate(), 1)

    def test_that_groups_not_allowed_to_intersect_in_service(self, sdk_client_fs, cluster_with_components):
        """Test that groups are not allowed to intersect in service"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create group for service and add the first host"):
            service_group = service.group_config_create(name=self.FIRST_GROUP)
            service_group.host_add(test_host_1)
        with allure.step("Create the second group for service and check that not allowed to add the first host to it"):
            service_group_2 = service.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                service_group_2.host_add(test_host_1)
            self.assert_that_host_add_is_unavaliable(e)
            self.assert_host_candidate_equal_expected(service_group_2.host_candidate(), 1)

    def test_that_groups_not_allowed_to_intersect_in_component(self, sdk_client_fs, cluster_with_components):
        """Test that groups are not allowed to intersect"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create config group for component and add the first host"):
            component_group = service.component(name=self.FIRST_COMPONENT_NAME).group_config_create(
                name=self.FIRST_GROUP
            )
            component_group.host_add(test_host_1)
        with allure.step(
            "Create the second group for component and check that not allowed to add the first host to it"
        ):
            component_group_2 = service.component(name=self.FIRST_COMPONENT_NAME).group_config_create(
                name=self.SECOND_GROUP
            )
            with pytest.raises(ErrorMessage) as e:
                component_group_2.host_add(test_host_1)
        self.assert_that_host_add_is_unavaliable(e)
        self.assert_host_candidate_equal_expected(component_group_2.host_candidate(), 1)
