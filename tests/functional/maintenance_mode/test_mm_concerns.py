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

"""Test designed to check behaviour of service and components with concern when they switched to MM 'ON'"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Cluster, Provider

from tests.functional.maintenance_mode.conftest import (
    BUNDLES_DIR,
    MM_IS_OFF,
    MM_IS_ON,
    add_hosts_to_cluster,
    check_concerns_on_object,
    check_mm_is,
    check_no_concerns_on_objects,
    set_maintenance_mode,
)
from tests.library.api.core import RequestResult

# pylint: disable=redefined-outer-name

DEFAULT_CLUSTER_PARAM = 12
EXPECTED_ERROR = "LOCK_ERROR"


@pytest.fixture()
def cluster_actions(sdk_client_fs) -> Cluster:
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_with_concerns" / "concern_cluster_action")
    cluster = bundle.cluster_create("Cluster actions")
    cluster.service_add(name="first_service")
    return cluster


@pytest.fixture()
def cluster_with_concern(sdk_client_fs) -> Cluster:
    """Create cluster and add service"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_with_concerns" / "concern_cluster")
    cluster = bundle.cluster_create("Cluster concern")
    cluster.service_add(name="first_service")
    return cluster


@pytest.fixture()
def provider_with_concern(sdk_client_fs) -> Provider:
    """Create provider and host"""
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "provider_with_issues")
    provider = bundle.provider_create("Provider with concerns")
    return provider


def test_mm_concern_cluster(api_client, cluster_with_concern, hosts):
    """
    Test to check behaviour cluster objects when cluster have a concern
    cluster, service and second_component have a concern
    """
    first_host, second_host, *_ = hosts
    cluster = cluster_with_concern
    first_service = cluster.service(name="first_service")
    first_component = first_service.component(name="first_component")
    second_component = first_service.component(name="second_component")

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    for obj in (cluster, first_service, second_component, second_host):
        check_concerns_on_object(
            adcm_object=obj,
            expected_concerns={cluster.name, first_service.name, second_component.name},
        )
    for obj in (first_component, first_host):
        check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name, first_service.name})

    with allure.step("Switch service MM 'ON' and check cluster objects"):
        set_maintenance_mode(api_client, first_service, MM_IS_ON)

        check_mm_is(MM_IS_ON, first_service, first_component, second_component)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        for obj in (cluster, first_component, first_host, second_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name})
        check_concerns_on_object(adcm_object=first_service, expected_concerns={cluster.name, first_service.name})
        check_concerns_on_object(adcm_object=second_component, expected_concerns={cluster.name, second_component.name})

    with allure.step(
        "Switch MM 'OFF' on service and component objects,"
        "switch MM 'ON' on component with concern and check cluster objects",
    ):
        set_maintenance_mode(api_client, first_service, MM_IS_OFF)
        set_maintenance_mode(api_client, second_component, MM_IS_ON)

        check_mm_is(MM_IS_ON, second_component)
        check_mm_is(MM_IS_OFF, first_service, first_component, first_host, second_host)

        check_concerns_on_object(
            adcm_object=second_component,
            expected_concerns={cluster.name, first_service.name, second_component.name},
        )
        for obj in (cluster, first_service, first_component, first_host, second_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name, first_service.name})

    with allure.step("Switch component to MM 'OFF', switch host to MM 'ON' and check cluster objects"):
        set_maintenance_mode(api_client, second_component, MM_IS_OFF)
        set_maintenance_mode(api_client, first_host, MM_IS_ON)

        check_mm_is(MM_IS_ON, first_component, first_host)
        check_mm_is(MM_IS_OFF, first_service, second_component, second_host)

        for obj in (cluster, first_service, second_component, second_host):
            check_concerns_on_object(
                adcm_object=obj,
                expected_concerns={cluster.name, first_service.name, second_component.name},
            )
        for obj in (first_component, first_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name, first_service.name})

    with allure.step("Switch another host to MM 'ON' and check cluster objects"):
        set_maintenance_mode(api_client, second_host, MM_IS_ON)

        check_mm_is(MM_IS_ON, first_service, first_component, first_host, second_component, second_host)

        for obj in (cluster, first_component, first_host, second_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name})
        check_concerns_on_object(adcm_object=first_service, expected_concerns={cluster.name, first_service.name})
        check_concerns_on_object(adcm_object=second_component, expected_concerns={cluster.name, second_component.name})

    with allure.step("Switch hosts to MM 'OFF' and check cluster objects"):
        set_maintenance_mode(api_client, first_host, MM_IS_OFF)
        set_maintenance_mode(api_client, second_host, MM_IS_OFF)

        check_mm_is(MM_IS_OFF, first_service, first_component, first_host, second_component, second_host)

        for obj in (cluster, first_service, second_component, second_host):
            check_concerns_on_object(
                adcm_object=obj,
                expected_concerns={cluster.name, first_service.name, second_component.name},
            )
        for obj in (first_component, first_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={cluster.name, first_service.name})


