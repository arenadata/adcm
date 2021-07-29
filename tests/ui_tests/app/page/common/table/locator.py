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


class CommonTable:
    """Common table locators (eg, cluster list page table)."""

    header = Locator(By.XPATH, "//mat-header-cell/div", "Table header")
    row = Locator(By.XPATH, "//mat-row", "Table row")

    class ActionPopup:
        """Common popup for action in tables."""

        block = Locator(By.XPATH, "//div[@role='menu']", "Action popup block")
        button = TemplateLocator(By.XPATH, "//button[@adcm_test='action_btn' and ./span[text()='{}']]",
                                 "Button with action {}")

    class Pagination:
        """Common table pagination locators."""

        previous_page = Locator(
            By.XPATH, "//button[@aria-label='Previous page']", "Previous page button"
        )
        page_btn = Locator(By.XPATH, "//a[contains(@class, 'page-button')]", "Page button")
        page_to_choose_btn = Locator(
            By.XPATH, "//a[contains(@class, 'page-button') and text()='{}']", "Page button"
        )
        next_page = Locator(By.XPATH, "//button[@aria-label='Next page']", "Next page button")
