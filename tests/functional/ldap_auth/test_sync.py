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

"""Test synchronization and test connection with LDAP"""
import time
from contextlib import contextmanager
from typing import Optional, Tuple

import allure
import pytest
import requests
from adcm_client.objects import ADCM, ADCMClient, Group, User
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import random_string, wait_until_step_succeeds
from coreapi.exceptions import ErrorMessage

from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import (
    DEFAULT_LOCAL_USERS,
    SYNC_ACTION_NAME,
    TEST_CONNECTION_ACTION,
    check_existing_groups,
    check_existing_users,
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
)
from tests.functional.rbac.conftest import BusinessRoles, RbacRoles
from tests.library.assertions import expect_api_error, expect_no_api_error
from tests.library.ldap_interactions import LDAPTestConfig, configure_adcm_for_ldap

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm, pytest.mark.ldap()]


@pytest.fixture()
def adcm_user_client(sdk_client_fs) -> ADCMClient:
    """Create simple user with ADCM User role"""
    username, password = "SimpleUser", "MegaPassword"
    user = sdk_client_fs.user_create(username, password)
    sdk_client_fs.policy_create("Simple user", role=sdk_client_fs.role(name=RbacRoles.ADCMUser.value), user=[user])
    return ADCMClient(url=sdk_client_fs.url, user=username, password=password)


@pytest.fixture()
def adcm_admin_client(sdk_client_fs) -> ADCMClient:
    """Create ADCM admin user that is allowed to edit ADCM settings"""
    username, password = "SupaADCMAdmin", "MegaPassword"
    user = sdk_client_fs.user_create(username, password)
    role = sdk_client_fs.role_create(
        "ADCM admin role",
        display_name="ADCM admin role",
        child=[{"id": sdk_client_fs.role(name=BusinessRoles.EditADCMSettings.value.role_name).id}],
    )
    sdk_client_fs.policy_create("ADCM Admins", role=role, user=[user])
    return ADCMClient(url=sdk_client_fs.url, user=username, password=password)


@pytest.fixture()
def adcm_superuser_client(sdk_client_fs) -> ADCMClient:
    """Create another ADCM superuser"""
    username, password = "SupaDupaADCMAdmin", "MegaPassword"
    sdk_client_fs.user_create(username, password, is_superuser=True)
    return ADCMClient(url=sdk_client_fs.url, user=username, password=password)


class TestDisablingCause:
    """Test LDAP-related ADCM actions have correct disabling cause"""

    DISABLING_CAUSE = "no_ldap_settings"

    def test_ldap_connection_test_disabling_cause(self, sdk_client_fs, ad_config, ldap_basic_ous):
        """Test that disabling cause is set right for "test_ldap_connection" action"""
        adcm = sdk_client_fs.adcm()

        with allure.step("Check that with default settings disabling cause is set"):
            self._check_disabling_cause(adcm, self.DISABLING_CAUSE)
        with allure.step("Set correct LDAP settings and check disabling cause is None"):
            self._set_ldap_settings(sdk_client_fs, ad_config, ldap_basic_ous)
            self._check_disabling_cause(adcm, None)
        with allure.step("Disable LDAP settings and check disabling cause is set"):
            adcm.config_set_diff({"attr": {"ldap_integration": {"active": False}}})
            self._check_disabling_cause(adcm, self.DISABLING_CAUSE)

    def _check_disabling_cause(self, adcm: ADCM, expected: Optional[str]):
        # retrieve each time to avoid rereading
        sync = adcm.action(name=SYNC_ACTION_NAME)
        test_connection = adcm.action(name=TEST_CONNECTION_ACTION)
        assert (
            sync.disabling_cause == expected
        ), f"Sync action has incorrect disabling cause: {sync.disabling_cause}.\nExpected: {expected}"
        assert test_connection.disabling_cause == expected, (
            f"Test connection action has incorrect disabling cause: {test_connection.disabling_cause}.\n"
            f"Expected: {expected}"
        )

    def _set_ldap_settings(self, client: ADCMClient, config: LDAPTestConfig, ous: Tuple[str, str]):
        groups_ou, users_ou = ous
        configure_adcm_for_ldap(client, config, False, None, users_ou, groups_ou)


