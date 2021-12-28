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

"""Admin pages PageObjects classes"""

from dataclasses import dataclass
from typing import (
    List,
    Optional,
)

import allure
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.admin.locators import (
    AdminUsersLocators,
    AdminIntroLocators,
    AdminSettingsLocators,
    AdminRolesLocators,
)
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)
from tests.ui_tests.app.page.common.common_locators import ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs_locators import DeleteDialog
from tests.ui_tests.app.page.common.table.locator import CommonTable
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.tooltip_links.locator import CommonToolbarLocators
from tests.ui_tests.app.page.common.tooltip_links.page import CommonToolbar


@dataclass
class AdminRoleInfo:
    """Information about role"""

    name: str
    description: str
    permissions: str


class GeneralAdminPage(BasePageObject):
    """Base class for admin pages"""

    MENU_SUFFIX: str
    MAIN_ELEMENTS: List[Locator]
    header: PageHeader
    footer: PageFooter
    config: CommonConfigMenuObj
    table: CommonTableObj
    toolbar: CommonToolbar

    def __init__(self, driver, base_url):
        if self.MENU_SUFFIX is None:
            raise AttributeError('You should explicitly set MENU_SUFFIX in class definition')
        super().__init__(driver, base_url, "/admin/" + self.MENU_SUFFIX)
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)
        self.toolbar = CommonToolbar(self.driver, self.base_url)

    @allure.step("Assert that all main elements are presented on the page")
    def check_all_elements(self):
        """Assert presence of the MAIN_ELEMENTS"""

        if len(self.MAIN_ELEMENTS) == 0:
            raise AttributeError('MAIN_ELEMENTS should contain at least 1 element')
        self.assert_displayed_elements(self.MAIN_ELEMENTS)

    def check_admin_toolbar(self):
        self.assert_displayed_elements([CommonToolbarLocators.admin_link])

    @allure.step('Open Admin Intro page by left menu item click')
    def open_intro_menu(self) -> "AdminIntroPage":
        """Open Admin Intro page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.intro_tab)
        page = AdminIntroPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Settings page by left menu item click')
    def open_settings_menu(self) -> "AdminSettingsPage":
        """Open Admin Settings page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.settings_tab)
        page = AdminSettingsPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Users page by left menu item click')
    def open_users_menu(self) -> "AdminUsersPage":
        """Open Admin Users page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.users_tab)
        page = AdminUsersPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Roles page by left menu item click')
    def open_roles_menu(self) -> "AdminRolesPage":
        """Open Admin Roles page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.roles_tab)
        page = AdminRolesPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page


class AdminIntroPage(GeneralAdminPage):
    """Admin Intro Page class"""

    MENU_SUFFIX = 'intro'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        CommonToolbarLocators.admin_link,
    ]


class AdminSettingsPage(GeneralAdminPage):
    """Admin Settings Page class"""

    MENU_SUFFIX = 'settings'
    MAIN_ELEMENTS = [
        AdminSettingsLocators.save_btn,
        AdminSettingsLocators.search_input,
        AdminSettingsLocators.advanced_label,
        CommonToolbarLocators.admin_link,
    ]


