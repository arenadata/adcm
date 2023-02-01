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
conftest.py for maintenance mode related tests
"""

# pylint: disable=redefined-outer-name

import os
from pathlib import Path
from typing import Iterable, Literal, Set, Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Component, Host, Provider, Service
from tests.functional.tools import AnyADCMObject, get_object_represent
from tests.library.api.client import APIClient
from tests.library.assertions import sets_are_equal
from tests.library.utils import get_hosts_fqdn_representation

BUNDLES_DIR = Path(os.path.dirname(__file__)) / 'bundles'

MM_IS_ON = "ON"
MM_IS_OFF = "OFF"
MM_IS_CHANGING = "CHANGING"
MM_ALLOWED = True
MM_NOT_ALLOWED = False

START_IMPOSSIBLE_REASONS = {
    "The Action is not available. One or more hosts in 'Maintenance mode'",
    "The Action is not available. Host in 'Maintenance mode'",
    "The Action is not available. Service in 'Maintenance mode'",
    "The Action is not available. Component in 'Maintenance mode'",
}

PROVIDER_NAME = 'Test Default Provider'
CLUSTER_WITH_MM_NAME = 'Test Cluster WITH Maintenance Mode'
CLUSTER_WITHOUT_MM_NAME = 'Test Cluster WITHOUT Maintenance Mode'
DEFAULT_SERVICE_NAME = 'test_service'
ANOTHER_SERVICE_NAME = 'another_service'
FIRST_COMPONENT = 'first_component'
SECOND_COMPONENT = 'second_component'


@pytest.fixture()
def provider(sdk_client_fs: ADCMClient) -> Provider:
    """Upload bundle and create default provider"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'default_provider')
    return bundle.provider_create(PROVIDER_NAME)


@pytest.fixture()
def hosts(provider) -> Tuple[Host, Host, Host, Host, Host, Host]:
    """Create 6 hosts from the default bundle"""
    return tuple(provider.host_create(f'test-host-{i}') for i in range(6))


