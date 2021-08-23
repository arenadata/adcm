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
from typing import List

import allure

from selenium.webdriver.remote.webelement import WebElement

from tests.ui_tests.app.helpers.locator import Locator
from tests.ui_tests.app.page.admin.locators import (
    AdminUsersLocators,
    AdminIntroLocators,
    AdminSettingsLocators,
)
from tests.ui_tests.app.page.common.common_locators import ObjectPageMenuLocators
from tests.ui_tests.app.page.common.configuration.page import CommonConfigMenuObj
from tests.ui_tests.app.page.common.dialogs import DeleteDialog
from tests.ui_tests.app.page.common.table.page import CommonTableObj
from tests.ui_tests.app.page.common.base_page import (
    BasePageObject,
    PageHeader,
    PageFooter,
)


class GeneralAdminPage(BasePageObject):
    MAIN_ELEMENTS: List[Locator]

    @allure.step("Check all main elements on the page are presented")
    def check_all_elements(self):
        if len(self.MAIN_ELEMENTS) == 0:
            raise AttributeError('MAIN_ELEMENTS should contain at least 1 element')
        self.assert_displayed_elements(self.MAIN_ELEMENTS)

    @allure.step('Open Admin Intro menu')
    def open_intro_menu(self):
        self.find_and_click(ObjectPageMenuLocators.intro_tab)

    @allure.step('Open Admin Settings menu')
    def open_settings_menu(self):
        self.find_and_click(ObjectPageMenuLocators.settings_tab)

    @allure.step('Open Admin Users menu')
    def open_users_menu(self):
        self.find_and_click(ObjectPageMenuLocators.users_tab)


class AdminIntroPage(GeneralAdminPage):
    MAIN_ELEMENTS = [AdminIntroLocators.intro_title, AdminIntroLocators.intro_text]

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/admin/intro")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)


class AdminSettingsPage(GeneralAdminPage):
    MAIN_ELEMENTS = [
        AdminSettingsLocators.save_btn,
        AdminSettingsLocators.search_input,
        AdminSettingsLocators.advanced_label,
    ]

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/admin/settings")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.config = CommonConfigMenuObj(self.driver, self.base_url)


class AdminUsersPage(GeneralAdminPage):
    MAIN_ELEMENTS = [AdminUsersLocators.add_user_btn, AdminUsersLocators.user_row]

    def __init__(self, driver, base_url):
        super().__init__(driver, base_url, "/admin/users")
        self.header = PageHeader(self.driver, self.base_url)
        self.footer = PageFooter(self.driver, self.base_url)
        self.table = CommonTableObj(self.driver, self.base_url)

    @allure.step('Get user row where username is {username}')
    def get_user_row_by_username(self, username: str) -> WebElement:
        """Search for user row by username and return it"""
        for row in self.table.get_all_rows():
            if self.find_child(row, AdminUsersLocators.Row.username).text == username:
                return row
        raise AssertionError(f'User row with username "{username}" was not found')

    def is_user_presented(self, username: str) -> bool:
        """Check if user is presented in users list"""
        for row in self.table.get_all_rows():
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
