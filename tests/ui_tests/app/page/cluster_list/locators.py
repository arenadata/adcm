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

"""Cluster List page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.table.locator import CommonTable


class ClusterListLocators:
    """Cluster List page elements locators"""

    class Tooltip:
        """Cluster List page tooltip elements locators"""

        cluster_add_btn = Locator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Cluster add button")

    class CreateClusterPopup:
        """Cluster List page create cluster popup elements locators"""

        block = Locator(By.CSS_SELECTOR, "mat-dialog-container", "Popup block")
        bundle_select_btn = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Bundle']", "Select bundle")
        version_select_btn = Locator(
            By.CSS_SELECTOR, "mat-select[formcontrolname='bundle_id']", "Select bundle version"
        )
        select_option = Locator(By.CSS_SELECTOR, "mat-option", "Select option")

        upload_bundle_btn = Locator(By.CSS_SELECTOR, "input[value='upload_bundle_file']", "Upload bundle button")
        cluster_name_input = Locator(By.CSS_SELECTOR, "input[data-placeholder='Cluster name']", "Cluster name input")
        description_input = Locator(By.CSS_SELECTOR, "input[data-placeholder='Description']", "Description input")

        create_btn = Locator(By.CSS_SELECTOR, "app-add-controls button:last-child", "Create button")
        cancel_btn = Locator(By.CSS_SELECTOR, "app-add-controls button:first-child", "Cancel button")

    class ClusterTable(CommonTable):
        """Cluster List page cluster table elements locators"""

        class ClusterRow:
            """Cluster List page cluster row elements locators"""

            name = Locator(By.CSS_SELECTOR, "mat-cell:first-of-type", "Cluster name in row")
            bundle = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Cluster bundle in row")
            description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Cluster description in row")
            state = Locator(By.CSS_SELECTOR, "app-state-column", "Cluster state in row")
            status = Locator(By.CSS_SELECTOR, "app-status-column button", "Cluster status in row")
            actions = Locator(By.CSS_SELECTOR, "app-actions-button button", "Cluster actions in row")
            imports = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(7) button", "Cluster imports in row")
            upgrade = Locator(By.CSS_SELECTOR, "app-upgrade button", "Cluster upgrade in row")
            config = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(9) button", "Cluster config in row")
            delete_btn = Locator(By.CSS_SELECTOR, "mat-cell:last-of-type button", "Cluster delete button in row")
            rename_btn = Locator(By.CLASS_NAME, "rename-button", "Cluster rename button in row")

    class LicensePopup:
        """Cluster List page licence popup elements locators"""

        block = Locator(By.XPATH, "//app-dialog[./h3[contains(text(), 'license')]]", "block with license agreement")
        agree_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Yes')]]", "Agree button")
