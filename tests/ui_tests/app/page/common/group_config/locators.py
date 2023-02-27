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

"""Group Configuration list page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.core.locators import BaseLocator


class GroupConfigLocators:
    """Group Configuration locators"""

    group_row = BaseLocator(By.CSS_SELECTOR, "app-group-fields mat-expansion-panel-header", "Configuration row")
    config_row = BaseLocator(By.CSS_SELECTOR, "app-config-field-attribute-provider", "Configuration row")
    customization_chbx = BaseLocator(By.CSS_SELECTOR, "mat-checkbox", "Checkbox customization")
    input = BaseLocator(By.CSS_SELECTOR, '*:not([style="display: none;"])>mat-form-field input,textarea', "Row input")
    add_item_btn = BaseLocator(
        By.XPATH,
        ".//button//mat-icon[text()='add_circle_outline']",
        "Add item to parameter button",
    )
