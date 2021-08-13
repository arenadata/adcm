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
# pylint: disable=W0621
import json
import tempfile
import requests
import allure
import pytest

from adcm_client.wrappers.docker import ADCM
from deprecated import deprecated
from selenium.common.exceptions import WebDriverException

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.pages import LoginPage as DeprecatedLoginPage


@allure.title("Additional ADCM init config")
@pytest.fixture(
    scope="session",
    params=[
        pytest.param({}, id="clean_adcm"),
    ],
)
def additional_adcm_init_config(request) -> dict:
    """
    Add options for ADCM init.
    Redefine this fixture in the actual project to alter additional options of ADCM initialisation.
    Ex. If this fixture will return {"fill_dummy_data": True}
    then on the init stage dummy objects will be added to ADCM image
    """
    return request.param


@pytest.fixture(scope="session")
def web_driver(browser):
    """
    Create ADCMTest object and initialize web driver session
    Destroy session after test is done
    :param browser: browser name from pytest_generate_tests hook
    """
    driver = ADCMTest(browser)
    driver.create_driver()
    yield driver
    try:
        driver.destroy()
    # If session connection was lost just pass
    # session will be closed automatically on driver side after timeout
    except WebDriverException:
        pass


@pytest.fixture()
def app_fs(adcm_fs: ADCM, web_driver: ADCMTest, request):
    """
    Attach ADCM API to ADCMTest object and open new tab in browser for test
    Collect logs on failure and close browser tab after test is done
    """
    try:
        web_driver.new_tab()
    # Recreate session on WebDriverException
    except WebDriverException:
        # this exception could be raised in case
        # when all tabs were closed in process of creating new one
        web_driver.create_driver()
    web_driver.attache_adcm(adcm_fs)
    yield web_driver
    try:
        if request.node.rep_setup.failed or request.node.rep_call.failed:
            allure.attach(
                web_driver.driver.page_source,
                name="page_source",
                attachment_type=allure.attachment_type.TEXT,
            )
            web_driver.driver.execute_script("document.body.bgColor = 'white';")
            allure.attach(
                web_driver.driver.get_screenshot_as_png(),
                name="screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            # this way of getting logs does not work for Firefox, see ADCM-1497
            if web_driver.capabilities['browserName'] != 'firefox':
                console_logs = web_driver.driver.get_log('browser')
                perf_log = web_driver.driver.get_log("performance")
                events = [_process_browser_log_entry(entry) for entry in perf_log]
                network_logs = [event for event in events if 'Network.response' in event['method']]
                events_json = _write_json_file("all_logs", events)
                network_console_logs = _write_json_file("network_log", network_logs)
                console_logs = _write_json_file("console_logs", console_logs)
                allure.attach(
                    web_driver.driver.current_url,
                    name='Current URL',
                    attachment_type=allure.attachment_type.TEXT,
                )
                allure.attach.file(
                    console_logs, name="console_log", attachment_type=allure.attachment_type.TEXT
                )
                allure.attach.file(
                    network_console_logs,
                    name="network_log",
                    attachment_type=allure.attachment_type.TEXT,
                )
                allure.attach.file(
                    events_json, name="all_events_log", attachment_type=allure.attachment_type.TEXT
                )
        elif web_driver.capabilities['browserName'] != 'firefox':
            with allure.step("Flush browser logs so as not to affect next tests"):
                web_driver.driver.get_log('browser')
                web_driver.driver.get_log("performance")
    except AttributeError:
        # rep_setup and rep_call attributes are generated in runtime and can be absent
        pass


@pytest.fixture(scope='session')
def adcm_credentials():
    """
    Provides ADCM username and password by default
    Examples:
        login(**adcm_credentials)
    """
    return {'username': 'admin', 'password': 'admin'}


@deprecated("Use auth_to_adcm")
@pytest.fixture()
def login_to_adcm(app_fs, adcm_credentials):
    """Perform login on Login page ADCM
    :param app_fs:
    :param adcm_credentials:
    """
    app_fs.driver.get(app_fs.adcm.url)
    login = DeprecatedLoginPage(app_fs.driver)
    login.login(**adcm_credentials)


@pytest.fixture()
def auth_to_adcm(app_fs, adcm_credentials):
    """Perform login on Login page ADCM"""

    login = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login.login_user(**adcm_credentials)
    login.wait_url_contains_path(AdminIntroPage(app_fs.driver, app_fs.adcm.url).path)
    login.wait_config_loaded()


def _process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response


def _write_json_file(f_name, j_data):
    f_path = "/".join([tempfile.mkdtemp(), f_name])
    with open(f_path, 'w') as f:
        json.dump(j_data, f, indent=2)
    return f_path


@allure.title("Login in ADCM over API")
@pytest.fixture()
def login_to_adcm_over_api(app_fs, adcm_credentials):
    """Perform login via API call"""
    login_endpoint = f'{app_fs.adcm.url.rstrip("/")}/api/v1/token/'
    app_fs.driver.get(app_fs.adcm.url)
    token = requests.post(login_endpoint, json=adcm_credentials).json()['token']
    with allure.step("Set token to localStorage"):
        auth = {'login': adcm_credentials['username'], 'token': token}
        script = f'localStorage.setItem("auth", JSON.stringify({auth}))'
        app_fs.driver.execute_script(script)
    AdminIntroPage(app_fs.driver, app_fs.adcm.url).open().wait_config_loaded()


@allure.title("Login in ADCM over UI")
@pytest.fixture()
def login_to_adcm_over_ui(app_fs, adcm_credentials):
    """Perform login on Login page ADCM"""

    login = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login.login_user(**adcm_credentials)
    login.wait_url_contains_path(AdminIntroPage(app_fs.driver, app_fs.adcm.url).path)
    login.wait_config_loaded()
