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

from typing import Literal

from selenium.webdriver.common.by import By
from tests.ui_tests.core.elements import AutoChildElement
from tests.ui_tests.core.locators import Descriptor, Locator, autoname


class WithMM:
    @property
    def maintenance_mode(self) -> Literal["ON", "OFF", "ANOTHER"]:
        classes = set(self.maintenance_mode_button.get_attribute("class").split())

        if "mat-on" in classes:
            return "ON"

        if "mat-primary" in classes:
            return "OFF"

        return "ANOTHER"


class ServiceRow(AutoChildElement, WithMM):
    @autoname
    class Locators:
        name = Locator(By.CSS_SELECTOR, "mat-cell:first-of-type")
        version = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)")
        state = Locator(By.CSS_SELECTOR, "app-state-column")
        status = Locator(By.CSS_SELECTOR, "app-status-column button", Descriptor.BUTTON)
        actions = Locator(By.CSS_SELECTOR, "app-actions-button button", Descriptor.BUTTON)
        service_import = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(6) button", Descriptor.BUTTON)
        config = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(7) button", Descriptor.BUTTON)
        maintenance_mode = Locator(By.CLASS_NAME, "mm-button", Descriptor.BUTTON)
        delete = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(9) button", Descriptor.BUTTON)


class ComponentRow(AutoChildElement, WithMM):
    @autoname
    class Locators:
        name = Locator(By.CSS_SELECTOR, "mat-cell:first-of-type")
        state = Locator(By.CSS_SELECTOR, "app-state-column")
        status = Locator(By.CSS_SELECTOR, "app-status-column button", Descriptor.BUTTON)
        actions = Locator(By.CSS_SELECTOR, "app-actions-button button", Descriptor.BUTTON)
        config = Locator(By.XPATH, "//button[.//span[text()='settings']]", Descriptor.BUTTON)
        maintenance_mode = Locator(By.CLASS_NAME, "mm-button", Descriptor.BUTTON)
