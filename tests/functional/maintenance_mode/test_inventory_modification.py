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

"""
Test inventory modification after host has entered maintenance mode
"""

import itertools
from typing import Set, Tuple

import allure
import pytest
from adcm_client.objects import Action, ADCMClient, Cluster, Component, GroupConfig, Host, Service
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.utils import get_or_add_service

from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    BUNDLES_DIR,
    DEFAULT_SERVICE_NAME,
    FIRST_COMPONENT,
    MM_IS_OFF,
    MM_IS_ON,
    SECOND_COMPONENT,
    add_hosts_to_cluster,
    set_maintenance_mode,
    turn_mm_on,
)
from tests.functional.maintenance_mode.test_hosts_behavior import ACTION_ALLOWED_IN_MM
from tests.functional.tools import (
    build_hc_for_hc_acl_action,
    create_config_group_and_add_host,
    get_inventory_file,
    get_object_represent,
)
from tests.library.assertions import sets_are_equal

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

DEFAULT_ACTION_NAME = "default_action"
HC_ACL_SERVICE_NAME = "hc_acl_service"

DEFAULT_SERVICE_COMPONENT_MM_BUNDLE = "cluster_mm_allowed"


@pytest.fixture(params=[pytest.param(DEFAULT_SERVICE_NAME, id="default_service")])
def cluster_with_hc_set(request, cluster_with_mm, hosts) -> Cluster:
    """
    Add 4 hosts to cluster
    first_component is placed on 4 hosts
    second_component on 2 hosts
    """
    service_name = request.param
    hosts_in_cluster = hosts[:4]
    service = get_or_add_service(cluster_with_mm, service_name)
    first_component = service.component(name=FIRST_COMPONENT)
    second_component = service.component(name=SECOND_COMPONENT)
    for host in hosts_in_cluster:
        cluster_with_mm.host_add(host)
    cluster_with_mm.hostcomponent_set(
        *[(host, first_component) for host in hosts_in_cluster],
        *[(host, second_component) for host in hosts_in_cluster[:2]],
    )
    return cluster_with_mm


@pytest.fixture(params=[pytest.param(DEFAULT_SERVICE_COMPONENT_MM_BUNDLE, id="default_cluster")])
def cluster_with_service_component_mm(
    request, sdk_client_fs, hosts
) -> tuple[Cluster, Service, Component, Component, Host, Host]:
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / request.param)
    cluster = bundle.cluster_create("Cluster with allowed MM")
    service = cluster.service_add(name="test_service")
    first_component = service.component(name="first_component")
    second_component = service.component(name="second_component")
    host_1, host_2, *_ = hosts
    cluster.hostcomponent_set((cluster.host_add(host_1), first_component), (cluster.host_add(host_2), second_component))
    return cluster, service, first_component, second_component, host_1, host_2


@pytest.fixture()
def config_groups(cluster_with_hc_set) -> Tuple[GroupConfig, GroupConfig, GroupConfig]:
    """Add config group to the cluster, service and one of components"""
    changed_config = {"attr": {"group_keys": {"some_param": True}}, "config": {"some_param": 42}}
    host_1, host_2, host_3, *_ = cluster_with_hc_set.host_list()
    service = cluster_with_hc_set.service()
    component = service.component(name=FIRST_COMPONENT)
    cluster_group = create_config_group_and_add_host("Cluster Config Group", cluster_with_hc_set, host_1)
    cluster_group.config_set_diff(changed_config)
    service_group = create_config_group_and_add_host("Service Config Group", service, host_2)
    service_group.config_set_diff(changed_config)
    component_group = create_config_group_and_add_host("Component Config Group", component, host_3)
    component_group.config_set_diff(changed_config)
    return cluster_group, service_group, component_group


@pytest.fixture()
def host_not_in_config_group(cluster_with_hc_set, config_groups) -> Host:
    """Get one host that is not in config group"""
    hosts_in_groups = {host.fqdn for host in itertools.chain.from_iterable(group.hosts() for group in config_groups)}
    return [host for host in cluster_with_hc_set.host_list() if host.fqdn not in hosts_in_groups][0]


