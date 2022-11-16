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
from tests.ui_tests.app.helpers.locator import Locator, TemplateLocator
from tests.ui_tests.app.page.common.configuration.locators import CommonConfigMenu


class CommonAdminPagesLocators:
    """Common locators for admin pages"""

    create_btn = Locator(By.CSS_SELECTOR, "app-add-button button", "Create button")
    delete_btn = Locator(By.CSS_SELECTOR, ".controls>button", "Delete Group button")
    field_error = TemplateLocator(By.XPATH, "//mat-error[contains(text(), '{}')]", 'Error "{}"')
    item = Locator(By.CSS_SELECTOR, "adwp-selection-list mat-list-option", "select items")
    save_update_btn = Locator(
        By.XPATH, "//button[./span[contains(text(), 'Add') or contains(text(), 'Update')]]", "Save/Update button"
    )
    cancel_btn = Locator(By.XPATH, "//button[./span[contains(text(), 'Cancel')]]", "Cancel button")


class AdminIntroLocators:
    """Locators for Admin Intro menu"""

    intro_title = Locator(By.CSS_SELECTOR, ".content mat-card-header", "Intro header container")
    intro_text = Locator(By.CSS_SELECTOR, ".content mat-card-content", "Intro text container")


class AdminSettingsLocators(CommonConfigMenu):
    """Locators for Admin Settings menu"""


class AdminUsersLocators:
    """Locators for Admin Users menu"""

    create_user_button = Locator(By.XPATH, "//button[@adcm_test='create-btn']", "Add user button")
    user_row = Locator(By.CSS_SELECTOR, "mat-row", "Table row")
    filter_btn = Locator(By.CSS_SELECTOR, "app-filter .filter-toggle-button", "Fulter button")
    filter_dropdown_select = Locator(By.CSS_SELECTOR, "app-filter mat-select", "Filter dropdown select")
    filter_dropdown_option = Locator(By.CSS_SELECTOR, "div[role='listbox'] mat-option", "Filter dropdown option")
    filter_dropdown_remove = Locator(By.CSS_SELECTOR, "app-filter button[aria-label='Remove']", "Filter remove button")

    class Row:
        """Existing user row"""

        username = Locator(By.XPATH, ".//mat-cell[2]", "Username in row")
        password = Locator(By.CSS_SELECTOR, "input[data-placeholder='Password']", "Password in row")
        password_confirm = Locator(
            By.CSS_SELECTOR, "input[data-placeholder='Confirm Password']", "Password confirmation in row"
        )
        confirm_update_btn = Locator(
            By.XPATH,
            ".//button[.//mat-icon[text()='done']]",
            "Confirm password update button in row",
        )
        select_checkbox = Locator(By.XPATH, ".//span[.//input[@type='checkbox']]", "Select user checkbox in row")
        delete_btn = Locator(By.XPATH, ".//button[.//mat-icon[text()='delete']]", "Delete user button in row")

    class AddUserPopup(CommonAdminPagesLocators):
        """Popup with new user info"""

        block = Locator(By.TAG_NAME, "mat-dialog-container", "Add user popup block")
        username = Locator(By.NAME, "username", "New user username")
        password = Locator(By.CSS_SELECTOR, "input[data-placeholder='Password']", "New user password")
        password_confirm = Locator(
            By.CSS_SELECTOR, "input[data-placeholder='Confirm password']", "New user password confirmation"
        )
        adcm_admin_chbx = Locator(
            By.CSS_SELECTOR, "mat-checkbox[formcontrolname='is_superuser']", "Checkbox ADCM Administrator"
        )
        first_name = Locator(By.NAME, "first_name", "New user first name")
        last_name = Locator(By.NAME, "last_name", "New user last name")
        email = Locator(By.NAME, "email", "New user email")
        select_groups = Locator(By.CSS_SELECTOR, "adwp-input-select[controlname='group']", "Select groups")
        group_item = Locator(By.CSS_SELECTOR, "mat-list-option[role='option']", "Group item")

    class FilterPopup:
        """Popup for filter info"""

        block = Locator(By.CSS_SELECTOR, "div[role='menu']", "Filter popup block")
        filter_item = Locator(By.CSS_SELECTOR, "button[role='menuitem']", "Filter item")


class AdminGroupsLocators(CommonAdminPagesLocators):
    """Locators for Admin Groups menu"""

    class GroupRow:
        """Row with groups info"""

        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", "Group checkbox")
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Group name")
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Group description")
        users = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", "Group users")

    class AddGroupPopup:
        """Locators for creating groups popup"""

        block = Locator(By.CSS_SELECTOR, "app-rbac-group-form", "Add group popup block")
        title = Locator(By.CSS_SELECTOR, "mat-dialog-container h3", "Popup title")
        name_input = Locator(By.CSS_SELECTOR, "adwp-input[label='Group name'] input", "Input name")
        description_input = Locator(By.CSS_SELECTOR, "adwp-input[label='Description'] input", "Input description")
        users_select = Locator(By.CSS_SELECTOR, "adwp-input-select[label='Select users'] adwp-select", "select users")

        class UserRow:
            """Locators for user row in creating groups popup"""

            checkbox = Locator(By.CSS_SELECTOR, "mat-pseudo-checkbox", "Group checkbox")


