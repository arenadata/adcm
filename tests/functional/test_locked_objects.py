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

"""Tests for ADCM objects locks"""

from typing import List, Tuple, Union

import allure
import pytest
from _pytest.outcomes import Failed
from adcm_client.base import ObjectNotFound
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Component,
    Host,
    Provider,
    Service,
    Task,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.asserts import assert_state
from adcm_pytest_plugin.utils import catch_failed, random_string
from coreapi.exceptions import ErrorMessage

LOCK_ACTION_NAMES = ["lock", "lock_multijob"]


@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload dummy cluster bundle and create cluster object
    """
    uploaded_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "cluster"))
    return uploaded_bundle.cluster_prototype().cluster_create(name=random_string())


@pytest.fixture()
def host_provider(sdk_client_fs: ADCMClient) -> Provider:
    """
    Upload dummy host provider bundle and create provider object
    """
    provider_bundle = sdk_client_fs.upload_from_fs(utils.get_data_dir(__file__, "provider"))
    return provider_bundle.provider_prototype().provider_create(random_string())


@pytest.fixture()
def host(host_provider: Provider) -> Host:
    """
    Create dummy host
    """
    return host_provider.host_create(random_string())


@pytest.fixture()
def complete_cluster(cluster: Cluster, host: Host) -> Cluster:
    """
    Prepare dummy cluster with service and component on host
    """
    cluster.host_add(host)
    service = cluster.service_add(name="first_service")
    cluster.hostcomponent_set((host, service.component(name="first_service_component_1")))
    return cluster


@pytest.fixture()
def cluster_with_two_hosts(cluster: Cluster, host_provider: Provider) -> Tuple[Cluster, List[Host]]:
    """
    Prepare dummy cluster with two hosts
    """
    hosts = []
    for i in range(2):
        host = host_provider.host_create(f"host-{i}")
        hosts.append(host)
        cluster.host_add(host)
    return cluster, hosts


@pytest.mark.parametrize("lock_action", LOCK_ACTION_NAMES)
class TestClusterLock:
    """Tests for cluster locks"""

    def test_lock_unlock(self, cluster: Cluster, host: Host, lock_action):
        """
        Test that cluster locked when action running and unlocked when action ends
        """
        cluster.host_add(host)
        is_free(cluster)
        task = _lock_obj(cluster, lock_action)
        is_locked(cluster)
        task.wait()
        is_free(cluster)

    def test_down_lock(self, complete_cluster: Cluster, sdk_client_fs: ADCMClient, lock_action):
        """
        Test that cluster lock also locks:
            - all cluster services
            - all service components
            - all hosts with components
        """
        task = _lock_obj(complete_cluster, lock_action)
        for service in complete_cluster.service_list():
            is_locked(service)
            for component in service.component_list():
                is_locked(component)
        for hc_map in complete_cluster.hostcomponent():
            is_locked(sdk_client_fs.host(id=hc_map["host_id"]))
        task.wait()
        for service in complete_cluster.service_list():
            is_free(service)
            for component in service.component_list():
                is_free(component)
        for hc_map in complete_cluster.hostcomponent():
            is_free(sdk_client_fs.host(id=hc_map["host_id"]))

    def test_no_horizontal_lock(self, cluster: Cluster, lock_action):
        """
        Test that no horizontal lock when cluster locked
        """
        second_cluster = cluster.prototype().cluster_create(name=random_string())
        _lock_obj(cluster, lock_action)
        is_free(second_cluster)


@pytest.mark.parametrize("lock_action", LOCK_ACTION_NAMES)
class TestServiceLock:
    """Tests for service locks"""

    def test_lock_unlock(self, cluster: Cluster, host: Host, lock_action):
        """
        Test that service locked when action running and unlocked when action ends
        """
        cluster.host_add(host)
        service = cluster.service_add(name="first_service")
        is_free(service)
        task = _lock_obj(service, lock_action)
        is_locked(service)
        task.wait()
        is_free(service)

    def test_up_lock(self, complete_cluster: Cluster, lock_action):
        """
        Test that service lock also locks parent objects:
            - Cluster
        """
        task = _lock_obj(complete_cluster.service(name="first_service"), lock_action)
        is_locked(complete_cluster)
        task.wait()
        is_free(complete_cluster)

    def test_down_lock(self, complete_cluster: Cluster, host: Host, lock_action):
        """
        Test that service lock also locks child objects:
            - Components
            - Hosts
        """
        service = complete_cluster.service(name="first_service")
        task = _lock_obj(service, lock_action)
        for component in service.component_list():
            is_locked(component)
        is_locked(host)
        task.wait()
        for component in service.component_list():
            is_free(component)
        is_free(host)

    def test_no_horizontal_lock(self, complete_cluster: Cluster, lock_action):
        """
        Test that no horizontal lock when service locked
        """
        second_service = complete_cluster.service_add(name="second_service")
        _lock_obj(complete_cluster.service(name="first_service"), lock_action)
        is_free(second_service)


@pytest.mark.parametrize("lock_action", LOCK_ACTION_NAMES)
class TestComponentLock:
    """Tests for component locks"""

    def test_lock_unlock(self, complete_cluster: Cluster, lock_action):
        """
        Test that component locked when action running and unlocked when action ends
        """
        service = complete_cluster.service(name="first_service")
        component = service.component(name="first_service_component_1")

        is_free(component)
        task = _lock_obj(component, lock_action)
        task.wait()
        is_free(service)

    def test_up_lock(self, complete_cluster: Cluster, lock_action):
        """
        Test that component lock also locks parent objects:
            - Service
            - Cluster
        """
        service = complete_cluster.service(name="first_service")
        task = _lock_obj(service.component(name="first_service_component_1"), lock_action)
        is_locked(service)
        is_locked(complete_cluster)
        task.wait()
        is_free(service)
        is_free(complete_cluster)

    def test_down_lock(self, complete_cluster: Cluster, host: Host, lock_action):
        """
        Test that component lock also locks child objects:
            - Host
        """
        task = _lock_obj(
            complete_cluster.service(name="first_service").component(name="first_service_component_1"),
            lock_action,
        )
        is_locked(host)
        task.wait()
        is_free(host)

    def test_no_horizontal_lock(self, complete_cluster: Cluster, lock_action):
        """
        Test that no horizontal lock when component locked
        """
        service = complete_cluster.service(name="first_service")
        _lock_obj(service.component(name="first_service_component_1"), lock_action)
        is_free(service.component(name="first_service_component_2"))


@pytest.mark.parametrize("lock_action", LOCK_ACTION_NAMES)
class TestHostLock:
    """Tests for host locks"""

    def test_lock_unlock(self, host: Host, lock_action):
        """
        Test that host locked when action running and unlocked when action ends
        """
        is_free(host)
        task = _lock_obj(host, lock_action)
        is_locked(host)
        task.wait()
        is_free(host)

    def test_up_lock(self, complete_cluster: Cluster, host: Host, lock_action):
        """
        Test that host lock also locks parent objects:
            - Component
            - Service
            - Cluster
        """
        service = complete_cluster.service(name="first_service")
        component = service.component(name="first_service_component_1")
        task = _lock_obj(host, lock_action)
        is_locked(component)
        is_locked(service)
        is_locked(complete_cluster)
        task.wait()
        is_free(component)
        is_free(service)
        is_free(complete_cluster)

    def test_no_horizontal_lock(self, host_provider: Provider, host: Host, lock_action):
        """
        Test that no horizontal lock when host locked
        """
        second_host = host_provider.host_create(fqdn=random_string())
        _lock_obj(host, lock_action)
        is_free(second_host)


@pytest.mark.parametrize("lock_action", LOCK_ACTION_NAMES)
class TestHostProviderLock:
    """Tests for provider locks"""

    def test_lock_unlock(self, host_provider: Provider, lock_action):
        """
        Test that host provider locked when action running and unlocked when action ends
        """
        is_free(host_provider)
        task = _lock_obj(host_provider, lock_action)
        is_locked(host_provider)
        task.wait()
        is_free(host_provider)

    def test_down_lock(self, host_provider: Provider, host: Host, lock_action):
        """
        Test that provider lock also locks child objects:
            - Host
        """
        task = _lock_obj(host_provider, lock_action)
        is_locked(host)
        task.wait()
        is_free(host)

    def test_no_horizontal_lock(self, host_provider: Provider, lock_action):
        """
        Test that no horizontal lock when host locked
        """
        second_provider = host_provider.prototype().provider_create(name=random_string())
        _lock_obj(host_provider, lock_action)
        is_free(second_provider)


def test_cluster_should_be_unlocked_when_ansible_task_killed(cluster: Cluster):
    """
    Test cluster unlock if ansible task killed
    """
    with allure.step("Run cluster action: lock-terminate for cluster"):
        task = cluster.action(name="lock-terminate").run()
    is_locked(cluster)
    task.wait()
    assert_state(cluster, "terminate_failed")


def test_host_should_be_unlocked_when_ansible_task_killed(complete_cluster: Cluster, host: Host):
    """
    Test host unlock if ansible task killed
    """
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()

    is_locked(host)
    task.wait()
    is_free(host)


def test_service_should_be_unlocked_when_ansible_task_killed(complete_cluster: Cluster):
    """Test that service is unlocked if ansible task is killed"""
    service = complete_cluster.service(name="first_service")
    with allure.step("Run action: lock-terminate for cluster"):
        task = complete_cluster.action(name="lock-terminate").run()
    is_locked(service)
    task.wait()
    is_free(service)


@pytest.mark.parametrize("adcm_object", ["Cluster", "Service", "Component"])
@pytest.mark.parametrize(
    "expand_action",
    ["expand_success", "expand_failed", "expand_success_multijob", "expand_failed_multijob"],
)
def test_host_should_be_unlocked_after_expand_action(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    adcm_object: str,
    expand_action: str,
):
    """
    Test host should be unlocked after expand action (success or failed) on ADCM object
    """
    action_args = {"obj_for_action": None}
    cluster, _ = cluster_with_two_hosts
    first_service = cluster.service_add(name="first_service")
    if adcm_object == "Cluster":
        action_args["obj_for_action"] = cluster
    elif adcm_object == "Service":
        action_args["obj_for_action"] = first_service
    elif adcm_object == "Component":
        action_args["obj_for_action"] = first_service.component(name="first_service_component_1")

    _test_expand_object_action(cluster_with_two_hosts, action_name=expand_action, **action_args)


@pytest.mark.parametrize("adcm_object", ["Cluster", "Service", "Component"])
@pytest.mark.parametrize(
    "shrink_action",
    ["shrink_success", "shrink_failed", "shrink_success_multijob", "shrink_failed_multijob"],
)
def test_host_should_be_unlocked_after_shrink_action(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    adcm_object: str,
    shrink_action: str,
):
    """Test that host is unlocked after shrink action"""
    action_args = {"obj_for_action": None}
    cluster, _ = cluster_with_two_hosts
    first_service = cluster.service_add(name="first_service")
    if adcm_object == "Cluster":
        action_args["obj_for_action"] = cluster
    elif adcm_object == "Service":
        action_args["obj_for_action"] = first_service
    elif adcm_object == "Component":
        action_args["obj_for_action"] = first_service.component(name="first_service_component_1")

    _test_shrink_object_action(cluster_with_two_hosts, action_name=shrink_action, **action_args)


@pytest.mark.parametrize("adcm_object", ["Cluster", "Service", "Component"])
@pytest.mark.parametrize(
    "expand_action",
    [
        "expand_success",
        "expand_failed",
    ],
)
def test_expand_on_clean_locked_host(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    adcm_object: str,
    expand_action: str,
):
    """
    Test attempt to expand component on locked host.
    Action must end with "...locked host..." API error
    """
    obj_for_action = None
    cluster, hosts = cluster_with_two_hosts
    host1, host2 = hosts

    dummy_service = cluster.service_add(name="first_service")
    dummy_component = dummy_service.component(name="first_service_component_1")
    cluster.hostcomponent_set(
        (host1, dummy_component),
    )
    _lock_obj(host2, duration=30)

    if adcm_object == "Cluster":
        obj_for_action = cluster
    elif adcm_object == "Service":
        obj_for_action = dummy_service
    elif adcm_object == "Component":
        obj_for_action = dummy_component

    with allure.step(f"Run {obj_for_action.__class__.__name__} action: expand on clean locked host"):
        with catch_failed(Failed, "Expand action should throw an API error as Host is locked"):
            with pytest.raises(ErrorMessage, match="is locked"):
                obj_for_action.action(
                    name=expand_action,
                ).run(
                    hc=[
                        {
                            "host_id": host1.host_id,
                            "service_id": dummy_component.service_id,
                            "component_id": dummy_component.component_id,
                        },
                        {
                            "host_id": host2.host_id,
                            "service_id": dummy_component.service_id,
                            "component_id": dummy_component.component_id,
                        },
                    ]
                ).wait()


@pytest.mark.parametrize(
    "action_with_ansible_plugin",
    [
        "delete_service",
        "hc_action_remove",
        "hc_action_add",
        "hc_and_host_remove",
        "delete_service_failed",
        "hc_action_remove_failed",
        "hc_action_add_failed",
        "hc_and_host_remove_failed",
        # MULTIJOBS
        "delete_service_multijob",
        "hc_action_remove_multijob",
        "hc_action_add_multijob",
        "delete_service_multijob_failed",
        "hc_action_remove_multijob_failed",
        "hc_action_add_multijob_failed",
    ],
)
def test_host_should_be_unlocked_after_service_action_with_ansible_plugin(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    action_with_ansible_plugin: str,
):
    """
    Test host should be unlocked after Service action with ansible plugin (simple job or multi-job)
    """
    cluster, _ = cluster_with_two_hosts
    dummy_service = cluster.service_add(name="first_service")
    _test_object_action_with_ansible_plugin(
        cluster_with_two_hosts, action_name=action_with_ansible_plugin, obj_for_action=dummy_service
    )


@pytest.mark.parametrize(
    "action_with_ansible_plugin",
    [
        "hc_action_remove",
        "hc_action_add",
        "hc_and_host_remove",
        "hc_action_remove_failed",
        "hc_action_add_failed",
        "hc_and_host_remove_failed",
        # MULTIJOBS
        "hc_action_remove_multijob",
        "hc_action_add_multijob",
        "hc_action_remove_multijob_failed",
        "hc_action_add_multijob_failed",
    ],
)
def test_host_should_be_unlocked_after_cluster_action_with_ansible_plugin(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    action_with_ansible_plugin: str,
):
    """
    Test host should be unlocked after Cluster action with ansible plugin (simple job or multi-job)
    """
    cluster, _ = cluster_with_two_hosts
    _test_object_action_with_ansible_plugin(
        cluster_with_two_hosts, action_name=action_with_ansible_plugin, obj_for_action=cluster
    )


@pytest.mark.parametrize("adcm_object", ["Cluster", "Service", "Component"])
@pytest.mark.parametrize(
    "host_action_postfix",
    [
        "host_action_success",
        "host_action_failed",
        "host_action_multijob_success",
        "host_action_multijob_failed",
    ],
)
@pytest.mark.parametrize(
    "run_on_host",
    [
        "host-with-two-components",
        "host-with-one-component",
        "host-with-different-services",
    ],
)
def test_host_should_be_unlocked_after_host_action(
    cluster: Cluster,
    host_provider: Provider,
    adcm_object: str,
    host_action_postfix: str,
    run_on_host: str,
):
    """Test that host is unlocked after host action"""
    action_name = f"{adcm_object}_{host_action_postfix}"
    first_service = cluster.service_add(name="first_service")
    second_service = cluster.service_add(name="second_service")

    host_with_two_components = host_provider.host_create("host-with-two-components")
    host_with_one_component = host_provider.host_create("host-with-one-component")
    host_with_different_services = host_provider.host_create("host-with-different-services")

    cluster_hosts = [
        host_with_two_components,
        host_with_one_component,
        host_with_different_services,
    ]
    for host in cluster_hosts:
        cluster.host_add(host)

    cluster.hostcomponent_set(
        (host_with_two_components, second_service.component(name="second_service_component_1")),
        (host_with_two_components, second_service.component(name="second_service_component_2")),
        (host_with_one_component, second_service.component(name="second_service_component_1")),
        (host_with_different_services, first_service.component(name="first_service_component_2")),
        (host_with_different_services, second_service.component(name="second_service_component_1")),
    )
    host = cluster.host(fqdn=run_on_host)
    with allure.step(f"Run action {action_name} on {host}"):
        host.action(name=action_name).run().wait(timeout=30)
    for host in cluster_hosts:
        is_free(host)


def _test_expand_object_action(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    obj_for_action: Union[Cluster, Service, Component],
    action_name: str,
):
    """
    Common method for expand object tests
    """
    cluster, hosts = cluster_with_two_hosts
    host1, host2 = hosts
    first_service = cluster.service(name="first_service")
    first_service_component = first_service.component(name="first_service_component_1")
    cluster.hostcomponent_set(
        (host1, first_service_component),
    )
    with allure.step(f"Run {obj_for_action.__class__.__name__} action: expand component from host"):
        obj_for_action.action(
            name=action_name,
        ).run(
            hc=[
                {
                    "host_id": host1.host_id,
                    "service_id": first_service_component.service_id,
                    "component_id": first_service_component.component_id,
                },
                {
                    "host_id": host2.host_id,
                    "service_id": first_service_component.service_id,
                    "component_id": first_service_component.component_id,
                },
            ]
        ).wait()
    is_free(host1)
    is_free(host2)


def _test_shrink_object_action(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    obj_for_action: Union[Cluster, Service, Component],
    action_name: str,
):
    """
    Common method for shrink object tests
    """
    cluster, hosts = cluster_with_two_hosts
    host1, host2 = hosts
    first_service_component, second_service_component = _cluster_with_components(cluster, hosts)
    with allure.step(f"Run {obj_for_action.__class__.__name__} action: shrink component from host"):
        obj_for_action.action(
            name=action_name,
        ).run(
            hc=[
                {
                    "host_id": host1.host_id,
                    "service_id": second_service_component.service_id,
                    "component_id": second_service_component.component_id,
                },
                {
                    "host_id": host2.host_id,
                    "service_id": first_service_component.service_id,
                    "component_id": first_service_component.component_id,
                },
            ]
        ).wait()
    is_free(host1)
    is_free(host2)


def _test_object_action_with_ansible_plugin(
    cluster_with_two_hosts: Tuple[Cluster, List[Host]],
    obj_for_action: Union[Cluster, Service, Component],
    action_name: str,
):
    """
    Common method for object action with ansible plugin
    """
    cluster, hosts = cluster_with_two_hosts
    host1, host2 = hosts
    _cluster_with_components(cluster, hosts)
    with allure.step(f"Run {obj_for_action.__class__.__name__} action {action_name}"):
        obj_for_action.action(name=action_name).run().wait(timeout=30)

    is_free(host1)
    is_free(host2)


def _cluster_with_components(cluster: Cluster, hosts: List[Host]):
    host1, host2 = hosts
    try:
        first_service = cluster.service(name="first_service")
    except ObjectNotFound:
        first_service = cluster.service_add(name="first_service")
    second_service = cluster.service_add(name="second_service")
    first_service_component = first_service.component(name="first_service_component_1")
    second_service_component = second_service.component(name="second_service_component_1")
    cluster.hostcomponent_set(
        (host1, first_service_component),
        (host1, second_service_component),
        (host2, first_service_component),
    )
    return first_service_component, second_service_component


def _lock_obj(
    obj: Union[Cluster, Service, Component, Provider, Host],
    lock_action: str = "lock",
    duration: int = 5,
) -> Task:
    """
    Run action lock on object
    """
    with allure.step(f"Lock {obj.__class__.__name__} with {duration} sec duration"):
        return obj.action(name=lock_action).run(config={"duration": duration})


def is_locked(obj: Union[Cluster, Service, Component, Provider, Host]):
    """
    Assert that object state is 'locked' and action list is empty
    """

    with allure.step(f"Assert that {obj.__class__.__name__} is locked"):
        assert_state(obj=obj, state="created")
        assert obj.locked is True, f"{obj.__class__.__name__} should be locked"
        assert (
            obj.action_list() == []
        ), f"{obj.__class__.__name__} action list isn't empty. {obj.__class__.__name__} not locked"


def is_free(obj: Union[Cluster, Service, Component, Provider, Host]):
    """
    Assert that object state is 'created' and action list isn't empty
    """
    with allure.step(f"Assert that {obj.__class__.__name__} is free"):
        assert_state(obj=obj, state="created")
        assert obj.locked is False, f"{obj.__class__.__name__} should be available"
        assert obj.action_list(), (
            f"{obj.__class__.__name__} action list is empty. " f"Actions should be available for unlocked objects"
        )
