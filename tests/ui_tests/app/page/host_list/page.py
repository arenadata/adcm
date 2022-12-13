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

"""Host List page PageObjects classes"""

from dataclasses import dataclass
from typing import ClassVar, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog, DeleteDialog
from tests.ui_tests.app.page.common.dialogs.rename import RenameDialog
from tests.ui_tests.app.page.common.popups.locator import HostCreationLocators
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.utils import assert_enough_rows


@dataclass
class HostRowInfo:
    """Information from host row about host"""

    # helper to check if any cluster is assigned
    UNASSIGNED_CLUSTER_VALUE: ClassVar[str] = 'Assign to cluster'
    fqdn: str
    provider: str
    cluster: Optional[str]
    state: str


class HostListPage(BasePageObject):  # pylint: disable=too-many-public-methods
    """Host List Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/host")
        self.table = CommonTableObj(self.driver, self.base_url, HostListLocators.HostTable)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)

    @allure.step('Get host information from row #{row_num}')
    def get_host_row(self, row_num: int = 0) -> WebElement:
        """Get host information from row"""

        def _table_has_enough_rows():
            assert_enough_rows(row_num, self.table.row_count)

        wait_until_step_succeeds(_table_has_enough_rows, timeout=5, period=0.1)
        rows = self.table.get_all_rows()
        assert_enough_rows(row_num, len(rows))
        return rows[row_num]

    @allure.step('Get host information from table row #{row_num}')
    def get_host_info_from_row(self, row_num: int = 0) -> HostRowInfo:
        """Get host information from table row"""
        row = self.table.get_row(row_num)
        row_elements = HostListLocators.HostTable.HostRow
        cluster_value = self.find_child(row, row_elements.cluster).text
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=cluster_value if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE else None,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step('Click on cell {child_locator} (row #{row_num})')
    def click_on_row_child(self, row_num: int, child_locator: Locator):
        """Click on row child"""
        row = self.table.get_row(row_num)
        self.find_child(row, child_locator).click()

    @allure.step("Create new host")
    def create_host(
        self,
        fqdn: str,
        cluster: Optional[str] = None,
    ):
        """Create host in popup"""
        self.open_host_creation_popup()
        self._insert_new_host_info(fqdn, cluster)
        self.click_create_host_in_popup()
        self.close_host_creation_popup()

    @allure.step("Upload bundle from host creation popup")
    def upload_bundle_from_host_create_popup(self, bundle_path: str):
        """Upload bundle in host creation popup and close popup"""
        self.open_host_creation_popup()
        self._upload_bundle(bundle_path)
        self.close_host_creation_popup()

    @allure.step("Create new provider and host")
    def create_provider_and_host(
        self,
        bundle_path: str,
        fqdn: str,
        cluster: Optional[str] = None,
    ) -> str:
        """
        Open host creation popup
        Upload bundle and create provider
        Fill in information about new host
        Create host
        Close popup
        :returns: Name of created provider
        """
        self.open_host_creation_popup()
        self._upload_bundle(bundle_path)
        provider_name = self._get_hostprovider_name()
        self._insert_new_host_info(fqdn, cluster)
        self.click_create_host_in_popup()
        self.close_host_creation_popup()
        # because we don't pass provider name
        return provider_name

    def open_run_action_menu(self, row: WebElement) -> None:
        self.find_child(row, HostListLocators.HostTable.HostRow.actions).click()
        self.wait_element_visible(HostListLocators.HostTable.HostRow.dropdown_menu, timeout=2)

    def get_actions_from_opened_menu(self) -> list[WebElement]:
        try:
            return self.find_elements(HostListLocators.HostTable.HostRow.action_option_all, timeout=1)
        except TimeoutException:
            return []

    def close_run_action_menu(self) -> None:
        # Typing Escape and clicking somewhere doesn't work
        self.driver.refresh()

    def get_enabled_action_names(self, row_num: int) -> list[str]:
        row = self.get_host_row(row_num)
        self.open_run_action_menu(row)
        action_names = [action.text for action in self.get_actions_from_opened_menu() if action.is_enabled()]
        self.close_run_action_menu()
        return action_names

    def get_disabled_action_names(self, row_num: int) -> list[str]:
        row = self.get_host_row(row_num)
        self.open_run_action_menu(row)
        action_names = [action.text for action in self.get_actions_from_opened_menu() if not action.is_enabled()]
        self.close_run_action_menu()
        return action_names

    @allure.step('Run action "{action_display_name}" on host in row {host_row_num}')
    def run_action(self, host_row_num: int, action_display_name: str):
        """Run action from Host row"""
        host_row = HostListLocators.HostTable.HostRow
        self.click_on_row_child(host_row_num, host_row.actions)
        init_action = self.wait_element_visible(host_row.action_option(action_display_name))
        init_action.click()
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @allure.step('Delete host in row {host_row_num}')
    def delete_host(self, host_row_num: int):
        """Delete host from table row"""
        self.click_on_row_child(host_row_num, HostListLocators.HostTable.HostRow.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step('Bind host in row {host_row_num} to cluster "{cluster_name}"')
    def bind_host_to_cluster(self, host_row_num: int, cluster_name: str):
        """Assign host to cluster in host list table"""
        self.click_on_row_child(host_row_num, HostListLocators.HostTable.HostRow.cluster)
        self.host_popup.wait_and_click_on_cluster_option(cluster_name, HostListLocators.HostTable.cluster_option)

    @allure.step('Assert host in row {row_num} is assigned to cluster {cluster_name}')
    def assert_host_bonded_to_cluster(self, row_num: int, cluster_name: str):
        """Assert host in row is assigned to cluster"""

        def _check_host_cluster(page: HostListPage, row: WebElement):
            real_cluster = page.find_child(row, HostListLocators.HostTable.HostRow.cluster).text
            assert real_cluster == cluster_name

        host_row = self.table.get_row(row_num)
        wait_until_step_succeeds(_check_host_cluster, timeout=5, period=0.1, page=self, row=host_row)

    @allure.step('Assert host in row {row_num} has state "{state}"')
    def assert_host_state(self, row_num: int, state: str):
        """Assert host in row has state  given state"""

        def _check_host_state(page: HostListPage, row: WebElement):
            real_state = page.find_child(row, HostListLocators.HostTable.HostRow.state).text
            assert real_state == state

        host_row = self.table.get_row(row_num)
        wait_until_step_succeeds(_check_host_state, timeout=10, period=0.5, page=self, row=host_row)

    @allure.step('Click on maintenance mode button in row {row_num}')
    def click_on_maintenance_mode_btn(self, row_num: int):
        """Click maintenance mode in row"""

        row = self.table.get_row(row_num)
        self.find_child(row, HostListLocators.HostTable.HostRow.maintenance_mode_btn).click()

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

        def _check_mm_state(page: HostListPage, row: WebElement):
            button_state = page.find_child(row, HostListLocators.HostTable.HostRow.maintenance_mode_btn).get_attribute(
                "class"
            )
            tooltips_info = [
                t.get_property("innerHTML") for t in page.find_elements(HostListLocators.HostTable.tooltip_text)
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

    @allure.step('Open host creation popup')
    def open_host_creation_popup(self):
        """Open host creation popup"""
        self.find_and_click(HostListLocators.Tooltip.host_add_btn)
        self.wait_element_visible(HostCreationLocators.block)

    @allure.step('Close host creation popup')
    def close_host_creation_popup(self):
        """Close popup with `Cancel` button"""
        self.find_and_click(HostCreationLocators.cancel_btn)

    @allure.step('Click "Create host" in popup')
    def click_create_host_in_popup(self):
        """Click create host button in popup"""
        self.find_and_click(HostCreationLocators.create_btn)

    @allure.step("Open host rename dialog by clicking on host rename button")
    def open_rename_dialog(self, row: WebElement) -> RenameDialog:
        self.hover_element(row)
        self.find_child(row, self.table.locators.HostRow.rename_btn).click()
        dialog = RenameDialog(driver=self.driver, base_url=self.base_url)
        dialog.wait_opened()
        return dialog

    def _insert_new_host_info(self, fqdn: str, cluster: Optional[str] = None):
        """Insert new host info in fields of opened popup"""
        self.wait_element_visible(HostCreationLocators.fqdn_input)
        self.send_text_to_element(HostCreationLocators.fqdn_input, fqdn)
        if cluster:
            self._choose_cluster_in_popup(cluster)

    def _upload_bundle(self, bundle_path: str):
        """
        Add new host provider
        Popup should be opened
        Popup is not closed at the end
        """
        provider_section = HostCreationLocators.Provider
        self.find_and_click(provider_section.add_btn)
        self.wait_element_visible(provider_section.new_provider_block)
        self.find_element(provider_section.upload_bundle_btn).send_keys(bundle_path)
        self.find_and_click(provider_section.new_provider_add_btn)
        self.wait_element_hide(provider_section.new_provider_block)

    def _get_hostprovider_name(self) -> str:
        """Get chosen provider from opened new host popup"""
        return self.find_element(HostCreationLocators.Provider.chosen_provider).text

    def _choose_cluster_in_popup(self, cluster_name: str):
        self.find_and_click(HostCreationLocators.Cluster.cluster_select)
        option = HostCreationLocators.Cluster.cluster_option
        self._wait_and_click_on_cluster_option(cluster_name, option)
        self.wait_element_hide(option)

    def _wait_and_click_on_cluster_option(self, cluster_name: str, option_locator: Locator):
        WDW(self.driver, self.default_loc_timeout).until(
            EC.presence_of_element_located([option_locator.by, option_locator.value.format(cluster_name)]),
            message=f"Can't find cluster with name {cluster_name} "
            f"in dropdown on page {self.driver.current_url} "
            f"for {self.default_loc_timeout} seconds",
        ).click()
