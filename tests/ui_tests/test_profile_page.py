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

"""UI tests for /profile page"""

import pytest
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.page.profile.page import ProfilePage

# pylint: disable=redefined-outer-name
pytestmark = [
    pytest.mark.smoke(),
    pytest.mark.include_firefox(),
    pytest.mark.usefixtures('_login_to_adcm_over_api'),
]


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
    profile_page.check_username(params['username'])


def test_login_as_new_user(another_user: dict, app_fs: ADCMTest):
    """Login as admin, logout, login as another user, check username"""
    params = {'admin_username': 'admin', 'another_username': another_user['username']}
    profile_page = ProfilePage(app_fs.driver, app_fs.adcm.url).open()
    profile_page.check_username(params['admin_username'])
    profile_page.header.logout()
    login_page = LoginPage(profile_page.driver, profile_page.base_url)
    login_page.wait_page_is_opened()
    login_page.login_user(**another_user)
    intro_page = AdminIntroPage(profile_page.driver, profile_page.base_url)
    intro_page.wait_config_loaded()
    intro_page.header.open_profile()
    profile_page.wait_page_is_opened()
    profile_page.check_required_fields_are_presented()
    profile_page.check_username(another_user['username'])


def test_change_password(adcm_credentials: dict, app_fs: ADCMTest):
    """Change admin password over UI and login under new credentials"""
    new_credentials = {**adcm_credentials, 'password': 'new_password'}
    profile_page = ProfilePage(app_fs.driver, app_fs.adcm.url).open()
    profile_page.set_new_password(new_credentials['password'])
    login_page = LoginPage(profile_page.driver, profile_page.base_url)
    login_page.wait_page_is_opened()
    login_page.login_user(**new_credentials)
    intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
    intro_page.wait_config_loaded()
    intro_page.header.open_profile()
    profile_page.wait_page_is_opened()
    profile_page.check_required_fields_are_presented()
    profile_page.check_username(adcm_credentials['username'])
