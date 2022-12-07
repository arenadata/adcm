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
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.table.locator import CommonTable


class ProviderListLocators:
    """Provider List page elements locators"""

    class Tooltip:
        """Provider List page tooltip elements locators"""

        add_btn = Locator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Provider add button")

    class CreateProviderPopup:
        """Provider List page create provider elements locators"""

        block = Locator(By.CSS_SELECTOR, "mat-dialog-container", "Popup block")
        bundle_select_btn = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Bundle']", "Select bundle")
        version_select_btn = Locator(
            By.CSS_SELECTOR, "mat-select[formcontrolname='bundle_id']", "Select bundle version"
        )
        select_option = Locator(By.CSS_SELECTOR, "mat-option", "Select option")

        upload_bundle_btn = Locator(By.CSS_SELECTOR, "input[value='upload_bundle_file']", "Upload bundle button")
        provider_name_input = Locator(
            By.CSS_SELECTOR, "input[data-placeholder='Hostprovider name']", "Provider name input"
        )
        description_input = Locator(By.CSS_SELECTOR, "input[data-placeholder='Description']", "Description input")

        create_btn = Locator(By.XPATH, "//button[./span[text()='Create']]", "Create button")
        cancel_btn = Locator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")

    class ProviderTable(CommonTable):
        """Provider List page provider table elements locators"""

        class ProviderRow:
            """Provider List page provider row elements locators"""

            name = Locator(By.CSS_SELECTOR, "mat-cell:first-child", "Provider name in row")
            bundle = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Provider bundle in row")
            state = Locator(By.CSS_SELECTOR, "app-state-column", "Provider state in row")
            actions = Locator(By.CSS_SELECTOR, "app-action-list button", "Provider actions in row")
            upgrade = Locator(By.CSS_SELECTOR, "app-upgrade button", "Provider upgrade in row")
            config = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(6) button", "Provider config in row")
            delete_btn = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(7) button", "Provider delete button in row")
