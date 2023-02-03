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

from pathlib import Path
from typing import Iterable

import allure
import pytest
from adcm_client.objects import Cluster, Component, Service
from tests.library.assertions import sets_are_equal
from tests.ui_tests.app.page.cluster.page import (
    ClusterComponentsPage,
    ClusterConfigPage,
    ClusterImportPage,
    ClusterServicesPage,
)
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.breadcrumbs import Breadcrumbs
from tests.ui_tests.app.page.common.concerns import ConcernPopover
from tests.ui_tests.app.page.common.left_menu import LeftMenu
from tests.ui_tests.app.page.component.page import ComponentConfigPage
from tests.ui_tests.app.page.service.page import ServiceConfigPage

BUNDLES_DIR = Path(__file__).parent / "bundles"


class Reason:
    CONFIG = "its config"
    IMPORT = "required import"
    SERVICE = "required service"
    HOST_COMPONENT = "host-component mapping"


# pylint: disable=redefined-outer-name


def _hover_concern_mark_of_last_breadcrumb(
    page: BasePageObject, breadcrumbs: Breadcrumbs | None = None
) -> ConcernPopover:
    breadcrumbs_ = breadcrumbs or page.header.get_breadcrumbs()
    breadcrumbs_.crumbs.last.get_concern_mark().hover()
    return ConcernPopover.wait_opened(page)


@pytest.fixture()
def clusters(sdk_client_fs) -> tuple[Cluster, Cluster]:
    cluster_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster")
    to_import_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / "cluster_to_import")
    return (
        cluster_bundle.cluster_create(name="WoHooo cluster"),
        to_import_bundle.cluster_create(name="Cluster to import"),
    )


@pytest.fixture()
def cluster_list_page(app_fs) -> ClusterListPage:
    return ClusterListPage(driver=app_fs.driver, base_url=app_fs.adcm.url).open()


@pytest.mark.usefixtures("_login_to_adcm_over_api")
def test_non_action_cluster_concerns(clusters, cluster_list_page):
    cluster, _ = clusters
    detail_page = open_service_concern_from_cluster_list(cluster_list_page, cluster)
    import_page = open_config_and_import_concern_on_detail_page(detail_page, cluster)
    cluster_list_page = import_cluster_and_check_concern_is_gone(import_page, cluster)
    service_with_component, required_service = add_services_and_check_concerns_changed(cluster_list_page, cluster)
    component_page, component = follow_service_and_component_concern_links(
        cluster_list_page, service_with_component, required_service
    )
    add_service_with_hc_constraint(component_page, component)


@allure.step("Open service issue from cluster list page")
def open_service_concern_from_cluster_list(list_page, cluster) -> ClusterServicesPage:
    current_concerns = (Reason.CONFIG, Reason.IMPORT, Reason.SERVICE)

    with allure.step("Check concerns in row's popover"):
        popover = list_page.hover_concern_button(row=list_page.get_row_by_cluster_name(cluster.name))
        # checking amount of concerns and to which objects they belong
        assert len(popover.concerns) == len(popover.concerns.with_link(cluster.name)) == 3
        for concern_reason in current_concerns:
            assert any(name.endswith(concern_reason) for name in popover.concerns.names)
        list_page_links = popover.get_concern_links()

    with allure.step("Follow service concern link"):
        popover.concerns.with_text(Reason.SERVICE).first.click()
        page = ClusterServicesPage(driver=list_page.driver, base_url=list_page.base_url, cluster_id=cluster.id)
        page.wait_page_is_opened(timeout=3)
        page.check_all_elements()

    check_menu(
        page,
        chosen_tab="Services",
        with_concerns=["Services", "Configuration", "Import"],
        without_concerns=["Hosts - Components"],
    )

    with allure.step("Check popover on breadcrumbs"):
        breadcrumbs = page.header.get_breadcrumbs()
        assert breadcrumbs.names == ("CLUSTERS", cluster.name.upper())
        popover = _hover_concern_mark_of_last_breadcrumb(page=page, breadcrumbs=breadcrumbs)
        assert len(popover.concerns) == len(popover.concerns.with_link(cluster.name)) == 3
        for concern_reason in current_concerns:
            assert any(name.endswith(concern_reason) for name in popover.concerns.names)
        compare_breadcrumb_and_table_row_concerns(
            from_breadcrumbs=popover.get_concern_links(), from_row=list_page_links
        )

    return page


