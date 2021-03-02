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
import allure
import pytest
from adcm_client.objects import Provider, Cluster, Host, ADCMClient
from adcm_pytest_plugin import utils

# pylint: disable=W0611, W0621
from adcm_pytest_plugin.utils import random_string


@pytest.fixture()
def prepared_cluster(sdk_client_fs: ADCMClient) -> Cluster:
    uploaded_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, "locked_when_action_running")
    )
    return uploaded_bundle.cluster_prototype().cluster_create(name=random_string())


@pytest.fixture()
def hostprovider(sdk_client_fs: ADCMClient) -> Provider:
    provider_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, "host_bundle_on_any_level")
    )
    return provider_bundle.provider_prototype().provider_create(random_string())


@pytest.fixture()
def host(hostprovider: Provider) -> Host:
    return hostprovider.host_create(random_string())


def test_cluster_must_be_locked_when_action_running(prepared_cluster: Cluster):
    with allure.step("Run action: lock cluster"):
        prepared_cluster.action_run(name="lock-cluster")
    with allure.step("Check if cluster is locked"):
        prepared_cluster.reread()
        assert prepared_cluster.state == "locked"


def test_run_new_action_on_locked_cluster_must_throws_exception(
    prepared_cluster: Cluster,
):
    with allure.step("Run first action: lock cluster"):
        prepared_cluster.action_run(name="lock-cluster")
    with allure.step("Check that Cluster is locked"):
        assert (
            prepared_cluster.action_list() == []
        ), "Cluster action list not empty. Cluster not locked"


def test_service_in_cluster_must_be_locked_when_cluster_action_running(
    prepared_cluster: Cluster,
):
    with allure.step("Add service and run action: lock cluster"):
        added_service = prepared_cluster.service_add(name="bookkeeper")
        prepared_cluster.action_run(name="lock-cluster")
    with allure.step("Check if service is locked"):
        added_service.reread()
        assert added_service.state == "locked"


def test_host_in_cluster_must_be_locked_when_cluster_action_running(
    prepared_cluster: Cluster, host: Host
):
    with allure.step("Add host and run action: lock cluster"):
        prepared_cluster.host_add(host)
        prepared_cluster.action_run(name="lock-cluster")
    with allure.step("Check if host is locked"):
        prepared_cluster.reread()
        assert prepared_cluster.state == "locked"


def test_host_must_be_locked_when_host_action_running(host):
    with allure.step("Run host action: action locker"):
        host.action_run(name="action-locker")
    with allure.step("Check if host is locked"):
        host.reread()
        assert host.state == "locked"


def test_cluster_must_be_locked_when_located_host_action_running(
    prepared_cluster: Cluster, host: Host
):
    with allure.step("Add host and run action: action locker"):
        prepared_cluster.host_add(host)
        host.action_run(name="action-locker")
    with allure.step("Check if host and cluster are locked"):
        prepared_cluster.reread()
        host.reread()
        assert prepared_cluster.state == "locked"
        assert host.state == "locked"


def test_cluster_service_locked_when_located_host_action_running(
    prepared_cluster: Cluster, host: Host
):
    with allure.step("Add host and service"):
        prepared_cluster.host_add(host)
        added_service = prepared_cluster.service_add(name="bookkeeper")
    with allure.step("Run action: action locker"):
        host.action_run(name="action-locker")
    with allure.step("Check if host, cluster and service are locked"):
        prepared_cluster.reread()
        host.reread()
        added_service.reread()
        assert prepared_cluster.state == "locked"
        assert host.state == "locked"
        assert added_service.state == "locked"


def test_run_service_action_locked_all_objects_in_cluster(
    prepared_cluster: Cluster, host: Host
):
    with allure.step("Add host and service"):
        prepared_cluster.host_add(host)
        added_service = prepared_cluster.service_add(name="bookkeeper")
    with allure.step("Run action: service lock"):
        added_service.action_run(name="service-lock")
    with allure.step("Check if host, cluster and service are locked"):
        prepared_cluster.reread()
        host.reread()
        added_service.reread()
        assert prepared_cluster.state == "locked"
        assert host.state == "locked"
        assert added_service.state == "locked"


def test_cluster_should_be_unlocked_when_ansible_task_killed(prepared_cluster: Cluster):
    with allure.step("Run cluster action: lock terminate"):
        task = prepared_cluster.action_run(name="lock-terminate")
    with allure.step("Check if cluster is locked and then terminate_failed"):
        prepared_cluster.reread()
        assert prepared_cluster.state == "locked"
        task.wait()
        prepared_cluster.reread()
        assert prepared_cluster.state == "terminate_failed"


def test_host_should_be_unlocked_when_ansible_task_killed(
    prepared_cluster: Cluster, host: Host
):
    with allure.step("Add host"):
        prepared_cluster.host_add(host)
    with allure.step("Run action: lock terminate"):
        task = prepared_cluster.action_run(name="lock-terminate")

    with allure.step("Check if host is locked and then created"):
        host.reread()
        assert host.state == "locked"
        task.wait()
        host.reread()
        assert host.state == "created"


def test_service_should_be_unlocked_when_ansible_task_killed(prepared_cluster: Cluster):
    with allure.step("Add service"):
        added_service = prepared_cluster.service_add(name="bookkeeper")
    with allure.step("Run action: lock-terminate"):
        task = prepared_cluster.action_run(name="lock-terminate")
    with allure.step("Check if service is locked and then created"):
        added_service.reread()
        assert added_service.state == "locked"
        task.wait()
        added_service.reread()
        assert added_service.state == "created"


def test_hostprovider_must_be_unlocked_when_his_task_finished(hostprovider: Provider):
    with allure.step("Run action: action locker and create hostprovider"):
        task = hostprovider.action_run(name="action-locker")
    with allure.step("Check if provider is locked and then created"):
        hostprovider.reread()
        assert hostprovider.state == "locked"
        task.wait()
        hostprovider.reread()
        assert hostprovider.state == "created"


def test_host_and_hostprovider_must_be_unlocked_when_his_task_finished(
    hostprovider: Provider, host: Host
):
    with allure.step("Run action: action locker and create hostprovider"):
        task = hostprovider.action_run(name="action-locker")
    with allure.step("Check if provider and host is locked and then created"):
        hostprovider.reread()
        host.reread()
        assert hostprovider.state == "locked"
        assert hostprovider.state == "locked"
        task.wait()
        hostprovider.reread()
        host.reread()
        assert hostprovider.state == "created"
        assert host.state == "created"
