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

from typing import Set, Tuple

import allure
import pytest
from adcm_client.objects import ADCMClient, Group, User
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import random_string

from tests.functional.ldap_auth.utils import (
    DEFAULT_LOCAL_USERS,
    SYNC_ACTION_NAME,
    check_existing_groups,
    check_existing_users,
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
    login_should_fail,
    login_should_succeed,
)

# pylint: disable=redefined-outer-name

UserInfo = dict
GroupInfo = dict

pytestmark = [pytest.mark.ldap()]


@pytest.fixture()
def two_ldap_groups_with_users(ldap_ad, ldap_basic_ous) -> Tuple[GroupInfo, UserInfo, GroupInfo, UserInfo]:
    """Create two ldap users and groups with a user in each one"""
    groups_ou, users_ou = ldap_basic_ous
    group_1 = {"name": "group-with-users-1"}
    group_2 = {"name": "group-with-users-2"}
    user_1 = {"name": f"user-1-{random_string(4)}-in-group", "password": random_string(12)}
    user_2 = {"name": f"user-2-{random_string(4)}-in-group", "password": random_string(12)}
    user_1["dn"] = ldap_ad.create_user(**user_1, custom_base_dn=users_ou)
    user_2["dn"] = ldap_ad.create_user(**user_2, custom_base_dn=users_ou)
    group_1["dn"] = ldap_ad.create_group(**group_1, custom_base_dn=groups_ou)
    ldap_ad.add_user_to_group(user_1["dn"], group_1["dn"])
    group_2["dn"] = ldap_ad.create_group(**group_2, custom_base_dn=groups_ou)
    ldap_ad.add_user_to_group(user_2["dn"], group_2["dn"])
    return group_1, user_1, group_2, user_2


@pytest.fixture()
def two_ldap_users(ldap_ad, ldap_basic_ous) -> Tuple[UserInfo, UserInfo]:
    """Create two ldap user that're not in any group"""
    _, users_ou = ldap_basic_ous
    user_1 = {"name": f"user-3-{random_string(4)}", "password": random_string(12)}
    user_2 = {"name": f"user-4-{random_string(4)}", "password": random_string(12)}
    user_1["dn"] = ldap_ad.create_user(**user_1, custom_base_dn=users_ou)
    user_2["dn"] = ldap_ad.create_user(**user_2, custom_base_dn=users_ou)
    return user_1, user_2


@pytest.fixture()
def two_adcm_users(sdk_client_fs) -> Tuple[User, User]:
    """Create two ADCM users"""
    return (
        sdk_client_fs.user_create("first-adcm-user", random_string(12)),
        sdk_client_fs.user_create("second-adcm-user", random_string(12)),
    )


@pytest.fixture()
def two_adcm_groups(sdk_client_fs) -> Tuple[Group, Group]:
    """Create two ADCM groups"""
    return sdk_client_fs.group_create("first-adcm-group"), sdk_client_fs.group_create("second-adcm-group")


