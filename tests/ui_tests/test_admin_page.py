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
import allure
import pytest

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage, AdminUsersPage, AdminSettingsPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.utils import expect_rows_amount_change

# pylint: disable=redefined-outer-name


@pytest.fixture()
def users_page(app_fs: ADCMTest, login_to_adcm_over_api) -> AdminUsersPage:
    """Get Admin Users Page"""
    return AdminUsersPage(app_fs.driver, app_fs.adcm.url).open()


@pytest.fixture()
def settings_page(app_fs: ADCMTest, login_to_adcm_over_api) -> AdminSettingsPage:
    """Get Admin Settings Page"""
    return AdminSettingsPage(app_fs.driver, app_fs.adcm.url).open()


def test_new_user_creation(users_page: AdminUsersPage):
    """Create new user, change password and login with new password"""
    params = {'username': 'testuser', 'password': 'test_pass', 'new_password': 'testtest'}
    users_page.create_user(params['username'], params['password'])
    with allure.step(f'Check user {params["username"]} is listed in users list'):
        assert users_page.is_user_presented(
            params['username']
        ), f'User {params["username"]} was not created'
    users_page.change_user_password(params['username'], params['new_password'])
    users_page.header.logout()
    with allure.step(f'Login as user {params["username"]} with password {params["new_password"]}'):
        login_page = LoginPage(users_page.driver, users_page.base_url)
        login_page.wait_page_is_opened()
        login_page.login_user(params['username'], params['new_password'])
        users_page.wait_page_is_opened()


def test_delete_user(users_page: AdminUsersPage):
    """Create new user, delete it and check current user can't be deleted"""
    params = {'username': 'testuser', 'password': 'test_pass', 'current_user': 'admin'}
    users_page.check_delete_button_not_presented(params['current_user'])
    with allure.step(f'Create user {params["username"]}'):
        users_page.create_user(params['username'], params['password'])
        assert users_page.is_user_presented(
            params['username']
        ), f'User {params["username"]} was not created'
    with allure.step(f'Delete user {params["username"]}'):
        users_page.delete_user(params['username'])
        assert not users_page.is_user_presented(
            params['username']
        ), f'User {params["username"]} should not be in users list'


def test_change_admin_password(users_page: AdminUsersPage):
    """Change admin password, login with new credentials"""
    params = {'username': 'admin', 'password': 'new_pass'}
    users_page.change_user_password(**params)
    with allure.step('Check Login page is opened'):
        login_page = LoginPage(users_page.driver, users_page.base_url)
        login_page.wait_page_is_opened()
    login_page.login_user(**params)
    with allure.step('Check login was successful'):
        users_page.wait_page_is_opened()


def test_check_menus(users_page: AdminUsersPage):
    """Click on different admin menus"""
    with allure.step('Check Settings menu'):
        users_page.open_settings_menu()
        settings_page = AdminSettingsPage(users_page.driver, users_page.base_url)
        settings_page.wait_page_is_opened()
    with allure.step('Check Users menu'):
        settings_page.open_users_menu()
        users_page.wait_page_is_opened()
    with allure.step('Check Intro menu'):
        users_page.open_intro_menu()
        intro_page = AdminIntroPage(users_page.driver, users_page.base_url)
        intro_page.wait_page_is_opened()


def test_settings_filter(settings_page: AdminSettingsPage):
    """Apply different filters on Admin Settings page"""
    params = {
        'search_text': 'ADCM',
        'field_display_name': "ADCM's URL",
        'group': 'Global Options',
    }
    get_rows_func = settings_page.config.get_all_config_rows
    with allure.step(
        f'Search {params["search_text"]} and check {params["field_display_name"]} '
        'is presented after search'
    ):
        with expect_rows_amount_change(get_rows_func):
            settings_page.config.search(params['search_text'])
        settings_page.config.get_config_row(params["field_display_name"])
    with allure.step('Clear search'), expect_rows_amount_change(get_rows_func):
        settings_page.config.clear_search()
    with allure.step(
        f'Click on {params["group"]} group and check {params["field_display_name"]} '
        'is not presented after group roll up'
    ):
        with expect_rows_amount_change(get_rows_func):
            settings_page.config.click_on_group(params['group'])
        with pytest.raises(AssertionError):
            settings_page.config.get_config_row(params["field_display_name"])
    with allure.step(
        f'Click on {params["group"]} group and check {params["field_display_name"]} '
        'is presented after group expand'
    ):
        with expect_rows_amount_change(get_rows_func):
            settings_page.config.click_on_group(params['group'])
        settings_page.config.get_config_row(params["field_display_name"])


def test_save_settings_with_different_name(settings_page: AdminSettingsPage):
    """Save settings with different name"""
    params = {'new_name': 'test_settings', 'field_display_name': 'client_id', 'field_value': '123'}
    settings_page.config.set_description(params['new_name'])
    with allure.step(
        f'Change value of field {params["field_display_name"]} to {params["field_value"]}'
    ):
        config_field_row = settings_page.config.get_config_row(params['field_display_name'])
        settings_page.config.type_in_config_field(params['field_value'], row=config_field_row)
    settings_page.config.save_config()
    settings_page.config.compare_current_to(params['new_name'])
    with allure.step('Check history'):
        config_field_row = settings_page.config.get_config_row(params['field_display_name'])
        history = settings_page.config.get_history_in_row(config_field_row)
        assert (
            len(history) == 1
        ), f'History should has exactly one entry for field {params["field_display_name"]}'
        assert (actual_value := history[0]) == (expected_value := params['field_value']), (
            f'History entry for field {params["field_display_name"]} '
            f'should be {expected_value}, not {actual_value}'
        )


def test_reset_config(settings_page: AdminSettingsPage):
    """Change config field, save, reset"""
    params = {'field_display_name': 'client_id', 'init_value': '', 'changed_value': '123'}
    with allure.step(f'Set value of {params["field_display_name"]} to {params["changed_value"]}'):
        config_field_row = settings_page.config.get_config_row(params['field_display_name'])
        settings_page.config.type_in_config_field(params['changed_value'], row=config_field_row)
    with allure.step('Save config'):
        settings_page.config.save_config()
        config_field_row = settings_page.config.get_config_row(params['field_display_name'])
        settings_page.config.assert_input_value_is(params['changed_value'], row=config_field_row)
    with allure.step(f'Reset value of {params["field_display_name"]}'):
        config_field_row = settings_page.config.get_config_row(params['field_display_name'])
        settings_page.config.reset_to_default(row=config_field_row)
        settings_page.config.assert_input_value_is(params['init_value'], row=config_field_row)
