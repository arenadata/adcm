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


class HostComponentsLocators:
    """Common host components page locators"""

    restore_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Restore')]]", "Restore button")
    save_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Save button")

    components_title = Locator(By.XPATH, "//h3[./span[contains(text(), 'Components')]]", "Title for Components block")
    service_page_link = Locator(By.CSS_SELECTOR, "mat-card-content a[href*='service']", "Link to service page")

    hosts_title = Locator(By.XPATH, "//h3[./span[contains(text(), 'Hosts')]]", "Title for Hosts block")
    hosts_page_link = Locator(By.CSS_SELECTOR, "mat-card-content a[href*='host']", "Link to hosts page")
    create_hosts_btn = Locator(
        By.CSS_SELECTOR, "app-service-host button[adcm_test='create-btn']", "Create hosts button"
    )

    host_row = Locator(By.XPATH, "//div[./h3/span[contains(text(), 'Host')]]//app-much-2-many", "Host row")
    component_row = Locator(
        By.XPATH,
        "//div[./h3/span[contains(text(), 'Components')]]//app-much-2-many",
        "Component row",
    )

    class Row:
        """Components page row elements locators"""

        name = Locator(By.XPATH, ".//button[@mat-button]/span/span[not(contains(@class, 'warn'))]", "Item name")
        number = Locator(By.CSS_SELECTOR, "button[mat-raised-button] span:first-of-type", "Amount of links")
        relations_row = Locator(By.CSS_SELECTOR, "div[class*='relations-list']", "Row with relations")

        class RelationsRow:
            """Components page relations row elements locators"""

            name = Locator(By.CSS_SELECTOR, "div>span", "Related item name")
            delete_btn = Locator(By.CSS_SELECTOR, "button", "Delete item button")
