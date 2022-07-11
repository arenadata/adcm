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

from contextlib import contextmanager
from typing import Collection, Optional, Tuple

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Group, ADCM, User
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import (
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
    TEST_CONNECTION_ACTION,
    SYNC_ACTION_NAME,
)
from tests.library.assertions import sets_are_equal, expect_no_api_error, expect_api_error
from tests.library.errorcodes import UNAUTHORIZED
from tests.library.ldap_interactions import LDAPTestConfig, configure_adcm_for_ldap


DEFAULT_LOCAL_USERS = ('admin', 'status')


pytestmark = [only_clean_adcm]


class TestDisablingCause:
    """Test LDAP-related ADCM actions have correct disabling cause"""

    DISABLING_CAUSE = 'no_ldap_settings'

    def test_ldap_connection_test_disabling_cause(self, sdk_client_fs, ad_config, ldap_basic_ous):
        """Test that disabling cause is set right for "test_ldap_connection" action"""
        adcm = sdk_client_fs.adcm()

        with allure.step('Check that with default settings disabling cause is set'):
            self._check_disabling_cause(adcm, self.DISABLING_CAUSE)
        with allure.step('Set correct LDAP settings and check disabling cause is None'):
            self._set_ldap_settings(sdk_client_fs, ad_config, ldap_basic_ous)
            self._check_disabling_cause(adcm, None)
        with allure.step('Disable LDAP settings and check disabling cause is set'):
            adcm.config_set_diff({'attr': {'ldap_integration': {'active': False}}})
            self._check_disabling_cause(adcm, self.DISABLING_CAUSE)

    def _check_disabling_cause(self, adcm: ADCM, expected: Optional[str]):
        # retrieve each time to avoid rereading
        sync = adcm.action(name=SYNC_ACTION_NAME)
        test_connection = adcm.action(name=TEST_CONNECTION_ACTION)
        assert (
            sync.disabling_cause == expected
        ), f'Sync action has incorrect disabling cause: {sync.disabling_cause}.\nExpected: {expected}'
        assert test_connection.disabling_cause == expected, (
            f'Test connection action has incorrect disabling cause: {test_connection.disabling_cause}.\n'
            f'Expected: {expected}'
        )

    def _set_ldap_settings(self, client: ADCMClient, config: LDAPTestConfig, ous: Tuple[str, str]):
        groups_ou, users_ou = ous
        configure_adcm_for_ldap(client, config, False, None, users_ou, groups_ou)


