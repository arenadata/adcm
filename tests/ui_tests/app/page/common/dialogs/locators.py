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

"""Dialog locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.core.locators import BaseLocator


class Dialog:
    """Generic dialog"""

    body = BaseLocator(By.CSS_SELECTOR, "mat-dialog-container", "Dialog with choices")


class DeleteDialogLocators(Dialog):
    yes = BaseLocator(By.XPATH, "//button//span[contains(text(), 'Yes')]", "Yes button in delete dialog")


class ActionDialog(Dialog):
    text = BaseLocator(By.CSS_SELECTOR, "app-dialog mat-dialog-content", "Dialog content")
    next_btn = BaseLocator(By.CSS_SELECTOR, ".mat-stepper-next", "Next button in action dialog")
    run = BaseLocator(By.CSS_SELECTOR, "app-dialog button[color='accent']", "Run button in action dialog")
    cancel = BaseLocator(By.CSS_SELECTOR, "app-dialog button[color='primary']", "Cancel button in action dialog")


class OperationChangesDialogLocators(Dialog):
    row = BaseLocator(By.TAG_NAME, "mat-row", "Changes row")

    class Row:
        attribute = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-child", "Attribute value of changes row")
        old_value = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Old value of changes row")
        new_value = BaseLocator(By.CSS_SELECTOR, "mat-cell:last-child", "New value of changes row")


class ServiceLicenseDialog:
    """Services page licence popup elements locators"""

    block_header = BaseLocator(
        By.XPATH,
        "//app-dialog/h3[contains(text(), 'license')]",
        "header of block with license agreement",
    )
    block = BaseLocator(
        By.XPATH,
        "//app-dialog[./h3[contains(text(), 'license')]]",
        "block with license agreement",
    )
    agree_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'Yes')]]", "Agree button")
    disagree_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'No')]]", "Disagree button")
    license_text_field = BaseLocator(
        By.XPATH,
        "//mat-dialog-content[./pre[contains(text(), '')]]",
        "license text",
    )
