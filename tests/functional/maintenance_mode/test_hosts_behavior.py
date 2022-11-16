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
Test hosts maintenance mode behaviour
"""

from typing import Iterable, Set, Tuple

import allure
import pytest
from adcm_client.objects import Cluster, Component, Host
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (
    ANOTHER_SERVICE_NAME,
    BUNDLES_DIR,
    DEFAULT_SERVICE_NAME,
    MM_IS_OFF,
    MM_IS_ON,
    MM_NOT_ALLOWED,
    add_hosts_to_cluster,
    check_mm_availability,
    check_mm_is,
    expect_changing_mm_fail,
    get_disabled_actions_names,
    get_enabled_actions_names,
    remove_hosts_from_cluster,
    turn_mm_off,
    turn_mm_on,
)
from tests.functional.tools import (
    AnyADCMObject,
    build_hc_for_hc_acl_action,
    get_object_represent,
)
from tests.library.assertions import (
    expect_api_error,
    expect_no_api_error,
    is_empty,
    sets_are_equal,
)
from tests.library.errorcodes import (
    ACTION_ERROR,
    INVALID_HC_HOST_IN_MM,
    MAINTENANCE_MODE_NOT_AVAILABLE,
    ADCMError,
)

# pylint: disable=redefined-outer-name

ACTION_ALLOWED_IN_MM = 'allowed_in_mm'
ACTION_NOT_ALLOWED_IN_MM = 'not_allowed_in_mm'
ENABLED_ACTIONS = {ACTION_ALLOWED_IN_MM}
DISABLED_ACTIONS = {'default_action', ACTION_NOT_ALLOWED_IN_MM}


@pytest.fixture()
def host_actions_cluster(sdk_client_fs) -> Cluster:
    """Upload and create cluster with host actions from cluster, service and component"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_host_actions')
    cluster = bundle.cluster_create('Cluster with host actions')
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


@only_clean_adcm
@pytest.mark.parametrize(
    'cluster_without_mm',
    ['cluster_mm_disallowed', 'cluster_mm_missing'],
    ids=lambda x: x.strip('cluster_'),
    indirect=True,
)
def test_adding_host_to_cluster(api_client, cluster_with_mm, cluster_without_mm, hosts):
    """
    Test that adding/removing host to/from cluster affects "maintenance_mode" flag on host
    """
    hosts_to_cluster_with_mm = first_host, second_host = hosts[:2]
    hosts_to_cluster_without_mm = third_host, _ = hosts[2:4]
    free_hosts = hosts[-2:]

    check_mm_availability(MM_NOT_ALLOWED, *hosts)

    add_hosts_to_cluster(cluster_without_mm, hosts_to_cluster_without_mm)
    check_mm_availability(MM_NOT_ALLOWED, *hosts)

    add_hosts_to_cluster(cluster_with_mm, hosts_to_cluster_with_mm)
    check_mm_is(MM_IS_OFF, *hosts_to_cluster_with_mm)
    check_mm_availability(MM_NOT_ALLOWED, *hosts_to_cluster_without_mm, *free_hosts)

    turn_mm_on(api_client, first_host)
    check_mm_is(MM_IS_ON, first_host)
    check_mm_is(MM_IS_OFF, second_host)
    check_mm_availability(MM_NOT_ALLOWED, *hosts_to_cluster_without_mm, *free_hosts)

    expect_changing_mm_fail(api_client, third_host, MM_IS_ON)
    check_mm_availability(MM_NOT_ALLOWED, *hosts_to_cluster_without_mm)
    turn_mm_off(api_client, third_host)
    check_mm_availability(MM_NOT_ALLOWED, *hosts_to_cluster_without_mm)

    remove_hosts_from_cluster(cluster_with_mm, hosts_to_cluster_with_mm)
    remove_hosts_from_cluster(cluster_without_mm, hosts_to_cluster_without_mm)
    check_mm_availability(MM_NOT_ALLOWED, *hosts)


def test_mm_hosts_not_allowed_in_hc_map(api_client, cluster_with_mm, hosts):
    """
    Test that hosts in MM aren't allowed to be used in hostcomponent map
    """
    cluster = cluster_with_mm
    first_component = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME).component(name='first_component')
    host_in_mm, regular_host, *_ = hosts

    add_hosts_to_cluster(cluster, (host_in_mm, regular_host))
    turn_mm_on(api_client, host_in_mm)
    with allure.step('Try to set HC map with one of hosts in MM'):
        _expect_hc_set_to_fail(cluster, [(host_in_mm, first_component)], err_=INVALID_HC_HOST_IN_MM)
        _expect_hc_set_to_fail(
            cluster, [(host_in_mm, first_component), (regular_host, first_component)], err_=INVALID_HC_HOST_IN_MM
        )

    with allure.step('Place component on "working" host'):
        hc_with_regular_host = cluster.hostcomponent_set((regular_host, first_component))

    with allure.step("Try to set HC map with one of hosts in MM and check that hc-map hasn't changed"):
        _expect_hc_set_to_fail(
            cluster, [(host_in_mm, first_component), (regular_host, first_component)], err_=INVALID_HC_HOST_IN_MM
        )
        cluster.reread()
        _check_hostcomponents_are_equal(cluster.hostcomponent(), hc_with_regular_host)


