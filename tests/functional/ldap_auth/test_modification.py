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

"""Test modification of ldap-related entities"""

from typing import Union

import allure
import pytest
from adcm_client.objects import ADCMClient, Group, User
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result

from tests.functional.ldap_auth.utils import (
    SYNC_ACTION_NAME,
    TEST_CONNECTION_ACTION,
    get_ldap_group_from_adcm,
    get_ldap_user_from_adcm,
)
from tests.library.assertions import expect_api_error, expect_no_api_error
from tests.library.errorcodes import GROUP_UPDATE_ERROR, USER_UPDATE_ERROR

# pylint: disable=redefined-outer-name

pytestmark = [
    pytest.mark.usefixtures("configure_adcm_ldap_ad"),
    pytest.mark.ldap(),
]


@pytest.fixture()
def local_user(sdk_client_fs) -> User:
    """Create ADCM user"""
    return sdk_client_fs.user_create("Uma", "Uma" * 12)


@pytest.fixture()
def local_group(sdk_client_fs) -> Group:
    """Create ADCM group"""
    return sdk_client_fs.group_create("Book club")


def test_ldap_user_manual_modification_is_forbidden(sdk_client_fs, ldap_user_in_group):
    """
    Test that users came from LDAP can't be modified by ADCM local admins
    """
    with allure.step("Sync with LDAP and retrieve LDAP user from ADCM"):
        _sync_with_ldap(sdk_client_fs)
        user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group["name"])

    for attr in ("first_name", "last_name", "email", "username"):
        _check_change_is_forbidden(user, attr)

    with allure.step("Check that changing password for LDAP user is forbidden"):
        new_password = f'px-{ldap_user_in_group["password"]}'
        expect_api_error("change password of a user", user.change_password, new_password, err_=USER_UPDATE_ERROR)
        expect_api_error(
            'login with "new" password',
            ADCMClient,
            url=sdk_client_fs.url,
            user=user.username,
            password=new_password,
        )
        expect_no_api_error(
            'login with "original LDAP" password',
            ADCMClient,
            url=sdk_client_fs.url,
            user=user.username,
            password=ldap_user_in_group["password"],
        )


@pytest.mark.usefixtures("ldap_user_in_group")
def test_ldap_group_manual_modification_is_forbidden(sdk_client_fs, ldap_group):
    """
    Test that groups came from LDAP can't be modified by ADCM local admins
    """
    with allure.step("Sync with LDAP and retrieve LDAP group from ADCM"):
        _sync_with_ldap(sdk_client_fs)
        group = get_ldap_group_from_adcm(sdk_client_fs, ldap_group["name"])

    for attr in ("name", "description"):
        _check_change_is_forbidden(group, attr)


def test_membership(
    sdk_client_fs,
    local_user,
    local_group,
    ldap_group,
    ldap_user_in_group,
    another_ldap_user_in_group,
):
    """
    Test that LDAP user can be added to local groups, but not to LDAP ones in ADCM.
    And that no user can be added to an LDAP group in ADCM.
    """
    with allure.step("Sync with LDAP and retrieve user and group"):
        _sync_with_ldap(sdk_client_fs)
        user_from_ldap = get_ldap_user_from_adcm(sdk_client_fs, ldap_user_in_group["name"])
        another_user_form_ldap = get_ldap_user_from_adcm(sdk_client_fs, another_ldap_user_in_group["name"])
        group_from_ldap = get_ldap_group_from_adcm(sdk_client_fs, ldap_group["name"])

    expect_no_api_error("add LDAP user to a local group", local_group.add_user, user=user_from_ldap)
    expect_api_error("add local user to an LDAP group", group_from_ldap.add_user, user=local_user)
    expect_api_error("add LDAP user to an LDAP group", group_from_ldap.add_user, user=another_user_form_ldap)


def _sync_with_ldap(client: ADCMClient):
    wait_for_task_and_assert_result(client.adcm().action(name=TEST_CONNECTION_ACTION).run(), "success")
    wait_for_task_and_assert_result(client.adcm().action(name=SYNC_ACTION_NAME).run(), "success")


def _check_change_is_forbidden(entity: Union[User, Group], attr: str):
    entity_class = entity.__class__.__name__
    with allure.step(f"Check that changing {attr} of {entity_class} is forbidden for LDAP {entity_class}"):
        err = USER_UPDATE_ERROR if isinstance(entity, User) else GROUP_UPDATE_ERROR
        original_value = getattr(entity, attr)
        changed_value = f"px-{original_value}"
        expect_api_error(f"change {attr} of a {entity_class}", entity.update, **{attr: changed_value}, err_=err)
        entity.reread()
        assert getattr(entity, attr) == original_value, "Value should not be changed"
