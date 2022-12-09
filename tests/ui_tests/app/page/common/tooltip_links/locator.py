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

"""Tooltip page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator


class CommonToolbarLocators:
    """Common toolbar elements locators"""

    progress_bar = Locator(By.CSS_SELECTOR, "*.mat-progress-bar-background", "Loading info")
    all_links = Locator(By.CSS_SELECTOR, "app-navigation mat-nav-list", "Link to /admin")
    admin_link = Locator(By.CSS_SELECTOR, "a[routerlink='/admin']", "Link to /admin")
    text_link = TemplateLocator(By.XPATH, "//a[text()='{}']", "Link to {}")
    action_btn = TemplateLocator(By.XPATH, "//span[.//a[text()='{}']]//app-action-list/button", "Action button to {}")
    adcm_action_btn = Locator(
        By.XPATH,
        "//mat-nav-list[./a[@routerlink='/admin']]//app-action-list/button",
        "Action button to adcm",
    )
    upgrade_btn = TemplateLocator(By.XPATH, "//*[.//a[text()='{}']]//app-upgrade/button", "Upgrade button to {}")
    warn_btn = TemplateLocator(By.XPATH, "//span[.//a[text()='{}']]//app-concern-list-ref/button", "Warn button to {}")

    class Popup:
        """Popup to choose action or import"""

        popup_block = Locator(By.CSS_SELECTOR, "*.mat-menu-content", "Header popup block")
        item = TemplateLocator(By.XPATH, "//button[@role='menuitem' and ./*[text()='{}']]", "Item {}")

    class WarnPopup:
        """Warning Popup"""

        popup_block = Locator(By.CSS_SELECTOR, "app-popover", "Warning popup block")
        item = Locator(By.CSS_SELECTOR, "app-popover app-concern", "Item with warning")

    class Hint:
        """Hints with information"""

        hint_text = Locator(By.CSS_SELECTOR, "mat-tooltip-component div", "Hint text")
