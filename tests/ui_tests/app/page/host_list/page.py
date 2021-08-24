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
from typing import Optional, ClassVar
from dataclasses import dataclass

import allure
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
from tests.ui_tests.app.page.common.popups.locator import HostCreationLocators
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.host_list.locators import HostListLocators


@dataclass
class HostRowInfo:
    """Information from host row about host"""

    # helper to check if any cluster is assigned
    UNASSIGNED_CLUSTER_VALUE: ClassVar[str] = 'Assign to cluster'
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
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)

    def get_host_info_from_row(self, row_num: int = 0) -> HostRowInfo:
        row = self.table.get_row(row_num)
        row_elements = HostListLocators.HostTable.HostRow
        cluster_value = self.find_child(row, row_elements.cluster).text
        return HostRowInfo(
            fqdn=self.find_child(row, row_elements.fqdn).text,
            provider=self.find_child(row, row_elements.provider).text,
            cluster=cluster_value if cluster_value != HostRowInfo.UNASSIGNED_CLUSTER_VALUE else None,
            state=self.find_child(row, row_elements.state).text,
        )

    def click_on_row_child(self, row_num: int, child_locator: Locator):
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

    @allure.step('Bind host in row {host_row_num} to cluster "{cluster_name}"')
    def bind_host_to_cluster(self, host_row_num: int, cluster_name: str):
        """Assign host to cluster in host list table"""
        self.click_on_row_child(host_row_num, HostListLocators.HostTable.HostRow.cluster)
        self.host_popup.wait_and_click_on_cluster_option(cluster_name, HostListLocators.HostTable.cluster_option)

    @allure.step('Assert host in row {row_num} is assigned to cluster {cluster_name}')
    def assert_host_bonded_to_cluster(self, row_num: int, cluster_name: str):
        def check_host_cluster(page: HostListPage, row: WebElement):
            real_cluster = page.find_child(row, HostListLocators.HostTable.HostRow.cluster).text
            assert real_cluster == cluster_name

        host_row = self.table.get_row(row_num)
        wait_until_step_succeeds(check_host_cluster, timeout=5, period=0.1, page=self, row=host_row)

    @allure.step('Assert host in row {row_num} has state "{state}"')
    def assert_host_state(self, row_num: int, state: str):
        def check_host_state(page: HostListPage, row: WebElement):
            real_state = page.find_child(row, HostListLocators.HostTable.HostRow.state).text
            assert real_state == state

        host_row = self.table.get_row(row_num)
        wait_until_step_succeeds(check_host_state, timeout=10, period=0.5, page=self, row=host_row)

    def open_host_creation_popup(self):
        self.find_and_click(HostListLocators.Tooltip.host_add_btn)
        self.wait_element_visible(HostCreationLocators.block)

    def close_host_creation_popup(self):
        """Close popup with `Cancel` button"""
        self.find_and_click(HostCreationLocators.cancel_btn)

    def click_create_host_in_popup(self):
        """Click create host button in popup"""
        self.find_and_click(HostCreationLocators.create_btn)

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