@pytest.mark.usefixtures(
    "configure_adcm_ldap_ad", "two_ldap_users"
)  # pylint: disable-next=too-many-locals,too-many-statements
def test_users_in_groups_sync(
    sdk_client_fs,
    ldap_ad,
    two_adcm_users,
    two_adcm_groups,
    two_ldap_users,
    two_ldap_groups_with_users,
):
    """
    Test ADCM/LDAP users in groups manipulation and sync.
    """
    sdk_client_fs.adcm().config_set_diff({"ldap_integration": {"sync_interval": 0}})
    adcm_user_1, adcm_user_2 = two_adcm_users
    adcm_user_names = {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS}
    adcm_group_1, adcm_group_2 = two_adcm_groups
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users
    user_info_3, _ = two_ldap_users

    with allure.step("Add ADCM users to ADCM groups"):
        adcm_group_1.add_user(adcm_user_1)
        adcm_group_2.add_user(adcm_user_2)
    with allure.step("Sync and add LDAP users to ADCM groups"):
        _run_sync(sdk_client_fs)
        check_existing_groups(
            sdk_client_fs,
            {group_info_1["name"], group_info_2["name"]},
            {adcm_group_1.name, adcm_group_2.name},
        )
        check_existing_users(sdk_client_fs, {user_info_1["name"], user_info_2["name"]}, adcm_user_names)
        ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1["name"])
        ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2["name"])
        ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
        ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])
        adcm_group_1.add_user(ldap_user_1)
        adcm_group_2.add_user(ldap_user_2)
        _check_users_in_group(ldap_group_1, ldap_user_1)
        _check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        _check_users_in_group(ldap_group_2, ldap_user_2)
        _check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)
    with allure.step("Check both LDAP users can login"):
        for user_info in (user_info_1, user_info_2):
            _check_login_succeed(sdk_client_fs, user_info)
    with allure.step("Swap LDAP users in LDAP groups"):
        ldap_ad.remove_user_from_group(user_info_1["dn"], group_info_1["dn"])
        ldap_ad.add_user_to_group(user_info_1["dn"], group_info_2["dn"])
        ldap_ad.remove_user_from_group(user_info_2["dn"], group_info_2["dn"])
        ldap_ad.add_user_to_group(user_info_2["dn"], group_info_1["dn"])
    with allure.step("Sync and check groups"):
        _run_sync(sdk_client_fs)
        check_existing_groups(
            sdk_client_fs,
            {group_info_1["name"], group_info_2["name"]},
            {adcm_group_1.name, adcm_group_2.name},
        )
        check_existing_users(sdk_client_fs, {user_info_1["name"], user_info_2["name"]}, adcm_user_names)
        _check_users_in_group(ldap_group_1, ldap_user_2)
        _check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        _check_users_in_group(ldap_group_2, ldap_user_1)
        _check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)
    with allure.step("Check both LDAP users can login"):
        for user_info in (user_info_1, user_info_2):
            _check_login_succeed(sdk_client_fs, user_info)
    with allure.step("Remove one LDAP user from one group"):
        ldap_ad.remove_user_from_group(user_info_2["dn"], group_info_1["dn"])
    with allure.step("Sync and check user state"):
        _run_sync(sdk_client_fs)
        check_existing_groups(
            sdk_client_fs,
            {group_info_1["name"], group_info_2["name"]},
            {adcm_group_1.name, adcm_group_2.name},
        )
        check_existing_users(sdk_client_fs, {user_info_1["name"], user_info_2["name"]}, adcm_user_names)
        assert not get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"]).is_active, "User should be deactivated"
        _check_users_in_group(ldap_group_1)
        _check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        _check_users_in_group(ldap_group_2, ldap_user_1)
        _check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)
    with allure.step("Check login permissions"):
        _check_login_succeed(sdk_client_fs, user_info_1)
        login_should_fail(
            "login as user removed from ldap groups",
            sdk_client_fs,
            user_info_2["name"],
            user_info_2["password"],
        )
    with allure.step('Add "free" LDAP user to a group, sync and check results'):
        ldap_ad.add_user_to_group(user_info_3["dn"], group_info_2["dn"])
        _run_sync(sdk_client_fs)
        check_existing_users(
            sdk_client_fs,
            {user_info_1["name"], user_info_2["name"], user_info_3["name"]},
            adcm_user_names,
        )
        ldap_user_3 = get_ldap_user_from_adcm(sdk_client_fs, user_info_3["name"])
        _check_users_in_group(ldap_group_1)
        _check_users_in_group(ldap_group_2, ldap_user_1, ldap_user_3)
        _check_login_succeed(sdk_client_fs, user_info_3)


def _check_login_succeed(client: ADCMClient, user_info: dict):
    login_should_succeed(f'login as {user_info["name"]}', client, user_info["name"], user_info["password"])


def _run_sync(client: ADCMClient):
    action = client.adcm().action(name=SYNC_ACTION_NAME)
    wait_for_task_and_assert_result(action.run(), "success")


def _check_users_in_group(group: Group, *users: User):
    assert {u.username for u in users} == _get_usernames_in_group(group), f"Incorrect user list in group {group.name}"


def _get_usernames_in_group(group: Group) -> Set[str]:
    group.reread()
    return {u.username for u in group.user_list()}
