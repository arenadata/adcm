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

from tests.functional.conftest import only_clean_adcm
from tests.library.assertions import expect_no_api_error, expect_api_error
from tests.library.errorcodes import UNAUTHORIZED

pytestmark = [only_clean_adcm]


@pytest.mark.usefixtures('configure_adcm_ldap_ad')
def test_basic_ldap_auth(sdk_client_fs, ldap_user, ldap_user_in_group):
    """
    Test basic scenarios of LDAP auth:
    1. Login of user in "correct" group is permitted
    2. Login of user not in group is not permitted
    """
    with allure.step('Login with LDAP user in group'):
        expect_no_api_error(
            'login with LDAP user',
            lambda: ADCMClient(
                url=sdk_client_fs.url, user=ldap_user_in_group['name'], password=ldap_user_in_group['password']
            ),
        )
    with allure.step('Login with LDAP user that is not in group'):
        expect_api_error(
            'login with LDAP user not in allowed group',
            lambda: ADCMClient(url=sdk_client_fs.url, user=ldap_user['name'], password=ldap_user['password']),
            err_=UNAUTHORIZED,
        )
