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

# pylint: disable=redefined-outer-name,no-self-use,too-few-public-methods

"""UI tests for /admin page"""

import allure
import pytest
from adcm_pytest_plugin.utils import random_string

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import (
    AdminIntroPage,
    AdminUsersPage,
    AdminSettingsPage,
    AdminRolesPage,
    AdminGroupsPage,
    AdminRoleInfo,
    AdminGroupInfo,
)
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.utils import expect_rows_amount_change

# !===== Fixtures =====!


pytestmark = [pytest.mark.usefixtures("login_to_adcm_over_api")]


@pytest.fixture()
# pylint: disable-next=unused-argument
def users_page(app_fs: ADCMTest) -> AdminUsersPage:
    """Get Admin Users Page"""
    return AdminUsersPage(app_fs.driver, app_fs.adcm.url).open()


@pytest.fixture()
# pylint: disable-next=unused-argument
def settings_page(app_fs: ADCMTest) -> AdminSettingsPage:
    """Get Admin Settings Page"""
    return AdminSettingsPage(app_fs.driver, app_fs.adcm.url).open()


# !===== Tests =====!


class TestAdminIntroPage:
    """Tests for the /admin/intro"""

    def test_open_by_tab_admin_intro_page(self, app_fs):
        """Test open /admin/intro from left menu"""

        users_page = AdminUsersPage(app_fs.driver, app_fs.adcm.url).open()
        intro_page = users_page.open_settings_menu()
        intro_page.wait_page_is_opened()
        intro_page.check_all_elements()
        intro_page.check_admin_toolbar()


