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

"""Common fixtures and methods for ADCM UI tests"""

# pylint:disable=redefined-outer-name

import json
import os
import tempfile
from typing import Generator

import allure
import pytest
import requests
from _pytest.fixtures import SubRequest
from adcm_client.objects import ADCMClient
from adcm_client.wrappers.docker import ADCM
from selenium.common.exceptions import WebDriverException

from tests.conftest import CLEAN_ADCM_PARAM
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage

SELENOID_DOWNLOADS_PATH = '/home/selenium/Downloads'


def pytest_generate_tests(metafunc):
    """
    Parametrize for running tests on clean ADCM only
    """
    if "additional_adcm_init_config" in metafunc.fixturenames:
        metafunc.parametrize("additional_adcm_init_config", [CLEAN_ADCM_PARAM], scope="session")


@pytest.fixture(scope="session")
def downloads_directory(tmpdir_factory: pytest.TempdirFactory):
    """
    Folder in which browser downloads will be stored
    If SELENOID_HOST env variable is provided, then no directory is created
    and path to selenoid downloads returned as string
    """
    if os.environ.get("SELENOID_HOST"):
        return SELENOID_DOWNLOADS_PATH
    downloads_dirname = 'browser-downloads'
    return tmpdir_factory.mktemp(downloads_dirname)


@pytest.fixture()
def _clean_downloads_fs(request: SubRequest, downloads_directory):
    """Clean downloads directory before use"""
    if downloads_directory == SELENOID_DOWNLOADS_PATH:
        yield
        return
    for item in downloads_directory.listdir():
        item.remove()
    yield
    if request.node.rep_setup.passed and request.node.rep_call.failed:
        allure.attach(
            '\n'.join(str(doc) for doc in downloads_directory.listdir()),
            name='Files in "Downloads" directory',
            attachment_type=allure.attachment_type.TEXT,
        )


@pytest.fixture(scope="session")
def web_driver(browser, downloads_directory):
    """
    Create ADCMTest object and initialize web driver session
    Destroy session after test is done
    :param browser: browser name from pytest_generate_tests hook
    :param downloads_directory: directory to store browser downloads
    """
    driver = ADCMTest(browser, downloads_directory)
    driver.create_driver()
    yield driver
    try:
        driver.destroy()
    # If session connection was lost just pass
    # session will be closed automatically on driver side after timeout
    except WebDriverException:
        pass


@pytest.fixture()
def _skip_firefox(browser: str):
    """Skip one test on firefox"""
    if browser == 'Firefox':
        pytest.skip("This test shouldn't be launched on Firefox")


@allure.title("Data for failure investigation")
@pytest.fixture()
def _attach_debug_info_on_ui_test_fail(request, web_driver):
    """Attach screenshot, etc. to allure + cleanup for firefox"""
    yield
    try:
        if request.node.rep_setup.failed or request.node.rep_call.failed:
            allure.attach(
                web_driver.driver.page_source,
                name="page_source",
                attachment_type=allure.attachment_type.HTML,
            )
            web_driver.driver.execute_script("document.body.bgColor = 'white';")
            allure.attach(
                web_driver.driver.get_screenshot_as_png(),
                name="screenshot",
                attachment_type=allure.attachment_type.PNG,
            )
            allure.attach(
                json.dumps(web_driver.driver.execute_script("return localStorage"), indent=2),
                name="localStorage",
                attachment_type=allure.attachment_type.JSON,
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
                allure.attach.file(console_logs, name="console_log", attachment_type=allure.attachment_type.TEXT)
                allure.attach.file(
                    network_console_logs,
                    name="network_log",
                    attachment_type=allure.attachment_type.TEXT,
                )
                allure.attach.file(events_json, name="all_events_log", attachment_type=allure.attachment_type.TEXT)
        elif web_driver.capabilities['browserName'] != 'firefox':
            with allure.step("Flush browser logs so as not to affect next tests"):
                web_driver.driver.get_log('browser')
                web_driver.driver.get_log("performance")
    except AttributeError:
        # rep_setup and rep_call attributes are generated in runtime and can be absent
        pass


@pytest.fixture()
def app_fs(adcm_fs: ADCM, web_driver: ADCMTest, _attach_debug_info_on_ui_test_fail):
    """
    Attach ADCM API to ADCMTest object and open new tab in browser for test
    Collect logs on failure and close browser tab after test is done
    """
    _ = _attach_debug_info_on_ui_test_fail
    web_driver.attache_adcm(adcm_fs)
    try:
        web_driver.new_tab()
    except WebDriverException:
        # this exception could be raised in case
        # when driver was crashed for some reason
        web_driver.create_driver()
    return web_driver


@pytest.fixture(scope='session')
def adcm_credentials():
    """
    Provides ADCM username and password by default
    Examples:
        login(**adcm_credentials)
    """
    return {'username': 'admin', 'password': 'admin'}


def _process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response


def _write_json_file(f_name, j_data):
    f_path = "/".join([tempfile.mkdtemp(), f_name])
    with open(f_path, 'w', encoding='utf_8') as file:
        json.dump(j_data, file, indent=2)
    return f_path


def login_over_api(app_fs, credentials):
    """Perform login with given credentials"""
    login_endpoint = f'{app_fs.adcm.url.rstrip("/")}/api/v1/token/'
    LoginPage(app_fs.driver, app_fs.adcm.url).open(close_popup=False)
    token = requests.post(login_endpoint, json=credentials).json()['token']
    with allure.step("Set token to localStorage"):
        auth = {'login': credentials['username'], 'token': token}
        script = f'localStorage.setItem("auth", JSON.stringify({json.dumps(auth)}))'
        app_fs.driver.execute_script(script)
        auth = app_fs.driver.execute_script("return localStorage.auth")
        assert token in auth, "Token was not set in localStorage"
    return AdminIntroPage(app_fs.driver, app_fs.adcm.url).open()


@allure.title("Login in ADCM over API")
@pytest.fixture()
def _login_to_adcm_over_api(app_fs, adcm_credentials):
    """Perform login via API call"""
    login_over_api(app_fs, adcm_credentials).wait_config_loaded()


@allure.title("Login in ADCM over UI")
@pytest.fixture()
def _login_to_adcm_over_ui(app_fs, adcm_credentials):
    """Perform login on Login page ADCM"""

    login = LoginPage(app_fs.driver, app_fs.adcm.url).open()
    login.login_user(**adcm_credentials)
    login.wait_url_contains_path(AdminIntroPage(app_fs.driver, app_fs.adcm.url).path)
    login.wait_config_loaded()


@pytest.fixture()
def another_user(sdk_client_fs: ADCMClient) -> Generator[dict, None, None]:
    """Create another user, return it's credentials, remove afterwards"""
    user_credentials = {'username': 'blondy', 'password': 'goodbadevil'}
    user = sdk_client_fs.user_create(**user_credentials)
    yield user_credentials
    user.delete()
