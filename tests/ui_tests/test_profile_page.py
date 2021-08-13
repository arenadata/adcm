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
import allure
import pytest

from adcm_pytest_plugin.utils import wait_until_step_succeeds

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.profile.page import ProfilePage
from tests.ui_tests.utils import restore_admin_password

# pylint: disable=redefined-outer-name


@pytest.mark.usefixtures("login_to_adcm_over_api")
def test_open_profile(app_fs: ADCMTest):
    """
    Open profile page via UI elements, check username is correct and required fields presented
    """
    params = {'username': 'admin'}
    intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
    intro_page.header.open_profile()
    profile_page = ProfilePage(intro_page.driver, intro_page.base_url)
    profile_page.wait_page_is_opened()
    profile_page.check_required_fields_are_presented()
    _assert_username_on_profile_page(profile_page, params['username'])


@pytest.mark.usefixtures("login_to_adcm_over_api")
def test_login_as_new_user(another_user: dict, app_fs: ADCMTest):
    """Login as admin, logout, login as another user, check username"""
    params = {'admin_username': 'admin', 'another_username': another_user['username']}
    profile_page = ProfilePage(app_fs.driver, app_fs.adcm.url).open()
    _assert_username_on_profile_page(profile_page, params['admin_username'])
    profile_page.header.logout()
    login_page = LoginPage(profile_page.driver, profile_page.base_url)
    login_page.wait_page_is_opened()
    login_page.login_user(**another_user)
    intro_page = AdminIntroPage(profile_page.driver, profile_page.base_url)
    intro_page.wait_config_loaded()
    intro_page.header.open_profile()
    profile_page.wait_page_is_opened()
    profile_page.check_required_fields_are_presented()
    _assert_username_on_profile_page(profile_page, another_user['username'])


@pytest.mark.usefixtures("login_to_adcm_over_api")
def test_change_password(adcm_credentials: dict, app_fs: ADCMTest):
    """Change admin password over UI and login under new credentials"""
    new_password = 'password'
    profile_page = ProfilePage(app_fs.driver, app_fs.adcm.url).open()
    with restore_admin_password(new_password, adcm_credentials, app_fs.adcm.url) as new_credentials:
        profile_page.set_new_password(new_password)
        login_page = LoginPage(profile_page.driver, profile_page.base_url)
        login_page.wait_page_is_opened()
        login_page.login_user(**new_credentials)
        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        intro_page.wait_config_loaded()
        intro_page.header.open_profile()
        profile_page.wait_page_is_opened()
        profile_page.check_required_fields_are_presented()
        _assert_username_on_profile_page(profile_page, adcm_credentials['username'])


@allure.step('Check username on profile page is {expected_username}')
def _assert_username_on_profile_page(page: ProfilePage, expected_username: str):
    """Wait"""

    def check_username_on_profile_page():
        assert (
            username := page.get_username()
        ) == expected_username, f'Expected username is {expected_username}, got {username} instead'

    wait_until_step_succeeds(check_username_on_profile_page, timeout=5, period=0.5)
