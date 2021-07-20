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


class ClusterListLocators:
    """Cluster List page elements locators"""

    class Tooltip:
        cluster_add_btn = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Cluster add button")

    class CreateClusterPopup:
        block = Locator(By.XPATH, "//mat-dialog-container", "Popup block")
        bundle_select_btn = Locator(By.XPATH, "//mat-select[@placeholder='Bundle']", "Select bundle")
        version_select_btn = Locator(By.XPATH, "//mat-select[@formcontrolname='bundle_id'']", "Select bundle version")
        select_option = Locator(By.XPATH, "//mat-option", "Select option")

        upload_bundle_btn = Locator(By.XPATH, "//input[@value='upload_bundle_file']", "Upload bundle button")
        cluster_name_input = Locator(By.XPATH, "//input[@data-placeholder='Cluster name']", "Cluster name input")
        description_input = Locator(By.XPATH, "//input[@data-placeholder='Description']", "Description input")

        create_btn = Locator(By.XPATH, "//button[./span[text()='Create']]", "Create button")

    class ClusterTable:
        header = Locator(By.XPATH, "//mat-header-cell/div", "Cluster table header")
        row = Locator(By.XPATH, "//mat-row", "Cluster table row")

        class ClusterRow:
            name = Locator(By.XPATH, "./mat-cell[1]", "Cluster name in row")
            bundle = Locator(By.XPATH, "./mat-cell[2]", "Cluster bundle in row")
            description = Locator(By.XPATH, "./mat-cell[3]", "Cluster description in row")
            state = Locator(By.XPATH, "./mat-cell[4]", "Cluster state in row")
            status = Locator(By.XPATH, ".//app-status-column/button", "Cluster status in row")
            actions = Locator(By.XPATH, ".//app-actions-button/button", "Cluster actions in row")
            imports = Locator(By.XPATH, "./mat-cell[7]/button", "Cluster imports in row")
            upgrade = Locator(By.XPATH, ".//app-upgrade/button", "Cluster upgrade in row")
            config = Locator(By.XPATH, "./mat-cell[9]/button", "Cluster config in row")
            delete_btn = Locator(By.XPATH, "./mat-cell[10]/button", "Cluster delete button in row")
