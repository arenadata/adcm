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

from itertools import chain

import allure
import pytest
from adcm_client.objects import Cluster, Service
from adcm_pytest_plugin.utils import get_data_dir
from tests.library.predicates import attr_is, name_is
from tests.library.retry import should_become_truth
from tests.library.utils import get_or_raise
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.cluster.elements import ComponentRow, ServiceRow
from tests.ui_tests.app.page.cluster.page import (
    ClusterServicesPage,
    ServiceComponentsPage,
)
from tests.ui_tests.app.page.common.base_page import Header

# pylint: disable=redefined-outer-name

pytestmark = [pytest.mark.usefixtures("_login_to_adcm_over_api")]


@pytest.fixture()
def cluster(sdk_client_fs) -> Cluster:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__)).cluster_create("Awesome")


@pytest.fixture()
def services(cluster) -> tuple[Service, Service, Service]:
    return (
        cluster.service_add(name="no_mm_action"),
        cluster.service_add(name="mm_action"),
        cluster.service_add(name="mm_long_action"),
    )


@pytest.fixture()
def _map_components_to_hosts(cluster, services, generic_provider):
    host = cluster.host_add(generic_provider.host_create("some-host"))
    cluster.hostcomponent_set(
        *[(host, component) for component in chain.from_iterable(service.component_list() for service in services)]
    )


@pytest.fixture()
def cluster_services_page(app_fs, cluster) -> ClusterServicesPage:
    return ClusterServicesPage(app_fs.driver, app_fs.adcm.url, cluster_id=cluster.id)


@pytest.fixture()
def long_action_components_page(app_fs, cluster, services) -> ServiceComponentsPage:
    *_, service = services
    return ServiceComponentsPage(app_fs.driver, app_fs.adcm.url, cluster_id=cluster.id, service_id=service.id)


@pytest.mark.usefixtures("_map_components_to_hosts")
def test_switch_service_maintenance_mode(cluster, app_fs, services, cluster_services_page):
    no_action_service, short_action_service, long_action_service = services

    with allure.step("Open page with services and check MM is OFF"):
        services_page = cluster_services_page.open(close_popup=True)
        services = services_page.get_rows()
        assert len(services) == 3
        assert all(row.maintenance_mode == "OFF" for row in services)

    with allure.step("Turn MM ON on one of services"):
        no_action_row = get_or_raise(services, name_is(no_action_service.name))
        no_action_row.maintenance_mode_button.click()
        should_become_truth(lambda: no_action_row.maintenance_mode == "ON", period=0.3)
        should_become_truth(
            lambda: (
                get_or_raise(services, name_is(long_action_service.name)).maintenance_mode == "OFF"
                and get_or_raise(services, name_is(short_action_service.name)).maintenance_mode == "OFF"
            ),
            period=0.3,
        )

    with allure.step("Check that all service's components are ON, components of another service are OFF"):
        components_page = _open_components_page_for_service(no_action_service, app_fs)
        assert all(row.maintenance_mode == "ON" for row in components_page.get_rows())
        another_components = _open_components_page_for_service(short_action_service, app_fs)
        assert all(row.maintenance_mode == "OFF" for row in another_components.get_rows())

    with allure.step("Change MM back to OFF and check services and components"):
        services_page.open()
        no_action_row = services_page.get_row(name_is(no_action_service.name))
        no_action_row.maintenance_mode_button.click()
        should_become_truth(lambda: all(row.maintenance_mode == "OFF" for row in services_page.get_rows()), period=0.3)
        components_page.open()
        assert all(row.maintenance_mode == "OFF" for row in components_page.get_rows())