class AdminUsersPage(GeneralAdminPage):
    """Admin Users Page class"""

    MENU_SUFFIX = 'users'
    MAIN_ELEMENTS = [
        AdminUsersLocators.add_user_btn,
        AdminUsersLocators.user_row,
        CommonToolbarLocators.admin_link,
    ]

    def get_all_user_rows(self) -> List[WebElement]:
        """Get all user rows (locator differs from self.table.get_all_rows())"""
        try:
            return self.find_elements(AdminUsersLocators.user_row, timeout=5)
        except TimeoutException:
            return []

    @allure.step('Get user row where username is {username}')
    def get_user_row_by_username(self, username: str) -> WebElement:
        """Search for user row by username and return it"""
        for row in self.get_all_user_rows():
            if self.find_child(row, AdminUsersLocators.Row.username).text == username:
                return row
        raise AssertionError(f'User row with username "{username}" was not found')

    def is_user_presented(self, username: str) -> bool:
        """Check if user is presented in users list"""
        for row in self.get_all_user_rows():
            if self.find_child(row, AdminUsersLocators.Row.username).text == username:
                return True
        return False

    @allure.step('Create new user "{username}" with password "{password}"')
    def create_user(self, username: str, password: str):
        """Create new user via add user popup"""
        self.find_and_click(AdminUsersLocators.add_user_btn)
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.username, username)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password, password)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password_confirm, password)
        self.find_and_click(AdminUsersLocators.AddUserPopup.save_btn)
        self.wait_element_hide(AdminUsersLocators.AddUserPopup.block)

    @allure.step('Change password of user {username} to {password}')
    def change_user_password(self, username: str, password: str):
        """Change user password"""
        user_row = self.get_user_row_by_username(username)
        pass_input = self.find_child(user_row, AdminUsersLocators.Row.password)
        pass_input.send_keys(password)
        pass_confirm_input = self.find_child(user_row, AdminUsersLocators.Row.password_confirm)
        pass_confirm_input.send_keys(password)
        update_pass = self.find_child(user_row, AdminUsersLocators.Row.confirm_update_btn)
        update_pass.click()

    @allure.step('Delete user {username}')
    def delete_user(self, username: str):
        """Delete existing user"""
        user_row = self.get_user_row_by_username(username)
        delete_button = self.find_child(user_row, AdminUsersLocators.Row.delete_btn)
        delete_button.click()
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step('Check delete button is not presented for user {username}')
    def check_delete_button_not_presented(self, username: str):
        """Check that delete button is not presented in user row"""
        user_row = self.get_user_row_by_username(username)
        assert not self.is_child_displayed(user_row, AdminUsersLocators.Row.delete_btn, timeout=3)


