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
from tests.ui_tests.app.page.common.table.locator import CommonTable


class HostListLocators:
    """Host List page elements locators"""

    class Tooltip:
        apps_btn = Locator(By.XPATH, "//a[.//mat-icon[text()='apps']]", "Apps button")
        host_add_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Host add button")

    class HostTable(CommonTable):
        cluster_option = TemplateLocator(
            By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Table dropdown option"
        )

        class HostRow:
            fqdn = Locator(By.XPATH, "./mat-cell[1]", "Host FQDN in row")
            provider = Locator(By.XPATH, "./mat-cell[2]", "Host provider in row")
            cluster = Locator(By.XPATH, ".//app-cluster-column", "Host cluster in row")
            state = Locator(By.XPATH, ".//app-state-column", "Host state in row")
            status = Locator(By.XPATH, ".//app-status-column/button", "Host status in row")
            actions = Locator(By.XPATH, ".//app-actions-column//button", "Host actions in row")
            config = Locator(By.XPATH, ".//button[.//mat-icon[text()='settings']]", "Host config in row")
            delete_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Host delete button in row")
            link_off_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='link_off']]", "Host link off button in row")
            action_option = TemplateLocator(By.XPATH, "//button/span[text()='{}']", "Action dropdown option")
