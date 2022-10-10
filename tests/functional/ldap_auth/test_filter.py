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

"""Test designed to check LDAP filters"""

from typing import Set

import allure
import pytest
from adcm_client.objects import ADCMClient, Group, User
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import random_string

from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import (
    SYNC_ACTION_NAME,
    check_existing_groups,
    login_should_succeed,
)

# pylint: disable=redefined-outer-name

UserInfo = dict
GroupInfo = dict

pytestmark = [pytest.mark.ldap(), only_clean_adcm]


def create_adcm_users(sdk_client_fs: ADCMClient, user_name: str) -> User:
    """Create ADCM user"""
    return sdk_client_fs.user_create(user_name, random_string(12))


def create_adcm_group(sdk_client_fs: ADCMClient, group_name: str) -> Group:
    """Create ADCM group"""
    return sdk_client_fs.group_create(group_name)


def create_ldap_user(ldap_ad, user_name, users_ou) -> UserInfo:
    """Create LDAP user"""
    user = {'name': user_name, 'password': random_string(12)}
    user['dn'] = ldap_ad.create_user(**user, custom_base_dn=users_ou)
    return user


def create_ldap_group(ldap_ad, group_name, groups_ou) -> GroupInfo:
    """Create LDAP user"""
    group = {'name': group_name}
    group['dn'] = ldap_ad.create_group(**group, custom_base_dn=groups_ou)
    return group


def add_user_to_group_ldap(ldap_ad, user_dn, group_dn) -> None:
    """Add LDAP user to LDAP group"""
    ldap_ad.add_user_to_group(user_dn, group_dn)


@pytest.mark.usefixtures('configure_adcm_ldap_ad')
# pylint: disable-next=too-many-arguments, too-many-locals, too-many-statements
def test_filter(sdk_client_fs, ldap_ad, ldap_basic_ous):
    """
    Test designed to check LDAP filters
    Scenario:
    Step 1. Create ADCM 2 user and 1 ADCM group
    Step 2. Add 1 ADCM user to ADCM group
    Step 3. Create 2 LDAP users and 2 LDAP groups
    Step 4. Add first LDAP user to both LDAP groups add second LDAP user to 1 group
    Step 5. Check filters to search by LDAP groups
    Step 6. Check filters to search by LDAP users
    """
    # Create ADCM users and group
    sdk_client_fs.adcm().config_set_diff({'ldap_integration': {'sync_interval': 0}})
    adcm_user_1 = create_adcm_users(sdk_client_fs, 'first-adcm-user')
    adcm_user_2 = create_adcm_users(sdk_client_fs, 'second-adcm-user')
    adcm_group_1 = create_adcm_group(sdk_client_fs, 'first-adcm-group')

    # Create LDAP users and group
    groups_ou, users_ou = ldap_basic_ous
    ldap_user_1 = create_ldap_user(ldap_ad, f'user-1-{random_string(4)}-in-group', users_ou)
    ldap_group_1 = create_ldap_group(ldap_ad, 'group-with-users-1', groups_ou)
    add_user_to_group_ldap(ldap_ad, ldap_user_1['dn'], ldap_group_1['dn'])

    ldap_user_2 = create_ldap_user(ldap_ad, f'user-2-{random_string(4)}-in-group', users_ou)
    ldap_group_2 = create_ldap_group(ldap_ad, 'group-with-users-2', groups_ou)
    add_user_to_group_ldap(ldap_ad, ldap_user_2['dn'], ldap_group_2['dn'])
    add_user_to_group_ldap(ldap_ad, ldap_user_1['dn'], ldap_group_2['dn'])

    with allure.step('Add ADCM users to ADCM groups'):
        adcm_group_1.add_user(adcm_user_1)
    with allure.step('Sync and add LDAP users to ADCM groups'):
        _run_sync(sdk_client_fs)
        check_existing_groups(sdk_client_fs,
                              {ldap_group_1['name'], ldap_group_2['name']},
                              {adcm_group_1.name})

    with allure.step("Create user and deactivate it"):
        filter_str = f"(&(objectcategory=person)(objectclass=person)(name={ldap_user_1}))"
        res = ldap_ad.set_filter(base=ldap_user_1['dn'], filterstr=filter_str)

        # check_existing_users(sdk_client_fs, {user_info_1['name'], user_info_2['name']}, adcm_user_names)
        # ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1['name'])
        # ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2['name'])
        # ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1['name'])
        # ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2['name'])
        # adcm_group_1.add_user(ldap_user_1)
        # adcm_group_2.add_user(ldap_user_2)
        # _check_users_in_group(ldap_group_1, ldap_user_1)
        # _check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        # _check_users_in_group(ldap_group_2, ldap_user_2)
        # _check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)


def _check_login_succeed(client: ADCMClient, user_info: dict):
    login_should_succeed(f'login as {user_info["name"]}', client, user_info['name'], user_info['password'])


def _run_sync(client: ADCMClient):
    action = client.adcm().action(name=SYNC_ACTION_NAME)
    wait_for_task_and_assert_result(action.run(), 'success')


def _check_users_in_group(group: Group, *users: User):
    assert {u.username for u in users} == _get_usernames_in_group(group), f'Incorrect user list in group {group.name}'


def _get_usernames_in_group(group: Group) -> Set[str]:
    group.reread()
    return {u.username for u in group.user_list()}
