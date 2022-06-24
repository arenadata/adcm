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

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.params import including_https
from adcm_pytest_plugin.utils import random_string

from tests.functional.conftest import only_clean_adcm
from tests.library.assertions import expect_no_api_error, expect_api_error
from tests.library.errorcodes import UNAUTHORIZED

pytestmark = [only_clean_adcm, pytest.mark.usefixtures('configure_adcm_ldap_ad')]


@pytest.mark.xfail(reason="Expected behavior isn't finally decided: https://tracker.yandex.ru/ADCM-2916")
def test_basic_ldap_auth(sdk_client_fs, ldap_user, ldap_user_in_group):
    """
    Test basic scenarios of LDAP auth:
    1. Login of user in "correct" group is permitted
    2. Login of user not in group is not permitted
    """
    _login_should_succeed(
        'login with LDAP user in group', sdk_client_fs, ldap_user_in_group['name'], ldap_user_in_group['password']
    )
    _login_should_fail(
        'login with LDAP user not in allowed group', sdk_client_fs, ldap_user['name'], ldap_user['password']
    )


@including_https
@pytest.mark.xfail(reason="Expected behavior isn't finally decided: https://tracker.yandex.ru/ADCM-2916")
def test_remove_from_group_leads_to_access_loss(sdk_client_fs, ldap_ad, ldap_user_in_group, ldap_group):
    """
    Test that removing LDAP user from "allowed" group leads to lost access to ADCM.
    """
    username, password = ldap_user_in_group['name'], ldap_user_in_group['password']
    _login_should_succeed('login with LDAP user in group', sdk_client_fs, username, password)
    ldap_ad.remove_user_from_group(ldap_user_in_group['dn'], ldap_group['dn'])
    _login_should_fail('login with removed from group LDAP user', sdk_client_fs, username, password)


@including_https
def test_deactivation_leads_to_access_loss(sdk_client_fs, ldap_ad, ldap_user_in_group):
    """
    Test that LDAP user deactivation leads to lost access to ADCM.
    """
    username, password = ldap_user_in_group['name'], ldap_user_in_group['password']
    _login_should_succeed('login with LDAP user in group', sdk_client_fs, username, password)
    ldap_ad.deactivate_user(ldap_user_in_group['dn'])
    _login_should_fail('login with removed from group LDAP user', sdk_client_fs, username, password, None)


@pytest.mark.xfail(reason="Expected behavior isn't finally decided: https://tracker.yandex.ru/ADCM-2916")
def test_ldap_user_access_restriction(sdk_client_fs, ldap_ad, ldap_group, ldap_basic_ous):
    """
    Test that access is denied for LDAP user:
    - inactive not in group
    - inactive in group
    - in group, but with "old" password
    - active and not in group
    """
    username, password = f'testUser-{random_string(6)}', 'awesomepass'
    new_password = 'anotherpassword'
    _, users_ou = ldap_basic_ous

    with allure.step('Create user and deactivate it'):
        user_dn = ldap_ad.create_user(username, password, users_ou)
        ldap_ad.deactivate_user(user_dn)
    _login_should_fail('login as deactivated user not in group', sdk_client_fs, username, password, None)
    ldap_ad.add_user_to_group(user_dn, ldap_group['dn'])
    _login_should_fail('login as deactivated user in group', sdk_client_fs, username, password, None)
    ldap_ad.activate_user(user_dn)
    _login_should_succeed('login as activated user in group', sdk_client_fs, username, password)
    ldap_ad.set_user_password(user_dn, new_password)
    # TODO: return after https://tracker.yandex.ru/ADCM-2916 is resolved
    # _login_should_fail('login as activated user with wrong password', sdk_client_fs, username, password, None)
    _login_should_succeed('login as activated user with new password', sdk_client_fs, username, new_password)
    ldap_ad.remove_user_from_group(user_dn, ldap_group['dn'])
    _login_should_fail('login as user removed from group', sdk_client_fs, username, new_password, None)


def _login_should_succeed(operation_name: str, client: ADCMClient, username: str, password: str):
    with allure.step(operation_name.capitalize()):
        expect_no_api_error(
            operation_name,
            ADCMClient,
            url=client.url,
            user=username,
            password=password,
        )


def _login_should_fail(operation_name: str, client: ADCMClient, username: str, password: str, err=UNAUTHORIZED):
    with allure.step(operation_name.capitalize()):
        expect_api_error(
            operation_name,
            ADCMClient,
            err_=err,
            url=client.url,
            user=username,
            password=password,
        )