def test_mm_concern_provider_host(api_client, provider_with_concern, cluster_with_mm, hosts):
    """Test to check behaviour provider objects with hosts when provider have a concern"""
    first_host, *_ = hosts
    cluster = cluster_with_mm
    first_service = cluster.service()
    first_component = first_service.component()

    provider = provider_with_concern
    host_concern = provider.host_create("host-with-concerns")

    add_hosts_to_cluster(cluster, (first_host, host_concern))
    cluster.hostcomponent_set(
        (first_host, first_component),
        (host_concern, first_component),
    )
    for obj in (cluster, first_service, first_component, host_concern):
        check_concerns_on_object(adcm_object=obj, expected_concerns={provider.name, host_concern.fqdn})

    check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})

    check_no_concerns_on_objects(first_host)

    with allure.step("Switch service to MM 'ON' and check cluster objects and hosts"):
        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_component)
        check_mm_is(MM_IS_OFF, first_host, host_concern)

        check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})
        for obj in (first_component, host_concern):
            check_concerns_on_object(adcm_object=obj, expected_concerns={provider.name, host_concern.fqdn})

        check_no_concerns_on_objects(first_service, first_host)

    with allure.step("Switch component to MM 'ON' and check cluster objects and hosts"):
        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_component)
        check_mm_is(MM_IS_OFF, first_host, host_concern)

        check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})
        for obj in (first_component, host_concern):
            check_concerns_on_object(adcm_object=obj, expected_concerns={provider.name, host_concern.fqdn})

        check_no_concerns_on_objects(cluster, first_service, first_host)

    with allure.step(
        "Switch service and component to MM 'OFF', "
        "switch host without concern to MM 'ON' and check cluster objects and hosts",
    ):
        set_maintenance_mode(api_client=api_client, adcm_object=first_service, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=first_component, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_host)
        check_mm_is(MM_IS_OFF, first_service, first_component, host_concern)

        check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})
        for obj in (cluster, first_service, first_component, host_concern):
            check_concerns_on_object(adcm_object=obj, expected_concerns={provider.name, host_concern.fqdn})

        check_no_concerns_on_objects(first_host)

    with allure.step("Switch host with concern to MM 'ON' and check cluster objects and hosts"):
        set_maintenance_mode(api_client=api_client, adcm_object=host_concern, maintenance_mode=MM_IS_ON)
        check_mm_is(MM_IS_ON, first_service, first_component, first_host, host_concern)

        check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})
        check_concerns_on_object(adcm_object=host_concern, expected_concerns={provider.name, host_concern.fqdn})
        check_no_concerns_on_objects(cluster, first_component, first_host)

    with allure.step("Switch all objects to MM 'OFF' and check cluster objects and hosts"):
        set_maintenance_mode(api_client=api_client, adcm_object=first_host, maintenance_mode=MM_IS_OFF)
        set_maintenance_mode(api_client=api_client, adcm_object=host_concern, maintenance_mode=MM_IS_OFF)
        check_mm_is(MM_IS_OFF, first_service, first_component, first_host, host_concern)

        check_concerns_on_object(adcm_object=provider, expected_concerns={provider.name})
        for obj in (cluster, first_service, first_component, host_concern):
            check_concerns_on_object(adcm_object=obj, expected_concerns={provider.name, host_concern.fqdn})

        check_no_concerns_on_objects(first_host)


def test_mm_concern_upgrade(api_client, sdk_client_fs, hosts):
    """Test to check behaviour objects with concern after upgrade"""
    first_host, second_host, *_ = hosts
    old_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_with_concerns" / "concern_upgrade" / "cluster")
    cluster = old_bundle.cluster_create("Old cluster")

    first_service = cluster.service_add(name="test_service")
    first_component = first_service.component(name="test_component")
    second_component = first_service.component(name="new_component")

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    cluster_objects = cluster, first_service, first_component, second_component, first_host, second_host
    check_no_concerns_on_objects(*cluster_objects)

    with allure.step(f"Switch {second_component.name} without concern to MM 'ON' before upgrade cluster"):
        set_maintenance_mode(api_client, second_component, MM_IS_ON)
        check_mm_is(MM_IS_ON, second_component)

    with allure.step(f"Upgrade cluster to config with concern on {second_component.name}"):
        sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_with_concerns" / "concern_upgrade" / "second_cluster")
        upgrade_task = cluster.upgrade().do()
        if upgrade_task:
            upgrade_task.wait()
        cluster.reread()

    with allure.step(f"Check that {second_component.name} have MM 'ON' after upgrade and cluster have concern"):
        check_mm_is(MM_IS_ON, second_component)
        check_concerns_on_object(adcm_object=second_component, expected_concerns={second_component.name})
        check_no_concerns_on_objects(cluster, first_service, first_component, first_host, second_host)

    with allure.step(f"Switch MM to 'OFF' on {second_component.name} and check concerns on cluster"):
        set_maintenance_mode(api_client, second_component, MM_IS_OFF)
        check_mm_is(MM_IS_OFF, second_component)

        for obj in (cluster, first_service, second_component, second_host):
            check_concerns_on_object(obj, {second_component.name})
        check_no_concerns_on_objects(first_component, first_host)


