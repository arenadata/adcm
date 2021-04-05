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
    uploaded_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, "cluster")
    )
    return uploaded_bundle.cluster_prototype().cluster_create(name=random_string())


@pytest.fixture()
def host_provider(sdk_client_fs: ADCMClient) -> Provider:
    provider_bundle = sdk_client_fs.upload_from_fs(
        utils.get_data_dir(__file__, "provider")
    )
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
        assert_state(cluster, "created")
        task = _lock_obj(cluster)
        _check_that_object_is_locked(cluster)
        task.wait()
        assert_state(cluster, "created")

    def test_down_lock(self, complete_cluster, host, sdk_client_fs):
        """
        Test that cluster lock also locks:
            - all cluster services
            - all service components
            - all hosts with components
        """
        task = _lock_obj(complete_cluster)
        for service in complete_cluster.service_list():
            _check_that_object_is_locked(service)
            for component in service.component_list():
                _check_that_object_is_locked(component)
        for hc in complete_cluster.hostcomponent():
            _check_that_object_is_locked(sdk_client_fs.host(id=hc["host_id"]))
        task.wait()
        for service in complete_cluster.service_list():
            assert_state(service, "created")
            for component in service.component_list():
                assert_state(component, "created")
        for hc in complete_cluster.hostcomponent():
            assert_state(sdk_client_fs.host(id=hc["host_id"]), "created")

    def test_no_horizontal_lock(self, cluster: Cluster):
        """
        Test that no horizontal lock when cluster locked
        """
        second_cluster = cluster.prototype().cluster_create(name=random_string())
        _lock_obj(cluster)
        assert_state(second_cluster, "created")


class TestServiceLock:
    def test_lock_unlock(self, cluster, host):
        """
        Test that service locked when action running and unlocked when action ends
        """
        cluster.host_add(host)
        service = cluster.service_add(name="dummy")
        assert_state(service, "created")
        task = _lock_obj(service)
        _check_that_object_is_locked(service)
        task.wait()
        assert_state(service, "created")

    def test_up_lock(self, complete_cluster):
        """
        Test that service lock also locks parent objects:
            - Cluster
        """
        task = _lock_obj(complete_cluster.service(name="dummy"))
        _check_that_object_is_locked(complete_cluster)
        task.wait()
        assert_state(complete_cluster, "created")

    def test_down_lock(self, complete_cluster, host):
        """
        Test that service lock also locks child objects:
            - Components
            - Hosts
        """
        service = complete_cluster.service(name="dummy")
        task = _lock_obj(service)
        for component in service.component_list():
            _check_that_object_is_locked(component)
        _check_that_object_is_locked(host)
        task.wait()
        for component in service.component_list():
            assert_state(component, "created")
        assert_state(host, "created")

    def test_no_horizontal_lock(self, complete_cluster):
        """
        Test that no horizontal lock when service locked
        """
        second_service = complete_cluster.service_add(name="second")
        _lock_obj(complete_cluster.service(name="dummy"))
        assert_state(second_service, "created")


class TestComponentLock:
    def test_lock_unlock(self, complete_cluster, host):
        """
        Test that component locked when action running and unlocked when action ends
        """
        service = complete_cluster.service(name="dummy")
        component = service.component(name="dummy")

        assert_state(component, "created")
        task = _lock_obj(component)
        task.wait()
        assert_state(service, "created")

    def test_up_lock(self, complete_cluster):
        """
        Test that component lock also locks parent objects:
            - Service
            - Cluster
        """
        service = complete_cluster.service(name="dummy")
        task = _lock_obj(service.component(name="dummy"))
        _check_that_object_is_locked(service)
        _check_that_object_is_locked(complete_cluster)
        task.wait()
        assert_state(service, "created")
        assert_state(complete_cluster, "created")

    def test_down_lock(self, complete_cluster, host):
        """
        Test that component lock also locks child objects:
            - Host
        """
        task = _lock_obj(complete_cluster.service(name="dummy").component(name="dummy"))
        _check_that_object_is_locked(host)
        task.wait()
        assert_state(host, "created")

    def test_no_horizontal_lock(self, complete_cluster):
        """
        Test that no horizontal lock when component locked
        """
        service = complete_cluster.service(name="dummy")
        _lock_obj(service.component(name="dummy"))
        assert_state(service.component(name="second"), "created")


class TestHostLock:
    def test_lock_unlock(self, host):
        """
        Test that host locked when action running and unlocked when action ends
        """
        assert_state(host, "created")
        task = _lock_obj(host)
        _check_that_object_is_locked(host)
        task.wait()
        assert_state(host, "created")

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
        _check_that_object_is_locked(component)
        _check_that_object_is_locked(service)
        _check_that_object_is_locked(complete_cluster)
        task.wait()
        assert_state(component, "created")
        assert_state(service, "created")
        assert_state(complete_cluster, "created")

    def test_no_horizontal_lock(self, host_provider, host):
        """
        Test that no horizontal lock when host locked
        """
        second_host = host_provider.host_create(fqdn=random_string())
        _lock_obj(host)
        assert_state(second_host, "created")


class TestHostProviderLock:
    def test_lock_unlock(self, host_provider):
        """
        Test that host provider locked when action running and unlocked when action ends
        """
        assert_state(host_provider, "created")
        task = _lock_obj(host_provider)
        _check_that_object_is_locked(host_provider)
        task.wait()
        assert_state(host_provider, "created")

    def test_down_lock(self, host_provider, host):
        """
        Test that provider lock also locks child objects:
            - Host
        """
        task = _lock_obj(host_provider)
        _check_that_object_is_locked(host)
        task.wait()
        assert_state(host, "created")

    def test_no_horizontal_lock(self, host_provider):
        """
        Test that no horizontal lock when host locked
        """
        second_provider = host_provider.prototype().provider_create(
            name=random_string()
        )
        _lock_obj(host_provider)
        assert_state(second_provider, "created")


def test_cluster_should_be_unlocked_when_ansible_task_killed(cluster: Cluster):
    with allure.step("Run cluster action: lock-terminate for cluster"):
        task = cluster.action(name="lock-terminate").run()
    _check_that_object_is_locked(cluster)
    task.wait()
    assert_state(cluster, "terminate_failed")


def test_host_should_be_unlocked_when_ansible_task_killed(
    complete_cluster: Cluster, host: Host
):
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()

    _check_that_object_is_locked(host)
    task.wait()
    assert_state(host, "created")


def test_service_should_be_unlocked_when_ansible_task_killed(complete_cluster: Cluster):
    service = complete_cluster.service(name="dummy")
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()
    _check_that_object_is_locked(service)
    task.wait()
    assert_state(service, "created")


def _lock_obj(obj) -> Task:
    """
    Run action lock on object
    """
    with allure.step(f"Lock {obj.__class__.__name__}"):
        return obj.action(name="lock").run()


def _check_that_object_is_locked(
    obj: Union[Cluster, Service, Component, Provider, Host]
):
    """
    Assert that object state is 'locked' and action list is empty
    """

    with allure.step(f"Assert that {obj.__class__.__name__} is locked"):
        obj.reread()
        assert_state(obj=obj, state="locked")
        assert (
            obj.action_list() == []
        ), f"{obj.__class__.__name__} action list isn't empty. {obj.__class__.__name__} not locked"
