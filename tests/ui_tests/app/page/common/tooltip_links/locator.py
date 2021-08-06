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


from selenium.webdriver.common.by import By

from tests.ui_tests.app.helpers.locator import (
    Locator,
    TemplateLocator,
)


class CommonToolbarLocators:
    """Common toolbar elements locators"""

    progress_bar = Locator(
        By.XPATH,
        "//mat-progress-bar/div[contains(@class, 'mat-progress-bar-secondary')]",
        "Loading info",
    )
    admin_link = Locator(By.XPATH, "//a[@routerlink='/admin']", "Link to /admin")
    text_link = TemplateLocator(By.XPATH, "//a[text()='{}']", "Link to {}")
    action_btn = TemplateLocator(
        By.XPATH, "//span[.//a[text()='{}']]//app-action-list/button", "Action button to {}"
    )
    upgrade_btn = TemplateLocator(
        By.XPATH, "//span[.//a[text()='{}']]//app-upgrade/button", "Upgrade button to {}"
    )

    class Popup:
        """Popup to choose action or import"""

        popup_block = Locator(
            By.XPATH, "//div[contains(@class, 'mat-menu-content')]", "Header popup block"
        )
        item = TemplateLocator(
            By.XPATH, "//button[@role='menuitem' and ./*[text()='{}']]", "Item {}"
        )