@pytest.fixture()
def cluster_with_mm(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_allowed')
    cluster = bundle.cluster_create(CLUSTER_WITH_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


@pytest.fixture(params=['cluster_mm_disallowed'], ids=lambda x: x.strip('cluster_'))
def cluster_without_mm(request, sdk_client_fs: ADCMClient):
    """
    Upload cluster bundle with disallowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / request.param)
    cluster = bundle.cluster_create(CLUSTER_WITHOUT_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


def set_maintenance_mode(
    api_client: APIClient, adcm_object: Host | Service | Component, maintenance_mode: bool
) -> None:
    """Change maintenance mode on ADCM objects"""
    if isinstance(adcm_object, Service):
        client = api_client.service
    elif isinstance(adcm_object, Component):
        client = api_client.component
    else:
        client = api_client.host
    representation = get_object_represent(adcm_object)
    with allure.step(f'Turn MM to mode {maintenance_mode} on object {representation}'):
        client.change_maintenance_mode(adcm_object.id, maintenance_mode).check_code(200)
        adcm_object.reread()
        assert (actual_mm := adcm_object.maintenance_mode) == maintenance_mode, (
            f'Maintenance mode of object {representation} should be {maintenance_mode},' f' not {actual_mm}'
        )


def turn_mm_on(api_client: APIClient, host: Host):
    """Turn maintenance mode "on" on host"""
    with allure.step(f'Turn MM "on" on host {host.fqdn}'):
        api_client.host.change_maintenance_mode(host.id, MM_IS_ON).check_code(200)
        host.reread()
        assert (
            actual_mm := host.maintenance_mode
        ) == MM_IS_ON, f'Maintenance mode of host {host.fqdn} should be {MM_IS_ON}, not {actual_mm}'


def turn_mm_off(api_client: APIClient, host: Host, expected_code: int = 200):
    """Turn maintenance mode "off" on host"""
    with allure.step(f'Turn MM "off" on host {host.fqdn}'):
        api_client.host.change_maintenance_mode(host.id, MM_IS_OFF).check_code(expected_code)
        host.reread()
        assert (
            actual_mm := host.maintenance_mode
        ) == MM_IS_OFF, f'Maintenance mode of host {host.fqdn} should be {MM_IS_OFF}, not {actual_mm}'


def expect_changing_mm_fail(
    api_client: APIClient, object_with_mm: Host | Service | Component, new_mm: Literal["ON", "OFF"]
) -> None:
    """
    Check that changing MM is disallowed on object.
    Be careful with CHANGING status.
    """
    object_with_mm.reread()
    previous_mm = object_with_mm.maintenance_mode
    object_represent = get_object_represent(object_with_mm)
    with allure.step(f'Check setting MM "{new_mm}" on "{object_represent}" will fail'):
        api_node = getattr(api_client, object_with_mm.__class__.__name__.lower())
        api_node.change_maintenance_mode(object_with_mm.id, new_mm).check_code(409)
        object_with_mm.reread()
        assert (
            actual_mm := object_with_mm.maintenance_mode
        ) == previous_mm, f'Maintenance mode of "{object_represent}" should stay {previous_mm}, not become {actual_mm}'


def add_hosts_to_cluster(cluster: Cluster, hosts: Iterable[Host]):
    """Add hosts to cluster"""
    with allure.step(f'Add hosts to the cluster "{cluster.name}": {get_hosts_fqdn_representation(hosts)}'):
        for host in hosts:
            cluster.host_add(host)


def remove_hosts_from_cluster(cluster: Cluster, hosts: Iterable[Host]):
    """Remove hosts from cluster"""
    with allure.step(f'Add hosts to the cluster "{cluster.name}": {get_hosts_fqdn_representation(hosts)}'):
        for host in hosts:
            cluster.host_delete(host)


def check_mm_is(maintenance_mode: str, *adcm_object: Host | Service | Component) -> None:
    """Check value of maintenance_mode on object"""
    representation = [get_object_represent(obj) for obj in adcm_object]
    with allure.step(
        f'Check that "maintenance_mode" is equal to "{maintenance_mode}" ' f'on objects: {representation}'
    ):
        for obj in adcm_object:
            obj.reread()
        obj_in_wrong_mode = tuple(obj for obj in adcm_object if obj.maintenance_mode != maintenance_mode)
        if len(obj_in_wrong_mode) == 0:
            return
        raise AssertionError(
            f"{', '.join(get_object_represent(obj) for obj in obj_in_wrong_mode)} "
            "have incorrect value of 'maintenance_mode' flag.\n"
            f"Expected: {maintenance_mode}\nActual: {obj_in_wrong_mode[0].maintenance_mode}"
        )


def check_mm_availability(is_mm_available: bool, *hosts: Host):
    """Check that MM change is allowed/disallowed for the given hosts"""
    with allure.step(
        f'Check that "is_maintenance_mode_available" is {is_mm_available} '
        f'on hosts: {get_hosts_fqdn_representation(hosts)}'
    ):
        for host in hosts:
            host.reread()
        hosts_in_wrong_mode = tuple(host for host in hosts if host.is_maintenance_mode_available is not is_mm_available)
        if len(hosts_in_wrong_mode) == 0:
            return
        raise AssertionError(
            'Some hosts have incorrect value of "is_maintenance_mode_available" flag.\n'
            f'Hosts: {get_hosts_fqdn_representation(hosts_in_wrong_mode)}'
        )


def get_enabled_actions_names(adcm_object: AnyADCMObject) -> Set[str]:
    """Get actions that aren't disabled by maintenance mode"""
    return {
        action.name
        for action in adcm_object.action_list()
        if action.start_impossible_reason not in START_IMPOSSIBLE_REASONS
    }


def get_disabled_actions_names(adcm_object: AnyADCMObject) -> Set[str]:
    """Get actions disabled because of maintenance mode"""
    return {
        action.name
        for action in adcm_object.action_list()
        if action.start_impossible_reason in START_IMPOSSIBLE_REASONS
    }


def check_concerns_on_object(adcm_object: AnyADCMObject, expected_concerns: set[str]) -> None:
    """Check concerns on object"""
    with allure.step(f"Check concerns on object {adcm_object}"):
        adcm_object.reread()
        actual_concerns = {concern.reason["placeholder"]["source"]["name"] for concern in adcm_object.concerns()}
        sets_are_equal(
            actual_concerns,
            expected_concerns,
            "Actual concerns must be equal with expected concerns"
            f" on: {get_object_represent(adcm_object)}\n"
            f"Actual concerns: {actual_concerns}\n"
            f"Expected concerns: {expected_concerns}",
        )


def check_no_concerns_on_objects(*adcm_object):
    """Method to check concerns on adcm_object is absent"""
    for obj in adcm_object:
        obj.reread()
    report = [
        (
            f"{get_object_represent(obj)} have concern:\n"
            f"{[issue.name for issue in obj.concerns()]}\n"
            "while concern is not expected"
        )
        for obj in adcm_object
        if len(obj.concerns()) != 0
    ]
    if not report:
        return
    raise AssertionError(f"{', '.join(obj for obj in report)}")


def check_actions_availability(
    adcm_object: AnyADCMObject, expected_enabled: set[str], expected_disabled: set[str]
) -> None:
    """Method to check actual enabled and disabled actions with expected"""
    representation = get_object_represent(adcm_object)
    actual_enabled = get_enabled_actions_names(adcm_object)
    actual_disabled = get_disabled_actions_names(adcm_object)

    with allure.step(f"Compare actual enabled actions with expected enabled actions on object {representation}"):
        sets_are_equal(
            actual_enabled,
            expected_enabled,
            f"Incorrect actions are enabled on object {representation}\n"
            f"Actual enabled actions: {actual_enabled}\n"
            f"Expected enabled actions: {expected_enabled}",
        )

    with allure.step(f"Compare actual disabled actions with expected disabled actions on object {representation}"):
        sets_are_equal(
            actual_disabled,
            expected_disabled,
            f"Incorrect actions are disabled on object {representation}\n"
            f"Actual disabled actions: {actual_disabled}\n"
            f"Expected disabled actions: {expected_disabled}",
        )
