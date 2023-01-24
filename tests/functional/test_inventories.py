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

"""Tests for actions inventory"""

import json
from typing import Optional, Tuple

import allure
import pytest
from _pytest.fixtures import SubRequest
from adcm_client.objects import (
    ADCM,
    ADCMClient,
    Cluster,
    Component,
    Host,
    Provider,
    Service,
)
from adcm_pytest_plugin import utils
from adcm_pytest_plugin.steps.actions import (
    run_cluster_action_and_assert_result,
    run_component_action_and_assert_result,
)
from adcm_pytest_plugin.utils import get_data_dir
from docker.models.containers import Container
from tests.functional.tools import (
    BEFORE_UPGRADE_DEFAULT_STATE,
    compare_inventory_files,
    create_config_group_and_add_host,
    get_inventory_file,
)

# pylint: disable=redefined-outer-name,too-many-locals


HOST_FQDN = "awesome-future"
CLUSTER_NAME = "dumMxpQA"
GROUP_COMPONENT_NAME = "GROUP_BUDDY"
CHANGE_FLOAT = 3.0
CLUSTER_ACTION_NAME = "cluster_action"
CONFIG_TO_CHANGE = {
    "config": {
        "json_field": {"there_is": "no one"},
        "map_field": {"here": "but me"},
        "__main_info": "I'm a very important string, don't touch me",
        "simple_field": 1,
    },
    "attr": {
        "group_keys": {
            "json_field": True,
            "map_field": True,
            "simple_field": False,
            "__main_info": False,
        },
        "custom_group_keys": {
            "json_field": True,
            "map_field": True,
            "simple_field": True,
            "__main_info": False,
        },
    },
}


