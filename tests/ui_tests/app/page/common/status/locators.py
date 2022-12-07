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

"""Cluster page locators"""

from selenium.webdriver.common.by import By
from tests.ui_tests.app.helpers.locator import Locator


class StatusLocators:
    """Status page elements locators"""

    expand_collapse_btn = Locator(By.CSS_SELECTOR, "mat-card-content .mat-raised-button", "Expand/Collapse All button")
    group_row = Locator(By.CSS_SELECTOR, "mat-card-content mat-tree-node", "Status row")

    class StatusRow:
        """Status page row elements locators"""

        collapse_btn = Locator(By.CSS_SELECTOR, "button", "Collapse list button")
        icon = Locator(By.XPATH, ".//mat-icon[not(contains(text(), 'expand_more'))]", "Status icon")
        group_name = Locator(By.CSS_SELECTOR, ".expandable", "Status group name")
        state = Locator(By.CSS_SELECTOR, ".counts", "Status group state")
        link = Locator(By.CSS_SELECTOR, "a", "Link")
