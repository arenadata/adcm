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

"""Common Host Component classes"""

from dataclasses import dataclass

import allure
from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.create_host import HostCreateDialog
from tests.ui_tests.app.page.common.dialogs.create_host_locators import (
    HostCreationLocators,
)
from tests.ui_tests.app.page.common.host_components.locators import (
    HostComponentsLocators,
)


@dataclass
class ComponentsHostRowInfo:
    """Information from host row about host on Components page"""

    name: str
    components: str


class HostComponentsPage(BasePageObject):
    """HostComponentsPage page components menu"""

    def click_service_page_link(self):
        """Click on Service page link"""
        self.find_and_click(HostComponentsLocators.service_page_link)

    def click_hosts_page_link(self):
        """Click on Hosts page link"""
        self.find_and_click(HostComponentsLocators.hosts_page_link)

    def click_add_host_btn(self) -> HostCreateDialog:
        """Click on Add Host button"""
        self.find_and_click(HostComponentsLocators.create_hosts_btn)
        self.wait_element_visible(HostCreationLocators.block)
        return HostCreateDialog(driver=self.driver)

    def get_host_rows(self):
        """Get all hosts rows"""
        return self.find_elements(HostComponentsLocators.host_row, timeout=5)

    def get_components_rows(self):
        """Get all components rows"""
        return self.find_elements(HostComponentsLocators.component_row)

    def get_row_info(self, row: WebElement):
        """Get components row info"""
        return ComponentsHostRowInfo(
            name=self.find_child(row, HostComponentsLocators.Row.name).text,
            components=self.find_child(row, HostComponentsLocators.Row.number).text,
        )

    def find_host_row_by_name(self, host_name: str):
        """Find Host row by name"""
        for host_row in self.get_host_rows():
            host_name_element = self.find_child(host_row, HostComponentsLocators.Row.name)
            if host_name_element.text == host_name:
                return host_row
        raise AssertionError(f"There are no host with name '{host_name}'")

    def find_component_row_by_name(self, component_name: str):
        """Find Component row by name"""
        for component_row in self.get_components_rows():
            component_name_element = self.find_child(component_row, HostComponentsLocators.Row.name)
            if component_name_element.text == component_name:
                return component_row
        raise AssertionError(f"There are no component with name '{component_name}'")

    @allure.step("Click on host row")
    def click_host(self, host_row: WebElement):
        """Click on Host row"""
        self.find_child(host_row, HostComponentsLocators.Row.name).click()

    @allure.step("Click on component row")
    def click_component(self, component_row: WebElement):
        """Click on Component row"""
        self.find_child(component_row, HostComponentsLocators.Row.name).click()

    @allure.step("Click on row number in component row")
    def click_number_in_component(self, component_row: WebElement):
        """Click on Component row number"""
        self.find_child(component_row, HostComponentsLocators.Row.number).click()

    @allure.step("Click on save button")
    def click_save_btn(self):
        """Click on Save button"""
        self.find_and_click(HostComponentsLocators.save_btn)

    @allure.step("Click on restore button")
    def click_restore_btn(self):
        """Click on Restore button"""
        self.find_and_click(HostComponentsLocators.restore_btn)

    @allure.step("Delete item {item_name} from row")
    def delete_related_item_in_row_by_name(self, row: WebElement, item_name: str):
        """Delete related item by button from row"""
        self.wait_element_visible(HostComponentsLocators.Row.relations_row)
        for item_row in self.find_children(row, HostComponentsLocators.Row.relations_row):
            item_name_element = self.find_child(item_row, HostComponentsLocators.Row.RelationsRow.name)
            if item_name_element.text == item_name:
                self.find_child(item_row, HostComponentsLocators.Row.RelationsRow.delete_btn).click()
                return
        raise AssertionError(f"There are no item with name '{item_name}'")

    def check_that_save_btn_disabled(self):
        """Get Save button available state"""
        return self.find_element(HostComponentsLocators.save_btn).get_attribute("disabled") == "true"