class TestAdminSettingsPage:
    """Tests for the /admin/roles"""

    def test_open_by_tab_admin_settings_page(self, app_fs):
        """Test open /admin/settings from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        settings_page = intro_page.open_settings_menu()
        settings_page.wait_page_is_opened()
        settings_page.check_all_elements()
        settings_page.check_admin_toolbar()

    def test_settings_filter(self, settings_page: AdminSettingsPage):
        """Apply different filters on Admin Settings page"""
        params = {
            'search_text': 'ADCM',
            'field_display_name': "ADCM's URL",
            'group': 'Global Options',
        }
        get_rows_func = settings_page.config.get_all_config_rows
        with allure.step(
            f'Search {params["search_text"]} and check {params["field_display_name"]} is presented after search'
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

    def test_save_settings_with_different_name(self, settings_page: AdminSettingsPage):
        """Save settings with different name"""
        params = {'new_name': 'test_settings', 'field_display_name': 'client_id', 'field_value': '123'}
        settings_page.config.set_description(params['new_name'])
        with allure.step(f'Change value of field {params["field_display_name"]} to {params["field_value"]}'):
            config_field_row = settings_page.config.get_config_row(params['field_display_name'])
            settings_page.config.type_in_field_with_few_inputs(row=config_field_row, values=[params['field_value']])
        settings_page.config.save_config()
        settings_page.config.compare_versions(params['new_name'], 'init')
        with allure.step('Check history'):
            config_field_row = settings_page.config.get_config_row(params['field_display_name'])
            history = settings_page.config.get_history_in_row(config_field_row)
            assert len(history) == 1, f'History should has exactly one entry for field {params["field_display_name"]}'
            assert (actual_value := history[0]) == (expected_value := params['field_value']), (
                f'History entry for field {params["field_display_name"]} '
                f'should be {expected_value}, not {actual_value}'
            )

    def test_reset_config(self, settings_page: AdminSettingsPage):
        """Change config field, save, reset"""
        params = {'field_display_name': 'client_id', 'init_value': '', 'changed_value': '123'}
        with allure.step(f'Set value of {params["field_display_name"]} to {params["changed_value"]}'):
            config_field_row = settings_page.config.get_config_row(params['field_display_name'])
            settings_page.config.type_in_field_with_few_inputs(row=config_field_row, values=[params['changed_value']])
        with allure.step('Save config'):
            settings_page.config.save_config()
            settings_page.config.assert_input_value_is(params['changed_value'], params['field_display_name'])
        with allure.step(f'Reset value of {params["field_display_name"]}'):
            config_field_row = settings_page.config.get_config_row(params['field_display_name'])
            settings_page.config.reset_to_default(config_field_row)
            settings_page.config.assert_input_value_is(params['init_value'], params['field_display_name'])


class TestAdminUsersPage:
    """Tests for the /admin/users"""

    def test_open_by_tab_admin_users_page(self, app_fs):
        """Test open /admin/users from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        users_page = intro_page.open_users_menu()
        users_page.wait_page_is_opened()
        users_page.check_all_elements()
        users_page.check_admin_toolbar()

    def test_new_user_creation(self, users_page: AdminUsersPage):
        """Create new user, change password and login with new password"""

        params = {
            'username': 'testuser',
            'password': 'test_pass',
            'new_password': 'testtest',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'priv@et.ru',
        }
        users_page.create_user(
            params['username'], params['password'], params['first_name'], params['last_name'], params['email']
        )
        with allure.step(f'Check user {params["username"]} is listed in users list'):
            assert users_page.is_user_presented(params['username']), f'User {params["username"]} was not created'
        users_page.change_user_password(params['username'], params['new_password'])
        users_page.header.logout()
        with allure.step(f'Login as user {params["username"]} with password {params["new_password"]}'):
            login_page = LoginPage(users_page.driver, users_page.base_url)
            login_page.wait_page_is_opened()
            login_page.login_user(params['username'], params['new_password'])
            AdminIntroPage(users_page.driver, users_page.base_url).wait_page_is_opened()

    def test_delete_user(self, users_page: AdminUsersPage):
        """Create new user, delete it and check current user can't be deleted"""

        params = {
            'username': 'testuser',
            'password': 'test_pass',
            'current_user': 'admin',
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'priv@et.ru',
        }
        users_page.check_delete_button_not_presented(params['current_user'])
        with allure.step(f'Create user {params["username"]}'):
            users_page.create_user(
                params['username'], params['password'], params['first_name'], params['last_name'], params['email']
            )
            assert users_page.is_user_presented(params['username']), f'User {params["username"]} was not created'
        with allure.step(f'Delete user {params["username"]}'):
            users_page.delete_user(params['username'])
            assert not users_page.is_user_presented(
                params['username']
            ), f'User {params["username"]} should not be in users list'

    @pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2555")
    def test_change_admin_password(self, users_page: AdminUsersPage):
        """Change admin password, login with new credentials"""

        params = {'username': 'admin', 'password': 'new_pass'}
        users_page.update_user_info(params['username'], first_name='Best', last_name='Admin')
        users_page.change_user_password(**params)
        with allure.step('Check Login page is opened'):
            login_page = LoginPage(users_page.driver, users_page.base_url)
            login_page.wait_page_is_opened()
        login_page.login_user(**params)
        with allure.step('Check login was successful'):
            users_page.wait_page_is_opened(timeout=5)


