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

# pylint: disable=redefined-outer-name,too-many-lines

"""UI tests for /admin page"""

import os
from copy import deepcopy
from typing import Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Bundle, Cluster, Host, Provider, Service
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import get_data_dir, random_string
from tests.library.assertions import is_in_collection, is_superset_of
from tests.library.predicates import name_is, username_is
from tests.library.retry import should_become_truth
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import (
    AdminGroupsPage,
    AdminIntroPage,
    AdminPoliciesPage,
    AdminPolicyInfo,
    AdminRolesPage,
    AdminSettingsPage,
    AdminUsersPage,
    GroupRow,
    RoleRow,
    UserRow,
)
from tests.ui_tests.app.page.cluster.page import (
    ClusterComponentsPage,
    ClusterConfigPage,
)
from tests.ui_tests.app.page.cluster_list.page import ClusterListPage
from tests.ui_tests.app.page.common.dialogs.group import UpdateGroupDialog
from tests.ui_tests.app.page.common.dialogs.user import UpdateUserDialog
from tests.ui_tests.app.page.component.page import ComponentConfigPage
from tests.ui_tests.app.page.host.page import HostConfigPage
from tests.ui_tests.app.page.host_list.page import HostListPage
from tests.ui_tests.app.page.job.page import JobPageStdout
from tests.ui_tests.app.page.job_list.page import JobListPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.provider.page import ProviderConfigPage
from tests.ui_tests.app.page.service.page import ServiceConfigPage
from tests.ui_tests.conftest import login_over_api
from tests.ui_tests.core.checks import check_pagination
from tests.ui_tests.utils import expect_rows_amount_change

BUNDLE = "cluster_with_services"
CLUSTER_NAME = "test cluster"
SERVICE_NAME = "test_service_1"
FIRST_COMPONENT_NAME = "first"
PROVIDER_NAME = "test provider"
HOST_NAME = "test-host"


# !===== Fixtures =====!


@pytest.fixture()
def users_page(app_fs: ADCMTest) -> AdminUsersPage:
    return AdminUsersPage(app_fs.driver, app_fs.adcm.url).open(close_popup=True)


@pytest.fixture()
def settings_page(app_fs: ADCMTest) -> AdminSettingsPage:
    return AdminSettingsPage(app_fs.driver, app_fs.adcm.url).open(close_popup=True)


@allure.step("Upload cluster bundle")
def cluster_bundle(sdk_client_fs: ADCMClient, data_dir_name: str) -> Bundle:
    return sdk_client_fs.upload_from_fs(get_data_dir(__file__, data_dir_name))


@pytest.fixture()
def create_cluster_with_service(sdk_client_fs: ADCMClient) -> Tuple[Cluster, Service]:
    bundle = cluster_bundle(sdk_client_fs, BUNDLE)
    cluster = bundle.cluster_create(name=CLUSTER_NAME)
    return cluster, cluster.service_add(name=SERVICE_NAME)


@pytest.fixture()
def create_cluster_with_component(
    create_cluster_with_service: Tuple[Cluster, Service], sdk_client_fs: ADCMClient
) -> Tuple[Cluster, Service, Host, Provider]:
    """Create cluster with component"""

    cluster, service = create_cluster_with_service
    provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
    provider = provider_bundle.provider_create("test provider")
    host = provider.host_create("test-host")
    cluster.host_add(host)
    cluster.hostcomponent_set((host, service.component(name=FIRST_COMPONENT_NAME)))
    return cluster, service, host, provider


# !===== Tests =====!


CUSTOM_ROLE_NAME = "Test_Role"
CUSTOM_POLICY = AdminPolicyInfo(
    name="Test policy name",
    description="Test policy description",
    role="ADCM User",
    users="admin, status",
    groups=None,
    objects=None,
)
ACTION_HINT = "The Action is not available. You need to fill in the LDAP integration settings."


@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestAdminIntroPage:
    """Tests for the /admin/intro"""

    def test_open_by_tab_admin_intro_page(self, app_fs):
        """Test open /admin/intro from left menu"""

        users_page = AdminUsersPage(app_fs.driver, app_fs.adcm.url).open()
        intro_page = users_page.open_settings_menu()
        intro_page.check_all_elements()
        intro_page.check_admin_toolbar()


