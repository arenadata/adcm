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

"""Bundle List page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.core.locators import BaseLocator


class BundleListLocators:
    """Bundle List page elements locators"""

    class Toolbar:
        """Bundle List page toolbar elements locators"""

        apps_btn = BaseLocator(By.XPATH, "//a[.//mat-icon[text()='apps']]", "Apps button")
        upload_btn = BaseLocator(By.CSS_SELECTOR, "input[value='upload_bundle_file']", "Bundle upload button")

    class Table(CommonTable):
        """Bundle List page table elements locators"""

        class Row:
            """Bundle List page table row elements locators"""

            name = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-child", "Bundle name in row")
            version = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Bundle version in row")
            edition = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Bundle edition in row")
            description = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", "Bundle description in row")
            delete_btn = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(5) button", "Bundle delete button in row")
            license_btn = BaseLocator(
                By.CSS_SELECTOR,
                "button[mattooltip='Accept license agreement']",
                "Licence warning button in row",
            )

    class LicensePopup:
        """Bundle List page licence popup elements locators"""

        block = BaseLocator(
            By.XPATH,
            "//app-dialog[./h3[contains(text(), 'license')]]",
            "block with license agreement",
        )
        agree_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'Yes')]]", "Agree button")
