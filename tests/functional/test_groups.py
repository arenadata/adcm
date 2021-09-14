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

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Provider
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import get_data_dir
from coreapi.exceptions import ErrorMessage

from tests.library.errorcodes import GROUP_CONFIG_HOST_ERROR

DEFAULT_CLUSTER_BUNDLE_PATH = get_data_dir(__file__, "cluster_simple")
DEFAULT_PROVIDER_BUNDLE_PATH = get_data_dir(__file__, "hostprovider_bundle")


@pytest.fixture()
def cluster_bundle(request, sdk_client_fs: ADCMClient) -> Bundle:
    bundle_path = request.param if hasattr(request, "param") else DEFAULT_CLUSTER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster(cluster_bundle: Bundle) -> Cluster:
    return cluster_bundle.cluster_create(name=utils.random_string())


@pytest.fixture()
def provider_bundle(request, sdk_client_fs: ADCMClient) -> Bundle:
    bundle_path = request.param if hasattr(request, "param") else DEFAULT_PROVIDER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def provider(provider_bundle: Bundle) -> Provider:
    return provider_bundle.provider_create(name=utils.random_string())


class TestGroups:

    HOST_ERROR_MESSAGE = (
        "host is not available for this object, or host already is a member of another group of this object"
    )
    FIRST_COMPONENT_NAME = "first"
    SECOND_COMPONENT_NAME = "second"
    FIRST_GROUP = "test_group"
    SECOND_GROUP = "test_group_2"
    FIRST_HOST = "test_host_1"
    SECOND_HOST = "test_host_2"

    def create_two_hosts(self, provider: Provider):
        with allure.step("Create host for config groups"):
            test_host_1 = provider.host_create(fqdn=self.FIRST_HOST)
        with allure.step("Create host for host candidate check"):
            test_host_2 = provider.host_create(fqdn=self.SECOND_HOST)
        return test_host_1, test_host_2

    @allure.step('Check error')
    def check_group_config_error(self, error):
        GROUP_CONFIG_HOST_ERROR.equal(error)
        assert self.HOST_ERROR_MESSAGE in error.value.error['desc']

    @pytest.fixture()
    def cluster_with_components(self, cluster, provider):
        service = cluster.service_add(name='test_service_1')
        test_host_1, test_host_2 = self.create_two_hosts(provider)
        cluster.host_add(test_host_1)
        with allure.step("Create hostcomponent"):
            cluster.host_add(test_host_2)
            cluster.hostcomponent_set(
                (test_host_1, service.component(name=self.FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=self.FIRST_COMPONENT_NAME)),
                (test_host_2, service.component(name=self.SECOND_COMPONENT_NAME)),
            )
        return service, test_host_1, test_host_2

    def test_that_groups_not_allowed_to_intersect_in_cluster(self, sdk_client_fs, cluster, provider):
        """Test that groups are not allowed to intersect in cluster"""

        test_host_1, test_host_2 = self.create_two_hosts(provider)
        cluster.host_add(test_host_1)
        cluster.host_add(test_host_2)
        with allure.step("Create group Configuration group for cluster and add the first host"):
            cluster_group = cluster.group_config_create(name=self.FIRST_GROUP)
            cluster_group.host_add(test_host_1)
        with allure.step("Create second group for cluster and add the first host"):
            cluster_group_2 = cluster.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                cluster_group_2.host_add(test_host_1)
            self.check_group_config_error(e)
        with allure.step("Check that 1 group available to add to cluster group"):
            assert len(cluster_group_2.host_candidate()) == 1, "One host should be available in cluster group"
            assert (
                cluster_group_2.host_candidate()[0].fqdn == self.SECOND_HOST
            ), f"Should be available host '{self.SECOND_HOST}'"

    def test_that_groups_not_allowed_to_intersect_in_provider(self, sdk_client_fs, provider):
        """Test that groups are not allowed to intersect in provider"""

        test_host_1, _ = self.create_two_hosts(provider)
        with allure.step("Create group Configuration group for provider and add the first host"):
            provider_group = provider.group_config_create(name=self.FIRST_GROUP)
            provider_group.host_add(test_host_1)
        with allure.step("Create second group for provider and add the first host"):
            provider_group_2 = provider.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                provider_group_2.host_add(test_host_1)
        self.check_group_config_error(e)
        with allure.step("Check that 1 group available to add to provider group"):
            assert len(provider_group_2.host_candidate()) == 1, "One host should be available in provider group"
            assert (
                provider_group_2.host_candidate()[0].fqdn == self.SECOND_HOST
            ), f"Should be available host '{self.SECOND_HOST}'"

    def test_that_groups_not_allowed_to_intersect_in_service(self, sdk_client_fs, cluster_with_components):
        """Test that groups are not allowed to intersect in service"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create group Configuration group for service and add the first host"):
            service_group = service.group_config_create(name=self.FIRST_GROUP)
            service_group.host_add(test_host_1)
        with allure.step("Create second group for service and add the first host"):
            service_group_2 = service.group_config_create(name=self.SECOND_GROUP)
            with pytest.raises(ErrorMessage) as e:
                service_group_2.host_add(test_host_1)
            self.check_group_config_error(e)
        with allure.step("Check that 1 group available to add to service group"):
            assert len(service_group_2.host_candidate()) == 1, "One host should be available in service group"
            assert (
                service_group_2.host_candidate()[0].fqdn == self.SECOND_HOST
            ), f"Should be available host '{self.SECOND_HOST}'"

    def test_that_groups_not_allowed_to_intersect_in_component(self, sdk_client_fs, cluster_with_components):
        """Test that groups are not allowed to intersect"""

        service, test_host_1, _ = cluster_with_components
        with allure.step("Create group Configuration group for component and add the first host"):
            component_group = service.component(name=self.FIRST_COMPONENT_NAME).group_config_create(
                name=self.FIRST_GROUP
            )
            component_group.host_add(test_host_1)
        with allure.step("Create second group for component and add the first host"):
            component_group_2 = service.component(name=self.FIRST_COMPONENT_NAME).group_config_create(
                name=self.SECOND_GROUP
            )
            with pytest.raises(ErrorMessage) as e:
                component_group_2.host_add(test_host_1)
            self.check_group_config_error(e)
        with allure.step("Check that 1 group available to add to component group"):
            assert len(component_group_2.host_candidate()) == 1, "One host should be available in component group"
            assert (
                component_group_2.host_candidate()[0].fqdn == self.SECOND_HOST
            ), f"Should be available host '{self.SECOND_HOST}'"