def test_actions_not_allowed_in_mm_are_disabled_due_to_host_in_mm(api_client, cluster_with_mm, hosts):
    """
    Test that actions that aren't allowed in maintenance mode
    - are disabled when MM host is in vertical hierarchy (cluster-service-component)
    - aren't disabled when MM host is on another service's component / on another component.
    """
    first_host, second_host, *_ = hosts
    cluster = cluster_with_mm
    first_service = cluster.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_component = first_service.component(name='second_component')
    second_service = cluster.service_add(name=ANOTHER_SERVICE_NAME)
    second_service_components = second_service.component_list()
    all_objects = [
        cluster,
        first_service,
        second_service,
        first_component,
        second_component,
        *second_service_components,
    ]

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
        (second_host, second_service_components[0]),
        (second_host, second_service_components[1]),
    )
    check_all_actions_are_enabled(*all_objects)

    with allure.step(f'Turn MM "on" on host {first_host.fqdn} and check actions are disabled correctly'):
        turn_mm_on(api_client, first_host)
        check_actions_are_disabled_on(cluster, first_service, first_component)
        check_all_actions_are_enabled(second_component, second_service, *second_service_components)

    with allure.step(f'Turn MM "off" on host {first_host.fqdn} and expect all objects\' actions to be enabled'):
        turn_mm_off(api_client, first_host)
        check_all_actions_are_enabled(*all_objects)


def test_provider_and_host_actions_affected_by_mm(api_client, cluster_with_mm, provider, hosts):
    """
    Test that host in MM doesn't affect provider's actions,
    but cleans action list of this host (including `host_action: true`)
    """
    cluster = cluster_with_mm
    component = cluster.service(name=DEFAULT_SERVICE_NAME).component(name='first_component')
    first_host, second_host, *_ = hosts
    actions_on_provider = {'default_action'}
    actions_on_host = {'default_action', 'see_me_on_host'}

    def _available_actions_are(on_first_host: set, on_second_host: set, on_provider: set):
        check_visible_actions(first_host, on_first_host)
        check_visible_actions(second_host, on_second_host)
        check_visible_actions(provider, on_provider)

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set((first_host, component), (second_host, component))
    _available_actions_are(actions_on_host, actions_on_host, actions_on_provider)

    turn_mm_on(api_client, first_host)
    _available_actions_are(actions_on_host, actions_on_host, actions_on_provider)

    turn_mm_off(api_client, first_host)
    _available_actions_are(actions_on_host, actions_on_host, actions_on_provider)


def test_host_actions_on_another_component_host(api_client, host_actions_cluster, hosts):
    """
    Test host_actions from cluster, service and component are working correctly
    with regular host with component that is also mapped to an MM host
    """
    expected_enabled = {'default_action'} | {
        f'{obj_type}_host_action_allowed' for obj_type in ('cluster', 'service', 'component')
    }
    expected_disabled = {f'{obj_type}_host_action_disallowed' for obj_type in ('cluster', 'service', 'component')}

    host_in_mm, regular_host, *_ = hosts
    cluster = host_actions_cluster
    component = cluster.service().component()

    add_hosts_to_cluster(cluster, (host_in_mm, regular_host))
    cluster.hostcomponent_set((host_in_mm, component), (regular_host, component))

    turn_mm_on(api_client, host_in_mm)

    enabled_actions = get_enabled_actions_names(regular_host)
    disabled_actions = get_disabled_actions_names(regular_host)

    with allure.step('Check that correct actions are enabled/disabled on the host'):
        sets_are_equal(enabled_actions, expected_enabled, f'Incorrect actions are enabled on host {regular_host.fqdn}')
        sets_are_equal(
            disabled_actions, expected_disabled, f'Incorrect actions are disabled on host {regular_host.fqdn}'
        )


def test_running_disabled_actions_is_forbidden(api_client, cluster_with_mm, hosts):
    """
    Test that disabled actions actually can't be launched
    and that host's filtered action can't be launched directly via API
    """
    cluster = cluster_with_mm
    service = cluster.service(name=DEFAULT_SERVICE_NAME)
    first_component, second_component = service.component_list()
    first_host, second_host, *_ = hosts

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set((first_host, first_component), (second_host, second_component))

    host_action_from_itself = first_host.action(name='default_action')
    host_action_from_component = first_host.action(name='see_me_on_host')

    turn_mm_on(api_client, first_host)

    expect_api_error(
        'run not allowed in MM action on service',
        service.action(name=ACTION_NOT_ALLOWED_IN_MM).run,
        err_=ACTION_ERROR,
    )
    task = expect_no_api_error('run allowed in MM action on service', service.action(name=ACTION_ALLOWED_IN_MM).run)

    expect_api_error('run action on host in MM', host_action_from_itself.run, err_=ACTION_ERROR)
    task.wait()
    expect_no_api_error('run action `host_action: true` on host in MM', host_action_from_component.run)


