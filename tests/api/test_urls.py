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

"""ADCM API urls checks"""
# pylint: disable=redefined-outer-name
from typing import List

import allure
import pytest
from tests.api.testdata.db_filler import DbFiller
from tests.api.testdata.generators import (
    TestData,
    TestDataWithPreparedPath,
    get_data_for_urls_check,
)

pytestmark = [
    allure.suite("API Urls tests"),
]


@allure.title("Prepare data for urls tests")
@pytest.fixture(params=get_data_for_urls_check())
def prepare_data(request, adcm_api_fs):
    """
    Generate request body here since it depends on actual ADCM instance
    and can't be determined when generating
    """
    test_data_list: List[TestDataWithPreparedPath] = request.param
    final_test_data: List[TestData] = []
    for td_with_url in test_data_list:
        test_data, path = td_with_url.test_data, td_with_url.request_path
        request_data = DbFiller(adcm=adcm_api_fs).generate_valid_request_data(
            endpoint=test_data.request.endpoint, method=test_data.request.method
        )

        test_data.request.data = request_data["data"]
        test_data.request.object_id = request_data.get("object_id")
        test_data.request.endpoint.path = path
        final_test_data.append(test_data)
    return adcm_api_fs, final_test_data


def test_urls(prepare_data):
    """
    Test that urls with incorrect data has correct error
    """
    adcm, test_data_list = prepare_data
    for test_data in test_data_list:
        adcm.exec_request(request=test_data.request, expected_response=test_data.response)
