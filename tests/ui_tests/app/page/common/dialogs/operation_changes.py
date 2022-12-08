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

from selenium.webdriver.remote.webelement import WebElement
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import (
    OperationChangesDialogLocators,
)


@dataclass()
class ChangesRow:
    attribute: str
    old_value: str
    new_value: str


class OperationChangesDialog(BasePageObject):
    def wait_opened(self):
        self.wait_element_visible(OperationChangesDialogLocators.body)

    def get_rows(self) -> list[WebElement]:
        body = self.find_element(OperationChangesDialogLocators.body, timeout=0.5)
        return self.find_children(body, OperationChangesDialogLocators.row, timeout=1)

    def get_changes(self) -> list[ChangesRow]:
        row_locators = OperationChangesDialogLocators.Row
        return [
            ChangesRow(
                attribute=self.find_child(row, row_locators.attribute, timeout=0.5).text.strip(),
                old_value=self.find_child(row, row_locators.old_value, timeout=0.5).text.strip(),
                new_value=self.find_child(row, row_locators.new_value, timeout=0.5).text.strip(),
            )
            for row in self.get_rows()
        ]