@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestAdminSettingsPage:
    """Tests for the /admin/roles"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_admin_settings_page(self, app_fs):
        """Test open /admin/settings from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        settings_page = intro_page.open_settings_menu()
        settings_page.check_all_elements()
        settings_page.check_admin_toolbar()

    @pytest.mark.full()
    def test_settings_filter(self, settings_page: AdminSettingsPage):
        """Apply different filters on Admin Settings page"""
        params = {
            "search_text": "ADCM",
            "field_display_name": "ADCM's URL",
            "group": "Global Options",
        }
        get_rows_func = settings_page.config.get_all_config_rows
        with allure.step(
            f'Search {params["search_text"]} and check {params["field_display_name"]} is presented after search'
        ):
            with expect_rows_amount_change(get_rows_func):
                settings_page.config.search(params["search_text"])
            settings_page.config.get_config_row(params["field_display_name"])
        with allure.step("Clear search"), expect_rows_amount_change(get_rows_func):
            settings_page.config.clear_search()
        with allure.step(
            f'Click on {params["group"]} group and check {params["field_display_name"]} '
            "is not presented after group roll up"
        ):
            with expect_rows_amount_change(get_rows_func):
                settings_page.config.click_on_group(params["group"])
            with pytest.raises(AssertionError):
                settings_page.config.get_config_row(params["field_display_name"])
        with allure.step(
            f'Click on {params["group"]} group and check {params["field_display_name"]} '
            "is presented after group expand"
        ):
            with expect_rows_amount_change(get_rows_func):
                settings_page.config.click_on_group(params["group"])
            settings_page.config.get_config_row(params["field_display_name"])

    @pytest.mark.full()
    def test_save_settings_with_different_name(self, settings_page: AdminSettingsPage):
        """Save settings with different name"""
        params = {
            "new_name": "test_settings",
            "field_display_name": "client_id",
            "field_value": "123",
        }
        settings_page.config.set_description(params["new_name"])
        with allure.step(f'Change value of field {params["field_display_name"]} to {params["field_value"]}'):
            config_field_row = settings_page.config.get_config_row(params["field_display_name"])
            settings_page.config.type_in_field_with_few_inputs(row=config_field_row, values=[params["field_value"]])
        settings_page.config.save_config()
        settings_page.config.compare_versions(params["new_name"], "init")
        with allure.step("Check history"):
            config_field_row = settings_page.config.get_config_row(params["field_display_name"])
            history = settings_page.config.get_history_in_row(config_field_row)
            assert len(history) == 1, f'History should has exactly one entry for field {params["field_display_name"]}'
            assert (actual_value := history[0]) == (expected_value := params["field_value"]), (
                f'History entry for field {params["field_display_name"]} '
                f"should be {expected_value}, not {actual_value}"
            )

    @pytest.mark.full()
    def test_negative_values_in_adcm_config(self, settings_page: AdminSettingsPage):
        """Put negative numbers in the fields of ADCM settings"""
        params = (
            (
                "Log rotation from file system",
                -1,
                "Field [Log rotation from file system] value cannot be less than 0!",
            ),
            (
                "Log rotation from database",
                -1,
                "Field [Log rotation from database] value cannot be less than 0!",
            ),
            ("Forks", 0, "Field [Forks] value cannot be less than 1!"),
        )

        for field, inappropriate_value, error_message in params:
            with allure.step(
                f'Set value {inappropriate_value} to field "{field}" and expect error message: {error_message}'
            ):
                config_row = settings_page.config.get_config_row(field)
                settings_page.scroll_to(config_row)
                settings_page.config.type_in_field_with_few_inputs(
                    row=config_row, values=[inappropriate_value], clear=True
                )
                settings_page.config.check_invalid_value_message(error_message)

    def test_reset_config(self, settings_page: AdminSettingsPage):
        """Change config field, save, reset"""
        params = {"field_display_name": "client_id", "init_value": "", "changed_value": "123"}
        with allure.step(f'Set value of {params["field_display_name"]} to {params["changed_value"]}'):
            config_field_row = settings_page.config.get_config_row(params["field_display_name"])
            settings_page.config.type_in_field_with_few_inputs(row=config_field_row, values=[params["changed_value"]])
        with allure.step("Save config"):
            settings_page.config.save_config()
            settings_page.config.assert_input_value_is(params["changed_value"], params["field_display_name"])
        with allure.step(f'Reset value of {params["field_display_name"]}'):
            config_field_row = settings_page.config.get_config_row(params["field_display_name"])
            settings_page.config.reset_to_default(config_field_row)
            settings_page.config.assert_input_value_is(params["init_value"], params["field_display_name"])

    @pytest.mark.ldap()
    def test_ldap_config(self, settings_page: AdminSettingsPage):
        """Test ldap"""
        params = {
            "test_action": "Test LDAP connection",
            "connect_action": "Run LDAP sync",
            "test_value": "test",
        }
        with allure.step("Check ldap actions are disabled"):
            assert settings_page.toolbar.is_adcm_action_inactive(
                action_name=params["connect_action"]
            ), f"Action {params['connect_action']} should be disabled"
            assert settings_page.toolbar.is_adcm_action_inactive(
                action_name=params["test_action"]
            ), f"Action {params['test_action']} should be disabled"

        with allure.step("Check actions hint is present on toolbar"):
            hint_text = settings_page.toolbar.get_action_hint(action_name=params["connect_action"])
            assert hint_text == ACTION_HINT, f"Action hint text should be {ACTION_HINT}\nActual hint text: {hint_text}"

            hint_text = settings_page.toolbar.get_action_hint(action_name=params["test_action"])
            assert hint_text == ACTION_HINT, f"Action hint text should be {ACTION_HINT}\nActual hint text: {hint_text}"

        with allure.step("Fill ldap config"):
            settings_page.config.expand_or_close_group(group_name="LDAP integration")
            settings_page.config.type_in_field_with_few_inputs(row="LDAP URI", values=[params["test_value"]])
            settings_page.config.type_in_field_with_few_inputs(row="Bind DN", values=[params["test_value"]])
            settings_page.config.type_in_field_with_few_inputs(
                row="Bind Password", values=[params["test_value"], params["test_value"]]
            )
            settings_page.config.type_in_field_with_few_inputs(row="User search base", values=[params["test_value"]])
            settings_page.config.type_in_field_with_few_inputs(row="Group search base", values=[params["test_value"]])
            settings_page.config.save_config()
            settings_page.config.wait_config_loaded()
        with allure.step("Check ldap actions are enabled"):
            assert not settings_page.toolbar.is_adcm_action_inactive(
                action_name=params["connect_action"]
            ), f"Action {params['connect_action']} should be enabled"
            assert not settings_page.toolbar.is_adcm_action_inactive(
                action_name=params["test_action"]
            ), f"Action {params['test_action']} should be enabled"
        with allure.step("Check Test LDAP connection action"):
            settings_page.toolbar.run_adcm_action(action_name=params["test_action"])
            settings_page.header.wait_in_progress_job_amount(expected_job_amount=1)
            settings_page.header.wait_in_progress_job_amount(expected_job_amount=0)
        with allure.step("Check Run LDAP sync action"):
            settings_page.toolbar.run_adcm_action(action_name=params["connect_action"])
            settings_page.header.wait_in_progress_job_amount(expected_job_amount=1)