@pytest.mark.usefixtures("_map_components_to_hosts")
def test_switch_component_maintenance_mode(cluster, services, long_action_components_page, cluster_services_page):
    *_, long_action_service = services

    with allure.step("Turn component's MM ON"):
        components_page = long_action_components_page.open(close_popup=True)
        components: tuple[ComponentRow, ...] = components_page.get_rows()
        assert len(components) == 2
        assert all(row.maintenance_mode == "OFF" for row in components)
        without_action = get_or_raise(components, name_is("no_action"))
        without_action.maintenance_mode_button.click()
        should_become_truth(lambda: without_action.maintenance_mode == "ON", period=0.3)
        assert get_or_raise(components, name_is("with_action")).maintenance_mode == "OFF"

    with allure.step("Check all services' maintenance_mode is OFF"):
        services_page = cluster_services_page.open()
        assert all(row.maintenance_mode == "OFF" for row in services_page.get_rows())

    with allure.step("Turn component with action to MM ON"):
        components_page.open()
        components: tuple[ComponentRow, ...] = components_page.get_rows()
        get_or_raise(components, name_is("with_action")).maintenance_mode_button.click()
        expect_job_start_and_succeed(components_page.header, 1)
        should_become_truth(lambda: all(row.maintenance_mode == "ON" for row in components), retries=5, period=0.2)

    with allure.step("Check one service is now in MM"):
        services_page.open()
        services: tuple[ServiceRow, ...] = services_page.get_rows()
        assert get_or_raise(services, name_is(long_action_service.name)).maintenance_mode == "ON"
        not_in_mm = tuple(filter(attr_is("maintenance_mode", "OFF"), services))
        assert len(not_in_mm) == 2

    with allure.step("Turn component back OFF and check MM of components and services"):
        components_page.open()
        components: tuple[ComponentRow, ...] = components_page.get_rows()
        with_action: ComponentRow = get_or_raise(components, name_is("with_action"))
        with_action.maintenance_mode_button.click()
        expect_job_start_and_succeed(components_page.header, 2)
        should_become_truth(lambda: with_action.maintenance_mode == "OFF", retries=5, period=0.2)
        assert get_or_raise(components, name_is("no_action")).maintenance_mode == "ON"

        services_page.open()
        assert len(services_page.get_rows(attr_is("maintenance_mode", "OFF"))) == 3


def test_change_mm_with_and_without_hc(cluster, services, cluster_services_page, generic_provider, app_fs):
    _, service_with_action, _ = services

    with allure.step("Change one unmapped service"):
        services_page = cluster_services_page.open(close_popup=True)
        service, *_ = services_page.get_rows(name_is(service_with_action.name))
        service.maintenance_mode_button.click()
        should_become_truth(lambda: service.maintenance_mode == "ON", period=0.3)
        check_amount_of_jobs(services_page.header, 0, 0, 0)
        service.maintenance_mode_button.click()
        should_become_truth(lambda: service.maintenance_mode == "OFF", period=0.3)

    with allure.step("Change one unmapped component"):
        components_page = _open_components_page_for_service(service_with_action, app_fs)
        component, *_ = components_page.get_rows(name_is("with_action"))
        assert component.maintenance_mode == "OFF"
        component.maintenance_mode_button.click()
        should_become_truth(lambda: component.maintenance_mode == "ON", period=0.3)
        check_amount_of_jobs(components_page.header, 0, 0, 0)
        component.maintenance_mode_button.click()
        should_become_truth(lambda: component.maintenance_mode == "OFF", period=0.3)

    with allure.step("Map service to a host and check action's launched now"):
        cluster.hostcomponent_set(
            (cluster.host_add(generic_provider.host_create("some-host")), service_with_action.component())
        )
        services_page.open()
        service, *_ = services_page.get_rows(name_is(service_with_action.name))
        service.maintenance_mode_button.click()
        should_become_truth(lambda: services_page.header.get_in_progress_job_amount() == 1, retries=5, period=0.3)


def expect_job_start_and_succeed(header: Header, expected_succeed: int) -> None:
    should_become_truth(lambda: header.get_in_progress_job_amount() == 1, retries=5, period=0.3)
    should_become_truth(lambda: header.get_success_job_amount() == expected_succeed, retries=20)


def check_amount_of_jobs(header: Header, succeed: int, in_progress: int, failed: int) -> None:
    assert header.get_success_job_amount() == succeed
    assert header.get_in_progress_job_amount() == in_progress
    assert header.get_failed_job_amount() == failed
    header.hover_logo()


def _open_components_page_for_service(service: Service, app: ADCMTest) -> ServiceComponentsPage:
    return ServiceComponentsPage(
        app.driver, app.adcm.url, cluster_id=service.cluster().id, service_id=service.id
    ).open()