def test_hosts_in_mm_removed_from_inventory(api_client, adcm_fs, cluster_with_hc_set):
    """Test filtering of hosts in inventory file when hosts are in MM"""
    host, *_ = cluster_with_hc_set.host_list()
    service = cluster_with_hc_set.service()
    action_on_service = service.action(name=ACTION_ALLOWED_IN_MM)

    inventory = run_action_and_get_inventory(action_on_service, adcm_fs)
    check_all_hosts_are_present(inventory, cluster_with_hc_set)

    turn_mm_on(api_client, host)

    inventory = run_action_and_get_inventory(action_on_service, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


def test_hosts_in_mm_removed_from_group_config(
    api_client, adcm_fs, cluster_with_hc_set, config_groups, host_not_in_config_group
):
    """Test filtering of hosts in inventory file when hosts are in MM and in config group"""
    *_, component_group = config_groups
    component: Component = cluster_with_hc_set.service().component(name=FIRST_COMPONENT)
    action_on_component = component.action(name=ACTION_ALLOWED_IN_MM)

    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_all_hosts_are_present(inventory, cluster_with_hc_set)

    turn_mm_on(api_client, component_group.hosts()[0])
    turn_mm_on(api_client, host_not_in_config_group)

    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


def test_hosts_filtered_when_added_to_group_config_after_entering_mm(api_client, adcm_fs, cluster_with_hc_set):
    """Test filtering of hosts in inventory file when host entered MM and then added to config group"""
    component: Component = cluster_with_hc_set.service().component(name=FIRST_COMPONENT)
    host = cluster_with_hc_set.host(
        fqdn=next(filter(lambda hc: hc["component_id"] == component.id, cluster_with_hc_set.hostcomponent()))["host"]
    )
    action_on_component = component.action(name=ACTION_ALLOWED_IN_MM)

    turn_mm_on(api_client, host)

    create_config_group_and_add_host("Component Group", component, host)
    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


@pytest.mark.parametrize("cluster_with_hc_set", [HC_ACL_SERVICE_NAME], indirect=True)
def test_host_filtering_with_hc_acl(api_client, adcm_fs, cluster_with_hc_set: Cluster, hosts):
    """Test filtering of hosts in MM in inventory groups when action have `hc_acl` directive"""
    cluster = cluster_with_hc_set
    service = cluster.service(name=HC_ACL_SERVICE_NAME)
    first_component = service.component(name=FIRST_COMPONENT)
    host, *_ = cluster.host_list()
    *_, free_host = hosts

    add_hosts_to_cluster(cluster, [free_host])

    turn_mm_on(api_client, host)

    inventory = run_action_and_get_inventory(
        service.action(name="change"),
        adcm_fs,
        hc=build_hc_for_hc_acl_action(cluster, add=[(first_component, free_host)], remove=[(first_component, host)]),
    )
    check_hosts_in_mm_are_absent(inventory, cluster, service_name=HC_ACL_SERVICE_NAME)
    _check_add_remove_groups(inventory, add={free_host.fqdn}, remove=set())


def test_mm_flag_on_service_and_components(cluster_with_service_component_mm, sdk_client_fs, api_client, adcm_fs: ADCM):
    """Test that MM flag is set correctly on services and components in inventory"""
    action_name = "allowed_in_mm"
    _, service, first_component, second_component, _, second_host = cluster_with_service_component_mm

    set_maintenance_mode(api_client=api_client, adcm_object=service, maintenance_mode=MM_IS_ON)
    check_mm_flag_in_inventory(
        client=sdk_client_fs,
        inventory=run_action_and_get_inventory(service.action(name=action_name), adcm_fs),
        expect_on=(service, first_component, second_component),
    )

    set_maintenance_mode(api_client=api_client, adcm_object=service, maintenance_mode=MM_IS_OFF)
    set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_ON)
    check_mm_flag_in_inventory(
        client=sdk_client_fs,
        inventory=run_action_and_get_inventory(service.action(name=action_name), adcm_fs),
        expect_on=(first_component,),
        expect_off=(service, second_component),
    )

    set_maintenance_mode(api_client=api_client, adcm_object=second_host, maintenance_mode=MM_IS_ON)
    set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_OFF)
    check_mm_flag_in_inventory(
        client=sdk_client_fs,
        inventory=run_action_and_get_inventory(service.action(name=action_name), adcm_fs),
        expect_on=(second_component,),
        expect_off=(service, first_component),
    )


def run_action_and_get_inventory(action: Action, adcm: ADCM, **run_kwargs) -> dict:
    """Run action and get inventory file contents from container"""
    with allure.step(f"Run action {action.name}"):
        task = action.run(**run_kwargs)
        task.wait()
    with allure.step(f"Get inventory of task {task.id}"):
        return get_inventory_file(adcm, task.id)


@allure.step("Check that all hosts are presented in inventory")
def check_all_hosts_are_present(inventory: dict, cluster: Cluster) -> None:
    """Expect all hosts to be presented in inventory"""
    expected = {host.fqdn for host in cluster.host_list()}
    expected_on_second_component = {hc["host"] for hc in cluster.hostcomponent() if hc["component"] == SECOND_COMPONENT}
    _check_groups(inventory, expected, expected_on_second_component)


@allure.step("Check that hosts in maintenance mode are absent in regular groups")
def check_hosts_in_mm_are_absent(inventory: dict, cluster: Cluster, service_name: str = DEFAULT_SERVICE_NAME) -> None:
    """Expect hosts in MM are filtered out from inventory"""
    hostnames_in_mm = {host.fqdn for host in cluster.host_list() if host.maintenance_mode == MM_IS_ON}
    expected = {host.fqdn for host in cluster.host_list()}.difference(hostnames_in_mm)
    expected_on_second_component = {
        hc["host"] for hc in cluster.hostcomponent() if hc["component"] == SECOND_COMPONENT
    }.difference(hostnames_in_mm)
    _check_groups(inventory, expected, expected_on_second_component, service_name)
    components_with_mm = {hc["component"] for hc in cluster.hostcomponent() if hc["host"] in hostnames_in_mm}
    if len(components_with_mm) == 0:
        raise RuntimeError('There should be at least 1 component with host in MM')
    for component in components_with_mm:
        _check_mm_groups(inventory, service_name, component, hostnames_in_mm)