@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestAdminUsersPage:
    """Tests for the /admin/users"""

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_admin_users_page(self, app_fs):
        """Test open /admin/users from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        users_page = intro_page.open_users_menu()
        users_page.check_all_elements()
        users_page.check_admin_toolbar()

    def test_new_user_creation(self, users_page: AdminUsersPage):
        """Create new user, change password and login with new password"""

        params = {
            "username": "testuser",
            "password": "test_pass",
            "new_password": "testtest",
            "first_name": "First",
            "last_name": "Last",
            "email": "priv@et.ru",
        }
        users_page.create_user(
            params["username"],
            params["password"],
            params["first_name"],
            params["last_name"],
            params["email"],
        )
        with allure.step(f'Check user {params["username"]} is listed in users list'):
            self.check_user_is_listed_on_page(users_page, params["username"])

        with allure.step("Change user's password"):
            dialog: UpdateUserDialog = users_page.get_row(username_is(params["username"])).open_update_dialog()
            dialog.password_input.fill(params["new_password"])
            dialog.password_confirm_input.fill(params["new_password"])
            dialog.update()

        with allure.step(f'Login as user {params["username"]} with password {params["new_password"]}'):
            users_page.header.logout()
            login_page = LoginPage(users_page.driver, users_page.base_url)
            login_page.wait_page_is_opened()
            login_page.login_user(params["username"], params["new_password"])

        with allure.step("Check login was successful"):
            AdminIntroPage(users_page.driver, users_page.base_url).wait_page_is_opened(timeout=5)

    def test_delete_user(self, users_page: AdminUsersPage):
        """Create new user, delete it and check current user can't be deleted"""
        username = "testuser"
        current_user = "admin"

        # TODO rework, it makes no sense
        with allure.step("Check user can't delete itself"):
            assert not users_page.get_row(
                username_is(current_user)
            ).is_delete_button_presented, f"Delete button for user {current_user} should be disabled"

        with allure.step(f"Create user {username} and check it has appeared in users list"):
            users_page.create_user(username, "test_pass", "First", "Last", "priv@et.ru")
            self.check_user_is_listed_on_page(users_page, username)

        with allure.step(f"Deactivate user {username} and check UI reacted on it"):
            user_row = users_page.get_row(username_is(username))
            user_row.select.click()
            users_page.delete_selected_users()
            self.check_user_is_listed_on_page(users_page, username)
            assert not users_page.get_row(username_is(username)).is_active, "User should be deactivated"

        with allure.step("Check user update is not allowed"):
            user_row: UserRow = users_page.get_row(username_is(username))
            dialog: UpdateUserDialog = user_row.open_update_dialog()
            assert not dialog.has_update_button(), "Update button should not be visible"
            # we don't check is_superuser and groups here because of their complex structure
            # and minor effect of such check
            for field_name in ("username", "first_name", "last_name", "email"):
                assert not getattr(
                    dialog, f"{field_name}_element"
                ).is_enabled(), f"Field '{field_name}' should not be editable"

    def test_change_admin_password(self, users_page: AdminUsersPage):
        """Change admin password, login with new credentials"""
        username = "admin"
        password = "new_pass"

        with allure.step("Change password of admin user"):
            dialog: UpdateUserDialog = users_page.get_row(username_is(username)).open_update_dialog()
            dialog.first_name_input.fill("Best")
            dialog.last_name_input.fill("Admin")
            dialog.password_input.fill(password)
            dialog.password_confirm_input.fill(password)
            dialog.update()

        with allure.step("Refresh page and check Login page is opened"):
            users_page.refresh()
            login_page = LoginPage(users_page.driver, users_page.base_url)
            login_page.wait_page_is_opened()

        with allure.step("Login with new credentials"):
            login_page.login_user(username=username, password=password)
            AdminIntroPage(users_page.driver, users_page.base_url).wait_page_is_opened(timeout=5)

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_ldap_user_change_is_forbidden(self, users_page: AdminUsersPage, ldap_user_in_group):
        """Change ldap user"""
        username = ldap_user_in_group["name"]

        users_page.header.wait_success_job_amount(1)
        with allure.step(f'Check user {username} is listed in users list'):
            self.check_user_is_listed_on_page(users_page, username)

        with allure.step('Check that changing ldap user is prohibited'):

            dialog: UpdateUserDialog = users_page.get_row(username_is(username)).open_update_dialog()
            element_names = ("username", "password", "password_confirm", "first_name", "last_name", "email")
            for name in element_names:
                assert not getattr(dialog, f"{name}_element").is_enabled(), "Ldap user fields should be disabled"
            assert dialog.groups_element.is_enabled(), "LDAP user groups should not be disabled"
            assert not dialog.update_button.is_enabled(), "Update button should be disabled"

    def test_add_user_to_group(self, user, users_page, sdk_client_fs):
        """Add group for user"""
        name = "test"
        email = "test@test.ru"
        test_group = sdk_client_fs.group_create("test_group")

        with allure.step("Fill user info and add to group"):
            dialog: UpdateUserDialog = users_page.get_row(username_is(user.username)).open_update_dialog()
            dialog.first_name_input.fill(name)
            dialog.last_name_input.fill(name)
            dialog.email_input.fill(email)
            dialog.add_to_group(test_group.name)
            dialog.update()

        with allure.step(f"Check user {user.username} is listed in users list with changed params"):
            user_row = users_page.get_row(username_is(user.username))
            assert test_group.name in user_row.get_groups(), "User group hasn't changed"
            assert email in user_row.email, "User email hasn't changed"

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_add_ldap_group_to_users(self, user, users_page, sdk_client_fs, ldap_user_in_group):
        """Check that user can't add ldap group to usual user"""
        with allure.step("Wait ldap integration ends"):
            wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name="run_ldap_sync").run(), "success")

        with allure.step("Check that changing user group is prohibited"):
            dialog: UpdateUserDialog = users_page.get_row(username_is(user.username)).open_update_dialog()
            assert dialog.get_unavailable_groups() == ("adcm_users",)

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_add_group_to_ldap_users(self, user, users_page, sdk_client_fs, ldap_user_in_group):
        """Check that user can add group to ldap user"""
        username = ldap_user_in_group["name"]
        with allure.step("Wait ldap integration ends"):
            wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name="run_ldap_sync").run(), "success")
        test_group = sdk_client_fs.group_create("test_group")
        dialog: UpdateUserDialog = users_page.get_row(username_is(username)).open_update_dialog()
        dialog.add_to_group(test_group.name)
        dialog.update()
        with allure.step(f"Check user {user.username} is listed in users list with changed params"):
            user_row = users_page.get_row(username_is(username))
            assert test_group.name in user_row.get_groups(), "User group hasn't changed"

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_filter_users(self, user, users_page, sdk_client_fs, ldap_user_in_group):
        """Check that users can be filtered"""

        with allure.step("Wait ldap integration ends"):
            wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name="run_ldap_sync").run(), "success")
        users_page.driver.refresh()
        users_page.filter_users_by("status", "active")
        with allure.step("Check users are filtered by active status"):
            assert users_page.get_all_user_names() == [
                user.username for user in sdk_client_fs.user_list(is_active=True)
            ], "Not all active users are visible"
        users_page.remove_user_filter()
        users_page.filter_users_by("status", "inactive")
        with allure.step("Check users are filtered by inactive status"):
            assert users_page.get_all_user_names() == [
                user.username for user in sdk_client_fs.user_list(is_active=False)
            ], "Not all inactive users are visible"
        users_page.remove_user_filter()
        users_page.filter_users_by("type", "local")
        with allure.step("Check users are filtered by local type"):
            assert users_page.get_all_user_names() == [
                user.username for user in sdk_client_fs.user_list(type="local")
            ], "Not all local users are visible"
        users_page.remove_user_filter()
        users_page.filter_users_by("type", "ldap")
        with allure.step("Check users are filtered by ldap status"):
            assert users_page.get_all_user_names() == [
                user.username for user in sdk_client_fs.user_list(type="ldap")
            ], "Not all ldap users are visible"
        users_page.filter_users_by("status", "active")
        with allure.step("Check users are filtered both by active status and ldap"):
            assert users_page.get_all_user_names() == [
                user.username for user in sdk_client_fs.user_list(is_active=True, type="ldap")
            ], "Not all active ldap users are visible"

    def check_user_is_listed_on_page(self, users_page: AdminUsersPage, username: str) -> None:
        assert username in users_page.get_all_user_names(), f'User {username} was not created'


