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

from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage


def test_check_login_to_adcm(app_fs, adcm_credentials):
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.check_all_elements()
    login_page.login_user(**adcm_credentials)
    with allure.step("Check if user has been authorized"):
        intro_page = AdminIntroPage(app_fs.driver, app_fs.adcm.url)
        login_page.wait_url_contains_path(intro_page.path)
        login_page.wait_config_loaded()
        assert intro_page.path in app_fs.driver.current_url, f"Page '{intro_page.path}' has not been opened"
        intro_page.header.check_auth_page_elements()


@pytest.mark.parametrize(("name", "password"), [("", "admin"), ("admin", "")], ids=("no_name", "no_password"))
def test_check_login_button_unavailable(app_fs, name, password):
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.fill_login_user_form(name, password)
    login_page.check_check_login_button_unavailable()


@pytest.mark.parametrize(
    ("name", "password"),
    [("admin1", "admin"), ("admin", "admin1")],
    ids=("wrong_name", "wrong_pass"),
)
def test_check_error_in_login(app_fs, name, password):
    params = {"error_text": "Incorrect password or user."}
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.login_user(name, password)
    login_page.check_error_message(params["error_text"])


def test_check_header_links_in_login_page_unauthorised(app_fs):
    params = {"error_text": "User is not authorized!"}
    login_page = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login_page.header.click_arenadata_logo_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_cluster_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_hostproviders_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_hosts_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_jobs_tab_in_header()
    login_page.check_error_message(params["error_text"])
    login_page.header.click_bundles_tab_in_header()
    login_page.check_error_message(params["error_text"])