def test_mm_concern_action(api_client, sdk_client_fs, cluster_actions, hosts):
    """
    Test to check behaviour objects with concerns and actions
    service and second_component have a concern
    """
    first_host, second_host, *_ = hosts
    cluster = cluster_actions
    first_service = cluster.service(name="first_service")
    first_component = first_service.component(name="first_component")
    second_component = first_service.component(name="second_component")

    add_hosts_to_cluster(cluster, (first_host, second_host))
    cluster.hostcomponent_set(
        (first_host, first_component),
        (second_host, second_component),
    )

    for obj in (cluster, first_service, second_component, second_host):
        check_concerns_on_object(adcm_object=obj, expected_concerns={first_service.name, second_component.name})
    for obj in (first_component, first_host):
        check_concerns_on_object(adcm_object=obj, expected_concerns={first_service.name})

    with allure.step("Switch component with concern and action to MM 'ON' and check cluster objects"):
        api_client.component.change_maintenance_mode(second_component.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 1)
        check_mm_is(MM_IS_ON, second_component)
        check_mm_is(MM_IS_OFF, first_service, first_component, first_host, second_host)

        check_concerns_on_object(
            adcm_object=second_component,
            expected_concerns={first_service.name, second_component.name},
        )
        for obj in (cluster, first_service, first_component, first_host, second_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={first_service.name})

    with allure.step("Switch service with concern and action to MM 'ON' and check cluster objects"):
        api_client.service.change_maintenance_mode(first_service.id, MM_IS_ON).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 2)
        check_mm_is(MM_IS_ON, first_service, first_component, second_component)
        check_mm_is(MM_IS_OFF, first_host, second_host)

        check_concerns_on_object(adcm_object=first_service, expected_concerns={first_service.name})
        check_concerns_on_object(adcm_object=second_component, expected_concerns={second_component.name})
        check_no_concerns_on_objects(cluster, first_host, second_host)

    with allure.step("Switch seervice and component with concern and action to MM 'OFF'"):
        api_client.service.change_maintenance_mode(first_service.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 3)
        api_client.component.change_maintenance_mode(second_component.id, MM_IS_OFF).check_code(200)
        _wait_all_tasks_succeed(sdk_client_fs, 4)
        check_mm_is(MM_IS_OFF, first_service, first_component, second_component, first_host, second_host)

        for obj in (cluster, first_service, second_component, second_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={first_service.name, second_component.name})
        for obj in (first_component, first_host):
            check_concerns_on_object(adcm_object=obj, expected_concerns={first_service.name})

    with allure.step(f"Fix concern on {first_service.name} and {second_component.name}"):
        service_config = first_service.config()
        service_config["some_param_cluster"] = DEFAULT_CLUSTER_PARAM
        first_service.config_set(service_config)
        second_component_config = second_component.config()
        second_component_config["some_param_cluster"] = DEFAULT_CLUSTER_PARAM
        second_component.config_set(second_component_config)

    with allure.step("Start simple cluster action and switch component to MM 'ON'"):
        cluster.action(name="cluster_action").run()
        check_response_error(
            response=api_client.component.change_maintenance_mode(second_component.id, MM_IS_ON),
            expected_error=EXPECTED_ERROR,
        )


@allure.step("Check amount of jobs and all tasks finish successfully")
def _wait_all_tasks_succeed(client: ADCMClient, expected_amount: int):
    jobs = client.job_list()
    assert len(jobs) == expected_amount
    assert all(job.task().wait() == "success" for job in jobs)


@allure.step("Check response contain correct error")
def check_response_error(response: RequestResult, expected_error: str) -> None:
    """Method to check error message in response"""
    assert (
        response.data["code"] == expected_error
    ), f"Incorrect request data code.\nActual: {response.data['code']}\nExpected: {expected_error}"
