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

"""Cluster page PageObjects classes"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, List, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.checks import check_elements_are_displayed
from tests.ui_tests.app.page.cluster.components import ComponentRow
from tests.ui_tests.app.page.cluster.locators import (
    ClusterHostLocators,
    ClusterServicesLocators,
)
from tests.ui_tests.app.page.cluster.services import ServiceRow
from tests.ui_tests.app.page.common.base_page import BaseDetailedPage, BasePageObject
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog, DeleteDialog
from tests.ui_tests.app.page.common.group_config.page import CommonGroupConfigMenu
from tests.ui_tests.app.page.common.group_config_list.locators import (
    GroupConfigListLocators,
)
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigList
from tests.ui_tests.app.page.common.host_components.locators import (
    HostComponentsLocators,
)
from tests.ui_tests.app.page.common.host_components.page import HostComponentsPage
from tests.ui_tests.app.page.common.import_page.locators import ImportLocators
from tests.ui_tests.app.page.common.import_page.page import ImportPage
from tests.ui_tests.app.page.common.popups.locator import (
    HostAddPopupLocators,
    HostCreationLocators,
    ListConcernPopupLocators,
    PageConcernPopupLocators,
)
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.status.page import StatusPage
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.host_list.page import HostRowInfo


@dataclass
class StatusGroupInfo:
    """Information from group on Status page"""

    service: str
    hosts: list


class CommonClusterPage(BasePageObject):  # pylint: disable=too-many-instance-attributes
    """Helpers for working with cluster page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    host_popup: HostCreatePopupObj
    group_config = GroupConfigList

    def __init__(self, driver, base_url, cluster_id: int, **kwargs):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/cluster/{cluster_id}/" + self.MENU_SUFFIX, cluster_id=cluster_id, **kwargs)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)
        self.group_config = GroupConfigList(self.driver, self.base_url)

    def open_main_tab(self):
        """Open Main tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.main_tab)
        page = ClusterMainPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_services_tab(self):
        """Open Services tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.services_tab)
        page = ClusterServicesPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_hosts_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.hosts_tab)
        page = ClusterHostPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_components_tab(self):
        """Open Components tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.components_tab)
        page = ClusterComponentsPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Group Configuration tab by menu click")
    def open_group_config_tab(self) -> "ClusterGroupConfigPage":
        """Open Group Configuration tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.group_config_tab)
        page = ClusterGroupConfigPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_config_tab(self):
        """Open Configuration tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ClusterConfigPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_status_tab(self):
        """Open Status tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.status_tab)
        page = ClusterStatusPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    def open_import_tab(self):
        """Open Import tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.import_tab)
        page = ClusterImportPage(self.driver, self.base_url, self.cluster_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)

    def check_cluster_toolbar(self, cluster_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name])


class ClusterMainPage(CommonClusterPage, BaseDetailedPage):
    """Cluster page Main menu"""

    MENU_SUFFIX = 'main'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterServicesPage(CommonClusterPage):
    """Cluster page services menu"""

    MENU_SUFFIX = 'service'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterServicesLocators.add_services_btn,
        CommonTable.header,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]

    def get_row(self, predicate: Callable[[ServiceRow], bool]) -> ServiceRow:
        suitable_rows = self.get_rows(predicate=predicate)

        if suitable_rows:
            return suitable_rows[0]

        raise AssertionError("No suitable service row found")

    def get_rows(self, predicate: Callable[[ServiceRow], bool] = lambda _: True) -> tuple[ServiceRow, ...]:
        return tuple(
            filter(
                predicate,
                map(
                    lambda element: ServiceRow(row_element=element, driver=self._driver),
                    self.table.get_all_rows(timeout=1),
                ),
            )
        )

    def click_add_service_btn(self):
        """Click on Add service button"""
        self.find_and_click(ClusterServicesLocators.add_services_btn)

    @allure.step("Add service {service_name} to cluster")
    def add_service_by_name(self, service_name: str):
        """Add service to cluster"""
        self.find_and_click(ClusterServicesLocators.add_services_btn)
        self.wait_element_visible(ClusterServicesLocators.AddServicePopup.block)
        for service in self.find_elements(ClusterServicesLocators.AddServicePopup.service_row):
            service_text = self.find_child(service, ClusterServicesLocators.AddServicePopup.ServiceRow.text)
            if service_text.text == service_name:
                service_text.click()
        self.find_and_click(ClusterServicesLocators.AddServicePopup.create_btn)
        self.wait_element_hide(ClusterServicesLocators.AddServicePopup.block)

    @allure.step("Click on service concern object name from the row")
    def click_on_concern_by_object_name(self, row: WebElement, concern_object_name: str):
        """Click on concern object link from the row"""
        self.hover_element(self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions))
        self.wait_element_visible(ListConcernPopupLocators.block)
        for issue in self.find_elements(ListConcernPopupLocators.link_to_concern_object):
            if concern_object_name in issue.text:
                issue.click()
                return
        raise AssertionError(f"Issue name '{concern_object_name}' not found in issues")

    def click_action_btn_in_row(self, row: WebElement):
        """Click on Action button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions).click()

    def click_delete_btn_in_row(self, row: WebElement):
        """Click on delete button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    def click_import_btn_in_row(self, row: WebElement):
        """Click on Import button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.service_import).click()

    def click_config_btn_in_row(self, row: WebElement):
        """Click on Config button from the row"""
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.config).click()

    def get_service_state_from_row(self, row: WebElement):
        """Get service state from the row"""
        return self.find_child(row, ClusterServicesLocators.ServiceTableRow.state).text

    @allure.step("Run action {action_name} for service")
    def run_action_in_service_row(self, row: WebElement, action_name: str):
        """Run Action by Action button from the row"""
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @contextmanager
    def wait_service_state_change(self, row: WebElement):
        """Wait for service state to change"""
        state_before = self.get_service_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_service_state_from_row(row)
            assert state_after != state_before, f"State should not be equal {state_before}"
            assert (
                state_after != self.table.LOADING_STATE_TEXT
            ), f"State should not be equal {self.table.LOADING_STATE_TEXT}"

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)


