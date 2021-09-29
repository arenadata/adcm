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

"""Page objects for ActionPage"""

import allure

from tests.ui_tests.app.locators import ActionPageLocators
from tests.ui_tests.app.pages import BasePage


class ActionPage(BasePage):
    """Class for action page"""

    def __init__(self, driver, url=None, cluster_id=None):
        super().__init__(driver)
        self.get(f"{url}/cluster/{cluster_id}/action", "action")

    @allure.step('Open run action popup')
    def open_run_action_popup(self):
        """Open run action popup"""
        self._wait_element_present(ActionPageLocators.action_run_button, timer=15).click()
        self._wait_element_present(ActionPageLocators.run_action_popup)

    @allure.step('Check if verbose checkbox is displayed on popup')
    def check_verbose_chbx_displayed(self):
        """Check if verbose checkbox is displayed on popup"""
        verbose_chbx = ActionPageLocators.ActionRunPopup.verbose_chbx
        self.open_run_action_popup()
        return self.driver.find_element(*verbose_chbx).is_displayed()

    def run_action(self, is_verbose: bool = False):
        """Run action"""
        with allure.step(f'Run action {"with" if is_verbose else "without"} verbose checkbox'):
            self.open_run_action_popup()
            if is_verbose:
                self.driver.find_element(*ActionPageLocators.ActionRunPopup.verbose_chbx).click()
            self.driver.find_element(*ActionPageLocators.ActionRunPopup.run_btn).click()
            self._wait_element_hide(ActionPageLocators.ActionRunPopup.verbose_chbx)