class AdminRolesLocators(CommonAdminPagesLocators):
    """Locators for Admin Roles menu"""

    class RoleRow:
        """Row with role info"""

        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", "Role checkbox")
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "Role name")
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "Role description")
        permissions = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", "Role permissions")

    class AddRolePopup:
        """Locators for creating roles popup"""

        block = Locator(By.CSS_SELECTOR, "app-rbac-role-form", "Add role popup block")
        role_name_input = Locator(
            By.CSS_SELECTOR, "adwp-input[controlname='display_name'] input", "Input for role name"
        )
        description_name_input = Locator(
            By.CSS_SELECTOR, "adwp-input[controlname='description'] input", "Input for role description"
        )

        class PermissionItemsBlock:
            filter_input = Locator(
                By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter input", "Filter input"
            )
            item = Locator(
                By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-field mat-chip", "Selected permission item"
            )
            clear_all_btn = Locator(
                By.CSS_SELECTOR, ".adcm-input-rbac-permissions__selected-filter-clear", "Clear all button"
            )

            class PermissionItem:
                name = Locator(By.CSS_SELECTOR, "div", "Name")
                delete_btn = Locator(By.CSS_SELECTOR, "button", "Delete button")

        class SelectPermissionsBlock:
            permissions_filters = Locator(
                By.CSS_SELECTOR, ".adcm-rbac-permission__filter mat-chip", "filter item for permissions list"
            )
            permissions_search_row = Locator(By.CSS_SELECTOR, "adwp-selection-list-actions", "Permission search row")
            permissions_item_row = Locator(
                By.CSS_SELECTOR, ".adcm-rbac-permission__options mat-list-option", "Permission row"
            )
            select_btn = Locator(By.CSS_SELECTOR, ".adcm-rbac-permission__actions button", "Select button")

            class SelectPermissionsRow:
                checkbox = Locator(By.CSS_SELECTOR, "mat-pseudo-checkbox", "Checkbox")
                name = Locator(By.CSS_SELECTOR, ".mat-list-text", "Name")


class AdminPoliciesLocators(CommonAdminPagesLocators):
    """Locators for Admin Policies menu"""

    class PolicyRow:
        """Row with policy info"""

        checkbox = Locator(By.CSS_SELECTOR, "mat-checkbox", "policy checkbox")
        name = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(2)", "policy name")
        description = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(3)", "policy description")
        role = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(4)", "policy role")
        users = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(5)", "policy users")
        groups = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(6)", "policy groups")
        objects = Locator(By.CSS_SELECTOR, "mat-cell:nth-child(7)", "policy objects")

    class AddPolicyPopup:
        """Locators for creating policy popup"""

        block = Locator(By.CSS_SELECTOR, "app-rbac-policy-form>mat-horizontal-stepper", "Add policy popup block")

        class FirstStep:
            """Locators for first step"""

            name_input = Locator(By.CSS_SELECTOR, "input[name='name']", "Input name")
            description_input = Locator(By.CSS_SELECTOR, "input[name='description']", "Input description")
            role_select = Locator(By.CSS_SELECTOR, "mat-select[placeholder='Role']", "select role")
            role_item = Locator(
                By.XPATH, "//div[./mat-option//*[@placeholderlabel='Select role']]/mat-option", "select items for role"
            )

            users_select = Locator(By.CSS_SELECTOR, "adwp-input-select[label='User'] adwp-select", "select users")

            group_select = Locator(By.CSS_SELECTOR, "adwp-input-select[label='Group'] adwp-select", "select group")

            next_btn_first = Locator(
                By.CSS_SELECTOR,
                "app-rbac-policy-form-step-one~div button.mat-stepper-next",
                "Next button from first step",
            )

        class SecondStep:
            """Locators for second step"""

            back_btn_second = Locator(
                By.CSS_SELECTOR,
                "app-rbac-policy-form-step-two~div button[matstepperprevious]",
                "Back button from second step",
            )
            cluster_select = Locator(By.XPATH, "//div[./span//span[text()='Cluster']]//adwp-select", "select cluster")
            service_select = Locator(By.XPATH, "//div[./span//span[text()='Service']]//mat-select", "select service")
            service_item = Locator(By.CSS_SELECTOR, ".mat-select-panel mat-option", "select service item")
            provider_select = Locator(By.CSS_SELECTOR, "app-parametrized-by-provider adwp-select", "select provider")
            parent_select = Locator(By.XPATH, "//div[./span//span[text()='Parent']]//adwp-select", "select parent")
            hosts_select = Locator(By.CSS_SELECTOR, "app-parametrized-by-host mat-form-field", "select hosts")
            next_btn_second = Locator(
                By.CSS_SELECTOR, "app-rbac-policy-form-step-two~div .mat-stepper-next", "Next button from second step"
            )

        class ThirdStep:
            """Locators for third step"""

            back_btn_third = Locator(
                By.CSS_SELECTOR,
                "app-rbac-policy-form-step-three~div button[matstepperprevious]",
                "Next button from third step",
            )
            cancel_btn = Locator(By.XPATH, "//button[./span[text()='Cancel']]", "Cancel button")
