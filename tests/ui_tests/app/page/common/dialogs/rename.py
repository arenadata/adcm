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

import allure
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By

from tests.ui_tests.app.page.common.dialogs.locators import Dialog
from tests.ui_tests.core.elements import AutoChildDialog
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class RenameDialog(AutoChildDialog):
    @autoname
    class Locators(Dialog):
        object_name = Locator(By.TAG_NAME, "input", Descriptor.INPUT)
        error = Locator(By.TAG_NAME, "mat-error", name="Error message")
        save = Locator(By.XPATH, "//button//span[contains(text(), 'Save')]", Descriptor.BUTTON)
        cancel = Locator(By.XPATH, "//button//span[contains(text(), 'Cancel')]", Descriptor.BUTTON)

    @allure.step("Set new name/fqdn in rename dialog")
    def set_new_name(self, name: str) -> None:
        name_input = self.object_name
        name_input.clear()
        name_input.send_keys(name)

    @allure.step("Click 'Save' button on rename dialog")
    def save(self) -> None:
        self.save_button.click()
        self._view.wait_element_hide(self.Locators.body, timeout=5)

    @allure.step("Click 'Cancel' button on rename dialog")
    def cancel(self) -> None:
        self.cancel_button.click()
        self._view.wait_element_hide(self.Locators.body, timeout=5)

    def is_error_message_visible(self) -> bool:
        try:
            self._view.wait_element_visible(self.Locators.error, timeout=1)
        except TimeoutException:
            return False
        return True