class AdminRolesPage(GeneralAdminPage):
    """Admin Roles Page class"""

    MENU_SUFFIX = 'roles'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        AdminRolesLocators.create_role_btn,
        AdminRolesLocators.delete_btn,
        CommonTable.header,
        CommonTable.visible_row,
    ]

    def get_all_roles_info(self) -> [AdminRoleInfo]:
        """Get all roles info."""

        roles_items = []
        role_rows = self.table.get_all_rows()
        for row in role_rows:
            row_item = AdminRoleInfo(
                name=self.find_child(row, AdminRolesLocators.RoleRow.name).text,
                description=self.find_child(row, AdminRolesLocators.RoleRow.description).text,
                permissions=self.find_child(row, AdminRolesLocators.RoleRow.permissions).text,
            )
            roles_items.append(row_item)
        return roles_items

    @allure.step('Check default roles')
    def check_default_roles(self):
        default_roles = [
            AdminRoleInfo(
                name='ADCM User',
                description='',
                permissions='View application configurations, View infrastructure configurations, View imports, '
                'View host-components, Base role',
            ),
            AdminRoleInfo(
                name='Service Administrator',
                description='',
                permissions='Edit application configurations, Manage imports, ADCM User',
            ),
            AdminRoleInfo(
                name='Cluster Administrator',
                description='',
                permissions='Create host, Upload bundle, Add service, Remove service, Remove hosts, Map hosts, '
                'Unmap hosts, Edit host-components, Upgrade application bundle, Remove bundle, '
                'Service Administrator',
            ),
            AdminRoleInfo(
                name='Provider Administrator',
                description='',
                permissions='Create host, Upload bundle, Edit infrastructure configurations, Remove hosts, '
                'Upgrade infrastructure bundle, Remove bundle',
            ),
            AdminRoleInfo(
                name='ADCM Administrator',
                description='',
                permissions='Create provider, Create cluster, Remove cluster, Remove provider, View ADCM settings, '
                'Edit ADCM settings, View users, Create user, Edit user, Remove user, View roles, Create '
                'custom role, Edit role, Remove roles, View group, Create group, Edit group, Remove group, '
                'View policy, Create policy, Edit policy, Remove policy, Cluster Administrator',
            ),
        ]

        roles = self.get_all_roles_info()
        for role in default_roles:
            assert role in roles, f"Default role {role.name} is wrong or missing"

    @allure.step('Check custom roles')
    def check_custom_role(self, role: AdminRoleInfo):
        assert role in self.get_all_roles_info(), f"Role {role.name} is wrong or missing"

    @allure.step('Open create role popup')
    def open_create_role_popup(self):
        self.find_and_click(AdminRolesLocators.create_role_btn)
        self.wait_element_visible(AdminRolesLocators.AddRolePopup.block)

    @allure.step('Fill role name {role_name}')
    def fill_role_name_in_role_popup(self, role_name: str):
        self.send_text_to_element(AdminRolesLocators.AddRolePopup.role_name_input, role_name, clean_input=True)

    @allure.step('Fill description {description}')
    def fill_description_in_role_popup(self, description: str):
        self.send_text_to_element(AdminRolesLocators.AddRolePopup.description_name_input, description, clean_input=True)

    @allure.step('Create new role')
    def create_role(self, role: AdminRoleInfo):
        self.open_create_role_popup()
        self.fill_role_name_in_role_popup(role.name)
        self.fill_description_in_role_popup(role.description)
        for permission in role.permissions.split(", "):
            self.select_permission_in_add_role_popup(permission)
        self.wait_element_visible(AdminRolesLocators.AddRolePopup.PermissionItemsBlock.item)
        self.click_save_btn_in_role_popup()
        self.wait_element_hide(CommonToolbarLocators.progress_bar)

    @allure.step('Select permission {permission}')
    def select_permission_in_add_role_popup(self, permission: str):
        available_permissions = self.find_elements(
            AdminRolesLocators.AddRolePopup.SelectPermissionsBlock.permissions_item_row
        )
        for perm in available_permissions:
            if perm.text == permission:
                perm.click()
                self.find_and_click(AdminRolesLocators.AddRolePopup.SelectPermissionsBlock.select_btn)
                return
        raise ValueError(f"Permission {permission} has not found")

    @allure.step('Open role {role_name}')
    def open_role_by_name(self, role_name: str):
        role_rows = self.table.get_all_rows()
        for row in role_rows:
            if role_name in row.text:
                self.find_child(row, AdminRolesLocators.RoleRow.name).click()
                self.wait_element_visible(AdminRolesLocators.AddRolePopup.block)
                return
        raise ValueError(f"Role {role_name} has not found")

    @allure.step('Remove permissions {permissions_to_remove}')
    def remove_permissions_in_add_role_popup(
        self, permissions_to_remove: Optional[List], all_permissions: bool = False
    ):

        if all_permissions:
            self.find_and_click(AdminRolesLocators.AddRolePopup.PermissionItemsBlock.clear_all_btn)
        else:
            for permission_to_remove in permissions_to_remove:
                selected_permission = self.find_elements(AdminRolesLocators.AddRolePopup.PermissionItemsBlock.item)
                for permission in selected_permission:
                    if permission_to_remove in permission.text:
                        self.find_child(
                            permission, AdminRolesLocators.AddRolePopup.PermissionItemsBlock.PermissionItem.delete_btn
                        ).click()
                        break

    def click_save_btn_in_role_popup(self):
        self.find_and_click(AdminRolesLocators.AddRolePopup.save_btn)

    @allure.step('Check that save button is disabled')
    def check_save_button_disabled(self):
        assert (
            self.find_element(AdminRolesLocators.AddRolePopup.save_btn).get_attribute("disabled") == 'true'
        ), "Save role button should be disabled"

    @allure.step("Check {name} required error is presented")
    def check_field_is_required_in_role_popup(self, name: str):
        """Assert that message "{name} is required" is presented"""

        message = f'{name} is required.'
        self.check_element_should_be_visible(AdminRolesLocators.AddRolePopup.field_error(message))

    @allure.step("Check {name} not correct error is presented")
    def check_field_is_not_correct_in_role_popup(self, name: str):
        """Assert that message "{name} is not correct" is presented"""

        message = f'{name} is not correct.'
        self.check_element_should_be_visible(AdminRolesLocators.AddRolePopup.field_error(message))

    def select_all_roles(self):
        self.find_elements(self.table.locators.header)[0].click()

    def click_delete_button(self):
        self.find_and_click(AdminRolesLocators.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)