class TestLDAPSyncAction:
    """Test LDAP sync action"""

    pytestmark = [pytest.mark.usefixtures('configure_adcm_ldap_ad')]

    def test_ldap_simple_sync(self, sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group):
        """Test that LDAP sync action pulls users and groups from LDAP"""
        check_existing_users(sdk_client_fs)
        check_existing_groups(sdk_client_fs)
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user['name'], ldap_user_in_group['name']})
        check_existing_groups(sdk_client_fs, {ldap_group['name']})

    def test_sync_with_already_existing_group(self, sdk_client_fs, ldap_user_in_group, ldap_group):
        """Test that when LDAP group have a local group with the same name, there won't be a conflict"""
        with allure.step('Create group with the name of LDAP group'):
            local_group: Group = sdk_client_fs.group_create(name=ldap_group['name'])
        check_existing_users(sdk_client_fs)
        check_existing_groups(sdk_client_fs, expected_local={local_group.name})
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group['name']})
        check_existing_groups(sdk_client_fs, {ldap_group['name']}, {local_group.name})
        local_group.reread()
        assert len(local_group.user_list()) == 0, 'There should not be any user in local group'
        ldap_group_in_adcm = get_ldap_group_from_adcm(sdk_client_fs, ldap_group['name'])
        assert ldap_user_in_group['name'] in [
            u.username for u in ldap_group_in_adcm.user_list()
        ], f'Group from LDAP should have user {ldap_user_in_group["name"]}'

    # pylint: disable-next=too-many-arguments
    def test_ldap_group_removed(self, sdk_client_fs, ldap_ad, ldap_group, ldap_user, ldap_user_in_group):
        """Test LDAP group removed from ADCM after it's removed from LDAP"""
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group['name'], ldap_user['name']})
        check_existing_groups(sdk_client_fs, {ldap_group['name']})
        with allure.step('Delete group from LDAP'):
            ldap_ad.delete(ldap_group['dn'])
        _run_sync(sdk_client_fs)
        check_existing_users(sdk_client_fs, {ldap_user_in_group['name'], ldap_user['name']})
        check_existing_groups(sdk_client_fs)

    # pylint: disable-next=too-many-arguments
    def test_user_removed_from_group(self, sdk_client_fs, ldap_ad, ldap_group, ldap_user_in_group, ldap_user):
        """Test that when user is removed from group in AD, it is also removed in ADCM's LDAP group"""
        another_group: Group = sdk_client_fs.group_create('Another group')
        _run_sync(sdk_client_fs)
        with allure.step('Add LDAP users to the local group'):
            user_in_group = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group['name'])
            simple_user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user['name'])
            group = get_ldap_group_from_adcm(sdk_client_fs, ldap_group['name'])
            another_group.add_user(user_in_group)
            another_group.add_user(simple_user)
        with allure.step('Remove user in AD from LDAP group and rerun sync'):
            ldap_ad.remove_user_from_group(ldap_user_in_group['dn'], ldap_group['dn'])
            _run_sync(sdk_client_fs)
        with allure.step('Check user was removed only from LDAP group'):
            check_existing_users(sdk_client_fs, {ldap_user['name'], ldap_user_in_group['name']})
            check_existing_groups(sdk_client_fs, {ldap_group['name']}, {another_group.name})
            group.reread()
            assert len(group.user_list()) == 0, 'Group from LDAP should be empty'
            another_group.reread()
            assert len(another_group.user_list()) == 2, 'Local group should still have both users in it'

    def test_user_deactivated(self, sdk_client_fs, ldap_ad, ldap_user):
        """Test that user is deactivated in ADCM after it's deactivated in AD"""
        credentials = {'user': ldap_user['name'], 'password': ldap_user['password'], 'url': sdk_client_fs.url}
        with allure.step('Run sync and check that user is active and can log in'):
            _run_sync(sdk_client_fs)
            user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user['name'])
            assert user.is_active, 'User should be active'
            expect_no_api_error('login as LDAP active user', ADCMClient, **credentials)
        with allure.step('Deactivate user in LDAP and check it is deactivated after sync'):
            with session_should_expire(**credentials):
                ldap_ad.deactivate_user(ldap_user['dn'])
                _run_sync(sdk_client_fs)
                user.reread()
                assert not user.is_active, 'User should be deactivated'
                expect_api_error('login as deactivated user', ADCMClient, **credentials)

    def test_user_deleted(self, sdk_client_fs, ldap_ad, ldap_user):
        """Test that user is deleted in ADCM after it's deleted in AD"""
        credentials = {'user': ldap_user['name'], 'password': ldap_user['password'], 'url': sdk_client_fs.url}
        with allure.step('Run sync and check that user is active and can log in'):
            _run_sync(sdk_client_fs)

            check_existing_users(sdk_client_fs, {ldap_user['name']})
            expect_no_api_error('login as LDAP user', ADCMClient, **credentials)
        with allure.step('Delete user in LDAP and check access denied'):
            with session_should_expire(**credentials):
                ldap_ad.delete(ldap_user['dn'])
                _run_sync(sdk_client_fs)
                check_existing_users(sdk_client_fs)
                expect_api_error('login as deleted user', ADCMClient, **credentials)

    def test_name_email_sync_from_ldap(self, sdk_client_fs, ldap_ad, ldap_user_in_group):
        """Test that first/last name and email are synced with LDAP"""
        new_user_info = {'first_name': 'Babaika', 'last_name': 'Labadaika', 'email': 'doesnt@ex.ist'}
        _run_sync(sdk_client_fs)
        user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group['name'])
        self._check_user_info(user, ldap_user_in_group)
        ldap_ad.update_user(ldap_user_in_group['dn'], **new_user_info)
        _run_sync(sdk_client_fs)
        self._check_user_info(user, new_user_info)

    def _check_user_info(self, user: User, user_ldap_info: dict):
        user.reread()
        for field_name in ('first_name', 'last_name', 'email'):
            actual = getattr(user, field_name)
            expected = user_ldap_info[field_name]
            assert actual == expected, f'Field "{field_name}" is incorrect.\nExpected: {expected}\nActual: {actual}'


