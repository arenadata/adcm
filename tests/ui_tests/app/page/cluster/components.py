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
from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from tests.ui_tests.app.core import Interactor
from tests.ui_tests.app.helpers.locator import Locator


class RowLocators:
    name = Locator(By.CSS_SELECTOR, "mat-cell:first-of-type", "Component name")
    state = Locator(By.CSS_SELECTOR, "app-state-column", "Component state")
    status = Locator(By.CSS_SELECTOR, "app-status-column button", "Component status")
    actions = Locator(By.CSS_SELECTOR, "app-actions-button button", "Component actions")
    config = Locator(By.XPATH, "//button[.//span[text()='settings']]", "Component config")
    maintenance_mode = Locator(By.CLASS_NAME, "mm-button", "Maintenance mode button")


class ComponentRow:
    _loc = RowLocators

    def __init__(self, row_element: WebElement, driver: WebDriver):
        self._element = row_element
        self._view = Interactor(driver=driver, default_timeout=0.5)

        self.name: str = self._view.find_child(self._element, self._loc.name).text

    @property
    def state(self) -> str:
        return self._view.find_child(self._element, self._loc.state).text

    @property
    def status(self) -> str:
        return self._view.find_child(self._element, self._loc.status).text

    @property
    def actions_button(self) -> WebElement:
        return self._view.find_child(self._element, self._loc.actions)

    @property
    def config_button(self) -> WebElement:
        return self._view.find_child(self._element, self._loc.config)

    @property
    def maintenance_mode_button(self) -> WebElement:
        return self._view.find_child(self._element, self._loc.maintenance_mode)

    @property
    def maintenance_mode(self) -> Literal["ON", "OFF", "ANOTHER"]:
        classes = set(self.maintenance_mode_button.get_attribute("class").split())

        if "mat-on" in classes:
            return "ON"

        if "mat-primary" in classes:
            return "OFF"

        return "ANOTHER"
