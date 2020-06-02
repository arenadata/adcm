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
import os
import pytest
import sys

pytest_plugins = "adcm_pytest_plugin"

# We have a number of calls from functional or ui_tests to cm module,
# so we need a way to extend PYTHONPATH at test time.
testdir = os.path.dirname(__file__)
rootdir = os.path.dirname(testdir)
pythondir = os.path.abspath(os.path.join(rootdir, 'python'))
sys.path.append(pythondir)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # set a report attribute for each phase of a call, which can
    # be "setup", "call", "teardown"

    setattr(item, "rep_" + rep.when, rep)


@pytest.fixture()
def gather_logs(app, request):
    yield
    if request.node.rep_call.failed:
        logs = app.gather_logs(request.node.name)
        allure.attach.file(logs, "{}.tar".format(request.node.name))


@pytest.fixture()
def screenshot_on_failure(app, request):
    yield
    if request.node.rep_call.failed:
        app.driver.execute_script("document.body.bgColor = 'white';")
        allure.attach(app.driver.get_screenshot_as_png(),
                      name=request.node.name,
                      attachment_type=allure.attachment_type.PNG)
