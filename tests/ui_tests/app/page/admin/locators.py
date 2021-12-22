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

"""Admin page locators"""

from selenium.webdriver.common.by import By

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu


class AdminIntroLocators:
    """Locators for Admin Intro menu"""

    intro_title = Locator(By.CSS_SELECTOR, ".content mat-card-header", "Intro header container")
    intro_text = Locator(By.CSS_SELECTOR, ".content mat-card-content", "Intro text container")


class AdminSettingsLocators(CommonConfigMenu):
    """Locators for Admin Settings menu"""


class AdminUsersLocators:
    """Locators for Admin Users menu"""

    add_user_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Add user')]]", "Add user button")
    user_row = Locator(By.CSS_SELECTOR, "mat-row", "Table row")

    class Row:
        """Existing user row"""

        username = Locator(By.CSS_SELECTOR, "mat-cell:first-child", "Username in row")
        password = Locator(By.CSS_SELECTOR, "input[data-placeholder='Password']", "Password in row")
        password_confirm = Locator(
            By.CSS_SELECTOR, "input[data-placeholder='Confirm Password']", "Password confirmation in row"
        )
        confirm_update_btn = Locator(
            By.XPATH,
            ".//button[.//mat-icon[text()='done']]",
            "Confirm password update button in row",
        )
        delete_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Delete user button in row")

    class AddUserPopup:
        """Popup with new user info"""

        block = Locator(By.CSS_SELECTOR, "mat-card[class*='users-add-card']", "Add user popup block")
        username = Locator(By.CSS_SELECTOR, "input[formcontrolname='username']", "New user username")
        password = Locator(By.CSS_SELECTOR, "input[formcontrolname='password']", "New user password")
        password_confirm = Locator(
            By.CSS_SELECTOR, "input[formcontrolname='cpassword']", "New user password confirmation"
        )
        save_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Save')]]", "Add user save button")


class AdminRolesLocators:
    """Locators for Admin Roles menu"""

    create_role_btn = Locator(By.CSS_SELECTOR, "app-add-button button", "Create role button")
    delete_btn = Locator(By.CSS_SELECTOR, ".controls>button", "Delete role button")

    class RoleRow:
        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", "Role checkbox")
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Role name")
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Role description")
        permissions = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", "Role permissions")

    class AddRolePopup:
        """Locators for creating roles popup"""

        block = Locator(By.CSS_SELECTOR, "app-rbac-role-form", "Add role popup block")
        role_name_input = Locator(By.CSS_SELECTOR, "adwp-input[controlname='display_name'] input", "Input for role name")
        description_name_input = Locator(By.CSS_SELECTOR, "adwp-input[controlname='description'] input", "Input for role description")

        class PermissionItemsBlock:
            filter_input = Locator(By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter input", "Filter input")
            item = Locator(By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-field mat-chip", "Selected permission item")
            clear_all_btn = Locator(By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter-clear", "Clear all button")

            class PermissionItem:
                name = Locator(By.CSS_SELECTOR, "div", "Name")
                delete_btn = Locator(By.CSS_SELECTOR, "button", "Delete button")

        class SelectPermissionsBlock:
            permissions_filters = Locator(By.CSS_SELECTOR, ".adcm-rbac-permission__filter mat-chip",
                                          "filter item for permissions list")
            permissions_search_row = Locator(By.CSS_SELECTOR, "adwp-selection-list-actions", "Permission search row")
            permissions_item_row = Locator(By.CSS_SELECTOR, ".adcm-rbac-permission__options mat-list-option", "Permission row")
            select_btn = Locator(By.CSS_SELECTOR, ".adcm-rbac-permission__actions", "Select button")

            class SelectPermissionsRow:
                checkbox = Locator(By.CSS_SELECTOR, "mat-pseudo-checkbox", "Checkbox")
                name = Locator(By.CSS_SELECTOR, ".mat-list-text", "Name")

        create_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Create')]]", "Create button")
