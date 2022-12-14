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

"""Common import page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.core.locators import BaseLocator


class ImportLocators:
    """Common import page elements locators"""

    save_btn = BaseLocator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Save button")
    import_item_block = BaseLocator(By.CSS_SELECTOR, ".items>div", "Import item block")

    class ImportItem:
        """Import item elements locators"""

        name = BaseLocator(By.CSS_SELECTOR, "h3", "Import item name")
        import_chbx = BaseLocator(By.CSS_SELECTOR, "mat-checkbox", "Import checkbox")
        description = BaseLocator(By.CSS_SELECTOR, "app-exports>div>div", "Description text")
