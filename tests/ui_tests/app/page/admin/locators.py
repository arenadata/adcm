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
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu


class AdminIntroLocators:
    """Locators for Admin Intro menu"""

    intro_title = Locator(By.XPATH, "//mat-card-header", "Intro header container")
    intro_text = Locator(By.XPATH, "//mat-card-content", "Intro text container")


class AdminSettingsLocators(CommonConfigMenu):
    """Locators for Admin Settings menu"""


class AdminUsersLocators:
    """Locators for Admin Users menu"""

    add_user_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Add user')]]", "Add user button")
    user_row = Locator(By.XPATH, "//mat-row", "Table row")

    class Row:
        """Existing user row"""

        username = Locator(By.XPATH, "./mat-cell[1]", "Username in row")
        password = Locator(By.XPATH, "./mat-cell[2]//input[@data-placeholder='Password']", "Password in row")
        password_confirm = Locator(
            By.XPATH,
            "./mat-cell[2]//input[@data-placeholder='Confirm Password']",
            "Password confirmation in row",
        )
        confirm_update_btn = Locator(
            By.XPATH,
            ".//button[.//mat-icon[text()='done']]",
            "Confirm password update button in row",
        )
        delete_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Delete user button in row")

    class AddUserPopup:
        """Popup with new user info"""

        block = Locator(By.XPATH, "//mat-card[contains(@class, 'users-add-card')]", "Add user popup block")
        username = Locator(By.XPATH, "//input[@formcontrolname='username']", "New user username")
        password = Locator(By.XPATH, "//input[@formcontrolname='password']", "New user password")
        password_confirm = Locator(By.XPATH, "//input[@formcontrolname='cpassword']", "New user password confirmation")
        save_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Add user save button")
