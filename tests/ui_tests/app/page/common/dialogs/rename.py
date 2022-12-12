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
from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.dialogs.locators import RenameDialogLocators

WAIT_TIMEOUT = 0.5
MESSAGE_WAIT_TIMEOUT = 1


class RenameDialog(BasePageObject):
    def wait_opened(self):
        self.wait_element_visible(RenameDialogLocators.body)

    @allure.step("Set new name/fqdn in rename dialog")
    def set_new_name_in_rename_dialog(self, new_name: str) -> None:
        dialog = self.find_element(RenameDialogLocators.body, timeout=WAIT_TIMEOUT)
        name_input = self.find_child(dialog, RenameDialogLocators.object_name)
        name_input.clear()
        name_input.send_keys(new_name)

    @allure.step("Click 'Save' button on rename dialog")
    def click_save_on_rename_dialog(self):
        dialog = self.find_element(RenameDialogLocators.body, timeout=WAIT_TIMEOUT)
        self.find_child(dialog, RenameDialogLocators.save).click()
        self.wait_element_hide(RenameDialogLocators.body)

    @allure.step("Click 'Cancel' button on rename dialog")
    def click_cancel_on_rename_dialog(self):
        dialog = self.find_element(RenameDialogLocators.body, timeout=WAIT_TIMEOUT)
        self.find_child(dialog, RenameDialogLocators.cancel).click()
        self.wait_element_hide(RenameDialogLocators.body)

    def is_dialog_error_message_visible(self):
        self.wait_element_visible(RenameDialogLocators.body, timeout=WAIT_TIMEOUT)
        try:
            self.wait_element_visible(RenameDialogLocators.error, timeout=MESSAGE_WAIT_TIMEOUT)
        except TimeoutException:
            return False
        return True

    def get_dialog_error_message(self):
        dialog = self.wait_element_visible(RenameDialogLocators.body, timeout=WAIT_TIMEOUT)
        error = self.find_child(dialog, RenameDialogLocators.error, timeout=WAIT_TIMEOUT)
        return error.text
