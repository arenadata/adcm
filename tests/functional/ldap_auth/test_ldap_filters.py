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


import allure
import pytest
from adcm_client.objects import ADCMClient, Group, User
from adcm_pytest_plugin.utils import random_string

from tests.functional.ldap_auth.utils import (
    DEFAULT_LOCAL_USERS,
    check_existing_groups,
    check_existing_users,
    check_users_in_group,
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
    login_should_fail,
    login_should_succeed,
    turn_off_periodic_ldap_sync,
)
from tests.library.assertions import sets_are_equal
from tests.library.ldap_interactions import change_adcm_ldap_config, sync_adcm_with_ldap

# pylint: disable=redefined-outer-name


pytestmark = [pytest.mark.ldap()]
UserInfo = dict
GroupInfo = dict


@pytest.fixture()
def two_adcm_groups_with_users(sdk_client_fs) -> tuple[Group, User, Group, User]:
    """Method to create ADCM users ADCM groups and add users to groups"""
    adcm_user_1 = sdk_client_fs.user_create("first-adcm-user", random_string(12))
    adcm_user_2 = sdk_client_fs.user_create("second-adcm-user", random_string(12))
    adcm_group_1 = sdk_client_fs.group_create("first-adcm-group")
    adcm_group_2 = sdk_client_fs.group_create("second-adcm-group")
    adcm_group_1.add_user(adcm_user_1)
    adcm_group_2.add_user(adcm_user_2)
    return adcm_group_1, adcm_user_1, adcm_group_2, adcm_user_2


@pytest.fixture()
def two_ldap_groups_with_users(ldap_ad, ldap_basic_ous) -> tuple[GroupInfo, UserInfo, GroupInfo, UserInfo]:
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


def check_sync_with_filters(
    client: ADCMClient,
    user_filter: str,
    group_filter: str,
    expected_users: set,
    expected_groups: set,
) -> None:
    """Method to use filter and check result"""
    change_adcm_ldap_config(
        client,
        attach_to_allure=False,
        user_search_filter=user_filter,
        group_search_filter=group_filter,
    )
    sync_adcm_with_ldap(client)

    active_users_records = {u.username for u in client.user_list() if u.type == "ldap" and u.is_active}
    groups_records = {g.name for g in client.group_list() if g.type == "ldap"}
    sets_are_equal(
        actual=active_users_records,
        expected=expected_users,
        message="Not all filtered active LDAP users are presented in ADCM",
    )
    sets_are_equal(
        actual=groups_records,
        expected=expected_groups,
        message="Not all filtered LDAP groups are presented in ADCM",
    )


@pytest.mark.usefixtures("configure_adcm_ldap_ad")
# pylint: disable-next=too-many-locals,too-many-statements
def test_search_filters_users(sdk_client_fs, two_ldap_groups_with_users):
    """Check LDAP filters for users"""
    turn_off_periodic_ldap_sync(client=sdk_client_fs)
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users

    check_sync_with_filters(
        sdk_client_fs,
        user_filter="",
        group_filter="",
        expected_users={user_info_1["name"], user_info_2["name"]},
        expected_groups={group_info_1["name"], group_info_2["name"]},
    )

    ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
    ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])

    with allure.step("Check filter for one user and check"):
        search_filter = f"(&(objectcategory=person)(objectclass=person)(name={ldap_user_1.username}))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter=search_filter,
            group_filter="",
            expected_users={ldap_user_1.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check filter for incorrect name user and check"):
        search_filter = "(&(objectcategory=person)(objectclass=person)(name=user))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter=search_filter,
            group_filter="",
            expected_users=set(),
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check filter for all users and check"):
        search_filter = "(&(objectcategory=person)(objectclass=person)(name=*))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter=search_filter,
            group_filter="",
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check existing LDAP and ADCM users"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check both LDAP users can login"):
        for user_info in (user_info_1, user_info_2):
            login_should_succeed(
                f'login as {user_info["name"]}',
                sdk_client_fs,
                user_info["name"],
                user_info["password"],
            )


