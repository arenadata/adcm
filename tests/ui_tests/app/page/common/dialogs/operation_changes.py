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

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.core.elements import AutoChildElement, ObjectRowMixin
from tests.ui_tests.core.interactors import Interactor
from tests.ui_tests.core.locators import Locator, autoname


class ChangesRow(AutoChildElement):
    @autoname
    class Locators:
        attribute = Locator(By.CSS_SELECTOR, "mat-cell:first-child")
        old_value = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)")
        new_value = Locator(By.CSS_SELECTOR, "mat-cell:last-child")

    def __iter__(self):
        yield "attribute", self.attribute.strip()
        yield "old_value", self.old_value.strip()
        yield "new_value", self.new_value.strip()


class OperationChangesDialog(Interactor, ObjectRowMixin):
    ROW_CLASS = ChangesRow

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table = CommonTableObj(driver=self._driver)

    @classmethod
    def wait_opened(cls, driver: WebDriver) -> "OperationChangesDialog":
        interactor = Interactor(driver=driver, default_timeout=0.5)
        interactor.wait_element_visible(Dialog.body, timeout=5)
        return cls(parent_element=interactor.find_element(Dialog.body), interactor=interactor)