@allure.step("Check MM attributes of services and components in inventory")
def check_mm_flag_in_inventory(
    client: ADCMClient,
    inventory: dict,
    expect_on: tuple[Service | Component, ...] = (),
    expect_off: tuple[Service | Component, ...] = (),
):
    # pylint: disable=unsupported-membership-test,unsubscriptable-object
    for obj in expect_on:
        with allure.step(f"Check that MM of {get_object_represent(obj)} is 'ON' in inventory"):
            node = _get_object_node(inventory=inventory, client=client, adcm_object=obj)
            assert "maintenance_mode" in node, f"No field 'maintenance_mode' found within {node.keys()}"
            assert node["maintenance_mode"] is True

    for obj in expect_off:
        with allure.step(f"Check that MM of {get_object_represent(obj)} is 'OFF' in inventory"):
            node = _get_object_node(inventory=inventory, client=client, adcm_object=obj)
            assert "maintenance_mode" in node, f"No field 'maintenance_mode' found within {node.keys()}"
            assert node["maintenance_mode"] is False
    # pylint: enable=unsupported-membership-test,unsubscriptable-object


@allure.step("Check that correct hosts are presented in regular groups")
def _check_groups(
    inventory, expected_hosts: set, expected_on_second_component: set, service_name: str = DEFAULT_SERVICE_NAME
):
    children = inventory["all"]["children"]
    second_component_key = f"{service_name}.{SECOND_COMPONENT}"

    for group_to_check in ("CLUSTER", service_name, f"{service_name}.{FIRST_COMPONENT}"):
        hosts_on_object = set(children[group_to_check]["hosts"].keys())
        sets_are_equal(
            hosts_on_object, expected_hosts, f'Wrong hosts are presented in inventory of group "{group_to_check}"'
        )

    second_component_hosts = set(children[second_component_key]["hosts"].keys())
    sets_are_equal(
        second_component_hosts,
        expected_on_second_component,
        f'Wrong hosts are presented in inventory of "{second_component_key}"',
    )


def _check_mm_groups(inventory: dict, service_name: str, component_name: str, hosts_in_mm: Set[str]):
    children = inventory["all"]["children"]
    service_key = f"{service_name}.maintenance_mode"
    second_component_key = f"{service_name}.{component_name}.maintenance_mode"

    with allure.step("Check maintenance mode groups are presented in inventory"):
        assert service_key in children, f"{service_key} not found in: {', '.join(children.keys())}"
        assert second_component_key in children, f"{second_component_key} not found in: {', '.join(children.keys())}"

    with allure.step("Check that correct hosts are in MM groups"):
        hosts_in_group = set(children[service_key]["hosts"].keys())
        sets_are_equal(hosts_in_group, hosts_in_mm, "Wrong hosts in service's maintenance mode group")
        hosts_in_group = set(children[second_component_key]["hosts"].keys())
        sets_are_equal(hosts_in_group, hosts_in_mm, "Wrong hosts in component's maintenance mode group")


def _check_add_remove_groups(inventory, add: Set[str], remove: Set[str]):
    """Check one group with "add" and one with "remove" suffix"""
    children = inventory["all"]["children"]
    add_nodes = [(k, v) for k, v in children.items() if "add" in k]
    if not add_nodes:
        raise AssertionError('At least one node with "add" suffix should be presented in inventory')
    remove_nodes = [(k, v) for k, v in children.items() if "remove" in k]
    if not remove_nodes:
        raise AssertionError('At least on node with "remove" suffix should be presented in inventory')

    node_name, node_value = add_nodes[0]
    with allure.step(f"Check node {node_name}"):
        actual_hosts = set(node_value["hosts"].keys())
        sets_are_equal(actual_hosts, add, '"add" node is incorrect')

    node_name, node_value = remove_nodes[0]
    with allure.step(f"Check node {node_name}"):
        actual_hosts = set(node_value["hosts"].keys())
        sets_are_equal(actual_hosts, remove, '"remove" node is incorrect')


def _get_object_node(inventory: dict, client: ADCMClient, adcm_object: Service | Component) -> dict:
    services_node = inventory["all"]["children"]["CLUSTER"]["vars"]["services"]
    match adcm_object:
        case Service():
            return services_node[adcm_object.name]
        case Component():
            return services_node[client.service(id=adcm_object.service_id).name][adcm_object.name]
        case _:
            raise ValueError("`adcm_object` can be only Service or Component")
