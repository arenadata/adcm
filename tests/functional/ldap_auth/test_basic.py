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

"""Test basic login scenarios"""

from typing import Callable, Union

import allure
import pytest
from adcm_client.objects import ADCMClient, User
from adcm_pytest_plugin.params import including_https
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result
from adcm_pytest_plugin.utils import random_string
from tests.functional.ldap_auth.utils import (
    DEFAULT_LOCAL_USERS,
    LDAP_ACTION_CAN_NOT_START_REASON,
    check_existing_groups,
    check_existing_users,
    get_ldap_group_from_adcm,
    login_should_fail,
    login_should_succeed,
)

pytestmark = [
    pytest.mark.usefixtures("configure_adcm_ldap_ad"),
    pytest.mark.ldap(),
]


@pytest.mark.parametrize("configure_adcm_ldap_ad", [False, True], ids=["ssl_off", "ssl_on"], indirect=True)
def test_basic_ldap_auth(sdk_client_fs, ldap_user, ldap_user_in_group):
    """
    Test basic scenarios of LDAP auth:
    1. Login of user in "correct" group is permitted
    2. Login of user not in group is not permitted
    """
    login_should_succeed(
        "login with LDAP user in group",
        sdk_client_fs,
        ldap_user_in_group["name"],
        ldap_user_in_group["password"],
    )
    login_should_fail(
        "login with LDAP user not in allowed group",
        sdk_client_fs,
        ldap_user["name"],
        ldap_user["password"],
    )


@including_https
def test_remove_from_group_leads_to_access_loss(sdk_client_fs, ldap_ad, ldap_user_in_group, ldap_group):
    """
    Test that removing LDAP user from "allowed" group leads to lost access to ADCM.
    """
    username, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    login_should_succeed("login with LDAP user in group", sdk_client_fs, username, password)
    ldap_ad.remove_user_from_group(ldap_user_in_group["dn"], ldap_group["dn"])
    login_should_fail("login with removed from group LDAP user", sdk_client_fs, username, password)


@including_https
def test_deactivation_leads_to_access_loss(sdk_client_fs, ldap_ad, ldap_user_in_group):
    """
    Test that LDAP user deactivation leads to lost access to ADCM.
    """
    username, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    login_should_succeed("login with LDAP user in group", sdk_client_fs, username, password)
    ldap_ad.deactivate_user(ldap_user_in_group["dn"])
    login_should_fail("login with removed from group LDAP user", sdk_client_fs, username, password)


def test_ldap_user_access_restriction(sdk_client_fs, ldap_ad, ldap_group, ldap_basic_ous):
    """
    Test that access is denied for LDAP user:
    - inactive not in group
    - inactive in group
    - in group, but with "old" password
    - active and not in group
    """
    username, password = f"testUser-{random_string(6)}", "awesomepass"
    new_password = "anotherpassword"
    _, users_ou = ldap_basic_ous

    with allure.step("Create user and deactivate it"):
        user_dn = ldap_ad.create_user(username, password, users_ou)
        ldap_ad.deactivate_user(user_dn)
    login_should_fail("login as deactivated user not in group", sdk_client_fs, username, password)
    ldap_ad.add_user_to_group(user_dn, ldap_group["dn"])
    login_should_fail("login as deactivated user in group", sdk_client_fs, username, password)
    ldap_ad.activate_user(user_dn)
    login_should_succeed("login as activated user in group", sdk_client_fs, username, password)
    ldap_ad.set_user_password(user_dn, new_password)
    login_should_fail("login as activated user with wrong password", sdk_client_fs, username, password, None)
    login_should_succeed("login as activated user with new password", sdk_client_fs, username, new_password)
    ldap_ad.remove_user_from_group(user_dn, ldap_group["dn"])
    login_should_fail("login as user removed from group", sdk_client_fs, username, new_password)


@including_https
@pytest.mark.usefixtures("configure_adcm_ldap_ad")
@pytest.mark.parametrize("configure_adcm_ldap_ad", [True], ids=["ssl-on"], indirect=True)
def test_ssl_ldap_fails_with_wrong_path(sdk_client_fs, ldap_user_in_group):
    """
    Test that incorrect certificate path leads ldaps connection to fail to give the access to a user.
    """
    user, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    adcm = sdk_client_fs.adcm()

    login_should_succeed("login with LDAP user and OK config", sdk_client_fs, user, password)
    with allure.step("Set incorrect path to a file and check login fails"):
        adcm.config_set_diff({"ldap_integration": {"tls_ca_cert_file": "/does/not/exist"}})
        login_should_fail("login with LDAP user and wrong file in config", sdk_client_fs, user, password)


@including_https
@pytest.mark.usefixtures("configure_adcm_ldap_ad")
@pytest.mark.parametrize("configure_adcm_ldap_ad", [True], ids=["ssl-on"], indirect=True)
def test_ssl_ldap_fails_with_wrong_cert_content(adcm_fs, sdk_client_fs, ldap_user_in_group):
    """
    Test that incorrect certificate file content leads ldaps connection to fail to give the access to a user.
    """
    user, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    adcm = sdk_client_fs.adcm()

    login_should_succeed("login with LDAP user and OK config", sdk_client_fs, user, password)
    with allure.step("Set incorrect data to a cert file and check login fails"):
        path = adcm.config()["ldap_integration"]["tls_ca_cert_file"]
        result = adcm_fs.container.exec_run(["sh", "-c", f'echo "notacert" > {path}'])
        if result.exit_code != 0:
            raise ValueError("Failed to change certificate content")
        login_should_fail("login with LDAP user and wrong cert content", sdk_client_fs, user, password)