@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestAdminRolesPage:
    """Tests for the /admin/roles"""

    custom_role = dict(
        name="Test_role_name",
        description="Test role description",
        permissions=["Create provider", "Create cluster", "Create user", "Remove policy"],
    )

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_admin_roles_page(self, app_fs):
        """Test open /admin/roles from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        roles_page = intro_page.open_roles_menu()
        roles_page.check_all_elements()
        with allure.step("Check that there are 4 default roles"):
            assert roles_page.table.row_count == 4
        self.check_default_roles(roles_page)
        roles_page.check_admin_toolbar()

    def test_create_custom_role_on_roles_page(self, app_fs):
        """Test create a role on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role["name"], self.custom_role["description"], self.custom_role["permissions"])
        self.check_default_roles(page)
        assert dict(page.get_row(name_is(self.custom_role["name"]))) == self.custom_role

    @pytest.mark.full()
    def test_check_pagination_role_list_page(self, app_fs):
        """Test pagination on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Create 7 custom roles"):
            for _ in range(7):
                page.create_role(
                    f"{self.custom_role['name']}_{random_string()}",
                    self.custom_role["description"],
                    self.custom_role["permissions"],
                )
        check_pagination(page.table, expected_on_second=1)

    def test_check_role_popup_on_roles_page(self, app_fs):
        """Test changing a role on /admin/roles page"""
        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role["name"], self.custom_role["description"], self.custom_role["permissions"])
        dialog = page.open_role_by_name(self.custom_role["name"])

        with allure.step("Check that update unavailable without the role name"):
            dialog.name_input.fill(" ")
            assert not dialog.is_update_enabled()
            is_superset_of(
                dialog.get_error_messages(),
                {"Role name is required.", "Role name too short."},
                assertion_message="Incorrect validation error messages",
            )

            dialog.name_input.fill("")
            assert not dialog.is_update_enabled()
            is_in_collection("Role name is required.", dialog.get_error_messages())

            dialog.name_input.fill("йй")
            is_in_collection("Role name is not correct.", dialog.get_error_messages())
            dialog.name_input.fill("Correct name")

        with allure.step("Check that update unavailable without permissions"):
            dialog.remove_permissions(self.custom_role["permissions"])
            assert not dialog.is_update_enabled()
            dialog.add_permissions(self.custom_role["permissions"])
            assert dialog.is_update_enabled()
            dialog.clear_permissions()
            assert not dialog.is_update_enabled()

        with allure.step("Fill new role info and check"):
            name = "Test_another_name"
            description = "Test role description 2"
            permissions = ["Upload bundle"]

            dialog.name_input.fill(name)
            dialog.description_input.fill(description)
            dialog.add_permissions(permissions)
            dialog.update()

            self.check_default_roles(page)
            role: RoleRow = page.get_row(name_is(name))
            assert role.name == name
            assert role.description == description
            assert role.permissions == permissions

    def test_delete_role_from_roles_page(self, app_fs):
        """Test delete custom role on /admin/roles page"""

        page = AdminRolesPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_role(self.custom_role["name"], self.custom_role["description"], self.custom_role["permissions"])
        page.select_all_roles()
        page.delete_selected_roles()
        self.check_default_roles(page)
        with allure.step("Check that role has been deleted"):
            assert page.table.row_count == 4, "There should be only default roles"

    @allure.step("Check all default roles are presented")
    def check_default_roles(self, page: AdminRolesPage):
        default_roles = [
            dict(
                name="ADCM User",
                description="",
                permissions=[
                    "View any object configuration",
                    "View any object import",
                    "View any object host-components",
                ],
            ),
            dict(
                name="Service Administrator",
                description="",
                permissions=[
                    "View host configurations",
                    "Edit service configurations",
                    "Edit component configurations",
                    "View host-components",
                ],
            ),
            dict(
                name="Cluster Administrator",
                description="",
                permissions=[
                    "Create host",
                    "Upload bundle",
                    "Edit cluster configurations",
                    "Edit host configurations",
                    "Add service",
                    "Remove service",
                    "Remove hosts",
                    "Map hosts",
                    "Unmap hosts",
                    "Edit host-components",
                    "Upgrade cluster bundle",
                    "Remove bundle",
                    "Service Administrator",
                ],
            ),
            dict(
                name="Provider Administrator",
                description="",
                permissions=[
                    "Create host",
                    "Upload bundle",
                    "Edit provider configurations",
                    "Edit host configurations",
                    "Remove hosts",
                    "Upgrade provider bundle",
                    "Remove bundle",
                ],
            ),
        ]

        roles = tuple(map(dict, page.get_rows()))
        for role in default_roles:
            assert role in roles, f"Default role {role.name} is wrong or missing. Expected to find: {role} in {roles}"


@pytest.mark.usefixtures("_login_to_adcm_over_api")
class TestAdminGroupsPage:
    """Tests for the /admin/groups"""

    custom_group = dict(name="Test_group", description="Test description", users="admin")

    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_admin_groups_page(self, app_fs):
        """Test open /admin/groups from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page = intro_page.open_groups_menu()
        groups_page.check_all_elements()
        groups_page.check_admin_toolbar()

    def test_create_group_on_admin_groups_page(self, app_fs):
        """Test create a group on /admin/groups"""

        groups_page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page.create_custom_group(
            self.custom_group["name"], self.custom_group["description"], [self.custom_group["users"]]
        )
        current_groups = tuple(map(dict, groups_page.get_rows()))
        with allure.step("Check that there are 1 custom group"):
            assert len(current_groups) == 1, "There should be 1 group on the page"
            assert self.custom_group in current_groups, "Created group should be on the page"

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_create_group_with_ldap_user_on_admin_groups_page(self, sdk_client_fs, app_fs, ldap_user_in_group):
        """Test create a group on /admin/groups"""

        wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name="run_ldap_sync").run(), "success")
        groups_page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page.create_custom_group(
            self.custom_group["name"], self.custom_group["description"], [ldap_user_in_group["name"]]
        )
        current_groups = tuple(map(dict, groups_page.get_rows()))
        with allure.step("Check that there are 1 custom group and 1 ldap"):
            assert len(current_groups) == 2, "There should be 2 group on the page"
            assert (
                dict(
                    name="Test_group",
                    description="Test description",
                    users=ldap_user_in_group["name"],
                )
                in current_groups
            ), "Created group should be on the page"

    @pytest.mark.full()
    def test_check_pagination_groups_list_page(self, app_fs):
        """Test pagination on /admin/groups page"""

        page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Create 11 groups"):
            for _ in range(11):
                page.create_custom_group(
                    f"{self.custom_group['name']}_{random_string()}",
                    self.custom_group["description"],
                    [self.custom_group["users"]],
                )
        check_pagination(page.table, expected_on_second=1)

    def test_delete_group_from_groups_page(self, app_fs):
        """Test delete custom group on /admin/groups page"""

        page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        page.create_custom_group(
            self.custom_group["name"], self.custom_group["description"], [self.custom_group["users"]]
        )
        page.select_all_groups()
        page.delete_selected_groups()
        with allure.step("Check that group has been deleted"):
            assert len(page.table.get_all_rows()) == 0, "There should be 0 groups"

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_ldap_group_change_is_forbidden(self, app_fs, ldap_user_in_group):
        """Change ldap group"""

        params = {"group_name": "adcm_users"}
        groups_page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()
        groups_page.header.wait_success_job_amount(1)
        with allure.step(f"Check group {params['group_name']} is listed in groups list"):
            assert (
                groups_page.get_rows()[0].name == params["group_name"]
            ), f"Group {params['group_name']} should be in groups list"
        with allure.step("Check LDAP group is not editable via dialog"):
            group_row: GroupRow = groups_page.get_row(name_is(params["group_name"]))
            dialog = group_row.open_update_dialog()
            assert not dialog.name_input.element.is_enabled()
            assert not dialog.description_input.element.is_enabled()
            assert not dialog.update_button.is_enabled()
            # this element is considered disabled if one of the classes have "disabled" in name
            assert "disabled" in dialog.users_element.get_attribute("class")
            assert dialog.title == "Group Info", "Wrong title in popup"

    @pytest.mark.ldap()
    @pytest.mark.usefixtures("configure_adcm_ldap_ad")
    def test_add_ldap_user_to_group(self, app_fs, ldap_user_in_group):
        """Add ldap user to group"""

        group_name = "Test_group"
        username = ldap_user_in_group["name"]

        groups_page = AdminGroupsPage(app_fs.driver, app_fs.adcm.url).open()

        with allure.step("Create group only with name"):
            dialog = groups_page.open_add_group_dialog()
            dialog.name_input.fill(group_name)
            dialog.add()

        groups_page.header.wait_success_job_amount(1)

        with allure.step(f"Add user {username} to group"):
            dialog: UpdateGroupDialog = groups_page.get_row(name_is(group_name)).open_update_dialog()
            dialog.add_users([username])
            dialog.update()

        with allure.step(f"Check group {group_name} has user {username}"):
            assert (
                username in groups_page.get_row(name_is(group_name)).get_users()
            ), f"Group {group_name} should have user {username}"


