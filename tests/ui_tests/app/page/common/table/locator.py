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

"""Table page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.core.locators import BaseLocator, TemplateLocator


class CommonTable:
    """Common table locators (eg, cluster list page table)."""

    header = BaseLocator(By.CSS_SELECTOR, "mat-header-cell>div", "Table header")
    row = BaseLocator(By.CSS_SELECTOR, "mat-row[adwphover]", "Table row")
    backdrop = BaseLocator(By.CSS_SELECTOR, ".cdk-overlay-backdrop", "backdrop")
    tooltip_text = BaseLocator(By.CSS_SELECTOR, "#cdk-describedby-message-container div", "Tooltip text")

    class ActionPopup:
        """Common popup for action in tables."""

        block = BaseLocator(By.CSS_SELECTOR, "div[role='menu']", "Action popup block")
        button = TemplateLocator(
            By.XPATH,
            "//button[@adcm_test='action_btn' and ./span[text()='{}']]",
            "Button with action {}",
        )
        action_buttons = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='action_btn']", "Button with action")

    class UpgradePopup:
        """Common popup for upgrade in tables."""

        block = BaseLocator(By.CSS_SELECTOR, "div[role='menu']", "Upgrade popup block")
        button = TemplateLocator(By.XPATH, "//button[./span[text()='{}']]", "Button with upgrade {}")
        license_block = BaseLocator(
            By.XPATH,
            "//app-dialog[./h3[contains(text(), 'license')]]",
            "block with license agreement",
        )
        hide_btn = BaseLocator(By.XPATH, "//button[./span[text()='Hide']]", "Hide pop up button")
        text = BaseLocator(By.CSS_SELECTOR, "app-snack-bar .message", "Popup info message")

    class Pagination:
        """Common table pagination locators."""

        previous_page = BaseLocator(By.CSS_SELECTOR, "button[aria-label='Previous page']", "Previous page button")
        page_btn = BaseLocator(By.CSS_SELECTOR, "a[class*='page-button']", "Page button")
        page_to_choose_btn = TemplateLocator(
            By.XPATH,
            "//a[contains(@class, 'page-button') and text()='{}']",
            "Page button",
        )
        next_page = BaseLocator(By.CSS_SELECTOR, "button[aria-label='Next page']", "Next page button")

        per_page_dropdown = BaseLocator(
            By.CSS_SELECTOR,
            "mat-select[aria-label='Items per page:']",
            "Rows per page dropdown",
        )
        per_page_block = BaseLocator(
            By.CSS_SELECTOR,
            "div[aria-label='Items per page:']",
            "Container of rows per page options",
        )
        per_page_element = BaseLocator(By.TAG_NAME, "mat-option", "Rows per page option")
