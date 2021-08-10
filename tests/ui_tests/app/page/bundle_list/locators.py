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


class BundleListLocators:
    """Bundle List page elements locators"""

    class Tooltip:
        upload_btn = Locator(
            By.XPATH, "//input[@value='upload_bundle_file']", "Bundle upload button"
        )

    class Table(CommonTable):
        class Row:
            name = Locator(By.XPATH, "./mat-cell[1]", "Bundle name in row")
            version = Locator(By.XPATH, "./mat-cell[2]", "Bundle version in row")
            edition = Locator(By.XPATH, "./mat-cell[3]", "Bundle edition in row")
            description = Locator(By.XPATH, "./mat-cell[4]", "Bundle description in row")
            delete_btn = Locator(By.XPATH, "./mat-cell[5]//button", "Bundle delete button in row")
            license_btn = Locator(
                By.XPATH,
                "//button[@mattooltip='Accept license agreement']",
                "Licence warning button in row",
            )

    class LicensePopup:
        block = Locator(
            By.XPATH,
            "//app-dialog[./h3[contains(text(), 'license')]]",
            "block with license agreement",
        )
        agree_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Yes')]]", "Agree button")
