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

"""UI Tests for /login page"""

import allure
import pytest
from adcm_pytest_plugin.params import including_https
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage


@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_check_login_to_adcm(app_fs, adcm_credentials):
    """Test basic success UI login"""
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.check_all_elements()
    login_page.login_user(**adcm_credentials)
    with allure.step("Check if user has been authorized"):
        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        intro_page.wait_page_is_opened()
        # investigate why profile marker can't be found
        # login_page.wait_config_loaded()
        intro_page.header.check_auth_page_elements()


@pytest.mark.ldap()
@including_https
@pytest.mark.parametrize("configure_adcm_ldap_ad", [False, True], ids=["ssl-off", "ssl-on"], indirect=True)
@pytest.mark.usefixtures("configure_adcm_ldap_ad")
def test_login_as_ldap_user(app_fs, ldap_user_in_group):
    """Test successful LDAP user authentication"""
    username, password = ldap_user_in_group["name"], ldap_user_in_group["password"]
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.login_user(username, password)
    with allure.step("Check if LDAP user has been authorized"):
        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        intro_page.wait_page_is_opened()
        intro_page.header.check_auth_page_elements()


@pytest.mark.parametrize(("name", "password"), [("", "admin"), ("admin", "")], ids=("no_name", "no_password"))
def test_check_login_button_unavailable(app_fs, name, password):
    """Test that login button is unavailable for given conditions"""
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.fill_login_user_form(name, password)
    login_page.check_check_login_button_unavailable()


@pytest.mark.smoke()
@pytest.mark.include_firefox()
@pytest.mark.parametrize(
    ("name", "password"),
    [("admin1", "admin"), ("admin", "admin1")],
    ids=("wrong_name", "wrong_pass"),
)
def test_check_error_in_login(app_fs, name, password):
    """Test basic UI login with invalid credentials"""
    params = {"error_text": "Incorrect password or user."}
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.login_user(name, password)
    login_page.check_error_message(params["error_text"])


@pytest.mark.smoke()
@pytest.mark.include_firefox()
def test_check_header_links_in_login_page_unauthorised(app_fs):
    """Test header for unauthorised user"""
    params = {"error_text": "User is not authorized!"}
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.header.click_arenadata_logo_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_clusters_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_hostproviders_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_hosts_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_jobs_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_bundles_tab_in_header()
    login_page.check_error_message(params["error_text"])