class TestAdminPolicyPage:
    """Tests for the /admin/policies"""

    @allure.step("Check custome policy")
    def check_custom_policy(self, policies_page, policy=None):
        """Check that there is only one created policy with expected params"""

        policy = policy or CUSTOM_POLICY
        current_policies = policies_page.get_all_policies()
        assert len(current_policies) == 1, "There should be 1 policy on the page"
        assert current_policies == [policy], "Created policy should be on the page"

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    @pytest.mark.smoke()
    @pytest.mark.include_firefox()
    def test_open_by_tab_admin_policies_page(self, app_fs):
        """Test open /admin/policies from left menu"""

        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()
        policies_page = intro_page.open_policies_menu()
        policies_page.check_all_elements()
        policies_page.check_admin_toolbar()

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_create_policy_on_admin_groups_page(self, app_fs):
        """Test create a group on /admin/policies"""

        policies_page = AdminPoliciesPage(app_fs.driver, app_fs.adcm.url).open()
        policies_page.create_policy(
            policy_name=CUSTOM_POLICY.name,
            description=CUSTOM_POLICY.description,
            role=CUSTOM_POLICY.role,
            users=CUSTOM_POLICY.users,
        )
        self.check_custom_policy(policies_page)

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    @pytest.mark.full()
    def test_check_pagination_policy_list_page(self, app_fs):
        """Test pagination on /admin/policies page"""

        policies_page = AdminPoliciesPage(app_fs.driver, app_fs.adcm.url).open()
        with allure.step("Create 11 policies"):
            for i in range(11):
                policies_page.create_policy(
                    policy_name=f"{CUSTOM_POLICY.name}_{i}",
                    description=CUSTOM_POLICY.description,
                    role=CUSTOM_POLICY.role,
                    users=CUSTOM_POLICY.users,
                )
        check_pagination(policies_page.table, expected_on_second=1)

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_delete_policy_from_policies_page(self, app_fs):
        """Test delete custom group on /admin/policies page"""

        policies_page = AdminPoliciesPage(app_fs.driver, app_fs.adcm.url).open()
        policies_page.create_policy(
            policy_name=CUSTOM_POLICY.name,
            description=CUSTOM_POLICY.description,
            role=CUSTOM_POLICY.role,
            users=CUSTOM_POLICY.users,
        )
        policies_page.delete_all_policies()

    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    @pytest.mark.parametrize(
        ("clusters", "services", "providers", "hosts", "parents", "role_name"),
        [
            (CLUSTER_NAME, None, None, None, None, "View cluster configurations"),
            (None, SERVICE_NAME, None, None, CLUSTER_NAME, "View service configurations"),
            (None, None, PROVIDER_NAME, None, None, "View provider configurations"),
            (None, None, None, HOST_NAME, None, "View host configurations"),
            (None, SERVICE_NAME, None, None, CLUSTER_NAME, "View component configurations"),
            (
                CLUSTER_NAME,
                None,
                None,
                None,
                None,
                "View cluster configurations, View service configurations",
            ),
            (
                None,
                SERVICE_NAME,
                None,
                None,
                CLUSTER_NAME,
                "View cluster configurations, View service configurations, View component configurations, "
                "View host configurations",
            ),
            (
                None,
                None,
                PROVIDER_NAME,
                None,
                None,
                "View provider configurations, View host configurations",
            ),
            (
                None,
                None,
                None,
                HOST_NAME,
                None,
                "View provider configurations, View host configurations",
            ),
        ],
    )
    @pytest.mark.usefixtures("parents", "create_cluster_with_component")
    def test_check_policy_popup_for_entities(
        self,
        sdk_client_fs,
        app_fs,
        clusters,
        services,
        providers,
        hosts,
        role_name,
    ):
        """Test creating policy"""

        custom_policy = deepcopy(CUSTOM_POLICY)
        custom_policy.role = CUSTOM_ROLE_NAME
        custom_policy.objects = clusters or services or providers or hosts
        with allure.step("Create test role"):
            sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name=r).id} for r in role_name.split(", ")],
            )
        policies_page = AdminPoliciesPage(app_fs.driver, app_fs.adcm.url).open()
        policies_page.create_policy(
            policy_name=custom_policy.name,
            description=custom_policy.description,
            role=custom_policy.role,
            users=custom_policy.users,
            clusters=clusters,
            services=services,
            parent=CLUSTER_NAME,
            providers=providers,
            hosts=hosts,
        )
        self.check_custom_policy(policies_page, policy=custom_policy)

    # pylint: enable=too-many-locals

    def test_policy_permission_to_view_access_cluster(
        self, sdk_client_fs, app_fs, create_cluster_with_component, another_user
    ):
        """Test for the permissions to cluster."""

        cluster, *_ = create_cluster_with_component
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="View cluster configurations").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[cluster],
            )
        with allure.step("Create second cluster"):
            second_cluster = sdk_client_fs.bundle().cluster_create(name=f"{CLUSTER_NAME} 2")
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first cluster config"):
            cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
            cluster_config_page.config.check_config_fields_visibility({"str_param", "int", "param1", "param2"})
        with allure.step("Check that user can not view second cluster config"):
            second_cluster_config_page = ClusterConfigPage(app_fs.driver, app_fs.adcm.url, second_cluster.id).open()
            second_cluster_config_page.config.check_no_rows_or_groups_on_page()

    def test_policy_permission_to_view_access_service(
        self, sdk_client_fs, app_fs, create_cluster_with_component, another_user
    ):
        """Test for the permissions to service."""

        cluster, service, *_ = create_cluster_with_component
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="View service configurations").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[service],
            )
        with allure.step("Create second service"):
            second_service = cluster.service_add(name="test_service_2")
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first service config"):
            service_config_page = ServiceConfigPage(
                app_fs.driver, app_fs.adcm.url, cluster.id, service.service_id
            ).open()
            service_config_page.config.check_config_fields_visibility({"str_param", "int", "param1", "param2"})
        with allure.step("Check that user can not view second service config"):
            second_service_config_page = ServiceConfigPage(
                app_fs.driver, app_fs.adcm.url, cluster.id, second_service.service_id
            ).open()
            second_service_config_page.config.check_no_rows_or_groups_on_page()

    def test_policy_permission_to_view_access_component(
        self, sdk_client_fs, app_fs, create_cluster_with_component, another_user
    ):
        """Test for the permissions to component."""

        cluster, service, host, _ = create_cluster_with_component
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="View component configurations").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[service],
            )
        with allure.step("Create second component"):
            second_service = cluster.service_add(name="test_service_2")
            cluster.hostcomponent_set(
                (host, service.component(name=FIRST_COMPONENT_NAME)),
                (host, second_service.component(name="second")),
            )
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first component config"):
            component_config_page = ComponentConfigPage(
                app_fs.driver, app_fs.adcm.url, cluster.id, service.service_id, 1
            ).open()
            component_config_page.config.check_config_fields_visibility({"str_param"})
        with allure.step("Check that user can not view second component config"):
            second_component_config_page = ComponentConfigPage(
                app_fs.driver, app_fs.adcm.url, cluster.id, second_service.service_id, 2
            ).open()
            second_component_config_page.config.check_no_rows_or_groups_on_page()

    def test_policy_permission_to_view_access_provider(self, sdk_client_fs, app_fs, another_user):
        """Test for the permissions to provider."""

        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
        provider = provider_bundle.provider_create("test_provider")
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="View provider configurations").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[provider],
            )
        with allure.step("Create second provider"):
            provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(get_data_dir(__file__, "second_provider")))
            second_provider = provider_bundle.provider_create("second_test_provider")
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first provider config"):
            provider_config_page = ProviderConfigPage(app_fs.driver, app_fs.adcm.url, provider.id).open()
            provider_config_page.config.check_config_fields_visibility({"str_param"})
        with allure.step("Check that user can not view second provider config"):
            second_provider_config_page = ProviderConfigPage(app_fs.driver, app_fs.adcm.url, second_provider.id).open()
            second_provider_config_page.config.check_no_rows_or_groups_on_page()

    def test_policy_permission_to_view_access_host(self, sdk_client_fs, app_fs, another_user):
        """Test for the permissions to host."""

        provider_bundle = sdk_client_fs.upload_from_fs(get_data_dir(__file__, "provider"))
        provider = provider_bundle.provider_create("test_provider")
        host = provider.host_create("test-host")
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="View host configurations").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[host],
            )
        with allure.step("Create second host"):
            second_host = provider.host_create("test-host-2")
        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first host config"):
            host_config_page = HostConfigPage(app_fs.driver, app_fs.adcm.url, host.id).open()
            host_config_page.config.check_config_fields_visibility({"str_param"})
        with allure.step("Check that user can not view second host config"):
            second_host_config_page = HostConfigPage(app_fs.driver, app_fs.adcm.url, second_host.id).open()
            second_host_config_page.config.check_no_rows_or_groups_on_page()

    # pylint: disable=too-many-locals
    def test_policy_permission_to_run_cluster_action_and_view_task(
        self, sdk_client_fs, app_fs, create_cluster_with_component, another_user
    ):
        """Test for the permissions to task."""

        cluster, *_ = create_cluster_with_component
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="Cluster Action: some_action").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[cluster],
            )
        with allure.step("Create second cluster"):
            second_cluster = sdk_client_fs.bundle().cluster_create(name=f"{CLUSTER_NAME} 2")

        login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
        login_page.login_user(**another_user)
        AdminIntroPage(app_fs.driver, app_fs.adcm.url).wait_page_is_opened()
        with allure.step("Check that user can view first cluster"):
            cluster_list_page = ClusterListPage(app_fs.driver, app_fs.adcm.url).open()
            assert len(cluster_list_page.table.get_all_rows()) == 1, "There should be 1 row with cluster"
        with allure.step("Create second policy"):
            test_role_2 = sdk_client_fs.role_create(
                name=f"{CUSTOM_ROLE_NAME}_2",
                display_name=f"{CUSTOM_ROLE_NAME}_2",
                child=[{"id": sdk_client_fs.role(name="View cluster configurations").id}],
            )
            sdk_client_fs.policy_create(
                name="Test policy 2",
                role=test_role_2,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[second_cluster],
            )
        with allure.step("Check that user can view second cluster"):
            cluster_list_page.driver.refresh()
            cluster_rows = cluster_list_page.table.get_all_rows()
            assert len(cluster_rows) == 2, "There should be 2 row with cluster"
        with allure.step("Check actions in clusters"):
            assert cluster_list_page.get_all_actions_name_in_cluster(cluster_rows[0]) == [
                "some_action"
            ], "First cluster action should be visible"
            assert (
                cluster_list_page.get_all_actions_name_in_cluster(cluster_rows[1]) == []
            ), "Second cluster action should not be visible"
        with allure.step("Run action from first cluster"):
            cluster_list_page.run_action_in_cluster_row(cluster_rows[0], "some_action")
        with allure.step("Check task"):
            cluster_list_page.header.click_job_block()
            assert len(cluster_list_page.header.get_job_rows_from_popup()) == 1, "Job amount should be 1"
            job_list_page = JobListPage(app_fs.driver, app_fs.adcm.url).open()
            job_rows = job_list_page.table.get_all_rows()
            assert len(job_rows) == 1, "Should be only 1 task"
            task_info = job_list_page.get_task_info_from_table(0)
            assert task_info.action_name == "some_action", "Wrong task name"
            assert task_info.invoker_objects == cluster.name, "Wrong cluster name"
            job_list_page.click_on_action_name_in_row(job_rows[0])
            JobPageStdout(app_fs.driver, app_fs.adcm.url, 1).wait_page_is_opened()
        with allure.step("Check forbidden page hint"):
            cluster_hc_page = ClusterComponentsPage(app_fs.driver, app_fs.adcm.url, cluster.id).open()
            expected_text = "[ FORBIDDEN ] You do not have permission to perform this action"
            should_become_truth(lambda: expected_text in cluster_hc_page.get_info_popup_text())

    # pylint: enable=too-many-locals
    @pytest.mark.usefixtures("_login_to_adcm_over_api")
    def test_policy_with_maintenance_mode(self, sdk_client_fs, app_fs, another_user, create_cluster_with_component):
        """Test create a group on /admin/policies"""

        _, _, host, _ = create_cluster_with_component
        with allure.step("Create test role"):
            test_role = sdk_client_fs.role_create(
                name=CUSTOM_ROLE_NAME,
                display_name=CUSTOM_ROLE_NAME,
                child=[{"id": sdk_client_fs.role(name="Manage Maintenance mode").id}],
            )
        with allure.step("Create test policy"):
            sdk_client_fs.policy_create(
                name="Test policy",
                role=test_role,
                user=[sdk_client_fs.user(username=another_user["username"])],
                objects=[host],
            )
        login_over_api(app_fs, another_user)
        with allure.step("Check that user can change maintenance mode state"):
            host_list_page = HostListPage(app_fs.driver, app_fs.adcm.url).open()
            host_list_page.assert_maintenance_mode_state(0)
            host_list_page.click_on_maintenance_mode_btn(0)
            host_list_page.assert_maintenance_mode_state(0, False)
