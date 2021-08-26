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
from dataclasses import dataclass
from typing import Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.dialogs import (
    ActionDialog,
    DeleteDialog,
)
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar
from tests.ui_tests.app.page.common.popups.page import HostCreatePopupObj
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.host_list.locators import HostListLocators
from tests.ui_tests.app.page.provider_list.locators import ProviderListLocators


@dataclass
class ProviderRowInfo:
    """Information from provider row"""

    name: str
    bundle: str
    state: str


class ProviderListPage(BasePageObject):
    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/provider")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.toolbar = CommonToolbar(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url, HostListLocators.HostTable)
        self.host_popup = HostCreatePopupObj(self.driver, self.base_url)

    @allure.step("Create provider from bundle")
    def create_provider(self, bundle: str, name: Optional[str] = None, description: Optional[str] = None):
        self.find_and_click(ProviderListLocators.Tooltip.add_btn)
        popup = ProviderListLocators.CreateProviderPopup
        self.wait_element_visible(popup.block)
        self.find_element(popup.upload_bundle_btn).send_keys(bundle)
        if name:
            self.send_text_to_element(popup.provider_name_input, name)
        if description:
            self.send_text_to_element(popup.description_input, description)
        self.find_and_click(popup.create_btn)

    @allure.step("Get provider info from row")
    def get_provider_info_from_row(self, row: WebElement) -> ProviderRowInfo:
        row_elements = ProviderListLocators.ProviderTable.ProviderRow
        return ProviderRowInfo(
            name=self.find_child(row, row_elements.name).text,
            bundle=self.find_child(row, row_elements.bundle).text,
            state=self.find_child(row, row_elements.state).text,
        )

    @allure.step("Click action in row")
    def click_action_btn_in_row(self, row: WebElement):
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.actions).click()

    @allure.step("Click config in row")
    def click_config_btn_in_row(self, row: WebElement):
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.config).click()

    @allure.step("Click name in row")
    def click_name_in_row(self, row: WebElement):
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.name).click()

    @allure.step("Run action {action_name} for provider")
    def run_action_in_provider_row(self, row: WebElement, action_name: str):
        self.click_action_btn_in_row(row)
        self.wait_element_visible(self.table.table.ActionPopup.block)
        self.find_and_click(self.table.table.ActionPopup.button(action_name))
        self.wait_element_visible(ActionDialog.body)
        self.find_and_click(ActionDialog.run)

    @contextmanager
    def wait_provider_state_change(self, row: WebElement):
        state_before = self.get_provider_info_from_row(row).state
        yield

        def wait_state():
            state_after = self.get_provider_info_from_row(row).state
            assert state_after != state_before
            assert state_after != self.table.LOADING_STATE_TEXT

        wait_until_step_succeeds(wait_state, period=1, timeout=self.default_loc_timeout)

    @allure.step("Delete host")
    def delete_provider_by_row(self, row: WebElement):
        self.find_child(row, ProviderListLocators.ProviderTable.ProviderRow.delete_btn).click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)
