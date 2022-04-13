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