def _alter_user_search_base(client: ADCMClient) -> dict:
    old_base: str = client.adcm().config()["ldap_integration"]["user_search_base"]
    new_base = f"CN=notexist-{old_base[3:]}"
    return {"ldap_integration": {"user_search_base": new_base}}


_wrong_user_password = (
    ("wrong user", {"ldap_integration": {"ldap_user": "!#)F(JDKSLJ"}}),
    ("wrong password", {"ldap_integration": {"ldap_password": random_string(6)}}),
)

_deactivate_ldap_integration = (
    "LDAP config turned off",
    {"attr": {"ldap_integration": {"active": False}}},
)


@pytest.mark.parametrize(
    ("change_name", "config"),
    [_deactivate_ldap_integration, *_wrong_user_password],
    ids=lambda x: x.replace(" ", "_") if isinstance(x, str) else x,
)
def test_ldap_config_change(change_name: str, config: Union[dict, Callable], sdk_client_fs, ldap_user_in_group):
    """Test that changing ldap config to "incorrect" leads to users access loss"""
    login_operation = "login as LDAP user"
    user, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    adcm = sdk_client_fs.adcm()

    login_should_succeed(login_operation, sdk_client_fs, user, password)
    with allure.step(f"Check login is disabled after: {change_name}"):
        config = config if not callable(config) else config(sdk_client_fs)
        adcm.config_set_diff(config)
        login_should_fail(login_operation, sdk_client_fs, user, password)


@pytest.mark.parametrize("action_name", ["test_ldap_connection", "run_ldap_sync"])
def test_wrong_ldap_config_fail_actions(action_name: str, sdk_client_fs):
    """Test that incorrect/turned off LDAP configuration leads ldap-related actions to have disabling cause"""
    adcm = sdk_client_fs.adcm()
    original_config = adcm.config()
    for change_name, config in _wrong_user_password:
        with allure.step(f"Change LDAP config: {change_name}; and expect {action_name} to fail"):
            adcm.config_set_diff(config)
            task = adcm.action(name=action_name).run()
            wait_for_task_and_assert_result(task, "failed")
            adcm.config_set_diff(original_config)
            task.wait()
    with allure.step(f"Deactivate LDAP integration in settings and check action {action_name} is disabled"):
        adcm.config_set_diff(_deactivate_ldap_integration[1])
        assert action_name in [
            a.name for a in adcm.action_list() if LDAP_ACTION_CAN_NOT_START_REASON in a.start_impossible_reason
        ], f'Action {action_name} should have "{LDAP_ACTION_CAN_NOT_START_REASON}" as the reason for disabled launch'


def test_login_as_existing_user_is_forbidden(sdk_client_fs, ldap_user_in_group):
    """Test that login as existing user doesn't create user"""
    local_password = random_string(16)
    expected_local_users = (*DEFAULT_LOCAL_USERS, ldap_user_in_group["name"])
    with allure.step("Create user with the name of LDAP user"):
        local_user: User = sdk_client_fs.user_create(ldap_user_in_group["name"], local_password)
    check_existing_users(sdk_client_fs, expected_local=expected_local_users)
    check_existing_groups(sdk_client_fs)
    login_should_succeed("local user login", sdk_client_fs, local_user.username, local_password)
    login_should_fail(
        "login as LDAP user with same username as local",
        sdk_client_fs,
        ldap_user_in_group["name"],
        ldap_user_in_group["password"],
    )
    local_user.reread()
    with allure.step("Check user is of local type"):
        assert local_user.type == "local", 'User type should be "local"'
    check_existing_users(sdk_client_fs, expected_local=expected_local_users)
    check_existing_groups(sdk_client_fs)


@allure.issue("https://tracker.yandex.ru/ADCM-3019")
def test_login_when_group_itself_is_group_search_base(
    sdk_client_fs, ldap_user, ldap_user_in_group, another_ldap_user_in_group, ldap_group
):
    """Test login when group_search_base is set directly to LDAP group with one user"""
    ldap_group_name = ldap_group["name"]
    with allure.step(f"Set LDAP group_search_base to {ldap_group['dn']}"):
        sdk_client_fs.adcm().config_set_diff(
            {"ldap_integration": {"group_search_base": ldap_group["dn"], "sync_interval": 0}},
            attach_to_allure=False,
        )
    check_existing_groups(sdk_client_fs)
    check_existing_users(sdk_client_fs)
    login_should_succeed(
        "login as user in group",
        sdk_client_fs,
        ldap_user_in_group["name"],
        ldap_user_in_group["password"],
    )
    check_existing_groups(sdk_client_fs, {ldap_group_name})
    check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
    with allure.step("Check LDAP user is in LDAP group"):
        users = get_ldap_group_from_adcm(sdk_client_fs, ldap_group_name).user_list()
        assert len(users) == 1, "LDAP group should have exactly 1 user"
        assert (actual := users[0].username) == (
            expected := ldap_user_in_group["name"]
        ), f"Incorrect LDAP user name.\nExpected: {expected}\nActual: {actual}"
    for disallowed_user in (ldap_user, another_ldap_user_in_group):
        login_should_fail(
            f"login as {disallowed_user['name']}",
            sdk_client_fs,
            disallowed_user["name"],
            disallowed_user["password"],
        )
    check_existing_groups(sdk_client_fs, {ldap_group_name})
    check_existing_users(sdk_client_fs, {ldap_user_in_group["name"]})
