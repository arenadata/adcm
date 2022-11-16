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

from selenium.webdriver.remote.webdriver import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.import_page.locators import ImportLocators


@dataclass
class ImportItemInfo:
    """Information from import item on Import page"""

    name: str
    description: str


class ImportPage(BasePageObject):
    """Class for working with import page"""

    def get_import_items(self):
        """Get import items"""
        return self.find_elements(ImportLocators.import_item_block)

    def click_checkbox_in_import_item(self, import_item: WebElement):
        """Click on checkbox in import items"""
        self.find_child(import_item, ImportLocators.ImportItem.import_chbx).click()

    def is_chxb_in_item_checked(self, import_item: WebElement) -> bool:
        """Get checkbox element checked state"""
        return "checked" in self.find_child(import_item, ImportLocators.ImportItem.import_chbx).get_attribute("class")

    def click_save_btn(self):
        """Click on Save button"""
        self.find_and_click(ImportLocators.save_btn)

    def get_import_item_info(self, import_item: WebElement):
        """Get Import item info"""
        return ImportItemInfo(
            name=self.find_child(import_item, ImportLocators.ImportItem.name).text,
            description=self.find_child(import_item, ImportLocators.ImportItem.description).text,
        )
