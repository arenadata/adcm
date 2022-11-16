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

"""Service page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator


class ServiceComponentLocators:
    """Service component page elements locators"""

    component_row = Locator(By.CSS_SELECTOR, "app-service-components .mat-row", "Component row")

    class ComponentRow:
        """Component row locators"""

        name = Locator(By.CSS_SELECTOR, "mat-cell:first-of-type", "Component name")
        state = Locator(By.CSS_SELECTOR, "app-state-column", "Component state")
        status = Locator(By.CSS_SELECTOR, "app-status-column button", "Component status")
        actions = Locator(By.CSS_SELECTOR, "app-actions-button button", "Component actions")
        config = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(5) button", "Component config")