class TestLDAPSyncAction:
    """Test LDAP sync action"""

    pytestmark = [pytest.mark.usefixtures("configure_adcm_ldap_ad")]

    def test_ldap_simple_sync(self, sdk_client_fs, ldap_user_in_group, ldap_group):
        """Test that LDAP sync action pulls users and groups from LDAP"""
        self._simple_sync(sdk_client_fs, ldap_group, ldap_user_in_group, DEFAULT_LOCAL_USERS)

    # pylint: disable-next=too-many-arguments
    def test_access_to_tasks(
        self, adcm_user_client, adcm_admin_client, adcm_superuser_client, sdk_client_fs, ldap_user_in_group, ldap_group
    ):
        """Test that only superusers can see LDAP-related tasks"""
        superuser_name = adcm_superuser_client.me().username
        self._simple_sync(
            sdk_client_fs,
            ldap_group,
            ldap_user_in_group,
            (*DEFAULT_LOCAL_USERS, adcm_user_client.me().username, adcm_admin_client.me().username, superuser_name),
        )
        wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name=TEST_CONNECTION_ACTION).run(), "success")
        _check_task_logs_amount(adcm_user_client, 0)
        _check_task_logs_amount(adcm_admin_client, 0)
        _check_task_logs_amount(adcm_superuser_client, 2)
        with allure.step("Make superuser a regular user and check available tasks"):
            superuser: User = sdk_client_fs.user(username=superuser_name)
            superuser.update(is_superuser=False)
            _check_task_logs_amount(adcm_superuser_client, 0)

    def test_sync_with_already_existing_group(self, sdk_client_fs, ldap_user_in_group, ldap_group):
        """Test that when LDAP group have a local group with the same name, there won't be a conflict"""
        with allure.step("Create group with the name of LDAP group"):
            local_group: Group = sdk_client_fs.group_create(name=ldap_group["name"])
        check_existing_users(sdk_client_fs)
        check_existing_groups(sdk_client_fs, expected_local={local_group.name})
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
        check_existing_groups(sdk_client_fs, {ldap_group["name"]}, {local_group.name})
        local_group.reread()
        assert len(local_group.user_list()) == 0, "There should not be any user in local group"
        ldap_group_in_adcm = get_ldap_group_from_adcm(sdk_client_fs, ldap_group["name"])
        assert ldap_user_in_group["name"] in [
            u.username for u in ldap_group_in_adcm.user_list()
        ], f'Group from LDAP should have user {ldap_user_in_group["name"]}'

    def test_sync_with_already_existing_user(self, sdk_client_fs, ldap_group, ldap_user_in_group):
        """
        Test that during the sync existing users isn't overridden
        """
        group_name = "Some group"
        local_password = random_string(16)
        expected_local_users = (*DEFAULT_LOCAL_USERS, ldap_user_in_group["name"])

        with allure.step("Create user with the name of LDAP user"):
            local_user: User = sdk_client_fs.user_create(ldap_user_in_group["name"], local_password)
        with allure.step("Create group to add user to"):
            group: Group = sdk_client_fs.group_create(group_name)
            group.add_user(local_user)
        check_existing_users(sdk_client_fs, expected_local=expected_local_users)
        check_existing_groups(sdk_client_fs, expected_local=[group_name])
        _run_sync(sdk_client_fs)
        local_user.reread()
        with allure.step("Check user type is local"):
            assert local_user.type == "local", 'User type should stay "local"'
        with allure.step("Check user is still in group"):
            assert local_user.username in [
                u.username for u in group.user_list()
            ], "Local user should still be a part of the group"
        check_existing_users(sdk_client_fs, expected_local=expected_local_users)
        check_existing_groups(sdk_client_fs, expected_ldap=[ldap_group["name"]], expected_local=[group_name])

    # pylint: disable-next=too-many-arguments
    def test_ldap_group_removed(self, sdk_client_fs, ldap_ad, ldap_group, ldap_user_in_group):
        """Test LDAP group removed from ADCM after it's removed from LDAP"""
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
        check_existing_groups(sdk_client_fs, {ldap_group["name"]})
        with allure.step("Delete group from LDAP"):
            ldap_ad.delete(ldap_group["dn"])
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
        check_existing_groups(sdk_client_fs)

    # pylint: disable-next=too-many-arguments
    def test_user_removed_from_group(self, sdk_client_fs, ldap_ad, ldap_group, ldap_user_in_group):
        """Test that when user is removed from group in AD, it is also removed in ADCM's LDAP group"""
        another_group: Group = sdk_client_fs.group_create("Another group")
        _run_sync(sdk_client_fs)
        with allure.step("Add LDAP users to the local group"):
            user_in_group = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group["name"])
            group = get_ldap_group_from_adcm(sdk_client_fs, ldap_group["name"])
            another_group.add_user(user_in_group)
        with allure.step("Remove user in AD from LDAP group and rerun sync"):
            ldap_ad.remove_user_from_group(ldap_user_in_group["dn"], ldap_group["dn"])
            _run_sync(sdk_client_fs)
        with allure.step('Check user was removed only from LDAP group'):
            check_existing_users(sdk_client_fs, {ldap_user_in_group['name']})
            check_existing_groups(sdk_client_fs, {ldap_group['name']}, {another_group.name})
            group.reread()
            assert len(group.user_list()) == 0, "Group from LDAP should be empty"
            another_group.reread()
            assert len(another_group.user_list()) == 1, 'Local group should still have deactivated users in it'

    def test_user_deactivated(self, sdk_client_fs, ldap_ad, ldap_user_in_group):
        """Test that user is deactivated in ADCM after it's deactivated in AD"""
        ldap_user = ldap_user_in_group
        credentials = {"user": ldap_user["name"], "password": ldap_user["password"], "url": sdk_client_fs.url}
        with allure.step("Run sync and check that user is active and can log in"):
            _run_sync(sdk_client_fs)
            user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user["name"])
            assert user.is_active, "User should be active"
            expect_no_api_error("login as LDAP active user", ADCMClient, **credentials)
        with allure.step("Deactivate user in LDAP and check it is deactivated after sync"):
            with session_should_expire(**credentials):
                ldap_ad.deactivate_user(ldap_user["dn"])
                _run_sync(sdk_client_fs)
                user.reread()
                assert not user.is_active, 'User should be deactivated'
                expect_api_error('login as deactivated user', ADCMClient, **credentials)

    def test_user_deleted(self, sdk_client_fs, ldap_ad, ldap_user_in_group):
        """Test that user is deleted in ADCM after it's deleted in AD"""
        credentials = {
            "user": ldap_user_in_group["name"],
            "password": ldap_user_in_group["password"],
            "url": sdk_client_fs.url,
        }
        with allure.step("Run sync and check that user is active and can log in"):
            _run_sync(sdk_client_fs)

            check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
            expect_no_api_error("login as LDAP user", ADCMClient, **credentials)
        with allure.step("Delete user in LDAP and check access denied"):
            with session_should_expire(**credentials):
                ldap_ad.delete(ldap_user_in_group["dn"])
                _run_sync(sdk_client_fs)
                check_existing_users(sdk_client_fs, {ldap_user_in_group['name']})
                user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group['name'])
                assert not user.is_active, 'User should be deactivated'
                expect_api_error('login as deleted user', ADCMClient, **credentials)

    def test_name_email_sync_from_ldap(self, sdk_client_fs, ldap_ad, ldap_user_in_group):
        """Test that first/last name and email are synced with LDAP"""
        new_user_info = {"first_name": "Babaika", "last_name": "Labadaika", "email": "doesnt@ex.ist"}
        _run_sync(sdk_client_fs)
        user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group["name"])
        self._check_user_info(user, ldap_user_in_group)
        ldap_ad.update_user(ldap_user_in_group["dn"], **new_user_info)
        _run_sync(sdk_client_fs)
        self._check_user_info(user, new_user_info)

    @allure.issue("https://tracker.yandex.ru/ADCM-3019")
    def test_sync_when_group_itself_is_group_search_base(self, sdk_client_fs, ldap_user_in_group, ldap_group):
        """Test sync when group_search_base is set directly to LDAP group with one user"""
        ldap_group_name = ldap_group["name"]
        with allure.step(f"Set LDAP group_search_base to {ldap_group['dn']}"):
            sdk_client_fs.adcm().config_set_diff(
                {"ldap_integration": {"group_search_base": ldap_group["dn"], "sync_interval": 0}},
                attach_to_allure=False,
            )
        check_existing_groups(sdk_client_fs)
        check_existing_users(sdk_client_fs)
        _run_sync(sdk_client_fs)
        check_existing_groups(sdk_client_fs, {ldap_group_name})
        check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
        with allure.step("Check LDAP user is in LDAP group"):
            users = get_ldap_group_from_adcm(sdk_client_fs, ldap_group_name).user_list()
            assert len(users) == 1, "LDAP group should have exactly 1 user"
            assert (actual := users[0].username) == (
                expected := ldap_user_in_group["name"]
            ), f"Incorrect LDAP user name.\nExpected: {expected}\nActual: {actual}"

    def _check_user_info(self, user: User, user_ldap_info: dict):
        user.reread()
        for field_name in ("first_name", "last_name", "email"):
            actual = getattr(user, field_name)
            expected = user_ldap_info[field_name]
            assert actual == expected, f'Field "{field_name}" is incorrect.\nExpected: {expected}\nActual: {actual}'

    def _simple_sync(self, sdk_client_fs, ldap_group, ldap_user_in_group, expected_local_users):
        check_existing_users(sdk_client_fs, expected_local=expected_local_users)
        check_existing_groups(sdk_client_fs)
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]}, expected_local=expected_local_users)
        check_existing_groups(sdk_client_fs, {ldap_group["name"]})


