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

"""ADCM API POST body tests"""
from copy import deepcopy

# pylint: disable=redefined-outer-name
from typing import List

import allure
import pytest
from tests.api.test_body import generate_body_for_checks
from tests.api.testdata.db_filler import DbFiller
from tests.api.testdata.generators import (
    TestDataWithPreparedBody,
    get_negative_data_for_post_body_check,
    get_positive_data_for_post_body_check,
)
from tests.api.utils.methods import Methods
from tests.api.utils.types import get_fields

pytestmark = [
    allure.suite("POST"),
]


@allure.title("Prepare post body data")
@pytest.fixture()
def prepare_post_body_data(request, adcm_api):
    """
    Fixture for preparing test data for POST request, depending on generated test datasets
    """
    test_data_list: List[TestDataWithPreparedBody] = request.param
    valid_request_data = DbFiller(adcm=adcm_api).generate_valid_request_data(
        endpoint=test_data_list[0].test_data.request.endpoint, method=Methods.POST
    )
    final_test_data_list: List[TestDataWithPreparedBody] = []
    for test_data_with_prepared_values in test_data_list:
        test_data, prepared_field_values = test_data_with_prepared_values
        test_data.request.data = deepcopy(valid_request_data["data"])
        for field in get_fields(test_data.request.endpoint.data_class):
            if field.name in prepared_field_values:
                if not prepared_field_values[field.name].drop_key:
                    valid_field_value = None
                    if field.name in test_data.request.data:
                        valid_field_value = test_data.request.data[field.name]
                    test_data.request.data[field.name] = prepared_field_values[field.name].return_value(
                        valid_field_value
                    )

                else:
                    if field.name in test_data.request.data:
                        del test_data.request.data[field.name]
        final_test_data_list.append(TestDataWithPreparedBody(test_data, prepared_field_values))

    return adcm_api, final_test_data_list


@pytest.mark.parametrize("prepare_post_body_data", get_positive_data_for_post_body_check(), indirect=True)
def test_post_body_positive(prepare_post_body_data):
    """
    Positive cases of request body testing
    Includes sets of correct field values - boundary values, nullable and required if possible.
    """
    adcm, test_data_list = prepare_post_body_data
    for test_data_with_prepared_values in test_data_list:
        test_data, _ = test_data_with_prepared_values
        test_data.response.body = generate_body_for_checks(test_data_with_prepared_values)
        with allure.step(f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.mark.parametrize("prepare_post_body_data", get_negative_data_for_post_body_check(), indirect=True)
def test_post_body_negative(prepare_post_body_data, flexible_assert_step):
    """
    Negative cases of request body testing
    Includes sets of invalid field values - out of boundary values,
    nullable and required if not possible, fields with incorrect types and etc.
    """
    adcm, test_data_list = prepare_post_body_data
    for test_data_with_prepared_values in test_data_list:
        test_data, _ = test_data_with_prepared_values
        with flexible_assert_step(title=f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)
