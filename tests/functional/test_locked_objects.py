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
from typing import Union

import allure
import pytest
from adcm_client.objects import (
    Provider,
    Cluster,
    Host,
    ADCMClient,
    Service,
    Task,
    Component,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.asserts import assert_state
from adcm_pytest_plugin.utils import random_string


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    uploaded_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster"))
    return uploaded_bundle.cluster_prototype().cluster_create(name=random_string())


@pytest.fixture()
def host_provider(sdk_client_fs: ADCMClient) -> Provider:
    provider_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "provider"))
    return provider_bundle.provider_prototype().provider_create(random_string())


@pytest.fixture()
def host(host_provider: Provider) -> Host:
    return host_provider.host_create(random_string())


@pytest.fixture()
def complete_cluster(cluster: Cluster, host: Host):
    cluster.host_add(host)
    service = cluster.service_add(name="dummy")
    cluster.hostcomponent_set((host, service.component(name="dummy")))
    return cluster


class TestClusterLock:
    def test_lock_unlock(self, cluster, host):
        """
        Test that cluster locked when action running and unlocked when action ends
        """
        cluster.host_add(host)
        is_free(cluster)
        task = _lock_obj(cluster)
        is_locked(cluster)
        task.wait()
        is_free(cluster)

    def test_down_lock(self, complete_cluster, host, sdk_client_fs):
        """
        Test that cluster lock also locks:
            - all cluster services
            - all service components
            - all hosts with components
        """
        task = _lock_obj(complete_cluster)
        for service in complete_cluster.service_list():
            is_locked(service)
            for component in service.component_list():
                is_locked(component)
        for hc in complete_cluster.hostcomponent():
            is_locked(sdk_client_fs.host(id=hc["host_id"]))
        task.wait()
        for service in complete_cluster.service_list():
            is_free(service)
            for component in service.component_list():
                is_free(component)
        for hc in complete_cluster.hostcomponent():
            is_free(sdk_client_fs.host(id=hc["host_id"]))

    def test_no_horizontal_lock(self, cluster: Cluster):
        """
        Test that no horizontal lock when cluster locked
        """
        second_cluster = cluster.prototype().cluster_create(name=random_string())
        _lock_obj(cluster)
        is_free(second_cluster)


class TestServiceLock:
    def test_lock_unlock(self, cluster, host):
        """
        Test that service locked when action running and unlocked when action ends
        """
        cluster.host_add(host)
        service = cluster.service_add(name="dummy")
        is_free(service)
        task = _lock_obj(service)
        is_locked(service)
        task.wait()
        is_free(service)

    def test_up_lock(self, complete_cluster):
        """
        Test that service lock also locks parent objects:
            - Cluster
        """
        task = _lock_obj(complete_cluster.service(name="dummy"))
        is_locked(complete_cluster)
        task.wait()
        is_free(complete_cluster)

    def test_down_lock(self, complete_cluster, host):
        """
        Test that service lock also locks child objects:
            - Components
            - Hosts
        """
        service = complete_cluster.service(name="dummy")
        task = _lock_obj(service)
        for component in service.component_list():
            is_locked(component)
        is_locked(host)
        task.wait()
        for component in service.component_list():
            is_free(component)
        is_free(host)

    def test_no_horizontal_lock(self, complete_cluster):
        """
        Test that no horizontal lock when service locked
        """
        second_service = complete_cluster.service_add(name="second")
        _lock_obj(complete_cluster.service(name="dummy"))
        is_free(second_service)


