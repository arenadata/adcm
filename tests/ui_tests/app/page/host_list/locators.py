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

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.table.locator import CommonTable


class HostListLocators:
    """Cluster List page elements locators"""

    class Tooltip:
        host_add_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Host add button")

    class CreateHostPopup:
        block = Locator(By.XPATH, "//mat-dialog-container", "Popup block")

        # PROVIDER
        bundle_select_btn = Locator(
            By.XPATH, "//mat-select[@placeholder='Bundle']", "Select bundle"
        )
        select_option = Locator(By.XPATH, "//mat-option", "Select option")
        chosen_provider = Locator(
            By.XPATH,
            "//mat-select[contains(@placeholder, 'Hostprovider')]",
            "Chosen provider field",
        )
        provider_add_btn = Locator(By.XPATH, "//mat-icon[text()='add']", "Add host provider button")
        new_provider_block = Locator(By.XPATH, "//app-add-provider", "Host provider creation block")
        new_provider_name = Locator(
            By.XPATH, "//input[@formcontrolname='name']", "New host provider name"
        )
        upload_bundle_btn = Locator(
            By.XPATH, "//input[@value='upload_bundle_file']", "Upload bundle button"
        )
        new_provider_add_btn = Locator(
            By.XPATH, "//mat-icon[text()='add_box']", "Add new provider button"
        )

        # HOST
        fqdn_input = Locator(
            By.XPATH, "//input[@data-placeholder='Fully qualified domain name']", "Host FQDN input"
        )
        description_input = Locator(
            By.XPATH, "//input[@data-placeholder='Description']", "Description input"
        )
        create_btn = Locator(By.XPATH, "//button[./span[text()='Create']]", "Create button")
        cancel_btn = Locator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")

        # CLUSTER
        cluster_select = Locator(
            By.XPATH, "//mat-select[@formcontrolname='cluster_id']", "Cluster choice select"
        )
        cluster_option = Locator(By.XPATH, "//mat-option//span[text()='{}']", "Cluster select option")

    class DeleteDialog:
        body = Locator(By.XPATH, "//mat-dialog-container", "Dialog with choices")
        yes = Locator(By.XPATH, "//button//span[contains(text(), 'Yes')]", "Yes button in dialog")

    class HostTable(CommonTable):
        option = Locator(By.XPATH, "//mat-option//span[contains(text(), '{}')]", "Table dropdown option")

        class HostRow:
            fqdn = Locator(By.XPATH, "./mat-cell[1]", "Host FQDN in row")
            provider = Locator(By.XPATH, "./mat-cell[2]", "Host provider in row")
            cluster = Locator(By.XPATH, "./mat-cell[3]", "Host cluster in row")
            state = Locator(By.XPATH, "./mat-cell[4]", "Host state in row")
            status = Locator(By.XPATH, ".//app-status-column/button", "Host status in row")
            actions = Locator(By.XPATH, ".//app-actions-button/button", "Host actions in row")
            config = Locator(By.XPATH, "./mat-cell[7]/button", "Host config in row")
            delete_btn = Locator(By.XPATH, "./mat-cell[8]/button", "Host delete button in row")
