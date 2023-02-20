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

from tests.ui_tests.core.locators import BaseLocator


class HostComponentsLocators:
    """Common host components page locators"""

    restore_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'Restore')]]", "Restore button")
    save_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Save button")

    components_title = BaseLocator(
        By.XPATH,
        "//h3[./span[contains(text(), 'Components')]]",
        "Title for Components block",
    )
    service_page_link = BaseLocator(By.CSS_SELECTOR, "mat-card-content a[href*='service']", "Link to service page")

    hosts_title = BaseLocator(By.XPATH, "//h3[./span[contains(text(), 'Hosts')]]", "Title for Hosts block")
    hosts_page_link = BaseLocator(By.CSS_SELECTOR, "mat-card-content a[href*='host']", "Link to hosts page")
    create_hosts_btn = BaseLocator(
        By.CSS_SELECTOR,
        "app-service-host button[adcm_test='create-btn']",
        "Create hosts button",
    )

    host_row = BaseLocator(By.XPATH, "//div[./h3/span[contains(text(), 'Host')]]//app-much-2-many", "Host row")
    component_row = BaseLocator(
        By.XPATH,
        "//div[./h3/span[contains(text(), 'Components')]]//app-much-2-many",
        "Component row",
    )

    class Row:
        """Components page row elements locators"""

        name = BaseLocator(By.XPATH, ".//button[@mat-button]/span/span[not(contains(@class, 'warn'))]", "Item name")
        number = BaseLocator(By.CSS_SELECTOR, "button[mat-raised-button] span:first-of-type", "Amount of links")
        relations_row = BaseLocator(By.CSS_SELECTOR, "div[class*='relations-list']", "Row with relations")

        class RelationsRow:
            """Components page relations row elements locators"""

            name = BaseLocator(By.CSS_SELECTOR, "div>span", "Related item name")
            delete_btn = BaseLocator(By.CSS_SELECTOR, "button", "Delete item button")
