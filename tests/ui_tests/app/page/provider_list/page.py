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
from dataclasses import dataclass
from typing import Optional

import allure
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
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