class ServiceComponentsPage(BasePageObject):
    def __init__(self, driver, base_url, cluster_id: int, service_id: int):
        super().__init__(
            driver,
            base_url,
            path_template="/cluster/{cluster_id}/service/{service_id}/component",
            cluster_id=cluster_id,
            service_id=service_id,
        )
        self.table = CommonTableObj(self.driver, self.base_url)

    def get_row(self, predicate: Callable[[ComponentRow], bool]) -> ComponentRow:
        suitable_rows = self.get_rows(predicate=predicate)

        if suitable_rows:
            return suitable_rows[0]

        raise AssertionError("No suitable component row found")

    def get_rows(self, predicate: Callable[[ComponentRow], bool] = lambda _: True) -> tuple[ComponentRow, ...]:
        return tuple(
            filter(
                predicate,
                map(
                    lambda element: ComponentRow(row_element=element, driver=self._driver),
                    self.table.get_all_rows(timeout=1),
                ),
            )
        )


class ClusterImportPage(CommonClusterPage, ImportPage):
    """Cluster page import menu"""

    MENU_SUFFIX = 'import'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ImportLocators.save_btn,
        ImportLocators.import_item_block,
    ]


class ClusterConfigPage(CommonClusterPage):
    """Cluster page config menu"""

    MENU_SUFFIX = 'config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        CommonConfigMenu.description_input,
        CommonConfigMenu.search_input,
        CommonConfigMenu.advanced_label,
        CommonConfigMenu.save_btn,
        CommonConfigMenu.history_btn,
    ]

    @allure.step('Check that group field is visible = {is_group_visible} if group is active = {is_group_active}')
    def check_groups(
        self,
        group_names: List[str],
        is_group_visible: bool = True,
        is_group_active: bool = True,
        is_subs_visible: bool = True,
    ):
        group_names_on_page = [name.text for name in self.config.get_group_names()]
        if is_group_visible:
            assert group_names_on_page, "There are should be groups on the page"
            for group_name in group_names:
                self.config.expand_or_close_group(group_name, expand=is_group_active)
                self.config.check_subs_visibility(group_name, is_subs_visible)
                assert group_name in group_names_on_page, f"There is no {group_name} group on the page"
        else:
            for group_name in group_names:
                assert group_name not in group_names_on_page, f"There is visible '{group_name}' group on the page"


