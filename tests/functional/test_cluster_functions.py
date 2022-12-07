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

"""Tests for cluster functions"""

# pylint: disable=redefined-outer-name, protected-access

import allure
import coreapi
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.utils import get_data_dir
from tests.library import errorcodes as err

DEFAULT_CLUSTER_BUNDLE_PATH = get_data_dir(__file__, "cluster_simple")
DEFAULT_PROVIDER_BUNDLE_PATH = get_data_dir(__file__, "hostprovider_bundle")


@pytest.fixture()
def cluster_bundle(request, sdk_client_fs: ADCMClient) -> Bundle:
    """Upload cluster bundle"""
    bundle_path = request.param if hasattr(request, "param") else DEFAULT_CLUSTER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def cluster(cluster_bundle: Bundle) -> Cluster:
    """Create cluster"""
    return cluster_bundle.cluster_create(name=utils.random_string())


@pytest.fixture()
def provider_bundle(request, sdk_client_fs: ADCMClient) -> Bundle:
    """Upload provider bundle"""
    bundle_path = request.param if hasattr(request, "param") else DEFAULT_PROVIDER_BUNDLE_PATH
    return sdk_client_fs.upload_from_fs(bundle_path)


@pytest.fixture()
def provider(provider_bundle: Bundle) -> Provider:
    """Create provider"""
    return provider_bundle.provider_create(name=utils.random_string())


def _check_hosts(actual: Host, expected: Host):
    for prop in ["fqdn", "host_id", "cluster_id"]:
        assert getattr(actual, prop) == getattr(expected, prop)


class TestCluster:
    """Tests for cluster functions"""

    def test_get_cluster_list(self, cluster_bundle: Bundle):
        """Test get cluster list"""
        actual, expected = [], []
        # Create list of clusters and fill expected list
        for name in utils.random_string_list():
            cluster_bundle.cluster_create(name)
            expected.append(name)
        for cluster in cluster_bundle.cluster_list():
            actual.append(cluster.name)
        with allure.step("Check cluster list"):
            assert actual == expected

    def test_creating_cluster_with_name_and_desc(self, cluster_bundle: Bundle):
        """Test create cluster with name and desc"""
        name, description = utils.random_string_list(2)
        cluster = cluster_bundle.cluster_create(name=name, description=description)
        with allure.step("Check created cluster"):
            assert cluster.name == name
            assert cluster.description == description

    @pytest.mark.parametrize(
        "cluster_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "cluster_action_bundle"),
                id="cluster_action_bundle",
            )
        ],
        indirect=True,
    )
    def test_run_cluster_action(self, cluster: Cluster):
        """Test run cluster action"""
        cluster.config_set({"required": 10})
        cluster.service_add(name="ZOOKEEPER")
        result = cluster.action().run()
        with allure.step("Check if status is running"):
            assert result.status == "running"


class TestClusterHost:
    """Test cluster and host functions"""

    def test_adding_host_to_cluster(self, cluster: Cluster, provider: Provider):
        """Test add host to cluster"""
        host = provider.host_create(utils.random_string())
        expected = cluster.host_add(host)
        with allure.step("Get cluster host info"):
            host_list = cluster.host_list()
            assert len(host_list) == 1
            actual = host_list[0]
        with allure.step("Check mapping"):
            _check_hosts(actual, expected)

    def test_get_cluster_hosts_list(self, cluster: Cluster, provider: Provider):
        """Test get cluster hosts list"""
        actual, expected = [], []
        with allure.step("Create host list in cluster"):
            for fqdn in utils.random_string_list():
                host = provider.host_create(fqdn)
                cluster.host_add(host)
                expected.append(host.id)
        for host in cluster.host_list():
            actual.append(host.id)
        with allure.step("Check test data"):
            assert actual == expected

    def test_get_cluster_host_info(self, cluster: Cluster, provider: Provider):
        """Test get cluster host info"""
        host = provider.host_create(utils.random_string())
        with allure.step("Create mapping between cluster and host"):
            expected = cluster.host_add(host)
        with allure.step("Get cluster host info"):
            host.reread()
        with allure.step("Check test results"):
            _check_hosts(host, expected)

    def test_delete_host_from_cluster(self, cluster: Cluster, provider: Provider):
        """Test delete host from cluster"""
        host = provider.host_create(utils.random_string())
        expected = cluster.host_list()
        with allure.step("Create mapping between cluster and host"):
            cluster.host_add(host)
        with allure.step("Deleting host from cluster"):
            cluster.host_delete(host)
        actual = cluster.host_list()
        with allure.step("Check host removed from cluster"):
            assert actual == expected

    def test_host_belong_to_cluster_should_not_deleted(self, cluster: Cluster, provider: Provider):
        """Test that we should be unable to delete host bounded to cluster"""
        host = provider.host_create(utils.random_string())
        cluster.host_add(host)
        with pytest.raises(coreapi.exceptions.ErrorMessage) as e:
            host.delete()
        with allure.step("Check error host belong to cluster"):
            err.HOST_CONFLICT.equal(e, "Host", "belong to cluster")


class TestClusterService:
    """Test cluster ans service functions"""

    def test_cluster_service_create(self, cluster: Cluster):
        """Test create service"""
        expected = cluster.service_add(name="ZOOKEEPER")
        service_list = cluster.service_list()
        assert len(service_list) == 1
        actual = service_list[0]
        with allure.step("Check expected and actual value"):
            assert actual.id == expected.id
            assert actual.name == expected.name

    def test_get_cluster_service_list(self, sdk_client_fs: ADCMClient, cluster: Cluster):
        """Test cluster service list"""
        expected = []
        with allure.step("Create a list of services in the cluster"):
            for prototype in sdk_client_fs.service_prototype_list(bundle_id=cluster.bundle_id):
                service = cluster.service_add(name=prototype.name)
                expected.append(service._data)
        with allure.step("Get a service list in cluster"):
            actual = [x._data for x in cluster.service_list()]
        with allure.step("Check expected and actual value"):
            assert actual == expected

    @pytest.mark.parametrize(
        "cluster_bundle",
        [
            pytest.param(
                get_data_dir(__file__, "cluster_action_bundle"),
                id="cluster_action_bundle",
            )
        ],
        indirect=True,
    )
    def test_cluster_action_runs_task(self, cluster: Cluster):
        """Test run cluster action"""
        cluster.config_set({"required": 10})
        cluster.service_add(name="ZOOKEEPER")
        task = cluster.action(name="check-file-type").run()
        with allure.step("Check if status is running"):
            assert task.status == "running"