@only_clean_adcm
def test_host_actions_with_mm(api_client, cluster_with_mm, hosts):
    """
    Test that host actions (`host_action: true`) are working correctly
    with `allow_in_maintenance_mode` flag
    """
    allowed_action = 'allowed_in_mm'
    not_allowed_action = 'not_allowed_in_mm'
    default_action_of_host = 'default_action'
    all_actions = {allowed_action, not_allowed_action, default_action_of_host}
    cluster = cluster_with_mm
    component = cluster.service_add(name='host_actions').component()
    host_in_mm, regular_host, *_ = hosts

    add_hosts_to_cluster(cluster, (host_in_mm, regular_host))
    cluster.hostcomponent_set((host_in_mm, component), (regular_host, component))
    turn_mm_on(api_client, host_in_mm)

    check_visible_actions(host_in_mm, all_actions)
    check_visible_actions(regular_host, all_actions)

    expect_no_api_error('run allowed in MM action', host_in_mm.action(name=allowed_action).run).wait()

    expect_api_error(
        'run not allowed in MM action', regular_host.action(name=not_allowed_action).run, err_=ACTION_ERROR
    )
    expect_api_error('run not allowed in MM action', host_in_mm.action(name=not_allowed_action).run, err_=ACTION_ERROR)
    expect_api_error(
        'run not allowed in MM action of host', host_in_mm.action(name=default_action_of_host).run, err_=ACTION_ERROR
    )
    expect_no_api_error('run allowed in MM action', regular_host.action(name=allowed_action).run)


@only_clean_adcm
def test_hc_acl_action_with_mm(api_client, cluster_with_mm, hosts):
    """
    Test behaviour of actions with `hc_acl`:
    - adding component on host in MM should be forbidden
    - removing component from host in MM should be allowed
    """
    mm_host_1, mm_host_2, mm_host_3, regular_host_1, regular_host_2, *_ = hosts
    service = cluster_with_mm.service_add(name='hc_acl_service')
    first_component = service.component(name='first_component')
    second_component = service.component(name='second_component')

    add_hosts_to_cluster(cluster_with_mm, (mm_host_1, mm_host_2, mm_host_3, regular_host_1, regular_host_2))
    cluster_with_mm.hostcomponent_set(
        (mm_host_1, first_component),
        (regular_host_1, second_component),
        (mm_host_2, second_component),
        (mm_host_3, first_component),
        (mm_host_3, second_component),
    )
    turn_mm_on(api_client, mm_host_1)
    turn_mm_on(api_client, mm_host_2)
    turn_mm_on(api_client, mm_host_3)

    with allure.step('Check "adding" component to a host in MM is forbidden'):
        expect_api_error(
            'add component to a host in MM with hc_acl action',
            service.action(name='expand').run,
            hc=build_hc_for_hc_acl_action(cluster_with_mm, add=[(second_component, mm_host_1)]),
        )

    with allure.step('Check "removing" component from a host in MM is allowed'):
        expect_no_api_error(
            'remove component from a MM host with hc_acl action',
            service.action(name='shrink').run,
            hc=build_hc_for_hc_acl_action(cluster_with_mm, remove=[(second_component, mm_host_2)]),
        ).wait()

    with allure.step('Check "moving" component from host in MM to a regular host in one action is allowed'):
        expect_no_api_error(
            'move component from MM host to regular one',
            service.action(name='change').run,
            hc=build_hc_for_hc_acl_action(
                cluster_with_mm, [(first_component, mm_host_1)], [(first_component, regular_host_1)]
            ),
        )


@only_clean_adcm
def test_hosts_in_not_blocking_regular_hc_acl(cluster_with_mm, hosts):
    """
    Test that hosts in MM doesn't block operations on "regular" hosts
    (for components with both type of hosts)
    """
    service = cluster_with_mm.service_add(name='hc_acl_service')
    first_component = service.component(name='first_component')
    second_component = service.component(name='second_component')
    mm_host_1, mm_host_2, regular_host_1, regular_host_2, *_ = hosts

    add_hosts_to_cluster(cluster_with_mm, (mm_host_1, mm_host_2, regular_host_1, regular_host_2))
    cluster_with_mm.hostcomponent_set(
        (mm_host_1, first_component),
        (regular_host_1, first_component),
        (regular_host_1, second_component),
        (mm_host_2, second_component),
    )

    expect_no_api_error(
        'add component on host not in MM with hc_acl action',
        service.action(name='expand').run,
        hc=build_hc_for_hc_acl_action(cluster_with_mm, add=[(second_component, regular_host_2)]),
    ).wait()

    expect_no_api_error(
        'remove component from host not in MM with hc_acl_action',
        service.action(name='shrink').run,
        hc=build_hc_for_hc_acl_action(cluster_with_mm, remove=[(second_component, regular_host_2)]),
    )


