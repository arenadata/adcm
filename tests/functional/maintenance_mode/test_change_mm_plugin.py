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
from adcm_client.objects import ADCMClient, Bundle, Cluster, Component, Host, Service

from tests.functional.maintenance_mode.conftest import (
    BUNDLES_DIR,
    MM_IS_OFF,
    MM_IS_ON,
    check_mm_is,
)
from tests.functional.tools import AnyADCMObject, get_object_represent
from tests.library.assertions import does_not_intersect

# pylint: disable=redefined-outer-name


MM_CHANGE_RELATED_ACTION_NAMES = frozenset(
    {
        "adcm_host_turn_on_maintenance_mode",
        "adcm_host_turn_off_maintenance_mode",
        "adcm_turn_on_maintenance_mode",
        "adcm_turn_off_maintenance_mode",
    }
)


@pytest.fixture()
def bundle(sdk_client_fs) -> Bundle:
    return sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_using_plugin")


@pytest.fixture()
def first_cluster_objects(bundle) -> tuple[Service, Component, Component, Service, Component, Component]:
    return _prepare_new_cluster(bundle, "Cluster with MM actions")[1:]


@pytest.fixture()
def first_cluster_hosts(first_cluster_objects, hosts) -> tuple[Host, Host, Host]:
    host_1, host_2, host_3, *_ = hosts
    _, component_1, component_2, _, component_3, component_4 = first_cluster_objects

    _map_components_to_hosts((host_1, host_2, host_3), (component_1, component_2, component_3, component_4))

    return host_1, host_2, host_3


@pytest.fixture()
def second_cluster_objects(bundle) -> tuple[Service, Component, Component, Service, Component, Component]:
    return _prepare_new_cluster(bundle, "Control group cluster")[1:]


@pytest.fixture()
def second_cluster_hosts(second_cluster_objects, hosts) -> tuple[Host, Host, Host]:
    *_, host_1, host_2, host_3 = hosts
    _, component_1, component_2, _, component_3, component_4 = second_cluster_objects

    _map_components_to_hosts((host_1, host_2, host_3), (component_1, component_2, component_3, component_4))

    return host_1, host_2, host_3


def test_changing_mm_via_plugin(
    api_client, sdk_client_fs, first_cluster_objects, second_cluster_objects, first_cluster_hosts, second_cluster_hosts
):
    """
    Test changing MM flag of service and component via bonded action with MM changing plugin call
    """
    service, component_with_plugin, component_wo_plugin, *another_service_objects = first_cluster_objects
    hosts = *first_cluster_hosts, *second_cluster_hosts

    check_mm_related_actions_are_absent_on(
        service.cluster(), *first_cluster_objects, second_cluster_objects[0].cluster(), *second_cluster_objects, *hosts
    )

    with allure.step("Change service's MM to 'ON' with action bond to it"):
        api_client.service.change_maintenance_mode(service.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 1)
        check_mm_is(MM_IS_ON, service, component_with_plugin, component_wo_plugin)
        check_mm_is(MM_IS_OFF, *another_service_objects, *second_cluster_objects, *hosts)

    with allure.step("Change service's MM to 'OFF' with action bond to it"):
        api_client.service.change_maintenance_mode(service.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 2)
        check_mm_is(MM_IS_OFF, *first_cluster_objects, *second_cluster_objects, *hosts)

    with allure.step("Change component's MM to 'ON' with action bond to it"):
        api_client.component.change_maintenance_mode(component_with_plugin.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 3)
        check_mm_is(MM_IS_ON, component_with_plugin)
        check_mm_is(MM_IS_OFF, service, component_wo_plugin, *another_service_objects, *second_cluster_objects, *hosts)

    with allure.step("Change component's MM to 'OFF' with action bond to it"):
        api_client.component.change_maintenance_mode(component_with_plugin.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 4)
        check_mm_is(MM_IS_OFF, *first_cluster_objects, *second_cluster_objects, *hosts)

    check_mm_related_actions_are_absent_on(
        service.cluster(), *first_cluster_objects, second_cluster_objects[0].cluster(), *second_cluster_objects, *hosts
    )


