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

import allure
import pytest
from adcm_client.objects import ADCMClient
from adcm_pytest_plugin.steps.actions import wait_for_task_and_assert_result

from tests.functional.conftest import only_clean_adcm
from tests.functional.ldap_auth.utils import get_ldap_user_from_adcm, SYNC_ACTION_NAME
from tests.library.assertions import expect_api_error, expect_no_api_error
from tests.library.errorcodes import USER_UPDATE_ERROR

pytestmark = [only_clean_adcm, pytest.mark.usefixtures('configure_adcm_ldap_ad')]


def test_ldap_user_manual_modification_is_forbidden(sdk_client_fs, ldap_user):
    """
    Test that users came from LDAP can't be modified by ADCM local admins
    """
    with allure.step('Sync users and retrieve LDAP user and group from ADCM'):
        wait_for_task_and_assert_result(sdk_client_fs.adcm().action(name=SYNC_ACTION_NAME).run(), 'success')
        user = get_ldap_user_from_adcm(sdk_client_fs, ldap_user['name'])

    for attr in ('first_name', 'last_name', 'email', 'username'):
        with allure.step(f'Check that changing {attr} of user is forbidden for LDAP user'):
            original_value = getattr(user, attr)
            changed_value = f'px-{original_value}'
            expect_api_error(f'change {attr} of a user', user.update, **{attr: changed_value}, err_=USER_UPDATE_ERROR)
            user.reread()
            assert getattr(user, attr) == original_value, 'Value should not be changed'

    with allure.step('Check that changing password for LDAP user is forbidden'):
        new_password = f'px-{ldap_user["password"]}'
        expect_api_error('change password of a user', user.change_password, new_password,  err_=USER_UPDATE_ERROR)
        expect_api_error(
            'login with "new" password', ADCMClient, url=sdk_client_fs.url, user=user.username, password=new_password
        )
        expect_no_api_error(
            'login with "original LDAP" password',
            ADCMClient,
            url=sdk_client_fs.url,
            user=user.username,
            password=ldap_user['password'],
        )

    with allure.step('Check that LDAP user cannot be deleted'):
        expect_api_error('delete LDAP user', user.delete)
