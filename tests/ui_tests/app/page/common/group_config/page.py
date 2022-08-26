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

"""Config page PageObjects classes"""

from typing import (
    List,
)

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebElement

from tests.ui_tests.app.page.common.base_page import BasePageObject
from tests.ui_tests.app.page.common.group_config.locators import GroupConfigLocators


class CommonGroupConfigMenu(BasePageObject):
    """Class for working with group configuration menu"""

    def __init__(self, driver, base_url, config_class_locators=GroupConfigLocators):
        super().__init__(driver, base_url)
        self.locators = config_class_locators

    def is_customization_chbx_disabled(self, row: WebElement) -> bool:
        """Check if customization checkbox is disabled"""

        return 'mat-checkbox-disabled' in str(
            self.find_child(row, self.locators.customization_chbx).get_attribute("class")
        )

    @allure.step("Click on customization checkbox")
    def click_on_customization_chbx(self, row: WebElement):
        state_before = self.is_customization_chbx_checked(row)
        self.find_child(row, self.locators.customization_chbx).click()

        def wait_state_change():
            return state_before != self.is_customization_chbx_checked(row)

        wait_until_step_succeeds(wait_state_change, period=1, timeout=5)

    def is_customization_chbx_checked(self, row: WebElement) -> bool:
        """Check if customization checkbox is checked"""

        return 'mat-checkbox-checked' in str(
            self.find_child(row, self.locators.customization_chbx).get_attribute("class")
        )

    def get_all_group_config_rows(self, *, displayed_only: bool = True, timeout: int = 5) -> List[WebElement]:
        """Return all config field rows"""

        try:
            if displayed_only:
                return [r for r in self.find_elements(self.locators.config_row, timeout=timeout) if r.is_displayed()]
            return self.find_elements(self.locators.config_row, timeout=timeout)
        except TimeoutException:
            return []

    def get_all_group_rows(self, *, displayed_only: bool = True, timeout: int = 5) -> List[WebElement]:
        """Return all config group rows"""

        try:
            if displayed_only:
                return [r for r in self.find_elements(self.locators.group_row, timeout=timeout) if r.is_displayed()]
            return self.find_elements(self.locators.group_row, timeout=timeout)
        except TimeoutException:
            return []

    @allure.step('Check that there are no rows on group config page')
    def check_no_rows(self):
        assert len(self.get_all_group_config_rows(timeout=1)) == 0, "There should not be any rows"