class TestPeriodicSync:
    """Test that periodic LDAP synchronization tasks are launched correctly"""

    def test_sync_periodic_launch(self, sdk_client_fs, ad_config, ldap_basic_ous):
        """Test that sync task is launched periodically with correct settings"""
        groups_ou, users_ou = ldap_basic_ous

        with allure.step("Turn ADCM LDAP config on"):
            configure_adcm_for_ldap(sdk_client_fs, ad_config, False, None, users_ou, groups_ou, {"sync_interval": 1})

        with allure.step("Check that 1 minute after the config has been saved the sync task was launched"):
            assert len(sdk_client_fs.job_list()) == 0, "There should not be any jobs right after config is saved"
            wait_until_step_succeeds(self._check_sync_task_is_presented, timeout=70, period=5, client=sdk_client_fs)

        with allure.step("Check that after 1 more minute the second sync task was launched"):
            wait_until_step_succeeds(
                self._check_sync_task_is_presented, timeout=70, period=5, client=sdk_client_fs, expected_amount=2
            )

        with allure.step("Disable sync in settings and check no new task was launched"):
            configure_adcm_for_ldap(sdk_client_fs, ad_config, False, None, users_ou, groups_ou, {"sync_interval": 0})
            # this won't check for an error like "we didn't take last non-zero value as a wrong interval",
            # so if you'll have some more detailed check in mind, please use it
            time.sleep(65)
            self._check_sync_task_is_presented(sdk_client_fs, 2)

    def _check_sync_task_is_presented(self, client: ADCMClient, expected_amount: int = 1):
        with allure.step(f"Check {expected_amount} sync task(s) is presented among tasks"):
            sync_tasks = [
                task for task in (j.task() for j in client.job_list()) if task.action().name == SYNC_ACTION_NAME
            ]
            assert (
                actual_amount := len(sync_tasks)
            ) == expected_amount, f"Not enough sync tasks: {actual_amount}.\nExpected: {expected_amount}"


