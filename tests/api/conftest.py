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

"""ADCM API tests fixtures"""

import allure
import pytest

from tests.api.steps.asserts import BodyAssertionError
from tests.api.steps.common import assume_step
from tests.api.utils.api_objects import ADCMTestApiWrapper


@allure.title("Additional ADCM init config")
@pytest.fixture(
    scope="session",
    params=[
        pytest.param({"fill_dummy_data": True}, id="adcm_with_dummy_data"),
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


def pytest_addoption(parser):
    """
    Additional options for ADCM api testing
    """
    parser.addoption(
        "--disable-soft-assert",
        action="store_true",
        help="This option is needed to disable soft assert in 'flexible_assert_step' fixture",
    )


@pytest.fixture()
def adcm_api_fs(sdk_client_fs) -> ADCMTestApiWrapper:  # pylint: disable=redefined-outer-name
    """Runs ADCM container with previously initialized image.
    Returns authorized instance of ADCMTestApiWrapper object
    """
    return ADCMTestApiWrapper(adcm_api_wrapper=sdk_client_fs._api)  # pylint: disable=protected-access


@pytest.fixture()
def flexible_assert_step(cmd_opts):
    """
    Returns either allure.step or assume_step context manager
    depending on option '--disable-soft-assert'
    """

    def _flexible_assert_step(title, assertion_error=BodyAssertionError):
        if cmd_opts.disable_soft_assert is True:
            return allure.step(title)
        return assume_step(title, assertion_error)

    return _flexible_assert_step
