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

"""ADCM API methods checks"""
# pylint: disable=redefined-outer-name

import allure
import pytest

from tests.api.testdata.db_filler import DbFiller
from tests.api.testdata.generators import TestData, get_data_for_methods_check

pytestmark = [
    allure.suite("API Methods tests"),
]


@allure.title("Prepare data for methods tests")
@pytest.fixture(params=get_data_for_methods_check())
def prepare_data(request, adcm_api):
    """
    Generate request body here since it depends on actual ADCM instance
    and can't be determined when generating
    """
    test_data_list: list[TestData] = request.param
    for test_data in test_data_list:
        request_data = DbFiller(adcm=adcm_api).generate_valid_request_data(
            endpoint=test_data.request.endpoint,
            method=test_data.request.method,
        )

        test_data.request.data = request_data["data"]
        test_data.request.object_id = request_data.get("object_id")

    return adcm_api, test_data_list


def test_methods(prepare_data):
    """
    Testing of allowable methods
    Generate request and response pairs depending on allowable and unallowable methods
    for all api endpoints
    """
    adcm, test_data_list = prepare_data
    for test_data in test_data_list:
        request = test_data.request
        adcm.exec_request(request=request, expected_response=test_data.response)