def test_changing_host_mm_via_plugin(  # pylint: disable=too-many-locals
    api_client, sdk_client_fs, first_cluster_objects, second_cluster_objects, second_cluster_hosts, hosts
):
    """
    Test changing MM flag of host via bonded action with MM changing plugin call
    """
    host_1, host_2, host_3, *_ = hosts
    first_cluster_hosts = host_1, host_2, host_3
    second_objects = *second_cluster_objects, *second_cluster_hosts

    with allure.step("Check that MM of host outside of cluster can't be changed via bonded action"):
        api_client.host.change_maintenance_mode(host_1.id, MM_IS_ON).check_code(409)
        check_mm_is(MM_IS_OFF, *first_cluster_hosts, *first_cluster_objects, *second_objects)

    with allure.step("Map hosts to first cluster"):
        service, component_1, component_2, _, component_3, component_4 = first_cluster_objects
        _map_components_to_hosts((host_1, host_2, host_3), (component_1, component_2, component_3, component_4))
        _, _, _, *another_service_objects = first_cluster_objects

    with allure.step("Change one host's MM to 'ON'"):
        api_client.host.change_maintenance_mode(host_1.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 1)
        check_mm_is(MM_IS_ON, host_1)
        check_mm_is(MM_IS_OFF, host_2, host_3, *first_cluster_objects, *second_objects)

    with allure.step("Change second host's MM to 'ON'"):
        api_client.host.change_maintenance_mode(host_2.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 2)
        check_mm_is(MM_IS_ON, host_1, host_2, component_1)
        check_mm_is(MM_IS_OFF, host_3, service, component_2, *another_service_objects, *second_objects)

    with allure.step("Change third host's MM to 'ON' and check all mapped services and components switched"):
        api_client.host.change_maintenance_mode(host_3.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 3)
        check_mm_is(MM_IS_ON, *first_cluster_hosts, *first_cluster_objects)
        check_mm_is(MM_IS_OFF, *second_objects)

    with allure.step("Switch second host's MM to 'OFF'"):
        api_client.host.change_maintenance_mode(host_2.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 4)
        check_mm_is(MM_IS_ON, host_1, host_3, component_2)
        check_mm_is(MM_IS_OFF, host_2, service, component_1, *another_service_objects, *second_objects)

    with allure.step("Switch third host's MM to 'OFF'"):
        api_client.host.change_maintenance_mode(host_3.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 5)
        check_mm_is(MM_IS_ON, host_1)
        check_mm_is(MM_IS_OFF, host_2, host_3, *first_cluster_objects, *second_objects)

    with allure.step("Switch first host's MM to 'OFF' and check that everything's back to normal"):
        api_client.host.change_maintenance_mode(host_1.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 6)
        check_mm_is(MM_IS_OFF, *first_cluster_hosts, *first_cluster_objects, *second_objects)


@allure.step("Check MM related actions are not shown in actions list")
def check_mm_related_actions_are_absent_on(*adcm_objects: AnyADCMObject) -> None:
    for adcm_object in adcm_objects:
        action_names = {action.name for action in adcm_object.action_list()}
        does_not_intersect(
            action_names,
            MM_CHANGE_RELATED_ACTION_NAMES,
            f"One or more MM related actions are visible in actions list of {get_object_represent(adcm_object)}",
        )


@allure.step("Check amount of jobs is {expected_amount} and all tasks finish successfully")
def _wait_all_tasks_succeed(client: ADCMClient, expected_amount: int):
    jobs = client.job_list()
    assert len(jobs) == expected_amount
    assert all(job.task().wait() == "success" for job in jobs)


def _prepare_new_cluster(
    cluster_bundle: Bundle, cluster_name: str
) -> tuple[Cluster, Service, Component, Component, Service, Component, Component]:
    cluster = cluster_bundle.cluster_create(cluster_name)
    service_with_plugin = cluster.service_add(name="service_with_mm_plugin")
    service_second = cluster.service_add(name="service_2")
    return (
        cluster,
        service_with_plugin,
        service_with_plugin.component(name="component_with_mm_plugin"),
        service_with_plugin.component(name="component_wo_mm_plugin"),
        service_second,
        service_second.component(name="component_with_mm_plugin"),
        service_second.component(name="component_wo_mm_plugin"),
    )


def _map_components_to_hosts(
    hosts: tuple[Host, Host, Host], components: tuple[Component, Component, Component, Component]
) -> None:
    host_1, host_2, host_3 = hosts
    component_1, component_2, component_3, component_4 = components
    cluster = component_1.cluster()

    for host in (host_1, host_2, host_3):
        cluster.host_add(host)
        host.reread()

    cluster.hostcomponent_set(
        (host_1, component_1),
        (host_2, component_1),
        (host_3, component_2),
        (host_1, component_3),
        (host_2, component_3),
        (host_3, component_3),
        (host_1, component_4),
        (host_2, component_4),
        (host_3, component_4),
    )
