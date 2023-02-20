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

"""Profile List page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.core.locators import BaseLocator


class ProviderListLocators:
    """Provider List page elements locators"""

    class Tooltip:
        """Provider List page tooltip elements locators"""

        add_btn = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Provider add button")

    class CreateProviderPopup:
        """Provider List page create provider elements locators"""

        block = BaseLocator(By.CSS_SELECTOR, "mat-dialog-container", "Popup block")
        bundle_select_btn = BaseLocator(By.CSS_SELECTOR, "mat-select[placeholder='Bundle']", "Select bundle")
        version_select_btn = BaseLocator(
            By.CSS_SELECTOR,
            "mat-select[formcontrolname='bundle_id']",
            "Select bundle version",
        )
        select_option = BaseLocator(By.CSS_SELECTOR, "mat-option", "Select option")

        upload_bundle_btn = BaseLocator(By.CSS_SELECTOR, "input[value='upload_bundle_file']", "Upload bundle button")
        provider_name_input = BaseLocator(
            By.CSS_SELECTOR,
            "input[data-placeholder='Hostprovider name']",
            "Provider name input",
        )
        description_input = BaseLocator(By.CSS_SELECTOR, "input[data-placeholder='Description']", "Description input")

        create_btn = BaseLocator(By.XPATH, "//button[./span[text()='Create']]", "Create button")
        cancel_btn = BaseLocator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")

    class ProviderTable(CommonTable):
        """Provider List page provider table elements locators"""

        class ProviderRow:
            """Provider List page provider row elements locators"""

            name = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-child", "Provider name in row")
            bundle = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Provider bundle in row")
            state = BaseLocator(By.CSS_SELECTOR, "app-state-column", "Provider state in row")
            actions = BaseLocator(By.CSS_SELECTOR, "app-action-list button", "Provider actions in row")
            upgrade = BaseLocator(By.CSS_SELECTOR, "app-upgrade button", "Provider upgrade in row")
            config = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(6) button", "Provider config in row")
            delete_btn = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(7) button", "Provider delete button in row")
