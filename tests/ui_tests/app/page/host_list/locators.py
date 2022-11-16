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

"""Host List page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator
from tests.ui_tests.app.page.common.table.locator import CommonTable


class HostListLocators:
    """Host List page elements locators"""

    class Tooltip:
        """Host List page tooltip elements locators"""

        apps_btn = Locator(By.XPATH, "//a[.//mat-icon[text()='apps']]", "Apps button")
        host_add_btn = Locator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Host add button")

    class HostTable(CommonTable):
        """Host List page host table elements locators"""

        cluster_option = TemplateLocator(
            By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Table dropdown option"
        )

        class HostRow:
            """Host List page host row elements locators"""

            fqdn = Locator(By.CSS_SELECTOR, "mat-cell:first-child", "Host FQDN in row")
            provider = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Host provider in row")
            cluster = Locator(By.CSS_SELECTOR, "app-cluster-column", "Host cluster in row")
            state = Locator(By.CSS_SELECTOR, "app-state-column", "Host state in row")
            status = Locator(By.CSS_SELECTOR, "app-status-column button", "Host status in row")
            actions = Locator(By.CSS_SELECTOR, "app-actions-button button", "Host actions in row")
            config = Locator(By.XPATH, ".//button[.//mat-icon[text()='settings']]", "Host config in row")
            maintenance_mode_btn = Locator(
                By.XPATH, ".//button[.//mat-icon[text()='medical_services']]", "Maintenance Mode button in row"
            )
            delete_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Host delete button in row")
            link_off_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='link_off']]", "Host link off button in row")
            dropdown_menu = Locator(By.CSS_SELECTOR, "div[role='menu']", "Dropdown menu")
            action_option = TemplateLocator(By.XPATH, "//button/span[text()='{}']", "Action dropdown option")
            action_option_all = Locator(By.CSS_SELECTOR, "button[adcm_test='action_btn']", "Action dropdown options")
            rename_btn = Locator(By.CLASS_NAME, "rename-button", "Cluster rename button in row")
