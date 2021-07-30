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
import os
import sys
import tarfile
import tempfile
from typing import Optional

import allure
import pytest
from _pytest.python import Function
from adcm_client.wrappers.docker import ADCM
from allure_commons.model2 import TestResult, Parameter
from allure_pytest.listener import AllureListener
from deprecated import deprecated
from selenium.common.exceptions import WebDriverException

from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.app.page.admin_intro.page import AdminIntroPage
from tests.ui_tests.app.page.login.page import LoginPage
from tests.ui_tests.app.pages import LoginPage as DeprecatedLoginPage

pytest_plugins = "adcm_pytest_plugin"

# We have a number of calls from functional or ui_tests to cm module,
# so we need a way to extend PYTHONPATH at test time.
testdir = os.path.dirname(__file__)
rootdir = os.path.dirname(testdir)
pythondir = os.path.abspath(os.path.join(rootdir, 'python'))
sys.path.append(pythondir)


def pytest_generate_tests(metafunc):
    """
    Parametrize web_driver fixture of browser names based on run options
    """
    if 'browser' in metafunc.fixturenames:
        browsers = [pytest.param("Chrome"), pytest.param("Firefox", marks=[pytest.mark.full])]
        metafunc.parametrize('browser', browsers, scope='session')


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item: Function):
    """
    Pytest hook that overrides test parameters
    In case of adss tests, parameters in allure report don't make sense unlike test ID
    So, we remove all parameters in allure report but add one parameter with test ID
    """
    yield
    _override_allure_test_parameters(item)


def _override_allure_test_parameters(item: Function):
    """
    Overrides all pytest parameters in allure report with test ID
    """
    listener = _get_listener_by_item_if_present(item)
    if listener:
        test_result: TestResult = listener.allure_logger.get_test(None)
        test_result.parameters = [Parameter(name="ID", value=item.callspec.id)]


def _get_listener_by_item_if_present(item: Function) -> Optional[AllureListener]:
    """
    Find AllureListener instance in pytest pluginmanager
    """
    if hasattr(item, "callspec"):
        listener: AllureListener = next(
            filter(
                lambda x: isinstance(x, AllureListener),
                item.config.pluginmanager._name2plugin.values(),  # pylint: disable=protected-access
            ),
            None,
        )
        return listener
    return None
