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

import allure
import json
import os
import pytest
import sys
import tempfile

from selenium.common.exceptions import WebDriverException

from adcm_client.wrappers.docker import ADCM

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.pages import LoginPage

pytest_plugins = "adcm_pytest_plugin"

# We have a number of calls from functional or ui_tests to cm module,
# so we need a way to extend PYTHONPATH at test time.
testdir = os.path.dirname(__file__)
rootdir = os.path.dirname(testdir)
pythondir = os.path.abspath(os.path.join(rootdir, 'python'))
sys.path.append(pythondir)


def process_browser_log_entry(entry):
    response = json.loads(entry['message'])['message']
    return response


def write_json_file(f_name, j_data):
    f_path = "/".join([tempfile.mkdtemp(), f_name])
    with open(f_path, 'w') as f:
        json.dump(j_data, f, indent=2)
    return f_path


def pytest_addoption(parser):
    parser.addoption("--firefox", action="store_true", default=False,
                     help='Additionally run UI tests on Firefox browser.')


def pytest_generate_tests(metafunc):
    """
    Parametrize web_driver fixture of browser names based on run options
    """
    if 'browser' in metafunc.fixturenames:
        browsers = ['Chrome']
        firefox = metafunc.config.getoption('--firefox')
        if firefox:
            browsers.append('Firefox')

        metafunc.parametrize('browser', browsers, scope='session')


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
        web_driver.create_driver()
    web_driver.attache_adcm(adcm_fs)
    yield web_driver
    try:
        if request.node.rep_setup.failed or request.node.rep_call.failed:
            allure.attach(web_driver.driver.page_source,
                          name="page_source",
                          attachment_type=allure.attachment_type.TEXT)
            web_driver.driver.execute_script("document.body.bgColor = 'white';")
            allure.attach(web_driver.driver.get_screenshot_as_png(),
                          name="screenshot",
                          attachment_type=allure.attachment_type.PNG)
            # this way of getting logs does not work for Firefox, see ADCM-1497
            if web_driver.capabilities['browserName'] != 'firefox':
                console_logs = web_driver.driver.get_log('browser')
                perf_log = web_driver.driver.get_log("performance")
                events = [process_browser_log_entry(entry) for entry in perf_log]
                network_logs = [event for event in events if 'Network.response' in event['method']]
                events_json = write_json_file("all_logs", events)
                network_console_logs = write_json_file("network_log", network_logs)
                console_logs = write_json_file("console_logs", console_logs)
                allure.attach(web_driver.driver.current_url, name='Current URL',
                              attachment_type=allure.attachment_type.TEXT)
                allure.attach.file(console_logs, name="console_log",
                                   attachment_type=allure.attachment_type.JSON)
                allure.attach.file(network_console_logs, name="network_log",
                                   attachment_type=allure.attachment_type.JSON)
                allure.attach.file(events_json, name="all_events_log",
                                   attachment_type=allure.attachment_type.JSON)
    except AttributeError:
        # rep_setup and rep_call attributes are generated in runtime and can be absent
        pass
    web_driver.close_tab()


@pytest.fixture(scope='session')
def adcm_credentials():
    """
    Provides ADCM username and password by default
    Examples:
        login(**adcm_credentials)
    """
    return {'username': 'admin', 'password': 'admin'}


@pytest.fixture(scope="function")
def login_to_adcm(app_fs, adcm_credentials):
    """Perform login on Login page ADCM
    :param app_fs:
    :param adcm_credentials:
    """
    app_fs.driver.get(app_fs.adcm.url)
    login = LoginPage(app_fs.driver)
    login.login(**adcm_credentials)
