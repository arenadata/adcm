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


class GroupConfigListLocators:
    """Group Configuration list locators"""

    add_btn = BaseLocator(By.CSS_SELECTOR, "button[adcm_test='create-btn']", "Add config group button")
    header_item = BaseLocator(By.CSS_SELECTOR, "mat-table mat-header-cell", "Header item")
    group_config_row = BaseLocator(By.CSS_SELECTOR, "mat-table mat-row", "Group Configuration row")

    class GroupConfigRow:
        """Group Configuration row locators"""

        name = BaseLocator(By.CSS_SELECTOR, "mat-cell:first-child", "Row name")
        description = BaseLocator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Row description")
        delete_btn = BaseLocator(By.CSS_SELECTOR, "button", "Row delete button")

    class CreateGroupPopup:
        block = BaseLocator(By.CSS_SELECTOR, "app-dialog", "Popup block")
        name_input = BaseLocator(By.CSS_SELECTOR, "input[data-placeholder='Name']", "Name input")
        description_input = BaseLocator(By.CSS_SELECTOR, "input[data-placeholder='Description']", "Description input")
        create_btn = BaseLocator(By.CSS_SELECTOR, "app-add-controls button[color='accent']", "Create button")