@allure.title("Create provider")
@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Get dummy provider"""
    bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    return bundle.provider_create(name="test_provider")


@allure.title("Create cluster")
@pytest.fixture()
def cluster(sdk_client_fs: ADCMClient) -> Cluster:
    """Get cluster for inventory check"""
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_inventory_tests"))
    return cluster_bundle.cluster_prototype().cluster_create(CLUSTER_NAME)


@allure.title("Create cluster services and components")
@pytest.fixture()
def cluster_services_components(
    sdk_client_fs: ADCMClient,
) -> tuple[Cluster, Service, Service, Component, Component, Component, Component]:
    """Get cluster for inventory check"""
    cluster_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "check_bundle"))
    cluster = cluster_bundle.cluster_prototype().cluster_create("config_group")
    service_1 = cluster.service_add(name="service_1")
    service_2 = cluster.service_add(name="service_2")
    component1_s1 = service_1.component(name="component_1")
    component2_s1 = service_1.component(name="component_2")
    component1_s2 = service_2.component(name="component_1")
    component2_s2 = service_2.component(name="component_2")
    return cluster, service_1, service_2, component1_s1, component2_s1, component1_s2, component2_s2


def test_two_services_with_components_config_inventory(
    cluster_services_components, provider: Provider, adcm_fs: ADCM, request: SubRequest
):
    """Assert inventory file contents for the cluster with two services and four components"""
    adcm_objects = list(cluster_services_components)
    host = provider.host_create(fqdn=HOST_FQDN)
    (
        cluster,
        _,
        _,
        component1_s1,
        component2_s1,
        component1_s2,
        component2_s2,
    ) = cluster_services_components
    cluster.host_add(host)

    with allure.step("Configure cluster"):
        cluster.hostcomponent_set(
            (host, component1_s1), (host, component2_s1), (host, component1_s2), (host, component2_s2)
        )

    with allure.step("Create config group and set config"):
        for obj in adcm_objects:
            obj_float_name = (
                f"{obj.__class__.__name__.lower()}_some_float" if obj == cluster else f"{obj.display_name}_some_float"
            )
            config_group = create_config_group_and_add_host("config group", obj, host)
            config_group.config_set(
                {"config": {obj_float_name: CHANGE_FLOAT}, "attr": {"group_keys": {obj_float_name: True}}}
            )

    with allure.step("Run action on component object"):
        run_component_action_and_assert_result(component1_s1, CLUSTER_ACTION_NAME)
        path_to_expected_inventory = get_data_dir(__file__, "check_bundle", "cluster-inventory.json")
        compare_inventory_files(adcm=adcm_fs, path_to_expected=path_to_expected_inventory, job_id=1, request=request)


def test_two_services_with_components_config_inventory_without_group(
    cluster_services_components, provider: Provider, adcm_fs: ADCM, request: SubRequest
):
    """Assert inventory file contents for the cluster with two services and four components"""
    adcm_objects = list(cluster_services_components)
    host = provider.host_create(fqdn=HOST_FQDN)
    (
        cluster,
        _,
        _,
        component1_s1,
        component2_s1,
        component1_s2,
        component2_s2,
    ) = cluster_services_components
    cluster.host_add(host)

    with allure.step("Configure cluster"):
        cluster.hostcomponent_set(
            (host, component1_s1), (host, component2_s1), (host, component1_s2), (host, component2_s2)
        )

    with allure.step("Create config group and set config"):
        for obj in adcm_objects[:-1]:
            obj_float_name = (
                f"{obj.__class__.__name__.lower()}_some_float" if obj == cluster else f"{obj.display_name}_some_float"
            )
            config_group = create_config_group_and_add_host("config group", obj, host)
            config_group.config_set(
                {"config": {obj_float_name: CHANGE_FLOAT}, "attr": {"group_keys": {obj_float_name: True}}}
            )

    with allure.step("Run action on component object"):
        run_component_action_and_assert_result(component1_s1, CLUSTER_ACTION_NAME)
        path_to_expected_inventory = get_data_dir(
            __file__, "check_bundle", "cluster-inventory-component-groupless.json"
        )
        compare_inventory_files(adcm=adcm_fs, path_to_expected=path_to_expected_inventory, job_id=1, request=request)


def test_three_hosts_config_inventory(
    cluster_services_components, provider: Provider, adcm_fs: ADCM, request: SubRequest
):
    host_2 = provider.host_create(fqdn="service-host")
    host_3 = provider.host_create(fqdn="component-host")
    (
        cluster,
        service_1,
        service_2,
        component1_s1,
        component2_s1,
        component1_s2,
        component2_s2,
    ) = cluster_services_components
    cluster.host_add(host_2)
    cluster.host_add(host_3)

    with allure.step("Configure cluster"):
        cluster.hostcomponent_set(
            (host_2, component1_s1), (host_3, component2_s1), (host_2, component1_s2), (host_3, component2_s2)
        )

    with allure.step("Create config group and set config"):
        cluster_group = cluster.group_config_create(name="config group")
        cluster_group.host_add(host_2)
        cluster_group.host_add(host_3)
        cluster_group.config_set(
            {"config": {"cluster_some_float": CHANGE_FLOAT}, "attr": {"group_keys": {"cluster_some_float": True}}}
        )
        _create_group_add_host_set_config(adcm_object=service_1, host=host_2)
        _create_group_add_host_set_config(adcm_object=service_2, host=host_3)
        _create_group_add_host_set_config(adcm_object=component1_s1, host=host_2)
        _create_group_add_host_set_config(adcm_object=component2_s1, host=host_3)
        _create_group_add_host_set_config(adcm_object=component1_s2, host=host_2)
        _create_group_add_host_set_config(adcm_object=component2_s2, host=host_3)

    with allure.step("Run action and check inventory"):
        run_cluster_action_and_assert_result(cluster, "cluster_action")
        path_to_expected_inventory = get_data_dir(__file__, "check_bundle", "cluster-inventory-hosts.json")
        compare_inventory_files(adcm=adcm_fs, path_to_expected=path_to_expected_inventory, job_id=1, request=request)


def test_check_inventories_file(cluster: Cluster, provider: Provider, adcm_fs: ADCM, request: SubRequest):
    """Assert inventory file contents for the action"""
    host = provider.host_create(fqdn=HOST_FQDN)
    with allure.step("Configure cluster"):
        service = cluster.service_add(name="zookeeper")
        cluster.host_add(host)
        component = service.component(name=GROUP_COMPONENT_NAME)
        cluster.hostcomponent_set((host, component))
    with allure.step(f"Create config group with {GROUP_COMPONENT_NAME} and change it"):
        config_group = create_config_group_and_add_host("group_name", component, host)
        config_group.config_set(CONFIG_TO_CHANGE)
    with allure.step("Run actions on cluster"):
        run_cluster_action_and_assert_result(cluster, "set_multi_states")
        run_cluster_action_and_assert_result(cluster, "install")
        path_to_expected_inventory = get_data_dir(__file__, "cluster-inventory.json")
        compare_inventory_files(adcm=adcm_fs, path_to_expected=path_to_expected_inventory, job_id=2, request=request)


class TestStateBeforeUpgrade:
    """Test that state before upgrade is correctly presented in inventory.json file"""

    @pytest.fixture()
    def old_cluster(self, sdk_client_fs) -> Cluster:
        """Upload old and new version of cluster, create old one"""
        old_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade", "old"))
        sdk_client_fs.upload_from_fs(get_data_dir(__file__, "upgrade", "new"))
        return old_bundle.cluster_create(name="Test Cluster")

    def test_before_upgrade_in_inventory(self, adcm_fs, old_cluster):
        """Test value of before upgrade state in inventory.json before and after upgrade"""
        with allure.step("Check before_upgrade state before upgrade"):
            task = old_cluster.action(name="do_nothing").run()
            task.wait()
            self.check_before_upgrade_state_equal_to(BEFORE_UPGRADE_DEFAULT_STATE, get_inventory_file(adcm_fs, task.id))
        with allure.step("Check before_upgrade state after upgrade"):
            state_before_upgrade = old_cluster.state
            old_cluster.upgrade().do()
            old_cluster.reread()
            task = old_cluster.action(name="do_nothing").run()
            task.wait()
            self.check_before_upgrade_state_equal_to(state_before_upgrade, get_inventory_file(adcm_fs, task.id))

    def check_before_upgrade_state_equal_to(self, expected_state: Optional[str], inventory: dict):
        """Check that `state` key in inventory dictionary is equal to expected"""
        with utils.catch_failed(KeyError, "Structure of inventory.json file is unexpected"):
            actual_state = inventory["all"]["children"]["CLUSTER"]["vars"]["cluster"]["before_upgrade"]["state"]
        assert (
            actual_state == expected_state
        ), f'Before upgrade state should be "{expected_state}", but actual state is "{actual_state}"'


class TestHostInMultipleConfigGroups:
    """Test inventory generation when one host belongs to more than on config group"""

    @pytest.fixture()
    def hosts(self, provider) -> Tuple[Host, Host]:
        """Create 2 hosts"""
        return provider.host_create("host-1"), provider.host_create("host-2")

    @pytest.fixture()
    def cluster_with_components(self, sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service, Component, Component]:
        """Create cluster, add service and return itself, service and components"""
        bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "cluster_with_components"))
        cluster = bundle.cluster_create("Test Cluster")
        service = cluster.service_add(name="test_service")
        return (
            cluster,
            service,
            service.component(name="first_component"),
            service.component(name="second_component"),
        )

    @pytest.fixture()
    def second_service_with_components(self, cluster_with_components) -> Tuple[Service, Component, Component]:
        """Add second service to the cluster"""
        cluster, *_ = cluster_with_components
        service = cluster.service_add(name="second_service")
        return (
            service,
            service.component(name="first_component"),
            service.component(name="second_component"),
        )

    @pytest.fixture()
    def _map_hosts_to_components(self, hosts, cluster_with_components, second_service_with_components) -> None:
        cluster, *_, component_1, component_2 = cluster_with_components
        _, component_3, component_4 = second_service_with_components
        for host in hosts:
            cluster.host_add(host)
        cluster.hostcomponent_set(
            *[(host, component) for host in hosts for component in (component_1, component_2, component_3, component_4)]
        )

    @allure.issue(url="https://tracker.yandex.ru/ADCM-3153")
    @pytest.mark.usefixtures("_map_hosts_to_components")
    def test_hostvars_when_one_host_in_multiple_config_groups(self, hosts, cluster_with_components):
        """Test that hostvars are correct, when one host is in more than one config group"""
        host_1, _ = hosts
        cluster, service, component_1, _ = cluster_with_components
        with allure.step("Create config groups"):
            for obj in (cluster, service, component_1):
                group = create_config_group_and_add_host(f"{obj.__class__.__name__} group", obj, host_1)
                group.config_set({"config": {"param": "changed"}, "attr": {"group_keys": {"param": True}}})
        with allure.step("Run action that checks hostvars"):
            run_cluster_action_and_assert_result(cluster, "check")


def _read_job_inventory(container: Container, job_id: int) -> dict:
    exit_code, out = container.exec_run(["cat", f"/adcm/data/run/{job_id}/inventory.json"])
    content = out.decode("utf-8")
    if exit_code != 0:
        raise ValueError(f"Docker command failed: {content}")
    return json.loads(content)


def _create_group_add_host_set_config(adcm_object: Service | Component, host: Host):
    adcm_obj_group = adcm_object.group_config_create(name="config group")
    adcm_obj_group.host_add(host)
    adcm_obj_group.config_set(
        {
            "config": {f"{adcm_object.display_name}_some_float": CHANGE_FLOAT},
            "attr": {"group_keys": {f"{adcm_object.display_name}_some_float": True}},
        }
    )
