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

"""Test LDAP integration when group_search_base isn't provided"""

import allure
import pytest
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from tests.functional.ldap_auth.utils import (
    SYNC_ACTION_NAME,
    check_existing_groups,
    check_existing_users,
    get_ldap_group_from_adcm,
    login_should_succeed,
)
from tests.library.ldap_interactions import configure_adcm_for_ldap

pytestmark = [pytest.mark.ldap()]


@pytest.fixture()
def _configure_adcm(sdk_client_fs, ad_config, ldap_basic_ous):
    """Configure LDAP settings in ADCM and turn off LDAP sync"""
    _, users_ou = ldap_basic_ous
    configure_adcm_for_ldap(sdk_client_fs, ad_config, False, None, users_ou, None)
    sdk_client_fs.adcm().config_set_diff({"ldap_integration": {"sync_interval": 0}})


@pytest.mark.usefixtures("_configure_adcm", "another_ldap_group")
def test_login_no_group_base(sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group):
    """
    Test that users with or without LDAP group can log in and their groups are created
    """
    login_should_succeed("login as ldap user not in group", sdk_client_fs, ldap_user["name"], ldap_user["password"])
    check_existing_users(sdk_client_fs, [ldap_user["name"]])
    check_existing_groups(sdk_client_fs)
    login_should_succeed(
        "login as ldap user in group",
        sdk_client_fs,
        ldap_user_in_group["name"],
        ldap_user_in_group["password"],
    )
    _check_correct_objects_came_from_ldap(sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group)


@pytest.mark.usefixtures("_configure_adcm", "another_ldap_group")
def test_sync_no_group_base(sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group):
    """
    Test that sync without specified LDAP group_search_base works correctly:
    users are synced and only their groups are created in ADCM
    """
    wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name=SYNC_ACTION_NAME).run(), "success")
    _check_correct_objects_came_from_ldap(sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group)


def _check_correct_objects_came_from_ldap(sdk_client_fs, ldap_user, ldap_user_in_group, ldap_group):
    user_in_group_name = ldap_user_in_group["name"]
    check_existing_users(sdk_client_fs, [ldap_user["name"], user_in_group_name])
    check_existing_groups(sdk_client_fs, [ldap_group["name"]])
    with allure.step("Check group from LDAP"):
        users_in_group = get_ldap_group_from_adcm(sdk_client_fs, ldap_group["name"]).user_list()
        assert len(users_in_group) == 1, "Exactly 1 user should be in group from ldap"
        assert (
            actual := users_in_group[0].username
        ) == user_in_group_name, f"Incorrect username in group.\nExpected: {user_in_group_name}\nActual: {actual}"
