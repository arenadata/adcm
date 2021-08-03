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

from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator


class CommonPopupLocators:
    """ADCM popup locators"""

    block = Locator(By.XPATH, "//simple-snack-bar", "Popup block")
    hide_btn = Locator(By.XPATH, "//button[./span[text()='Hide']]", "Hide pop up button")


class HostCreationLocators:
    """Host creation popup without cluster selection"""

    block = Locator(By.XPATH, "//mat-dialog-container", "Popup block")
    fqdn_input = Locator(
        By.XPATH, "//input[@data-placeholder='Fully qualified domain name']", "Host FQDN input"
    )
    create_btn = Locator(By.XPATH, "//button[./span[text()='Create']]", "Create button")
    cancel_btn = Locator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")

    class Provider:
        """Provider creation and selection section"""

        bundle_select_btn = Locator(
            By.XPATH, "//mat-select[@placeholder='Bundle']", "Select bundle"
        )
        select_option = Locator(By.XPATH, "//mat-option", "Select option")
        chosen_provider = Locator(
            By.XPATH,
            "//mat-select[contains(@placeholder, 'Hostprovider')]",
            "Chosen provider field",
        )
        add_btn = Locator(By.XPATH, "//mat-icon[text()='add']", "Add host provider button")
        new_provider_block = Locator(By.XPATH, "//app-add-provider", "Host provider creation block")
        new_provider_name = Locator(
            By.XPATH, "//input[@formcontrolname='name']", "New host provider name"
        )
        upload_bundle_btn = Locator(
            By.XPATH, "//input[@value='upload_bundle_file']", "Upload bundle button"
        )
        new_provider_add_btn = Locator(
            By.XPATH, "//button[@mattooltip='Create hostprovider']", "Add new provider button"
        )

    class Cluster:
        """
        Cluster selection locators
        ! May not be presented (e.g. create host from cluster) !
        """

        cluster_select = Locator(
            By.XPATH, "//mat-select[@formcontrolname='cluster_id']", "Cluster choice select"
        )
        cluster_option = TemplateLocator(
            By.XPATH, "//mat-option//span[text()='{}']", "Cluster select option"
        )