class TestComponentLock:
    def test_lock_unlock(self, complete_cluster, host):
        """
        Test that component locked when action running and unlocked when action ends
        """
        service = complete_cluster.service(name="dummy")
        component = service.component(name="dummy")

        is_free(component)
        task = _lock_obj(component)
        task.wait()
        is_free(service)

    def test_up_lock(self, complete_cluster):
        """
        Test that component lock also locks parent objects:
            - Service
            - Cluster
        """
        service = complete_cluster.service(name="dummy")
        task = _lock_obj(service.component(name="dummy"))
        is_locked(service)
        is_locked(complete_cluster)
        task.wait()
        is_free(service)
        is_free(complete_cluster)

    def test_down_lock(self, complete_cluster, host):
        """
        Test that component lock also locks child objects:
            - Host
        """
        task = _lock_obj(complete_cluster.service(name="dummy").component(name="dummy"))
        is_locked(host)
        task.wait()
        is_free(host)

    def test_no_horizontal_lock(self, complete_cluster):
        """
        Test that no horizontal lock when component locked
        """
        service = complete_cluster.service(name="dummy")
        _lock_obj(service.component(name="dummy"))
        is_free(service.component(name="second"))


class TestHostLock:
    def test_lock_unlock(self, host):
        """
        Test that host locked when action running and unlocked when action ends
        """
        is_free(host)
        task = _lock_obj(host)
        is_locked(host)
        task.wait()
        is_free(host)

    def test_up_lock(self, complete_cluster, host_provider, host):
        """
        Test that host lock also locks parent objects:
            - Component
            - Service
            - Cluster
        """
        service = complete_cluster.service(name="dummy")
        component = service.component(name="dummy")
        task = _lock_obj(host)
        is_locked(component)
        is_locked(service)
        is_locked(complete_cluster)
        task.wait()
        is_free(component)
        is_free(service)
        is_free(complete_cluster)

    def test_no_horizontal_lock(self, host_provider, host):
        """
        Test that no horizontal lock when host locked
        """
        second_host = host_provider.host_create(fqdn=random_string())
        _lock_obj(host)
        is_free(second_host)


class TestHostProviderLock:
    def test_lock_unlock(self, host_provider):
        """
        Test that host provider locked when action running and unlocked when action ends
        """
        is_free(host_provider)
        task = _lock_obj(host_provider)
        is_locked(host_provider)
        task.wait()
        is_free(host_provider)

    def test_down_lock(self, host_provider, host):
        """
        Test that provider lock also locks child objects:
            - Host
        """
        task = _lock_obj(host_provider)
        is_locked(host)
        task.wait()
        is_free(host)

    def test_no_horizontal_lock(self, host_provider):
        """
        Test that no horizontal lock when host locked
        """
        second_provider = host_provider.prototype().provider_create(name=random_string())
        _lock_obj(host_provider)
        is_free(second_provider)


def test_cluster_should_be_unlocked_when_ansible_task_killed(cluster: Cluster):
    with allure.step("Run cluster action: lock-terminate for cluster"):
        task = cluster.action(name="lock-terminate").run()
    is_locked(cluster)
    task.wait()
    assert_state(cluster, "terminate_failed")


def test_host_should_be_unlocked_when_ansible_task_killed(complete_cluster: Cluster, host: Host):
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()

    is_locked(host)
    task.wait()
    is_free(host)


def test_service_should_be_unlocked_when_ansible_task_killed(complete_cluster: Cluster):
    service = complete_cluster.service(name="dummy")
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()
    is_locked(service)
    task.wait()
    is_free(service)


def _lock_obj(obj) -> Task:
    """
    Run action lock on object
    """
    with allure.step(f"Lock {obj.__class__.__name__}"):
        return obj.action(name="lock").run()


def is_locked(obj: Union[Cluster, Service, Component, Provider, Host]):
    """
    Assert that object state is 'locked' and action list is empty
    """

    with allure.step(f"Assert that {obj.__class__.__name__} is locked"):
        assert_state(obj=obj, state="locked")
        assert (
            obj.action_list() == []
        ), f"{obj.__class__.__name__} action list isn't empty. {obj.__class__.__name__} not locked"


def is_free(obj: Union[Cluster, Service, Component, Provider, Host]):
    """
    Assert that object state is 'created' and action list isn't empty
    """
    with allure.step(f"Assert that {obj.__class__.__name__} is free"):
        assert_state(obj, state="created")
        assert obj.action_list(), (
            f"{obj.__class__.__name__} action list is empty. "
            f"Actions should be available for unlocked objects"
        )
