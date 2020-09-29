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


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture()
def app_fs(adcm_fs, request):
    adcm_app = ADCMTest(adcm_fs)
    yield adcm_app
    if request.node.rep_setup.passed:
        if request.node.rep_call.failed:
            allure.attach(adcm_app.driver.page_source,
                          name="page_source",
                          attachment_type=allure.attachment_type.TEXT)
            adcm_app.driver.execute_script("document.body.bgColor = 'white';")
            allure.attach(adcm_app.driver.get_screenshot_as_png(),
                          name="screenshot",
                          attachment_type=allure.attachment_type.PNG)
            console_logs = adcm_app.driver.get_log('browser')
            perf_log = adcm_app.driver.get_log("performance")
            events = [process_browser_log_entry(entry) for entry in perf_log]
            network_logs = [event for event in events if 'Network.response' in event['method']]
            events_json = write_json_file("all_logs", events)
            network_console_logs = write_json_file("network_log", network_logs)
            console_logs = write_json_file("console_logs", console_logs)
            allure.attach(adcm_app.driver.current_url, name='Current URL',
                          attachment_type=allure.attachment_type.TEXT)
            allure.attach.file(console_logs, name="console_log",
                               attachment_type=allure.attachment_type.JSON)
            allure.attach.file(network_console_logs, name="network_log",
                               attachment_type=allure.attachment_type.JSON)
            allure.attach.file(events_json, name="all_events_log",
                               attachment_type=allure.attachment_type.JSON)
    adcm_app.destroy()


@pytest.fixture(scope="function")
def login_to_adcm(app_fs):
    """Perform login on Login page ADCM
    :param app_fs:
    """
    app_fs.driver.get(app_fs.adcm.url)
    login = LoginPage(app_fs.driver)
    login.login("admin", "admin")


@pytest.fixture()
def screenshot_on_failure(request, app):
    yield
    if request.node.rep_call.failed:
        app.driver.execute_script("document.body.bgColor = 'white';")
        allure.attach(app.driver.get_screenshot_as_png(),
                      name=request.node.name,
                      attachment_type=allure.attachment_type.PNG)