class ClusterGroupConfigPage(CommonClusterPage):
    """Cluster page group config menu"""

    MENU_SUFFIX = 'group_config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
        GroupConfigListLocators.header_item,
        GroupConfigListLocators.add_btn,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]


class ClusterHostPage(CommonClusterPage):
    """Cluster page host menu"""

    MENU_SUFFIX = 'host'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterHostLocators.add_host_btn,
        CommonTable.header,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]

    @allure.step("Click on add host button")
    def click_add_host_btn(self, is_not_first_host: bool = True):
        """
        Click on the button 'Add host' under the host table.
        In case there are any hosts that have been added earlier
        (no matter from this popup or from host list page)
        there will be a popup with the list of the existing hosts,
        so to open creating host popup you need again to click on
        a special button for creating hosts.
        In case there are no hosts at all, creating hosts popup will be open instantly.
        :param is_not_first_host: flag to indicate if there are any created hosts in adcm.
        """

        self.find_and_click(ClusterHostLocators.add_host_btn)
        self.wait_element_visible(HostCreationLocators.block)
        if is_not_first_host:
            self.wait_element_visible(HostAddPopupLocators.add_new_host_btn).click()

    @allure.step("Get info about host row")
    def get_host_info_from_row(self, row_num: int = 0, table_has_cluster_column: bool = True) -> HostRowInfo:
        """
        Compile the values of the fields describing the host.
        :param table_has_cluster_column: flag to define if there is a cluster column in the table
        (e.g. there are no such column in cluster host page).
        :param row_num: row number in the table.
        """
        row = self.table.get_all_rows()[row_num]
        row_elements = ClusterHostLocators.HostTable.HostRow
        cluster_value = (
            self.find_child(row, row_elements.cluster).text
            if table_has_cluster_column
            else HostRowInfo.UNASSIGNED_CLUSTER_VALUE
        )
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=self.find_child(row, row_elements.cluster).text
            if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE
            else None,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step("Click on host name in row")
    def click_on_host_name_in_host_row(self, row: WebElement):
        """Click on Host name in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.fqdn).click()

    @allure.step("Click on action in host row")
    def click_on_action_btn_in_host_row(self, row: WebElement):
        """Click on Action button in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions).click()

    @allure.step("Click on config in host row")
    def click_config_btn_in_row(self, row: WebElement):
        """Click on Configuration button in the Host row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.config).click()

    @allure.step('Click on concern of "{concern_object_name}" in host concerns')
    def click_on_concern_by_object_name(self, row: WebElement, concern_object_name: str):
        """Click on concern link in Host concerns"""
        self.hover_element(self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions))
        self.wait_element_visible(PageConcernPopupLocators.block)
        for concern in self.find_elements(PageConcernPopupLocators.link_to_concern_object):
            if concern_object_name in concern.text:
                concern.click()
                return
        raise AssertionError(f'Concern name "{concern_object_name}" not found in concerns')

    def get_host_state_from_row(self, row: WebElement):
        """Get Host state from the row"""
        return self.find_child(row, ClusterHostLocators.HostTable.HostRow.state).text

    @contextmanager
    def wait_host_state_change(self, row: WebElement):
        """Wait for Host state to change"""
        state_before = self.get_host_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_host_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Run action {action_name} for host")
    def run_action_in_host_row(self, row: WebElement, action_name: str):
        """Run Host action from the row"""
        self.click_on_action_btn_in_host_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step("Delete host")
    def delete_host_by_row(self, row: WebElement):
        """Delete Host by button from the row"""
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.link_off_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    def check_cluster_hosts_toolbar(self, cluster_name: str, host_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name, "HOSTS", host_name])

    @allure.step('Click on maintenance mode button in row {row_num}')
    def click_on_maintenance_mode_btn(self, row_num: int):
        """Click maintenance mode in row"""

        row = self.table.get_row(row_num)
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.maintenance_mode_btn).click()

    @allure.step('Assert maintenance mode state in row {row_num}')
    def assert_maintenance_mode_state(self, row_num: int, is_mm_state_on: Optional[bool] = True):
        """
        Assert maintenance mode state in row
        :param row_num: number of the row with maintenance mode button
        :param is_mm_state_on: state of maintenance mode button:
            True for ON state
            False for OFF state
            None for not available state
        """

        def _check_mm_state(page: ClusterHostPage, row: WebElement):
            button_state = page.find_child(
                row, ClusterHostLocators.HostTable.HostRow.maintenance_mode_btn
            ).get_attribute("class")
            tooltips_info = [
                t.get_property("innerHTML") for t in page.find_elements(ClusterHostLocators.HostTable.tooltip_text)
            ]
            if is_mm_state_on:
                assert "mat-primary" in button_state, "Button should be gray"
                assert (
                    "Turn maintenance mode ON" in tooltips_info
                ), "There should be tooltip that user could turn on maintenance mode"
            elif is_mm_state_on is False:
                assert "mat-on" in button_state, "Button should be red"
                assert (
                    "Turn maintenance mode OFF" in tooltips_info
                ), "There should be tooltip that user could turn off maintenance mode"
            else:
                assert "mat-button-disabled" in button_state, "Button should be disabled"
                assert (
                    "Maintenance mode is not available" in tooltips_info
                ), "There should be tooltip that maintenance mode is not available"

        host_row = self.table.get_row(row_num)
        wait_until_step_succeeds(_check_mm_state, timeout=4, period=0.5, page=self, row=host_row)


class ClusterComponentsPage(CommonClusterPage, HostComponentsPage):
    """Cluster page components menu"""

    MENU_SUFFIX = 'host_component'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        HostComponentsLocators.restore_btn,
        HostComponentsLocators.save_btn,
        HostComponentsLocators.components_title,
        HostComponentsLocators.hosts_title,
        HostComponentsLocators.service_page_link,
        HostComponentsLocators.hosts_page_link,
    ]


class ClusterStatusPage(CommonClusterPage, StatusPage):
    """Cluster page status menu"""

    MENU_SUFFIX = 'status'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterGroupConfigPageMixin(BasePageObject):  # pylint: disable-next=too-many-instance-attributes
    """Helpers for working with cluster group config page"""

    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    group_config_id: int
    config: CommonConfigMenuObj
    group_config: CommonGroupConfigMenu
    toolbar: CommonToolbar
    table: CommonTableObj

    def __init__(self, driver, base_url, cluster_id: int, group_config_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/group_config/{group_config_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            group_config_id=group_config_id,
        )
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.group_config = CommonGroupConfigMenu(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.group_config_id = group_config_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        """Assert all main elements presence"""
        check_elements_are_displayed(self, self.MAIN_ELEMENTS)

    def open_hosts_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.hosts_tab)
        page = ClusterGroupConfigHosts(self.driver, self.base_url, self.cluster_id, self.group_config_id)
        page.wait_page_is_opened()
        return page

    def open_config_tab(self):
        """Open Hosts tab by menu click"""

        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ClusterGroupConfigConfig(self.driver, self.base_url, self.cluster_id, self.group_config_id)
        page.wait_page_is_opened()
        return page

    def check_cluster_group_conf_toolbar(self, cluster_name: str, group_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name, "GROUPCONFIGS", group_name])


class ClusterGroupConfigHosts(ClusterGroupConfigPageMixin):
    """Cluster page status menu"""

    MENU_SUFFIX = 'host'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ClusterGroupConfigConfig(ClusterGroupConfigPageMixin):
    """Cluster page status menu"""

    MENU_SUFFIX = 'config'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]
