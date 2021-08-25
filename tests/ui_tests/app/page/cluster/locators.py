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
)
from tests.ui_tests.app.page.host_list.locators import HostListLocators


class ClusterMainLocators:
    """Cluster main page elements locators"""

    text = Locator(By.XPATH, "//mat-card-content", "Cluster main page text")


class ClusterServicesLocators:
    """Cluster main page elements locators"""

    add_services_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Add services button")
    service_row = Locator(By.XPATH, "//mat-row", "Service row")

    class AddServicePopup:
        """Popup for adding services"""

        block = Locator(By.XPATH, "//mat-dialog-container", "Popup block")
        service_row = Locator(By.XPATH, "//mat-list-option", "Service row")
        create_btn = Locator(By.XPATH, "//button[./span[text()='Add']]", "Add button")
        cancel_btn = Locator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")

        class ServiceRow:
            """Locators for services row"""

            text = Locator(By.XPATH, ".//div[@class='mat-list-text']", "Service name")

    class ServiceTableRow:
        """Services table roe locators"""

        name = Locator(By.XPATH, ".//mat-cell[1]", "Service name")
        version = Locator(By.XPATH, ".//mat-cell[2]", "Service version")
        state = Locator(By.XPATH, ".//app-state-column", "Service state")
        status = Locator(By.XPATH, ".//app-status-column//button", "Service status")
        actions = Locator(By.XPATH, ".//app-actions-button//button", "Service actions")
        service_import = Locator(By.XPATH, ".//mat-cell[6]//button", "Service import")
        config = Locator(By.XPATH, ".//mat-cell[7]//button", "Service config")


class ClusterImportLocators:
    """Cluster import page elements locators"""

    import_item_block = Locator(By.XPATH, "//div[@class='items']/div", "Import item block")


class ClusterHostLocators:
    """Cluster host page elements locators"""

    add_host_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Add host button")

    class HostTable(HostListLocators.HostTable):
        ...


class ClusterComponentsLocators:
    """Cluster components page elements locators"""

    restore_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Restore')]]", "Restore button")
    save_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Save button")

    components_title = Locator(By.XPATH, "//h3[./span[contains(text(), 'Components')]]", "Title for Components block")
    service_page_link = Locator(By.XPATH, "//mat-card-content//a[contains(@href, 'service')]", "Link to service page")

    hosts_title = Locator(By.XPATH, "//h3[./span[contains(text(), 'Hosts')]]", "Title for Hosts block")
    hosts_page_link = Locator(By.XPATH, "//mat-card-content//a[contains(@href, 'host')]", "Link to hosts page")
    create_hosts_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Create hosts button")

    host_row = Locator(By.XPATH, "//div[./h3/span[contains(text(), 'Host')]]//app-much-2-many", "Host row")
    component_row = Locator(
        By.XPATH,
        "//div[./h3/span[contains(text(), 'Components')]]//app-much-2-many",
        "Component row",
    )

    class Row:
        name = Locator(By.XPATH, ".//button[@mat-button]/span/span[not(contains(@class, 'warn'))]", "Item name")
        number = Locator(By.XPATH, ".//button[@mat-raised-button]/span[1]", "Amount of links")
        relations_row = Locator(By.XPATH, ".//div[contains(@class, 'relations-list')]", "Row with relations")

        class RelationsRow:
            name = Locator(By.XPATH, "./div/span", "Related item name")
            delete_btn = Locator(By.XPATH, ".//button", "Delete item button")
