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

"""Provider page PageObjects classes"""

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webelement import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import ActionDialog, DeleteDialog
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.app.page.provider_list.locators import ProviderListLocators


@dataclass
class ProviderRowInfo:
    """Information from provider row"""

    name: str
    bundle: str
    state: str


class ProviderListPage(BasePageObject):
    """Provider List Page class"""

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/provider")
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(driver=self.driver, locators_class=HostListLocators.HostTable)

    @allure.step("Create provider")
    def create_provider(self, bundle: str, name: Optional[str] = None, description: Optional[str] = None):
        """Create provider"""
        self.find_and_click(ProviderListLocators.Tooltip.add_btn)
        popup = ProviderListLocators.CreateProviderPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        if name:
            self.send_text_to_element(popup.provider_name_input, name)
        if description:
            self.send_text_to_element(popup.description_input, description)
        self.find_and_click(popup.create_btn)

    def get_provider_info_from_row(self, row: WebElement) -> ProviderRowInfo:
        """Get provider info from row"""
        row_elements = ProviderListLocators.ProviderTable.ProviderRow
        return ProviderRowInfo(
            name=self.find_child(row, row_elements.name).text,
            bundle=self.find_child(row, row_elements.bundle).text,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step("Click action button in row")
    def click_action_btn_in_row(self, row: WebElement):
        """Click Action button in row"""
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.actions).click()

    @allure.step("Click config button in row")
    def click_config_btn_in_row(self, row: WebElement):
        """Click Config button in row"""
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.config).click()

    @allure.step("Click name in row")
    def click_name_in_row(self, row: WebElement):
        """Click name in row"""
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.name).click()

    @allure.step("Run action {action_name} for provider from row")
    def run_action_in_provider_row(self, row: WebElement, action_name: str):
        """Run action for provider from row"""
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.locators.ActionPopup.block)
        self.find_and_click(self.table.locators.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)
        self.wait_element_hide(ActionDialog.body)

    @contextmanager
    def wait_provider_state_change(self, row: WebElement):
        """Wait for provider state change"""
        state_before = self.get_provider_info_from_row(row).state
        yield

        def _wait_state():
            state_after = self.get_provider_info_from_row(row).state
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(_wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Delete host by button from row")
    def delete_provider_in_row(self, row: WebElement):
        """Delete host by button from row"""
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)
