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
from typing import Optional

import allure

from dataclasses import dataclass

from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as WDW

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.dialogs import DeleteDialog, ActionDialog
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.host_list.locators import HostListLocators


@dataclass
class HostRowInfo:
    UNASSIGNED_CLUSTER_VALUE = 'Assign to cluster'
    fqdn: str
    provider: str
    cluster: Optional[str]
    state: str


class HostListPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/host")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, HostListLocators.HostTable)

    def get_host_row(self, row_num: int = 0) -> WebElement:
        rows = self.table.get_all_rows()
        assert (rows_count := len(rows)) >= (
            row_num + 1
        ), f"Host table has only {rows_count} rows when row #{row_num} was requested"
        return rows[row_num]

    def get_host_info_from_row(self, row_num: int = 0) -> HostRowInfo:
        row = self.get_host_row(row_num)
        row_elements = HostListLocators.HostTable.HostRow
        cluster_value = self.find_child(row, row_elements.cluster).text
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=cluster_value
            if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE
            else None,
            state=self.find_child(row, row_elements.state).text,
        )

    def click_on_row_child(self, row_num: int, child_locator: Locator):
        row = self.get_host_row(row_num)
        self.find_child(row, child_locator).click()

    @allure.step("Create new host")
    def create_host(
        self,
        fqdn: str,
        provider: Optional[str] = None,
        cluster: Optional[str] = None,
    ):
        """Create host in popup"""
        self.open_host_creation_popup()
        self.insert_new_host_info(fqdn, provider, cluster)
        self.click_create_host_in_popup()
        self.close_host_creation_popup()

    @allure.step("Create new provider and host")
    def create_provider_and_host(
        self,
        bundle_path: str,
        fqdn: str,
        provider: Optional[str] = None,
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
        self.upload_bundle(bundle_path)
        provider_name = self._get_hostprovider_name()
        self.insert_new_host_info(fqdn, provider, cluster)
        self.click_create_host_in_popup()
        self.close_host_creation_popup()
        # because we don't pass provider name
        return provider_name

    @allure.step('Run action "{action_display_name}" on host in row {host_row_num}')
    def run_action(self, host_row_num: int, action_display_name: str):
        host_row = HostListLocators.HostTable.HostRow
        self.click_on_row_child(host_row_num, host_row.actions)
        init_action = self.wait_element_visible(host_row.action_option(action_display_name))
        init_action.click()
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @allure.step('Delete host in row {host_row_num}')
    def delete_host(self, host_row_num: int):
        """Delete host from table row"""
        self.click_on_row_child(host_row_num, HostListLocators.HostTable.HostRow.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step('Assign host in row {host_row_num} to cluster "{cluster_name}"')
    def assign_host_to_cluster(self, host_row_num: int, cluster_name: str):
        """Assign host to cluster in host list table"""
        self.click_on_row_child(host_row_num, HostListLocators.HostTable.HostRow.cluster)
        self._wait_and_click_on_cluster_option(cluster_name, HostListLocators.HostTable.option)

    @allure.step('Assert host in row {row_num} has state "{state}"')
    def wait_for_host_state(self, row_num: int, state: str):
        def assert_host_state(page: HostListPage, row: WebElement):
            real_state = page.find_child(row, HostListLocators.HostTable.HostRow.state).text
            assert state == real_state

        host_row = self.get_host_row(row_num)
        wait_until_step_succeeds(assert_host_state, timeout=10, period=0.5, page=self, row=host_row)

    # HELPERS

    def open_host_creation_popup(self):
        self.find_and_click(HostListLocators.Tooltip.host_add_btn)
        self.wait_element_visible(HostListLocators.CreateHostPopup.block)

    def close_host_creation_popup(self):
        """Close popup with `Cancel` button"""
        self.find_and_click(HostListLocators.CreateHostPopup.cancel_btn)

    def click_create_host_in_popup(self):
        """Click create host button in popup"""
        self.find_and_click(HostListLocators.CreateHostPopup.create_btn)

    def insert_new_host_info(
        self, fqdn: str, provider: Optional[str] = None, cluster: Optional[str] = None
    ):
        """Insert new host info in fields of opened popup"""
        popup = HostListLocators.CreateHostPopup
        self.find_element(popup.fqdn_input).send_keys(fqdn)
        if provider:
            ...  # TODO implement
        if cluster:
            self._choose_cluster_in_popup(cluster)

    def upload_bundle(self, bundle_path: str):
        """
        Add new host provider
        Popup should be opened
        Popup is not closed at the end
        """
        popup = HostListLocators.CreateHostPopup
        self.find_and_click(popup.provider_add_btn)
        self.wait_element_visible(popup.new_provider_block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle_path)
        self.find_and_click(popup.new_provider_add_btn)

    def _get_hostprovider_name(self) -> str:
        """Get chosen provider from opened new host popup"""
        return self.find_element(HostListLocators.CreateHostPopup.chosen_provider).text

    def _choose_cluster_in_popup(self, cluster_name: str):
        self.find_and_click(HostListLocators.CreateHostPopup.cluster_select)
        option = HostListLocators.CreateHostPopup.cluster_option
        self._wait_and_click_on_cluster_option(cluster_name, option)

    def _wait_and_click_on_cluster_option(self, cluster_name: str, option_locator: Locator):
        WDW(self.driver, self.default_loc_timeout).until(
            EC.presence_of_element_located(
                [option_locator.by, option_locator.value.format(cluster_name)]
            ),
            message=f"Can't find cluster with name {cluster_name} in dropdown on page {self.driver.current_url} "
            f"for {self.default_loc_timeout} seconds",
        ).click()