class TestAdminRolesPage:
    """Tests for the /admin/roles"""

    custom_role = AdminRoleInfo(
        name='Test_role_name',
        description='Test role description',
        permissions='Create provider, Create cluster, Create user, Remove policy',
    )

    def test_open_by_tab_admin_roles_page(self, app_fs):
        """Test open /admin/roles from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        roles_page = intro_page.open_roles_menu()
        roles_page.wait_page_is_opened()
        roles_page.check_all_elements()
        roles_page.check_default_roles()
        assert len(roles_page.table.get_all_rows()) == 4, "There should be 4 default roles"
        roles_page.check_admin_toolbar()

    def test_create_custom_role_on_roles_page(self, app_fs):
        """Test create a role on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role.name, self.custom_role.description, self.custom_role.permissions)
        page.check_default_roles()
        page.check_custom_role(self.custom_role)

    def test_check_pagination_role_list_page(self, app_fs):
        """Test pagination on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Create 11 roles"):
            for _ in range(7):
                page.create_role(
                    f"{self.custom_role.name}_{random_string()}",
                    self.custom_role.description,
                    self.custom_role.permissions,
                )
        page.table.check_pagination(second_page_item_amount=1)

    @pytest.mark.xfail(reason="https://arenadata.atlassian.net/browse/ADCM-2531")
    def test_check_role_popup_on_roles_page(self, app_fs):
        """Test changing a role on /admin/roles page"""

        custom_role_changed = AdminRoleInfo(
            name='Test_another_name',
            description='Test role description 2',
            permissions='Upload bundle',
        )

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role.name, self.custom_role.description, self.custom_role.permissions)
        page.open_role_by_name(self.custom_role.name)
        with allure.step("Check that update unavailable without role name"):
            page.fill_role_name_in_role_popup(" ")
            page.check_save_button_disabled()
            page.check_field_is_not_correct_in_role_popup("Role name")
            page.fill_role_name_in_role_popup("")
            page.check_save_button_disabled()
            page.check_field_is_required_in_role_popup("Role name")
        with allure.step("Check that update unavailable without permissions"):
            page.remove_permissions_in_add_role_popup(permissions_to_remove=self.custom_role.permissions.split(", "))
            page.check_save_button_disabled()
            for permission in self.custom_role.permissions.split(", "):
                page.select_permission_in_add_role_popup(permission)
            page.remove_permissions_in_add_role_popup(permissions_to_remove=None, all_permissions=True)
            page.check_save_button_disabled()
        page.fill_role_name_in_role_popup(custom_role_changed.name)
        page.fill_description_in_role_popup(custom_role_changed.description)
        page.select_permission_in_add_role_popup(custom_role_changed.permissions)
        page.click_save_btn_in_role_popup()
        page.check_default_roles()
        page.check_custom_role(custom_role_changed)

    def test_delete_role_from_roles_page(self, app_fs):
        """Test delete custome role on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role.name, self.custom_role.description, self.custom_role.permissions)
        page.select_all_roles()
        page.click_delete_button()
        page.check_default_roles()
        assert len(page.table.get_all_rows()) == 4, "There should be 4 default roles"


class TestAdminGroupsPage:
    """Tests for the /admin/groups"""

    custom_group = AdminGroupInfo(name='Test_group', description='Test description', users='admin')

    def test_open_by_tab_admin_groups_page(self, app_fs):
        """Test open /admin/groups from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page = intro_page.open_groups_menu()
        groups_page.wait_page_is_opened()
        groups_page.check_all_elements()
        groups_page.check_admin_toolbar()

    def test_create_group_on_admin_groups_page(self, app_fs):
        """Test create a group on /admin/groups"""

        groups_page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page.create_custom_group(self.custom_group.name, self.custom_group.description, self.custom_group.users)
        current_groups = groups_page.get_all_groups()
        assert len(current_groups) == 1, "There should be 1 group on the page"
        assert self.custom_group in current_groups, "Created group should be on the page"

    def test_check_pagination_groups_list_page(self, app_fs):
        """Test pagination on /admin/groups page"""

        page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Create 11 groups"):
            for _ in range(11):
                page.create_custom_group(
                    f"{self.custom_group.name}_{random_string()}",
                    self.custom_group.description,
                    self.custom_group.users,
                )
        page.table.check_pagination(second_page_item_amount=1)

    def test_delete_group_from_groups_page(self, app_fs):
        """Test delete custom group on /admin/groups page"""

        page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_custom_group(self.custom_group.name, self.custom_group.description, self.custom_group.users)
        page.select_all_groups()
        page.click_delete_button()
        assert len(page.table.get_all_rows()) == 0, "There should be 0 groups"
