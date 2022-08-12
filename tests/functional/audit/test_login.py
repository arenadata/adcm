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

"""Test login audit logs"""

from typing import Callable

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient

from tests.functional.audit.conftest import make_auth_header


def _token_login(client: ADCMClient, username: str, password: str) -> requests.Response:
    return requests.post(f'{client.url}/api/v1/token/', json={'username': username, 'password': password})


def _rbac_token_login(client: ADCMClient, username: str, password: str) -> requests.Response:
    return requests.post(f'{client.url}/api/v1/rbac/token/', json={'username': username, 'password': password})


def _viewer_login(client: ADCMClient, username: str, password: str) -> requests.Response:
    return requests.post(f'{client.url}/api/v1/auth/login/', data={'username': username, 'password': password})


@pytest.mark.parametrize(
    'login', [_token_login, _rbac_token_login, _viewer_login], ids=['via_token', 'via_rbac_token', 'via_auth_login']
)
def test_login_audit(
    login: Callable[[ADCMClient, str, str], requests.Response], sdk_client_fs: ADCMClient, adcm_api_credentials: dict
):
    """Test audit of logins: results, details"""
    admin_username = adcm_api_credentials['user']
    not_existing_user = 'blahblah'
    expected_fields = {'id', 'user_id', 'login_result', 'login_time', 'login_details', 'url'}
    with allure.step('Correct login'):
        login(sdk_client_fs, admin_username, adcm_api_credentials['password'])
    with allure.step('Login as not existent user'):
        login(sdk_client_fs, not_existing_user, 'passwordiririri')
    with allure.step('Incorrect password'):
        login(sdk_client_fs, admin_username, adcm_api_credentials['password'] + 'alkjfelwm')
    with allure.step('Check logs are correct'):
        logins = requests.get(
            f'{sdk_client_fs.url}/api/v1/audit/login', headers=make_auth_header(sdk_client_fs)
        ).json()['results']
        assert len(logins) == 3, 'There should be exactly 3 records in login audit log'
        assert all(
            rec.keys() == expected_fields for rec in logins
        ), f'One of records have field not equal to: {", ".join(expected_fields)}'
    with allure.step('Check first successful login details'):
        first_login = logins[-1]
        assert first_login['user_id'] == sdk_client_fs.me().id, f'First login id should be {sdk_client_fs.me().id}'
        assert first_login['login_details'] is None, 'First login should not have login details'
        assert first_login['login_result'] == 'success', 'Login should succeed'
    with allure.step('Check second login failed because of user does not exist'):
        first_login = logins[-2]
        assert first_login['user_id'] is None, 'Login user_id should be None'
        assert first_login['login_details'] == {
            'username': not_existing_user
        }, f'Username in login details should be {not_existing_user}'
        assert first_login['login_result'] == 'user not found', 'Login should fail with "user not found" result'
    with allure.step('Check third login failed because of wrong password'):
        first_login = logins[-3]
        assert first_login['user_id'] is None, 'Login user_id should be None'
        assert first_login['login_details'] == {
            'username': admin_username
        }, f'Username in login details should be {not_existing_user}'
        assert first_login['login_result'] == 'wrong password', 'Login should fail with "wrong password" result'