@pytest.mark.usefixtures("configure_adcm_ldap_ad")
# pylint: disable-next=too-many-arguments, too-many-locals, too-many-statements
def test_search_filters_groups(sdk_client_fs, two_adcm_groups_with_users, two_ldap_groups_with_users):
    """Check LDAP filters for groups"""
    turn_off_periodic_ldap_sync(client=sdk_client_fs)
    adcm_group_1, adcm_user_1, adcm_group_2, adcm_user_2 = two_adcm_groups_with_users
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users

    with allure.step("Sync and add LDAP users to ADCM groups"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={user_info_1["name"], user_info_2["name"]},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

        ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1["name"])
        ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2["name"])
        ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
        ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])

        adcm_group_1.add_user(ldap_user_1)
        adcm_group_2.add_user(ldap_user_2)

        adcm_user_names = {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS}

    with allure.step("Check that users are in groups"):
        check_users_in_group(ldap_group_1, ldap_user_1)
        check_users_in_group(ldap_group_2, ldap_user_2)
        check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)

    with allure.step("Check filter for one group and check"):
        search_filter = f"(&(objectclass=group)(name={ldap_group_1.name}))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter=search_filter,
            expected_users={ldap_user_1.username},
            expected_groups={ldap_group_1.name},
        )

    with allure.step("Check filter for all groups and check"):
        search_filter = "(&(objectclass=group)(name=*))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter=search_filter,
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={ldap_group_1.name, ldap_group_2.name},
        )

    with allure.step("Check existing LDAP and ADCM groups"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

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

    check_users_in_group(ldap_group_1, ldap_user_1)
    check_users_in_group(ldap_group_2, ldap_user_2)
    check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
    check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)


@pytest.mark.usefixtures("configure_adcm_ldap_ad")
# pylint: disable-next=too-many-locals,too-many-statements
def test_search_filters_groups_with_symbols(sdk_client_fs, two_adcm_groups_with_users, two_ldap_groups_with_users):
    """Check LDAP filters for users and groups"""
    turn_off_periodic_ldap_sync(client=sdk_client_fs)

    adcm_group_1, adcm_user_1, adcm_group_2, adcm_user_2 = two_adcm_groups_with_users
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users

    with allure.step("Sync and add LDAP users to ADCM groups"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={user_info_1["name"], user_info_2["name"]},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

        ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1["name"])
        ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2["name"])
        ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
        ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])

        adcm_group_1.add_user(ldap_user_1)
        adcm_group_2.add_user(ldap_user_2)

        adcm_user_names = {adcm_user_1.username, adcm_user_2.username, *DEFAULT_LOCAL_USERS}

    with allure.step("Check that users are in groups"):
        check_users_in_group(ldap_group_1, ldap_user_1)
        check_users_in_group(ldap_group_2, ldap_user_2)
        check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)

    with allure.step("Check filter with filter symbol !"):
        search_filter = "(&(name=*user*)(!(name=*2*)))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter=search_filter,
            expected_users={ldap_user_1.username},
            expected_groups={ldap_group_1.name},
        )

    with allure.step("Check filter with filter symbols >="):
        turn_off_periodic_ldap_sync(client=sdk_client_fs)
        search_filter = "(&(name>=t))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter=search_filter,
            expected_users=set(),
            expected_groups=set(),
        )

    with allure.step("Check filter with filter symbols <="):
        turn_off_periodic_ldap_sync(client=sdk_client_fs)
        search_filter = "(&(name<=t))"
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter=search_filter,
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check existing LDAP and ADCM users and groups"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={ldap_user_1.username, ldap_user_2.username},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

    with allure.step("Check that users are in groups"):
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

        check_users_in_group(ldap_group_1, ldap_user_1)
        check_users_in_group(ldap_group_2, ldap_user_2)
        check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)

    with allure.step("Check both LDAP users can login"):
        for user_info in (user_info_1, user_info_2):
            login_should_succeed(
                f'login as {user_info["name"]}',
                sdk_client_fs,
                user_info["name"],
                user_info["password"],
            )


