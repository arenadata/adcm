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
from typing import List, Optional

import allure
from adcm_pytest_plugin.utils import wait_until_step_succeeds
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.admin.locators import (
    AdminGroupsLocators,
    AdminIntroLocators,
    AdminPoliciesLocators,
    AdminRolesLocators,
    AdminSettingsLocators,
    AdminUsersLocators,
)
from tests.ui_tests.app.page.common.base_page import BasePageObject, PageFooter, PageHeader
from tests.ui_tests.app.page.common.common_locators import ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs.locators import DeleteDialog
from tests.ui_tests.app.page.common.popups.locator import CommonPopupLocators
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


@dataclass
class AdminGroupInfo:
    """Information about group"""

    name: str
    description: str
    users: str


@dataclass
class AdminPolicyInfo:
    """Information about policy"""

    name: str
    description: Optional[str]
    role: str
    users: Optional[str]
    groups: Optional[str]
    objects: Optional[str]


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

    @allure.step("Check admin toolbar")
    def check_admin_toolbar(self):
        """Check that admin toolbar has all required elements in place"""
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

    @allure.step('Open Admin groups page by left menu item click')
    def open_groups_menu(self) -> "AdminGroupsPage":
        """Open Admin groups page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.groups_tab)
        page = AdminGroupsPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin Roles page by left menu item click')
    def open_roles_menu(self) -> "AdminRolesPage":
        """Open Admin Roles page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.roles_tab)
        page = AdminRolesPage(self.driver, self.base_url)
        page.wait_page_is_opened()
        return page

    @allure.step('Open Admin policies page by left menu item click')
    def open_policies_menu(self) -> "AdminPoliciesPage":
        """Open Admin policies page by menu object click"""

        self.find_and_click(ObjectPageMenuLocators.policies_tab)
        page = AdminPoliciesPage(self.driver, self.base_url)
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

    def get_info_popup_text(self):
        """Get text from info popup"""
        self.wait_element_visible(CommonPopupLocators.block)
        return self.wait_element_visible(CommonPopupLocators.text, timeout=5).text


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
        AdminUsersLocators.create_user_button,
        AdminUsersLocators.user_row,
        CommonToolbarLocators.admin_link,
    ]

    def get_all_user_rows(self) -> List[WebElement]:
        """Get all user rows (locator differs from self.table.get_all_rows())"""
        try:
            return self.find_elements(AdminUsersLocators.user_row, timeout=5)
        except TimeoutException:
            return []

    def get_all_user_names(self) -> List[WebElement]:
        """Get all users names"""
        try:
            return [self.find_child(user, AdminUsersLocators.Row.username).text for user in self.get_all_user_rows()]
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

    def is_user_deactivated(self, username: str) -> bool:
        """Get user's deactivation status on UI"""
        row = self.get_user_row_by_username(username)
        return "inactive" in row.get_attribute("class")

    @allure.step('Create new user "{username}" with password "{password}"')
    def create_user(
        self, username: str, password: str, first_name: str, last_name: str, email: str
    ):  # pylint: disable-next=too-many-arguments
        """Create new user via add user popup"""
        self.find_and_click(AdminUsersLocators.create_user_button)
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.username, username)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password, password)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password_confirm, password)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.first_name, first_name)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.last_name, last_name)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.email, email)
        self.find_and_click(AdminUsersLocators.AddUserPopup.save_update_btn)
        self.wait_element_hide(AdminUsersLocators.AddUserPopup.block)

    @allure.step('Update user {username} info')
    def update_user_info(
        self,
        username: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        group: Optional[str] = None,
    ):  # pylint: disable-next=too-many-arguments
        """Update some of fields for user"""
        if not (password or first_name or last_name or email or group):
            raise ValueError("You should provide at least one field's value to make an update")
        user_row = self.get_user_row_by_username(username)
        self.find_child(user_row, AdminUsersLocators.Row.username).click()
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        popup_locators = AdminUsersLocators.AddUserPopup
        for value, locator in (
            (password, popup_locators.password),
            (first_name, popup_locators.first_name),
            (last_name, popup_locators.last_name),
            (email, popup_locators.email),
        ):
            if value:
                self.send_text_to_element(locator, value)
        if group:
            with allure.step(f"Select group {group} in popup"):
                self.find_and_click(popup_locators.select_groups)
                self.wait_element_visible(popup_locators.group_item)
                available_groups = self.find_elements(popup_locators.group_item)
                for available_group in available_groups:
                    if available_group.text == group:
                        self.scroll_to(available_group)
                        self.hover_element(available_group)
                        available_group.click()
                        self.find_and_click(popup_locators.block, is_js=True)
                        break
                else:
                    raise AssertionError(f"There are no group {group} in select group popup")

        self.scroll_to(AdminUsersLocators.AddUserPopup.save_update_btn).click()
        self.wait_element_hide(AdminUsersLocators.AddUserPopup.block)

    @allure.step("Check user update is not allowed")
    def check_user_update_is_not_allowed(self, username: str):
        """Check that user can't be edited via UI"""
        self.get_user_row_by_username(username).click()
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        locators = AdminUsersLocators.AddUserPopup
        assert not self.is_element_displayed(locators.save_update_btn, timeout=1), "Update button should not be visible"
        # we don't check is_superuser and groups here because of their complex structure
        # and minor effect of such check
        for field in (locators.username, locators.first_name, locators.last_name, locators.email):
            assert not self.find_element(field).is_enabled(), f"Field '{field.name}' should not be editable"
        self.find_and_click(locators.cancel_btn)
        self.wait_element_hide(locators.block)

    @allure.step('Change password of user {username} to {password}')
    def change_user_password(self, username: str, password: str):
        """Change user password"""
        user_row = self.get_user_row_by_username(username)
        self.find_child(user_row, AdminUsersLocators.Row.username).click()
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password, password)
        self.send_text_to_element(AdminUsersLocators.AddUserPopup.password_confirm, password)
        self.find_and_click(AdminUsersLocators.AddUserPopup.save_update_btn)
        self.wait_element_hide(AdminUsersLocators.AddUserPopup.block)

    @allure.step('Check that changing user group is prohibited')
    def check_user_group_change_is_disabled(self, username: str, group_name: str):
        """Check that changing user group is prohibited"""

        user_row = self.get_user_row_by_username(username)
        self.find_child(user_row, AdminUsersLocators.Row.username).click()
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)

        self.find_and_click(AdminUsersLocators.AddUserPopup.select_groups)
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.group_item)
        available_groups = self.find_elements(AdminUsersLocators.AddUserPopup.group_item)
        for available_group in available_groups:
            if available_group.text == group_name:
                assert "disabled" in available_group.get_attribute("class"), f"Group {group_name} should be disabled"
                break
        else:
            raise AssertionError(f"There are no group {group_name} in select group popup")

    @allure.step('Check that changing ldap user is prohibited')
    def check_ldap_user(self, username: str):
        """Check that changing ldap user is prohibited"""

        def is_disabled(locators: [Locator]):
            for loc in locators:
                assert self.find_element(loc).get_attribute("disabled") == 'true', "Ldap user fields should be disabled"

        user_row = self.get_user_row_by_username(username)
        self.find_child(user_row, AdminUsersLocators.Row.username).click()
        self.wait_element_visible(AdminUsersLocators.AddUserPopup.block)
        is_disabled(
            [
                AdminUsersLocators.AddUserPopup.username,
                AdminUsersLocators.AddUserPopup.password,
                AdminUsersLocators.AddUserPopup.password_confirm,
                AdminUsersLocators.AddUserPopup.first_name,
                AdminUsersLocators.AddUserPopup.last_name,
                AdminUsersLocators.AddUserPopup.email,
                AdminUsersLocators.AddUserPopup.save_update_btn,
            ]
        )
        assert (
            self.find_element(AdminUsersLocators.AddUserPopup.select_groups).get_attribute("disabled") is None
        ), "Ldap user group should not be disabled"

    @allure.step('Delete user {username}')
    def delete_user(self, username: str):
        """Delete existing user"""
        user_row = self.get_user_row_by_username(username)
        self.find_child(user_row, AdminUsersLocators.Row.select_checkbox).click()
        self.find_and_click(AdminUsersLocators.Row.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    def is_delete_button_presented(self, username: str):
        """Check that delete button is not presented in user row"""
        row = self.get_user_row_by_username(username)
        return self.is_child_displayed(row, AdminUsersLocators.Row.delete_btn, timeout=1)

    @allure.step('Filter users by {filter_name}')
    def filter_users_by(self, filter_name: str, filter_option_name: str):
        """Filter users"""

        def click_filter_item():
            for filter_item in self.find_elements(AdminUsersLocators.FilterPopup.filter_item):
                if filter_item.text.lower() == filter_name.lower():
                    filter_item.click()
                    return
            raise AssertionError(f"Filter '{filter_name}' not found")

        def click_dropdown_option():
            for filter_option in self.find_elements(AdminUsersLocators.filter_dropdown_option):
                if filter_option.text.lower() == filter_option_name.lower():
                    filter_option.click()
                    return
            raise AssertionError(f"Filter option '{filter_option_name}' not found")

        self.find_and_click(AdminUsersLocators.filter_btn)
        self.wait_element_visible(AdminUsersLocators.FilterPopup.block)
        click_filter_item()
        self.wait_element_visible(AdminUsersLocators.filter_dropdown_select).click()
        self.wait_element_visible(AdminUsersLocators.filter_dropdown_option)
        click_dropdown_option()
        self.wait_page_is_opened()

    @allure.step('Remove filter from users page')
    def remove_user_filter(self):
        """Remove filter from users page"""

        self.find_and_click(AdminUsersLocators.filter_dropdown_remove)
        self.wait_page_is_opened()


class AdminGroupsPage(GeneralAdminPage):
    """Admin groups Page class"""

    MENU_SUFFIX = 'groups'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        AdminGroupsLocators.create_btn,
        AdminGroupsLocators.delete_btn,
        CommonTable.header,
    ]

    def click_create_group_btn(self):
        self.find_and_click(AdminGroupsLocators.create_btn)
        self.wait_element_visible(AdminGroupsLocators.AddGroupPopup.block)

    @allure.step('Create custom group {name}')
    def create_custom_group(self, name: str, description: Optional[str], users: Optional[str]):
        self.click_create_group_btn()
        self.send_text_to_element(AdminGroupsLocators.AddGroupPopup.name_input, name)
        if description:
            self.send_text_to_element(AdminGroupsLocators.AddGroupPopup.description_input, description)
        if users:
            self.find_and_click(AdminGroupsLocators.AddGroupPopup.users_select)
            self.wait_element_visible(AdminGroupsLocators.item)
            for user in users.split(", "):
                for user_item in self.find_elements(AdminGroupsLocators.item):
                    if user_item.text == user:
                        user_chbx = self.find_child(user_item, AdminGroupsLocators.AddGroupPopup.UserRow.checkbox)
                        self.hover_element(user_chbx)
                        user_chbx.click()
            self.find_and_click(AdminGroupsLocators.AddGroupPopup.users_select)
        self.find_and_click(AdminGroupsLocators.save_update_btn)
        self.wait_element_hide(AdminGroupsLocators.AddGroupPopup.block)

    @allure.step('Update group {name}')
    def update_group(
        self, name: str, new_name: Optional[str] = None, description: Optional[str] = None, users: Optional[str] = None
    ):
        self.get_group_by_name(name).click()
        if new_name:
            self.send_text_to_element(AdminGroupsLocators.AddGroupPopup.name_input, description, clean_input=True)
        if description:
            self.send_text_to_element(
                AdminGroupsLocators.AddGroupPopup.description_input, description, clean_input=True
            )
        if users:
            self.find_and_click(AdminGroupsLocators.AddGroupPopup.users_select)
            self.wait_element_visible(AdminGroupsLocators.item)
            for user in users.split(", "):
                for user_item in self.find_elements(AdminGroupsLocators.item):
                    if user_item.text == user:
                        user_chbx = self.find_child(user_item, AdminGroupsLocators.AddGroupPopup.UserRow.checkbox)
                        self.hover_element(user_chbx)
                        user_chbx.click()
            self.find_and_click(AdminGroupsLocators.AddGroupPopup.users_select)
        self.find_and_click(AdminGroupsLocators.save_update_btn)
        self.wait_element_hide(AdminGroupsLocators.AddGroupPopup.block)

    def get_all_groups(self) -> [AdminGroupInfo]:
        """Get all groups info."""

        groups_items = []
        groups_rows = self.table.get_all_rows()
        for row in groups_rows:
            row_item = AdminGroupInfo(
                name=self.find_child(row, AdminGroupsLocators.GroupRow.name).text,
                description=self.find_child(row, AdminGroupsLocators.GroupRow.description).text,
                users=self.find_child(row, AdminGroupsLocators.GroupRow.users).text,
            )
            groups_items.append(row_item)
        return groups_items

    def select_all_groups(self):
        self.find_elements(self.table.locators.header)[0].click()

    def click_delete_button(self):
        self.find_and_click(AdminRolesLocators.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    @allure.step('Get group {group_name}')
    def get_group_by_name(self, group_name: str):
        """Get group by name"""
        for group in self.table.get_all_rows():
            if group_name in group.text:
                return group
        raise AssertionError(f'Group {group_name} was not found')

    @allure.step('Check that changing ldap group is prohibited')
    def check_ldap_group(self, group_name: str):
        """Check that changing ldap group is prohibited"""

        def is_disabled(locators: [Locator]):
            for loc in locators:
                assert (
                    self.find_element(loc).get_attribute("disabled") == 'true'
                ), "Ldap group fields should be disabled"

        group_row = self.get_group_by_name(group_name)
        self.find_child(group_row, AdminGroupsLocators.GroupRow.name).click()
        self.wait_element_visible(AdminGroupsLocators.AddGroupPopup.block)
        is_disabled(
            [
                AdminGroupsLocators.AddGroupPopup.name_input,
                AdminGroupsLocators.AddGroupPopup.description_input,
                AdminGroupsLocators.save_update_btn,
            ]
        )
        assert "disabled" in self.find_element(AdminGroupsLocators.AddGroupPopup.users_select).get_attribute(
            "class"
        ), "Select users should be disabled"
        assert self.find_element(AdminGroupsLocators.AddGroupPopup.title).text == "Group Info", "Wrong title in popup"


class AdminRolesPage(GeneralAdminPage):
    """Admin Roles Page class"""

    MENU_SUFFIX = 'roles'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        AdminRolesLocators.create_btn,
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
        """Check default roles are listed on admin page"""

        default_roles = [
            AdminRoleInfo(
                name='ADCM User',
                description='',
                permissions='View any object configuration, View any object import, View any object host-components',
            ),
            AdminRoleInfo(
                name='Service Administrator',
                description='',
                permissions='View host configurations, Edit service configurations, Edit component configurations, '
                'View host-components',
            ),
            AdminRoleInfo(
                name='Cluster Administrator',
                description='',
                permissions='Create host, Upload bundle, Edit cluster configurations, Edit host configurations, '
                'Add service, Remove service, Remove hosts, Map hosts, Unmap hosts, Edit host-components, '
                'Upgrade cluster bundle, Remove bundle, Service Administrator',
            ),
            AdminRoleInfo(
                name='Provider Administrator',
                description='',
                permissions='Create host, Upload bundle, Edit provider configurations, Edit host configurations, '
                'Remove hosts, Upgrade provider bundle, Remove bundle',
            ),
        ]

        roles = self.get_all_roles_info()
        for role in default_roles:
            assert role in roles, f"Default role {role.name} is wrong or missing. Expected to find: {role} in {roles}"

    @allure.step('Check custom roles')
    def check_custom_role(self, role: AdminRoleInfo):
        assert role in self.get_all_roles_info(), f"Role {role.name} is wrong or missing"

    @allure.step('Open create role popup')
    def open_create_role_popup(self):
        self.find_and_click(AdminRolesLocators.create_btn)
        self.wait_element_visible(AdminRolesLocators.AddRolePopup.block)

    @allure.step('Fill role name {role_name}')
    def fill_role_name_in_role_popup(self, role_name: str):
        self.send_text_to_element(AdminRolesLocators.AddRolePopup.role_name_input, role_name)
        self.find_and_click(AdminRolesLocators.AddRolePopup.description_name_input)

    @allure.step('Fill description {description}')
    def fill_description_in_role_popup(self, description: str):
        self.send_text_to_element(AdminRolesLocators.AddRolePopup.description_name_input, description)
        self.find_and_click(AdminRolesLocators.AddRolePopup.role_name_input)

    @allure.step('Create new role')
    def create_role(self, role_name: str, role_description: str, role_permissions: str):
        self.open_create_role_popup()
        self.fill_role_name_in_role_popup(role_name)
        self.fill_description_in_role_popup(role_description)
        for permission in role_permissions.split(", "):
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
        self.find_and_click(AdminRolesLocators.save_update_btn)

    @allure.step('Check that save button is disabled')
    def check_save_button_disabled(self):
        assert (
            self.find_element(AdminRolesLocators.save_update_btn).get_attribute("disabled") == 'true'
        ), "Save role button should be disabled"

    @allure.step("Check {error_message} error is presented")
    def check_field_error_in_role_popup(self, error_message: str):
        """Assert that message "{error_message}" is presented"""

        self.check_element_should_be_visible(AdminRolesLocators.field_error(error_message))

    def select_all_roles(self):
        self.find_elements(self.table.locators.header)[0].click()

    def click_delete_button(self):
        self.find_and_click(AdminRolesLocators.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)


class AdminPoliciesPage(GeneralAdminPage):
    """Admin Policy Page class"""

    MENU_SUFFIX = 'policies'
    MAIN_ELEMENTS = [
        AdminIntroLocators.intro_title,
        AdminIntroLocators.intro_text,
        AdminGroupsLocators.create_btn,
        AdminGroupsLocators.delete_btn,
        CommonTable.header,
    ]

    def open_create_policy_popup(self):
        self.find_and_click(AdminPoliciesLocators.create_btn)
        self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.block)

    @allure.step('Fill first step in new policy')
    def fill_first_step_in_policy_popup(  # pylint: disable=too-many-arguments
        self, policy_name: str, description: Optional[str], role: str, users: Optional[str], groups: Optional[str]
    ):
        if not (users or groups):
            raise ValueError("There are should be users or groups in the policy")
        self.send_text_to_element(AdminPoliciesLocators.AddPolicyPopup.FirstStep.name_input, policy_name)
        if description:
            self.send_text_to_element(AdminPoliciesLocators.AddPolicyPopup.FirstStep.description_input, description)
        with allure.step(f"Select role {role} in popup"):
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_select)
            self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_item)
            available_roles = self.find_elements(AdminPoliciesLocators.AddPolicyPopup.FirstStep.role_item)
            for available_role in available_roles:
                if available_role.text == role:
                    self.scroll_to(available_role)
                    self.hover_element(available_role)
                    available_role.click()
                    break
            else:
                raise AssertionError(f"There are no role {role} in select role popup")
        if users:
            with allure.step(f"Select users {users} in popup"):
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.users_select)
                self.wait_element_visible(AdminPoliciesLocators.item)
                self.fill_select_in_policy_popup(users, AdminPoliciesLocators.item)
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.users_select)
        if groups:
            with allure.step(f"Select groups {groups} in popup"):
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.group_select)
                self.wait_element_visible(AdminPoliciesLocators.item)
                self.fill_select_in_policy_popup(groups, AdminPoliciesLocators.item)
                self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.group_select)
        self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.FirstStep.next_btn_first)

    def fill_select_in_policy_popup(self, items, available_items_locator):
        for item in items.split(", "):
            self.wait_element_visible(available_items_locator)
            for count, available_item in enumerate(self.find_elements(available_items_locator)):
                try:
                    if available_item.text == item:
                        available_item.click()
                        break
                except StaleElementReferenceException:
                    if self.find_elements(available_items_locator)[count].text == item:
                        self.find_elements(available_items_locator)[count].click()
                        break
            else:
                raise AssertionError(f"There are no item {item} in select popup")

    @allure.step('Fill second step in new policy')
    def fill_second_step_in_policy_popup(  # pylint: disable=too-many-arguments
        self,
        clusters: Optional[str] = None,
        services: Optional[str] = None,
        parent: Optional[str] = None,
        providers: Optional[str] = None,
        hosts: Optional[str] = None,
    ):
        self.wait_element_visible(AdminPoliciesLocators.AddPolicyPopup.SecondStep.next_btn_second)

        def fill_select(locator_select: Locator, locator_items: Locator, values: str):
            with allure.step(f"Select {values} in popup"):
                self.wait_element_visible(locator_select)
                self.find_and_click(locator_select)
                self.wait_element_visible(locator_items)
                self.fill_select_in_policy_popup(values, locator_items)

        if clusters:
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.cluster_select, AdminPoliciesLocators.item, clusters
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.cluster_select)
        if services:
            if not parent:
                raise ValueError("There are should be parent for service")
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.service_select,
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.service_item,
                services,
            )
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.parent_select, AdminPoliciesLocators.item, parent
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.parent_select)

        if hosts:
            fill_select(AdminPoliciesLocators.AddPolicyPopup.SecondStep.hosts_select, AdminPoliciesLocators.item, hosts)
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.hosts_select)
        if providers:
            fill_select(
                AdminPoliciesLocators.AddPolicyPopup.SecondStep.provider_select, AdminPoliciesLocators.item, providers
            )
            self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.provider_select)
        self.find_and_click(AdminPoliciesLocators.AddPolicyPopup.SecondStep.next_btn_second)

    @allure.step('Fill third step in new policy')
    def fill_third_step_in_policy_popup(self):
        self.wait_element_visible(AdminPoliciesLocators.save_update_btn)
        self.find_and_click(AdminPoliciesLocators.save_update_btn)
        self.wait_element_hide(AdminPoliciesLocators.AddPolicyPopup.block)

    @allure.step('Create new policy')
    def create_policy(  # pylint: disable=too-many-arguments
        self,
        policy_name: str,
        description: Optional[str],
        role: str,
        users: Optional[str] = None,
        groups: Optional[str] = None,
        clusters: Optional[str] = None,
        services: Optional[str] = None,
        parent: Optional[str] = None,
        providers: Optional[str] = None,
        hosts: Optional[str] = None,
    ):

        self.open_create_policy_popup()
        self.fill_first_step_in_policy_popup(policy_name, description, role, users, groups)
        self.fill_second_step_in_policy_popup(clusters, services, parent, providers, hosts)
        self.fill_third_step_in_policy_popup()

    def get_all_policies(self) -> [AdminPolicyInfo]:
        """Get all policies info and returns list with policies names."""

        policies_items = []
        policies_rows = self.table.get_all_rows()
        for policy in policies_rows:
            policy_groups = self.find_child(policy, AdminPoliciesLocators.PolicyRow.groups).text
            policy_objects = self.find_child(policy, AdminPoliciesLocators.PolicyRow.objects).text
            policy_item = AdminPolicyInfo(
                name=self.find_child(policy, AdminPoliciesLocators.PolicyRow.name).text,
                description=self.find_child(policy, AdminPoliciesLocators.PolicyRow.description).text,
                role=self.find_child(policy, AdminPoliciesLocators.PolicyRow.role).text,
                users=self.find_child(policy, AdminPoliciesLocators.PolicyRow.users).text,
                groups=policy_groups if policy_groups else None,
                objects=policy_objects if policy_objects else None,
            )
            policies_items.append(policy_item)
        return policies_items

    def select_all_policies(self):
        # first header element is checkbox for selecting all policies
        self.find_elements(self.table.locators.header)[0].click()

    def click_delete_button(self):
        """Click delete button and confirm the action in dialog popup."""

        self.find_and_click(AdminPoliciesLocators.delete_btn)
        self.wait_element_visible(DeleteDialog.body)
        self.find_and_click(DeleteDialog.yes)
        self.wait_element_hide(DeleteDialog.body)

    def delete_all_policies(self):
        def delete_all():
            self.select_all_policies()
            if "disabled" not in self.find_element(AdminPoliciesLocators.delete_btn).get_attribute("class"):
                self.click_delete_button()
            assert len(self.table.get_all_rows()) == 0, "There should be 0 policies on the page"

        wait_until_step_succeeds(delete_all, period=5)