@allure.step("Open config tab via link on detail page, then import tab")
def open_config_and_import_concern_on_detail_page(detail_page, cluster) -> ClusterImportPage:
    with allure.step("Follow config page concern link"):
        popover = _hover_concern_mark_of_last_breadcrumb(page=detail_page)
        popover.concerns.with_text(Reason.CONFIG).first.click()
        config_page: ClusterConfigPage = ClusterConfigPage.from_page(
            detail_page, cluster_id=cluster.id
        ).wait_page_is_opened(timeout=2)
        config_page.check_all_elements()

    check_menu(
        config_page,
        chosen_tab="Configuration",
        with_concerns=["Services", "Configuration", "Import"],
        without_concerns=["Hosts - Components"],
    )

    with allure.step("Follow import page concern link"):
        popover = _hover_concern_mark_of_last_breadcrumb(page=detail_page)
        popover.concerns.with_text(Reason.IMPORT).first.click()
        import_page: ClusterConfigPage = ClusterImportPage.from_page(
            detail_page, cluster_id=cluster.id
        ).wait_page_is_opened(timeout=2)
        import_page.check_all_elements()

    check_menu(
        import_page,
        chosen_tab="Import",
        with_concerns=["Configuration", "Services", "Import"],
        without_concerns=["Hosts - Components"],
    )

    return import_page


@allure.step("Import cluster and check 'Import concern' is gone from detailed and list pages")
def import_cluster_and_check_concern_is_gone(import_page, cluster) -> ClusterListPage:
    current_concerns = (Reason.CONFIG, Reason.SERVICE)

    with allure.step("Import cluster"):
        import_page.get_import_items()[0].get_available_exports()[0].check()
        import_page.click_save_btn()

    check_menu(
        import_page,
        chosen_tab="Import",
        with_concerns=["Configuration"],
        without_concerns=["Hosts - Components", "Import"],
    )

    with allure.step("Check concerns changed at breadcrumbs popover"):
        popover = _hover_concern_mark_of_last_breadcrumb(page=import_page)
        assert len(popover.concerns) == len(popover.concerns.with_link(cluster.name)) == 2
        for concern_reason in current_concerns:
            assert any(name.endswith(concern_reason) for name in popover.concerns.names)
        detail_page_links = popover.get_concern_links()

    with allure.step("Check concerns from table row"):
        import_page.header.click_clusters_tab()
        list_page = ClusterListPage.from_page(import_page).wait_page_is_opened(timeout=2)
        popover = list_page.hover_concern_button(row=list_page.get_row_by_cluster_name(cluster.name))
        assert len(popover.concerns) == len(popover.concerns.with_link(cluster.name)) == 2
        for concern_reason in current_concerns:
            assert any(name.endswith(concern_reason) for name in popover.concerns.names)
        compare_breadcrumb_and_table_row_concerns(
            from_breadcrumbs=detail_page_links, from_row=popover.get_concern_links()
        )

    return list_page


@allure.step("Add required and optional services to a cluster via API and check concern list is changed")
def add_services_and_check_concerns_changed(list_page, cluster: Cluster) -> tuple[Service, Service]:
    with allure.step("Add not required service with concerns and check concerns"):
        service: Service = cluster.service_add(name="service_with_concerns")
        component = service.component()
        row = list_page.get_row_by_cluster_name(cluster.name)
        list_page.hover_name(row)
        popover = list_page.hover_concern_button(row=row)
        assert len(popover.concerns.with_link(cluster.name).with_text(Reason.SERVICE)) == 1
        assert len(popover.concerns.with_link(cluster.name)) == 2
        for new_object in (service, component):
            concerns = popover.concerns.with_link(new_object.display_name)
            assert len(concerns) == 1
            assert concerns.first.name.endswith(Reason.CONFIG)

    with allure.step("Add required service with concerns"):
        required_service = cluster.service_add(name="very_important_service")
        list_page.hover_name(row)
        popover = list_page.hover_concern_button(row=row)
        assert len(popover.concerns.with_link(cluster.name).with_text(Reason.SERVICE)) == 0
        assert len(popover.concerns.with_link(cluster.name)) == 1
        for new_object in (required_service, service, component):
            concerns = popover.concerns.with_link(new_object.display_name)
            assert len(concerns) == 1
            assert concerns.first.name.endswith(Reason.CONFIG)

    return service, required_service


