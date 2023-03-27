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

from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.core.locators import BaseLocator, TemplateLocator


class HostListLocators:
    """Host List page elements locators"""

    class Tooltip:
        """Host List page tooltip elements locators"""

        apps_btn = BaseLocator(By.XPATH, "//a[.//mat-icon[text()='apps']]", "Apps button")
        host_add_btn = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Host add button")

    class HostTable(CommonTable):
        """Host List page host table elements locators"""

        cluster_option = TemplateLocator(
            By.XPATH,
            "//mat-option//span[contains(text(), '{}')]",
            "Table dropdown option",
        )
        header = BaseLocator(By.TAG_NAME, "mat-header-row", "Header of the table")

        class HostRow:
            """Host List page host row elements locators"""

            fqdn = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-child", "Host FQDN in row")
            provider = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Host provider in row")
            cluster = BaseLocator(By.CSS_SELECTOR, "app-cluster-column", "Host cluster in row")
            state = BaseLocator(By.CSS_SELECTOR, "app-state-column", "Host state in row")
            status = BaseLocator(By.CSS_SELECTOR, "app-status-column button", "Host status in row")
            actions = BaseLocator(By.CSS_SELECTOR, "app-actions-button button", "Host actions in row")
            config = BaseLocator(By.XPATH, ".//button[.//mat-icon[text()='settings']]", "Host config in row")
            maintenance_mode_btn = BaseLocator(
                By.XPATH,
                ".//button[.//mat-icon[text()='medical_services']]",
                "Maintenance Mode button in row",
            )
            delete_btn = BaseLocator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Host delete button in row")
            link_off_btn = BaseLocator(
                By.XPATH,
                ".//button[.//mat-icon[text()='link_off']]",
                "Host link off button in row",
            )
            dropdown_menu = BaseLocator(By.CSS_SELECTOR, "div[role='menu']", "Dropdown menu")
            action_option = TemplateLocator(By.XPATH, "//button/span[text()='{}']", "Action dropdown option")
            action_option_all = BaseLocator(
                By.CSS_SELECTOR,
                "button[adcm_test='action_btn']",
                "Action dropdown options",
            )
            rename_btn = BaseLocator(By.CLASS_NAME, "rename-button", "Cluster rename button in row")