class TestPeriodicSync:
    """Test that periodic LDAP synchronization tasks are launched correctly"""

    def test_sync_periodic_launch(self, sdk_client_fs, ad_config, ldap_basic_ous):
        """Test that sync task is launched periodically with correct settings"""
        groups_ou, users_ou = ldap_basic_ous

        with allure.step('Turn ADCM LDAP config on'):
            configure_adcm_for_ldap(sdk_client_fs, ad_config, False, None, users_ou, groups_ou, {'sync_interval': 1})

        with allure.step('Check that 1 minute after the config has been saved the sync task was launched'):
            assert len(sdk_client_fs.job_list()) == 0, 'There should not be any jobs right after config is saved'
            wait_until_step_succeeds(self._check_sync_task_is_presented, timeout=70, period=7, client=sdk_client_fs)

        with allure.step('Check that after 1 more minute the second sync task was launched'):
            wait_until_step_succeeds(
                self._check_sync_task_is_presented, timeout=70, period=7, client=sdk_client_fs, expected_amount=2
            )

    def _check_sync_task_is_presented(self, client: ADCMClient, expected_amount: int = 1):
        with allure.step(f'Check {expected_amount} sync task(s) is presented among tasks'):
            sync_tasks = [
                task for task in (j.task() for j in client.job_list()) if task.action().name == SYNC_ACTION_NAME
            ]
            assert (
                actual_amount := len(sync_tasks)
            ) == expected_amount, f'Not enough sync tasks: {actual_amount}.\nExpected: {expected_amount}'


@allure.step('Check users existing in ADCM')
def check_existing_users(
    client: ADCMClient, expected_ldap: Collection[str] = (), expected_local: Collection[str] = DEFAULT_LOCAL_USERS
):
    """Check that only provided users exists (both ldap and local)"""
    expected_ldap = set(expected_ldap)
    existing_ldap = {u.username for u in client.user_list() if u.type == 'ldap'}
    expected_local = set(expected_local)
    existing_local = {u.username for u in client.user_list() if u.type == 'local'}
    with allure.step('Check users from LDAP'):
        sets_are_equal(existing_ldap, expected_ldap)
    with allure.step('Check local users'):
        sets_are_equal(existing_local, expected_local)


@allure.step('Check groups existing in ADCM')
def check_existing_groups(
    client: ADCMClient, expected_ldap: Collection[str] = (), expected_local: Collection[str] = ()
):
    """Check that only provided groups exists (both ldap and local)"""
    expected_ldap = set(expected_ldap)
    existing_ldap = {g.name for g in client.group_list() if g.type == 'ldap'}
    expected_local = set(expected_local)
    existing_local = {g.name for g in client.group_list() if g.type == 'local'}
    with allure.step('Check groups from LDAP'):
        sets_are_equal(existing_ldap, expected_ldap, message='Not all LDAP groups are presented in ADCM')
    with allure.step('Check local groups'):
        sets_are_equal(existing_local, expected_local, message='Not all local groups are presented in ADCM')


@contextmanager
def session_should_expire(user: str, password: str, url: str):
    """Check that session expires"""
    with allure.step('Login via API'):
        client = ADCMClient(url=url, user=user, password=password)
    with requests.Session() as session:
        with allure.step('Get session cookies'):
            response = session.post(f'{url}/api/v1/rbac/token/', json={'username': user, 'password': password})
            assert response.status_code == 200, 'Clusters page should be available'
        yield
        with allure.step('Check session is "over"'):
            response = session.get(f'{url}/api/v1/cluster')
            assert response.status_code == 401, 'Request to ADCM should fail with 401 status'
    with allure.step('Check call via client is considered unauthorized'):
        expect_api_error('get cluster list', client.cluster_list, err_=UNAUTHORIZED)


@allure.step('Run LDAP sync action')
def _run_sync(client: ADCMClient):
    action = client.adcm().action(name=SYNC_ACTION_NAME)
    wait_for_task_and_assert_result(action.run(), 'success')


@allure.step('Run successful test connection')
def _test_connection(client: ADCMClient):
    wait_for_task_and_assert_result(client.adcm().action(name=TEST_CONNECTION_ACTION).run(), 'success')
