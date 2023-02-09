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

import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.import_page.locators import ImportLocators
from tests.ui_tests.core.elements import Element, as_element
from tests.ui_tests.core.locators import Locator, autoname


class ImportItem(Element):
    @autoname
    class Locators:
        export_item = Locator(By.CSS_SELECTOR, "app-exports > div")

    def get_available_exports(self) -> tuple["ExportItem", ...]:
        return tuple(
            map(as_element(ExportItem, self._view), self._view.find_children(self.element, self.Locators.export_item))
        )


class ExportItem(Element):
    class Locators:
        input = Locator(By.TAG_NAME, "input")
        check = Locator(By.CSS_SELECTOR, "span.mat-checkbox-inner-container")

    def check(self) -> None:
        if self.is_checked():
            with allure.step("Skipping checking export item checkbox, because it's already checked"):
                return

        with allure.step("Pick export item"):
            self._view.find_child(self.element, self.Locators.check, timeout=0.1).click()

    def uncheck(self) -> None:
        if not self.is_checked():
            with allure.step("Skipping unchecking export item, because it's already unchecked"):
                return

        with allure.step("Unpick export item"):
            self._view.find_child(self.element, self.Locators.check, timeout=0.1).click()

    def is_checked(self) -> bool:
        string_value = self._view.find_child(self.element, self.Locators.input, timeout=0.1).get_attribute(
            "aria-checked"
        )
        if string_value == "false":
            return False
        if string_value == "true":
            return True
        raise RuntimeError(f"Failed to get state of checkbox: {string_value}")


@dataclass
class ImportInfo:
    """Information from import item on Import page"""

    name: str
    description: str


class ImportPage(BasePageObject):
    """Class for working with import page"""

    def get_imports(self):
        """Get import items"""
        return self.find_elements(ImportLocators.import_item_block)

    def get_import_items(self) -> tuple[ImportItem, ...]:
        return tuple(map(as_element(ImportItem, self), self.find_elements(ImportLocators.import_item_block)))

    def click_checkbox_in_import_item(self, import_item: WebElement):
        """Click on checkbox in import items"""
        self.find_child(import_item, ImportLocators.ImportItem.import_chbx).click()

    def is_chxb_in_item_checked(self, import_item: WebElement) -> bool:
        """Get checkbox element checked state"""
        return "checked" in self.find_child(import_item, ImportLocators.ImportItem.import_chbx).get_attribute("class")

    def click_save_btn(self):
        """Click on Save button"""
        self.find_and_click(ImportLocators.save_btn)

    def get_import_info(self, import_item: WebElement):
        """Get Import item info"""
        return ImportInfo(
            name=self.find_child(import_item, ImportLocators.ImportItem.name).text,
            description=self.find_child(import_item, ImportLocators.ImportItem.description).text,
        )
