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

from contextlib import contextmanager

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.cluster.locators import (
    ClusterImportLocators,
    ClusterMainLocators,
    ClusterServicesLocators,
    ClusterHostLocators,
)
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.common_locators import (
    ObjectPageLocators,
    ObjectPageMenuLocators,
)
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs import (
    ActionDialog,
    DeleteDialog,
)
from tests.ui_tests.app.page.common.popups.locator import HostAddPopupLocators
from tests.ui_tests.app.page.common.popups.locator import HostCreationLocators
from tests.ui_tests.app.page.common.popups.locator import (
    PageIssuePopupLocators,
    ListIssuePopupLocators,
)
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.host_list.page import HostRowInfo


class ClusterPageMixin(BasePageObject):
    """Helpers for working with cluster page"""

    # /action /main etc.
    MENU_SUFFIX: str
    MAIN_ELEMENTS: list
    cluster_id: int
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    toolbar: CommonToolbar
    table: CommonTableObj
    host_popup: HostCreatePopupObj

    __ACTIVE_MENU_CLASS = 'active'

    def __init__(self, driver, base_url, cluster_id: int):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, f"/cluster/{cluster_id}/{self.MENU_SUFFIX}")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.cluster_id = cluster_id
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)

    def open_main_tab(self):
        self.find_and_click(ObjectPageMenuLocators.main_tab)

    def open_services_tab(self):
        self.find_and_click(ObjectPageMenuLocators.services_tab)

    def open_hosts_tab(self):
        self.find_and_click(ObjectPageMenuLocators.hosts_tab)

    def open_components_tab(self):
        self.find_and_click(ObjectPageMenuLocators.components_tab)

    def open_config_tab(self):
        self.find_and_click(ObjectPageMenuLocators.config_tab)

    def open_status_tab(self):
        self.find_and_click(ObjectPageMenuLocators.status_tab)

    def open_import_tab(self):
        self.find_and_click(ObjectPageMenuLocators.import_tab)

    def open_actions_tab(self):
        self.find_and_click(ObjectPageMenuLocators.actions_tab)

    @allure.step("Check all main elements on the page are presented")
    def check_all_elements(self):
        self.assert_displayed_elements(self.MAIN_ELEMENTS)


class ClusterMainPage(ClusterPageMixin):
    """Cluster page Main menu"""

    MENU_SUFFIX = 'main'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterMainLocators.text,
    ]


class ClusterServicesPage(ClusterPageMixin):
    """Cluster page config menu"""

    MENU_SUFFIX = 'service'
    MAIN_ELEMENTS = [
        ObjectPageLocators.title,
        ObjectPageLocators.subtitle,
        ClusterServicesLocators.add_services_btn,
        CommonTable.header,
        CommonTable.Pagination.next_page,
        CommonTable.Pagination.previous_page,
    ]

    def click_add_service_btn(self):
        self.find_and_click(ClusterServicesLocators.add_services_btn)

    @allure.step("Add service {service_name} in cluster")
    def add_service_by_name(self, service_name: str):
        self.find_and_click(ClusterServicesLocators.add_services_btn)
        self.wait_element_visible(ClusterServicesLocators.AddServicePopup.block)
        for service in self.find_elements(ClusterServicesLocators.AddServicePopup.service_row):
            service_text = self.find_child(
                service, ClusterServicesLocators.AddServicePopup.ServiceRow.text
            )
            if service_text.text == service_name:
                service_text.click()
        self.find_and_click(ClusterServicesLocators.AddServicePopup.create_btn)

    def click_on_issue_by_name(self, row: WebElement, issue_name: str):
        self.hover_element(self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions))
        self.wait_element_visible(ListIssuePopupLocators.block)
        for issue in self.find_elements(ListIssuePopupLocators.link_to_issue):
            if issue.text == issue_name:
                issue.click()
                return
        raise AssertionError(f"Issue name '{issue_name}' not found in issues")

    def click_action_btn_in_row(self, row: WebElement):
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.actions).click()

    def click_import_btn_in_row(self, row: WebElement):
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.service_import).click()

    def click_config_btn_in_row(self, row: WebElement):
        self.find_child(row, ClusterServicesLocators.ServiceTableRow.config).click()

    @allure.step("Get service state")
    def get_service_state_from_row(self, row: WebElement):
        return self.find_child(row, ClusterServicesLocators.ServiceTableRow.state).text

    @allure.step("Run action {action_name} for service")
    def run_action_in_service_row(self, row: WebElement, action_name: str):
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.table.ActionPopup.block)
        self.find_and_click(self.table.table.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @contextmanager
    def wait_service_state_change(self, row: WebElement):
        state_before = self.get_service_state_from_row(row)
        yield

        def wait_state():
            state_after = self.get_service_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(wait_state, period=1, timeout=self.default_loc_timeout)


class ClusterImportPage(ClusterPageMixin):
    """Cluster page import menu"""

    MENU_SUFFIX = 'import'

    def get_import_items(self):
        return self.find_elements(ClusterImportLocators.import_item_block)


class ClusterConfigPage(ClusterPageMixin):
    """Cluster page config menu"""

    MENU_SUFFIX = 'config'


class ClusterHostPage(ClusterPageMixin):
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
        self.find_and_click(ClusterHostLocators.add_host_btn)
        self.wait_element_visible(HostCreationLocators.block)
        if is_not_first_host:
            self.wait_element_visible(HostAddPopupLocators.add_new_host_btn).click()

    @allure.step("Get info about host row")
    def get_host_info_from_row(
        self, is_cluster_value: bool = True, row_num: int = 0
    ) -> HostRowInfo:
        row = self.table.get_all_rows()[row_num]
        row_elements = ClusterHostLocators.HostTable.HostRow
        cluster_value = (
            self.find_child(row, row_elements.cluster).text
            if is_cluster_value
            else HostRowInfo.UNASSIGNED_CLUSTER_VALUE
        )
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=cluster_value
            if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE
            else None,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step("Click on host name in row")
    def click_on_host_name_in_host_row(self, row):
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.fqdn).click()

    @allure.step("Click on action in host row")
    def click_on_action_btn_in_host_row(self, row):
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions).click()

    @allure.step("Click on config in host row")
    def click_config_btn_in_row(self, row: WebElement):
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.config).click()

    @allure.step("Click on issue '{issue_name}' in host issues")
    def click_on_issue_by_name(self, row: WebElement, issue_name: str):
        self.hover_element(self.find_child(row, ClusterHostLocators.HostTable.HostRow.actions))
        self.wait_element_visible(PageIssuePopupLocators.block)
        for issue in self.find_elements(PageIssuePopupLocators.link_to_issue):
            if issue.text == issue_name:
                issue.click()
                return
        raise AssertionError(f"Issue name '{issue_name}' not found in issues")

    @allure.step("Get host state")
    def get_host_state_from_row(self, row: WebElement):
        return self.find_child(row, ClusterHostLocators.HostTable.HostRow.state).text

    @contextmanager
    def wait_host_state_change(self, row: WebElement):
        state_before = self.get_host_state_from_row(row)
        yield

        def wait_state():
            state_after = self.get_host_state_from_row(row)
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Run action {action_name} for host")
    def run_action_in_host_row(self, row: WebElement, action_name: str):
        self.click_on_action_btn_in_host_row(row)
        self.wait_element_visible(self.table.table.ActionPopup.block)
        self.find_and_click(self.table.table.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @allure.step("Delete host")
    def delete_host_by_row(self, row: WebElement):
        self.find_child(row, ClusterHostLocators.HostTable.HostRow.link_off_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)