def follow_service_and_component_concern_links(list_page: ClusterListPage, service: Service, required_service: Service):
    cluster = service.cluster()
    component = service.component()

    with allure.step("Follow service config concern link from cluster list page"):
        row = list_page.get_row_by_cluster_name(cluster.name)
        list_page.hover_name(row)
        popover = list_page.hover_concern_button(row)
        popover.concerns.with_link(service.display_name).with_text(Reason.CONFIG).first.click()

        service_page = ServiceConfigPage.from_page(
            list_page, cluster_id=cluster.id, service_id=service.id
        ).wait_page_is_opened(timeout=2)
        service_page.check_all_elements()

    check_menu(service_page, "Configuration", with_concerns=["Configuration"], without_concerns=["Import"])

    with allure.step("Check breadcrumbs on service detail page"):
        breadcrumbs = service_page.header.get_breadcrumbs()
        assert breadcrumbs.names == ("CLUSTERS", cluster.name.upper(), "SERVICES", service.display_name.upper())
        popover = _hover_concern_mark_of_last_breadcrumb(page=service_page, breadcrumbs=breadcrumbs)
        assert len(popover.concerns.with_link(required_service.display_name)) == 0
        assert len(popover.concerns.with_link(service.display_name)) == 1
        assert len(popover.concerns.with_link(component.display_name)) == 1

        breadcrumbs.crumbs.named(cluster.name.upper()).get_concern_mark().hover()
        popover = ConcernPopover.wait_opened(service_page)
        assert len(popover.concerns.with_link(required_service.display_name)) == 1
        assert len(popover.concerns.with_link(service.display_name)) == 1
        assert len(popover.concerns.with_link(component.display_name)) == 1

    with allure.step("Follow component concern from service detail page"):
        popover = _hover_concern_mark_of_last_breadcrumb(page=service_page)
        popover.concerns.with_link(component.display_name).first.click()
        component_page = ComponentConfigPage.from_page(
            service_page, cluster_id=cluster.id, service_id=service.id, component_id=component.id
        ).wait_page_is_opened(timeout=2)
        component_page.check_all_elements()

    check_menu(component_page, "Configuration", with_concerns=["Configuration"])

    with allure.step("Check breadcrumbs on component detail page"):
        breadcrumbs = component_page.header.get_breadcrumbs()
        assert breadcrumbs.names == (
            "CLUSTERS",
            cluster.name.upper(),
            "SERVICES",
            service.display_name.upper(),
            "COMPONENTS",
            component.display_name.upper(),
        )
        popover = _hover_concern_mark_of_last_breadcrumb(page=component_page, breadcrumbs=breadcrumbs)
        assert len(popover.concerns.with_link(required_service.display_name)) == 0
        assert len(popover.concerns.with_link(service.display_name)) == 1
        assert len(popover.concerns.with_link(component.display_name)) == 1

    return component_page, component


def add_service_with_hc_constraint(component_page, component: Component):
    with allure.step("Add service with HC constraint"):
        cluster = component.cluster()
        cluster.service_add(name="with_constrainted_component")

    with allure.step("Check concerns from breadcrumbs"):
        component_page.refresh()
        for obj in (cluster, cluster.service(id=component.service_id), component):
            name = (obj.display_name if hasattr(obj, "display_name") else obj.name).upper()
            component_page.header.get_breadcrumbs().crumbs.named(name).get_concern_mark().hover()
            popover = ConcernPopover.wait_opened(component_page)
            assert len(popover.concerns.with_link(cluster.name).with_text(Reason.HOST_COMPONENT)) == 1

    with allure.step("Open cluster page following HC concern"):
        popover.concerns.with_link(cluster.name).with_text(Reason.HOST_COMPONENT).first.click()
        hc_page = ClusterComponentsPage.from_page(component_page, cluster_id=cluster.id).wait_page_is_opened(timeout=2)
        hc_page.check_all_elements()

        check_menu(hc_page, "Hosts - Components", with_concerns=["Hosts - Components", "Configuration"])


# !===== Checks =====!


@allure.step("Check left menu for chosen tab and concern marks")
def check_menu(page, chosen_tab: str, with_concerns: Iterable[str] = (), without_concerns: Iterable[str] = ()):
    menu: LeftMenu = page.get_menu() if hasattr(page, "get_menu") else LeftMenu.at_current_page(page)

    assert menu[chosen_tab].is_chosen

    for tab in with_concerns:
        assert menu[tab].has_concern_mark()

    for tab in without_concerns:
        assert not menu[tab].has_concern_mark()


def compare_breadcrumb_and_table_row_concerns(from_breadcrumbs: tuple[str, ...], from_row: tuple[str, ...]) -> None:
    assert len(from_breadcrumbs) == len(from_row)
    sets_are_equal(set(from_breadcrumbs), set(from_row), message="Links on list and detailed page should be the same")
