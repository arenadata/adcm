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

"""Service page PageObjects classes"""


from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.page.common.base_page import (
    BaseDetailedPage,
    BasePageObject,
    PageFooter,
    PageHeader,
)
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog
from tests.ui_tests.app.page.common.group_config_list.locators import (
    GroupConfigListLocators,
)
from tests.ui_tests.app.page.common.group_config_list.page import GroupConfigList
from tests.ui_tests.app.page.common.import_page.locators import ImportLocators
from tests.ui_tests.app.page.common.import_page.page import ImportPage
from tests.ui_tests.app.page.common.status.page import StatusPage
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.service.locators import ServiceComponentLocators


class ServicePageMixin(BasePageObject):  # pylint: disable=too-many-instance-attributes
    """Helpers for working with service page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    service_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    group_config = GroupConfigList

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, cluster_id: int, service_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(
            driver,
            base_url,
            "/cluster/{cluster_id}/service/{service_id}/" + self.MENU_SUFFIX,
            cluster_id=cluster_id,
            service_id=service_id,
        )
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.service_id = service_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)
        self.group_config = GroupConfigList(self.driver, self.base_url)

    @allure.step("Open Main tab by menu click")
    def open_main_tab(self) -> "ServiceMainPage":
        """Open Main tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.main_tab)
        page = ServiceMainPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Components tab by menu click")
    def open_components_tab(self) -> "ServiceComponentPage":
        """Open Components tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.service_components_tab)
        page = ServiceComponentPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Configuration tab by menu click")
    def open_config_tab(self) -> "ServiceConfigPage":
        """Open Configuration tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.config_tab)
        page = ServiceConfigPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Group Configuration tab by menu click")
    def open_group_config_tab(self) -> "ServiceGroupConfigPage":
        """Open Group Configuration tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.group_config_tab)
        page = ServiceGroupConfigPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Status tab by menu click")
    def open_status_tab(self) -> "ServiceStatusPage":
        """Open Status tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.status_tab)
        page = ServiceStatusPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Open Import tab by menu click")
    def open_import_tab(self) -> "ServiceImportPage":
        """Open Import tab by menu click"""
        self.find_and_click(ObjectPageMenuLocators.import_tab)
        page = ServiceImportPage(self.driver, self.base_url, self.cluster_id, self.service_id)
        page.wait_page_is_opened()
        return page

    @allure.step("Assert that all main elements on the page are presented")
    def check_all_elements(self):
        """Assert all main elements presence"""
        self.assert_displayed_elements(self.MAIN_ELEMENTS)

    def check_service_toolbar(self, cluster_name: str, service_name: str):
        self.toolbar.check_toolbar_elements(["CLUSTERS", cluster_name, "SERVICES", service_name])


class ServiceMainPage(ServicePageMixin, BaseDetailedPage):
    """Service page Main menu"""

    MENU_SUFFIX = 'main'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ServiceComponentPage(ServicePageMixin):
    """Service page component menu"""

    MENU_SUFFIX = 'component'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        CommonTable.header,
        CommonTable.row,
    ]

    def click_action_btn_in_row(self, row: WebElement):
        """Click on Action button from the row"""
        self.find_child(row, ServiceComponentLocators.ComponentRow.actions).click()

    @allure.step("Run action {action_name} for component")
    def run_action_in_component_row(self, row: WebElement, action_name: str):
        """Run Action by Action button from the row"""
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    def get_component_state_from_row(self, row: WebElement):
        """Get component state from the row"""
        return self.find_child(row, ServiceComponentLocators.ComponentRow.state).text

    @contextmanager
    def wait_component_state_change(self, row: WebElement):
        """Wait for component state to change"""
        state_before = self.get_component_state_from_row(row)
        yield

        def _wait_state():
            state_after = self.get_component_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)


class ServiceConfigPage(ServicePageMixin):
    """Service page Main menu"""

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


class ServiceGroupConfigPage(ServicePageMixin):
    """Service page GroupConfig menu"""

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


class ServiceStatusPage(ServicePageMixin, StatusPage):
    """Service page GroupConfig menu"""

    MENU_SUFFIX = 'status'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ObjectPageLocators.text,
    ]


class ServiceImportPage(ServicePageMixin, ImportPage):
    """Service page Main menu"""

    MENU_SUFFIX = 'import'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ImportLocators.save_btn,
        ImportLocators.import_item_block,
    ]
