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

"""conftest for config page UI tests"""

from typing import Generator

import allure
import pytest
from selenium.common.exceptions import WebDriverException
from tests.ui_tests.app.app import ADCMTest
from tests.ui_tests.conftest import login_over_api


@pytest.fixture(scope="module")
def app_ms(adcm_ms, web_driver) -> ADCMTest:
    """Analog of app_fs"""
    web_driver.attache_adcm(adcm_ms)
    # see app_fs for reasoning
    try:
        web_driver.new_tab()
    except WebDriverException:
        web_driver.create_driver()
    return web_driver


@allure.title("Login in ADCM over API")
@pytest.fixture(scope="module")
def _login_over_api_ms(app_ms, adcm_credentials):  # pylint: disable=redefined-outer-name
    login_over_api(app_ms, adcm_credentials).wait_config_loaded()


@pytest.fixture()
def objects_to_delete() -> Generator[list, None, None]:
    """Container for objects that'll be deleted after the test"""
    objects = []
    yield objects
    for obj in objects:
        obj.delete()
