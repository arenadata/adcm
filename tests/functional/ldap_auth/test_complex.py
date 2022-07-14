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

"""Test complex scenarios with ADCM LDAP integration"""

from typing import Tuple

import allure
import pytest
from adcm_client.objects import User, Group, ADCMClient
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import random_string

from tests.functional.ldap_auth.utils import (
    get_ldap_user_from_adcm,
    SYNC_ACTION_NAME,
    get_ldap_group_from_adcm,
    check_existing_groups,
    check_existing_users,
    DEFAULT_LOCAL_USERS,
)

UserInfo = dict
GroupInfo = dict


@pytest.fixture()
def two_ldap_groups_with_users(ldap_ad, ldap_basic_ous) -> Tuple[GroupInfo, UserInfo, GroupInfo, UserInfo]:
    groups_ou, users_ou = ldap_basic_ous
    group_1 = {'name': 'group-with-users-1'}
    group_2 = {'name': 'group-with-users-2'}
    user_1 = {'name': f'user-1-{random_string(4)}-in-group', 'password': random_string(12)}
    user_2 = {'name': f'user-2-{random_string(4)}-in-group', 'password': random_string(12)}
    user_1['dn'] = ldap_ad.create_user(**user_1, custom_base_dn=users_ou)
    user_2['dn'] = ldap_ad.create_user(**user_2, custom_base_dn=users_ou)
    group_1['dn'] = ldap_ad.create_group(**group_1, custom_base_dn=groups_ou)
    ldap_ad.add_user_to_group(user_1['dn'], group_1['dn'])
    group_2['dn'] = ldap_ad.create_group(**group_2, custom_base_dn=groups_ou)
    ldap_ad.add_user_to_group(user_2['dn'], group_2['dn'])
    return group_1, user_1, group_2, user_2


@pytest.fixture()
def two_ldap_users(ldap_ad, ldap_basic_ous) -> Tuple[UserInfo, UserInfo]:
    _, users_ou = ldap_basic_ous
    user_1 = {'name': f'user-3-{random_string(4)}', 'password': random_string(12)}
    user_2 = {'name': f'user-4-{random_string(4)}', 'password': random_string(12)}
    user_1['dn'] = ldap_ad.create_user(**user_1, custom_base_dn=users_ou)
    user_2['dn'] = ldap_ad.create_user(**user_2, custom_base_dn=users_ou)
    return user_1, user_2


@pytest.fixture()
def two_adcm_users(sdk_client_fs) -> Tuple[User, User]:
    return (
        sdk_client_fs.user_create('first-adcm-user', random_string(12)),
        sdk_client_fs.user_create('second-adcm-user', random_string(12)),
    )


@pytest.fixture()
def two_adcm_groups(sdk_client_fs) -> Tuple[Group, Group]:
    return sdk_client_fs.group_create('first-adcm-group'), sdk_client_fs.group_create('second-adcm-group')


@pytest.mark.usefixtures('configure_adcm_ldap_ad')
def test_users_in_groups_sync(
    sdk_client_fs, ldap_ad, two_adcm_users, two_adcm_groups, two_ldap_users, two_ldap_groups_with_users
):
    adcm_user_1, adcm_user_2 = two_adcm_users
    adcm_group_1, adcm_group_2 = two_adcm_groups
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users

    with allure.step('Add ADCM users to ADCM groups'):
        adcm_group_1.add_user(adcm_user_1)
        adcm_group_2.add_user(adcm_user_2)
    with allure.step('Sync and add LDAP users to ADCM groups'):
        _run_sync(sdk_client_fs)
        check_existing_groups(
            sdk_client_fs, {group_info_1['name'], group_info_2['name']}, {adcm_group_1.name, adcm_group_2.name}
        )
        check_existing_users(
            sdk_client_fs,
            {user_info_1['name'], user_info_2['name']},
            {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS},
        )
        ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1['name'])
        ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2['name'])
        ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1['name'])
        ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2['name'])
        adcm_group_1.add_user(ldap_user_1)
        adcm_group_2.add_user(ldap_user_2)
        # TODO add messages and groupin methods?
        assert {ldap_user_1.username} == {u.username for u in ldap_group_1.user_list()}
        assert {adcm_user_1.username, ldap_user_1.username} == {u.username for u in adcm_group_1.user_list()}
        assert {ldap_user_2.username} == {u.username for u in ldap_group_2.user_list()}
        assert {adcm_user_2.username, ldap_user_2.username} == {u.username for u in adcm_group_2.user_list()}
    with allure.step('Swap LDAP users in LDAP groups'):
        ldap_ad.remove_user_from_group(user_info_1['dn'], group_info_1['dn'])
        ldap_ad.add_user_to_group(user_info_1['dn'], group_info_2['dn'])
        ldap_ad.remove_user_from_group(user_info_2['dn'], group_info_2['dn'])
        ldap_ad.add_user_to_group(user_info_2['dn'], group_info_1['dn'])
    with allure.step('Sync and check groups'):
        _run_sync(sdk_client_fs)
        check_existing_groups(
            sdk_client_fs, {group_info_1['name'], group_info_2['name']}, {adcm_group_1.name, adcm_group_2.name}
        )
        check_existing_users(
            sdk_client_fs,
            {user_info_1['name'], user_info_2['name']},
            {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS},
        )
        assert {ldap_user_2.username} == {u.username for u in ldap_group_1.user_list()}
        assert {adcm_user_1.username, ldap_user_1.username} == {u.username for u in adcm_group_1.user_list()}
        assert {ldap_user_1.username} == {u.username for u in ldap_group_2.user_list()}
        assert {adcm_user_2.username, ldap_user_2.username} == {u.username for u in adcm_group_2.user_list()}
        # TODO add checks
    with allure.step('Remove one LDAP user from one group'):
        ldap_ad.remove_user_from_group(user_info_2['dn'], group_info_1['dn'])
    with allure.step('Sync and check user state'):
        check_existing_groups(
            sdk_client_fs, {group_info_1['name'], group_info_2['name']}, {adcm_group_1.name, adcm_group_2.name}
        )
        check_existing_users(
            sdk_client_fs,
            {user_info_1['name'], user_info_2['name']},
            {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS},
        )
        assert len(ldap_group_1.user_list()) == 0
        assert {adcm_user_1.username, ldap_user_1.username} == {u.username for u in adcm_group_1.user_list()}
        assert {ldap_user_1.username} == {u.username for u in ldap_group_2.user_list()}
        assert {adcm_user_2.username, ldap_user_2.username} == {u.username for u in adcm_group_2.user_list()}

    # TODO add checks


def _run_sync(client: ADCMClient):
    action = client.adcm().action(name=SYNC_ACTION_NAME)
    wait_for_task_and_assert_result(action.run(), 'success')