@contextmanager
def session_should_expire(user: str, password: str, url: str):
    """Check that session expires"""
    with allure.step("Login via API"):
        client = ADCMClient(url=url, user=user, password=password)
    with requests.Session() as session:
        with allure.step("Get session cookies"):
            response = session.post(f"{url}/api/v1/rbac/token/", json={"username": user, "password": password})
            assert response.status_code == 200, "Clusters page should be available"
        yield
        with allure.step('Check session is "over"'):
            response = session.get(f"{url}/api/v1/cluster")
            assert response.status_code == 401, "Request to ADCM should fail with 401 status"
    with allure.step("Check call via client is considered unauthorized"):
        with pytest.raises(ErrorMessage) as e:
            client.cluster_list()
        try:
            assert "401 Unauthorized" in e.value.error.title, "Operation should fail with 401 code"
        except (KeyError, AttributeError) as err:
            raise AssertionError(
                f"Operation should fail as an unauthorized one\nBut check was failed due to {err}\n"
            ) from err


@allure.step("Run LDAP sync action")
def _run_sync(client: ADCMClient):
    action = client.adcm().action(name=SYNC_ACTION_NAME)
    wait_for_task_and_assert_result(action.run(), "success")


@allure.step("Run successful test connection")
def _test_connection(client: ADCMClient):
    wait_for_task_and_assert_result(client.adcm().action(name=TEST_CONNECTION_ACTION).run(), "success")


def _check_task_logs_amount(client: ADCMClient, amount: int):
    client.reread()
    with allure.step(f"Check that user {client.me().username} can see {amount} tasks"):
        tasks = tuple(j.task() for j in client.job_list())
        assert len(tasks) == amount, f"Incorrect amount of tasks is available for user {client.me().username}"