@pytest.mark.usefixtures("configure_adcm_ldap_ad")
# pylint: disable-next=too-many-arguments, too-many-locals, too-many-statements
def test_search_filters_login_users(sdk_client_fs, two_adcm_groups_with_users, two_ldap_groups_with_users):
    """Check LDAP filters for users login"""
    turn_off_periodic_ldap_sync(client=sdk_client_fs)

    adcm_group_1, adcm_user_1, adcm_group_2, adcm_user_2 = two_adcm_groups_with_users
    group_info_1, user_info_1, group_info_2, user_info_2 = two_ldap_groups_with_users

    with allure.step("Sync and add LDAP users to ADCM groups"):
        check_sync_with_filters(
            sdk_client_fs,
            user_filter="",
            group_filter="",
            expected_users={user_info_1["name"], user_info_2["name"]},
            expected_groups={group_info_1["name"], group_info_2["name"]},
        )

        ldap_group_1 = get_ldap_group_from_adcm(sdk_client_fs, group_info_1["name"])
        ldap_group_2 = get_ldap_group_from_adcm(sdk_client_fs, group_info_2["name"])
        ldap_user_1 = get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
        ldap_user_2 = get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])

        adcm_group_1.add_user(ldap_user_1)
        adcm_group_2.add_user(ldap_user_2)

    with allure.step("Check that users are in groups"):
        check_users_in_group(ldap_group_1, ldap_user_1)
        check_users_in_group(ldap_group_2, ldap_user_2)
        check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)

    with allure.step("Check filter for one user and check"):
        search_filter = f"(&(objectcategory=person)(objectclass=person)(name={ldap_user_1.username}))"
        change_adcm_ldap_config(
            sdk_client_fs,
            attach_to_allure=False,
            user_search_filter=search_filter,
            group_search_filter="",
        )
    with allure.step("Check LDAP user_1 can login and LDAP user_2 login fail"):
        login_should_succeed(
            f'login as {user_info_1["name"]}',
            sdk_client_fs,
            user_info_1["name"],
            user_info_1["password"],
        )
        login_should_fail(
            f'login as {user_info_2["name"]}',
            sdk_client_fs,
            user_info_2["name"],
            user_info_2["password"],
        )
    with allure.step("Check filter for one group and check"):
        search_filter = f"(&(objectclass=group)(name={ldap_group_2.name}))"
        change_adcm_ldap_config(
            sdk_client_fs,
            attach_to_allure=False,
            user_search_filter="",
            group_search_filter=search_filter,
        )

    with allure.step("Check that users are in groups"):
        get_ldap_group_from_adcm(sdk_client_fs, group_info_1["name"])
        get_ldap_group_from_adcm(sdk_client_fs, group_info_2["name"])
        get_ldap_user_from_adcm(sdk_client_fs, user_info_1["name"])
        get_ldap_user_from_adcm(sdk_client_fs, user_info_2["name"])

        check_users_in_group(ldap_group_1, ldap_user_1)
        check_users_in_group(ldap_group_2, ldap_user_2)
        check_users_in_group(adcm_group_1, adcm_user_1, ldap_user_1)
        check_users_in_group(adcm_group_2, adcm_user_2, ldap_user_2)

    with allure.step("Check LDAP user from filtered group can login and LDAP user_1 login fail"):
        login_should_succeed(
            f'login as {user_info_2["name"]}',
            sdk_client_fs,
            user_info_2["name"],
            user_info_2["password"],
        )
        login_should_fail(
            f'login as {user_info_1["name"]}',
            sdk_client_fs,
            user_info_1["name"],
            user_info_1["password"],
        )
