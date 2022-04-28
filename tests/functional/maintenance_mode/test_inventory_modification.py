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
from typing import Tuple

import allure
import pytest
from adcm_client.objects import Cluster, GroupConfig, Action, Component, Host
from adcm_pytest_plugin.docker_utils import ADCM
from adcm_pytest_plugin.utils import get_or_add_service

from tests.functional.maintenance_mode.test_hosts_behavior import ACTION_ALLOWED_IN_MM
from tests.functional.tools import create_config_group_and_add_host, get_inventory_file, build_hc_for_hc_acl_action
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    DEFAULT_SERVICE_NAME,
    FIRST_COMPONENT,
    SECOND_COMPONENT,
    MM_IS_ON,
    turn_mm_on,
    add_hosts_to_cluster,
)
from tests.library.assertions import sets_are_equal

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

DEFAULT_ACTION_NAME = 'default_action'
HC_ACL_SERVICE_NAME = 'hc_acl_service'


@pytest.fixture(params=[pytest.param(DEFAULT_SERVICE_NAME, id='default_service')])
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


@pytest.fixture()
def config_groups(cluster_with_hc_set) -> Tuple[GroupConfig, GroupConfig, GroupConfig]:
    """Add config group to the cluster, service and one of components"""
    changed_config = {'some_param': 42}
    host_1, host_2, host_3, *_ = cluster_with_hc_set.host_list()
    service = cluster_with_hc_set.service()
    component = service.component(name=FIRST_COMPONENT)
    cluster_group = create_config_group_and_add_host('Cluster Config Group', cluster_with_hc_set, host_1)
    cluster_group.config_set_diff(changed_config)
    service_group = create_config_group_and_add_host('Service Config Group', service, host_2)
    service_group.config_set_diff(changed_config)
    component_group = create_config_group_and_add_host('Component Config Group', component, host_3)
    component_group.config_set_diff(changed_config)
    return cluster_group, service_group, component_group


@pytest.fixture()
def host_not_in_config_group(cluster_with_hc_set, config_groups) -> Host:
    """Get one host that is not in config group"""
    hosts_in_groups = {host.fqdn for host in itertools.chain.from_iterable(group.hosts() for group in config_groups)}
    return [host for host in cluster_with_hc_set.host_list() if host.fqdn not in hosts_in_groups][0]


def test_hosts_in_mm_removed_from_inventory(adcm_fs, cluster_with_hc_set):
    """Test filtering of hosts in inventory file when hosts are in MM"""
    host, *_ = cluster_with_hc_set.host_list()
    service = cluster_with_hc_set.service()
    action_on_service = service.action(name=ACTION_ALLOWED_IN_MM)

    inventory = run_action_and_get_inventory(action_on_service, adcm_fs)
    check_all_hosts_are_present(inventory, cluster_with_hc_set)

    turn_mm_on(host)

    inventory = run_action_and_get_inventory(action_on_service, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


def test_hosts_in_mm_removed_from_group_config(adcm_fs, cluster_with_hc_set, config_groups, host_not_in_config_group):
    """Test filtering of hosts in inventory file when hosts are in MM and in config group"""
    *_, component_group = config_groups
    component: Component = cluster_with_hc_set.service().component(name=FIRST_COMPONENT)
    action_on_component = component.action(name=ACTION_ALLOWED_IN_MM)

    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_all_hosts_are_present(inventory, cluster_with_hc_set)

    turn_mm_on(component_group.hosts()[0])
    turn_mm_on(host_not_in_config_group)

    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


def test_hosts_filtered_when_added_to_group_config_after_entering_mm(adcm_fs, cluster_with_hc_set):
    """Test filtering of hosts in inventory file when host entered MM and then added to config group"""
    component: Component = cluster_with_hc_set.service().component(name=FIRST_COMPONENT)
    host = cluster_with_hc_set.host(
        fqdn=next(filter(lambda hc: hc['component_id'] == component.id, cluster_with_hc_set.hostcomponent()))['host']
    )
    action_on_component = component.action(name=ACTION_ALLOWED_IN_MM)

    turn_mm_on(host)

    create_config_group_and_add_host('Component Group', component, host)
    inventory = run_action_and_get_inventory(action_on_component, adcm_fs)
    check_hosts_in_mm_are_absent(inventory, cluster_with_hc_set)


@pytest.mark.parametrize('cluster_with_hc_set', [HC_ACL_SERVICE_NAME], indirect=True)
def test_host_filtering_with_hc_acl(adcm_fs, cluster_with_hc_set: Cluster, hosts):
    """Test filtering of hosts in MM in inventory groups when action have `hc_acl` directive"""
    cluster = cluster_with_hc_set
    service = cluster.service(name=HC_ACL_SERVICE_NAME)
    first_component = service.component(name=FIRST_COMPONENT)
    host, *_ = cluster.host_list()
    *_, free_host = hosts

    add_hosts_to_cluster(cluster, [free_host])

    turn_mm_on(host)

    inventory = run_action_and_get_inventory(
        service.action(name='change'),
        adcm_fs,
        hc=build_hc_for_hc_acl_action(cluster, add=[(first_component, free_host)], remove=[(first_component, host)]),
    )
    check_hosts_in_mm_are_absent(inventory, cluster)


def run_action_and_get_inventory(action: Action, adcm: ADCM, **run_kwargs) -> dict:
    """Run action and get inventory file contents from container"""
    with allure.step(f'Run action {action.name}'):
        task = action.run(**run_kwargs)
        task.wait()
    with allure.step(f'Get inventory of task {task.id}'):
        return get_inventory_file(adcm, task.id)


@allure.step('Check that all hosts are presented in inventory')
def check_all_hosts_are_present(inventory: dict, cluster: Cluster) -> None:
    """Expect all hosts to be presented in inventory"""
    expected = {host.fqdn for host in cluster.host_list()}
    expected_on_second_component = {hc['host'] for hc in cluster.hostcomponent() if hc['component'] == SECOND_COMPONENT}
    _check_expected(inventory, expected, expected_on_second_component)


@allure.step('Check that hosts in maintenance mode are absent in inventory')
def check_hosts_in_mm_are_absent(inventory: dict, cluster: Cluster) -> None:
    """Expect hosts in MM are filtered out from inventory"""
    hostnames_in_mm = {host.fqdn for host in cluster.host_list() if host.maintenance_mode == MM_IS_ON}
    expected = {host.fqdn for host in cluster.host_list()}.difference(hostnames_in_mm)
    expected_on_second_component = {
        hc['host'] for hc in cluster.hostcomponent() if hc['component'] == SECOND_COMPONENT
    }.difference(hostnames_in_mm)
    _check_expected(inventory, expected, expected_on_second_component)


def _check_expected(inventory, expected_hosts: set, expected_on_second_component: set):
    children = inventory['all']['children']
    second_component_key = f'{DEFAULT_SERVICE_NAME}.{SECOND_COMPONENT}'

    for group_to_check in (k for k in children.keys() if not k.startswith(second_component_key)):
        hosts_on_object = set(children[group_to_check]['hosts'].keys())
        sets_are_equal(
            hosts_on_object, expected_hosts, f'Wrong hosts are presented in inventory of group "{group_to_check}"'
        )

    second_component_hosts = set(children[second_component_key]['hosts'].keys())
    sets_are_equal(
        second_component_hosts,
        expected_on_second_component,
        f'Wrong hosts are presented in inventory of "{second_component_key}"',
    )