@only_clean_adcm
def test_state_after_mm_switch(api_client, cluster_with_mm, hosts):
    """
    Test that state stays the same after switch of MM flag
    """
    host, *_ = hosts
    expected_state = host.state

    add_hosts_to_cluster(cluster_with_mm, [host])
    check_state(host, expected_state)
    turn_mm_on(api_client, host)
    check_state(host, expected_state)
    turn_mm_off(api_client, host)
    check_state(host, expected_state)
    remove_hosts_from_cluster(cluster_with_mm, [host])
    check_state(host, expected_state)


@only_clean_adcm
def test_set_value_not_in_enum_in_mm(cluster_with_mm, hosts):
    """
    Test that value 'disabled' can't be set to a host in 'on/off' mode
    and another value than 'on', 'off', 'disabled' can't be sent in MM field of the host
    """
    mm_value = 'diisabled'
    host, *_ = hosts

    add_hosts_to_cluster(cluster_with_mm, [host])
    expect_api_error('Set value "disabled" to MM', lambda: host.maintenance_mode_set('disabled'))
    expect_api_error(f'Set value "{mm_value}" to MM', lambda: host.maintenance_mode_set(mm_value))


def test_mm_after_cluster_deletion(api_client, cluster_with_mm, hosts):
    """
    Test that MM on hosts from deleted cluster is "disabled"
    """
    host_1, host_2, *_ = hosts
    add_hosts_to_cluster(cluster_with_mm, [host_1, host_2])
    turn_mm_on(api_client, host_2)
    check_mm_is(MM_IS_OFF, host_1)
    check_mm_is(MM_IS_ON, host_2)
    with allure.step('Delete cluster'):
        cluster_with_mm.delete()
    check_mm_availability(MM_NOT_ALLOWED, host_1, host_2)


def check_actions_are_disabled_on(*objects) -> None:
    """Check that correct actions are disabled on given objects"""
    for adcm_object in objects:
        object_representation = get_object_represent(adcm_object)
        enabled_actions_on_object = get_enabled_actions_names(adcm_object)
        sets_are_equal(
            enabled_actions_on_object,
            ENABLED_ACTIONS,
            f'Actions should be enabled on {object_representation}.\nCheck attachment.',
        )
        disabled_actions_on_object = get_disabled_actions_names(adcm_object)
        sets_are_equal(
            disabled_actions_on_object,
            DISABLED_ACTIONS,
            f'Actions should be disabled on {object_representation}.\nCheck attachment.',
        )


def check_all_actions_are_enabled(*objects) -> None:
    """Check that all actions are enabled on given objects"""
    for adcm_object in objects:
        disabled_actions_on_object = get_disabled_actions_names(adcm_object)
        is_empty(
            disabled_actions_on_object, f'None of actions should be disabled on {get_object_represent(adcm_object)}'
        )


def check_visible_actions(adcm_object: AnyADCMObject, action_names: Set[str]) -> None:
    """Check actions are presented in object's action list"""
    actual_names = {action.name for action in adcm_object.action_list()}
    object_represent = get_object_represent(adcm_object)
    with allure.step(f'Check action list of {object_represent}'):
        if action_names:
            sets_are_equal(
                actual_names,
                action_names,
                f'Action list is incorrect for object {object_represent}.\nCheck attachments for more details.',
            )
        else:
            is_empty(actual_names, 'Action list should be empty')


def check_state(host: Host, expected_state: str) -> None:
    """Check that state is equal to the expected state"""
    host.reread()
    assert (
        actual_state := host.state
    ) == expected_state, f'State of host {host.fqdn} should be {expected_state}, not {actual_state}'


def _expect_hc_set_to_fail(
    cluster: Cluster, hostcomponent: Iterable[Tuple[Host, Component]], err_: ADCMError = MAINTENANCE_MODE_NOT_AVAILABLE
) -> None:
    expect_api_error(
        'set hostcomponent with one of hosts in MM mode',
        cluster.hostcomponent_set,
        *hostcomponent,
        err_=err_,
    )


def _check_hostcomponents_are_equal(actual_hc, expected_hc) -> None:
    """Compare hostcomponent maps directly"""
    assert actual_hc == expected_hc, f'Hostcomponent map has changed.\nExpected:\n{expected_hc}\nActual:\n{actual_hc}'
