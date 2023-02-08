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

"""ADCM API PATCH body tests"""
# pylint: disable=redefined-outer-name
from copy import deepcopy
from typing import List

import allure
import pytest

from tests.api.test_body import _test_patch_put_body_positive
from tests.api.testdata.db_filler import DbFiller
from tests.api.testdata.generators import (
    TestDataWithPreparedBody,
    get_negative_data_for_patch_body_check,
    get_positive_data_for_patch_body_check,
)
from tests.api.utils.methods import Methods
from tests.api.utils.types import get_fields

pytestmark = [
    allure.suite("PATCH"),
]


@allure.title("Prepare patch body data")
@pytest.fixture()
def prepare_patch_body_data(request, adcm_api):
    """
    Fixture for preparing test data for PATCH request, depending on generated test datasets
    """
    test_data_list: List[TestDataWithPreparedBody] = request.param
    dbfiller = DbFiller(adcm=adcm_api)
    valid_data = dbfiller.generate_valid_request_data(
        endpoint=test_data_list[0].test_data.request.endpoint, method=Methods.PATCH
    )
    full_item = deepcopy(valid_data["full_item"])
    changed_fields = deepcopy(valid_data["changed_fields"])
    final_test_data_list: List[TestDataWithPreparedBody] = []
    for test_data_with_prepared_values in test_data_list:
        test_data, prepared_field_values = deepcopy(test_data_with_prepared_values)
        for field in get_fields(test_data.request.endpoint.data_class):
            if (field.name in prepared_field_values) and not prepared_field_values[field.name].drop_key:
                current_field_value = full_item[field.name]
                if prepared_field_values[field.name].unchanged_value is False:
                    changed_field_value = changed_fields.get(field.name, None)
                    test_data.request.data[field.name] = prepared_field_values[field.name].return_value(
                        dbfiller, current_field_value, changed_field_value
                    )
                else:
                    test_data.request.data[field.name] = current_field_value

        test_data.request.object_id = valid_data["object_id"]
        final_test_data_list.append(TestDataWithPreparedBody(test_data, prepared_field_values))

    return adcm_api, final_test_data_list


@pytest.mark.parametrize("prepare_patch_body_data", get_positive_data_for_patch_body_check(), indirect=True)
def test_patch_body_positive(prepare_patch_body_data):
    """
    Positive cases of PATCH request body testing
    Includes sets of correct field values - boundary values, nullable if possible.
    """
    _test_patch_put_body_positive(prepare_patch_body_data)


@pytest.mark.parametrize("prepare_patch_body_data", get_negative_data_for_patch_body_check(), indirect=True)
def test_patch_body_negative(prepare_patch_body_data, flexible_assert_step):
    """
    Negative cases of PATCH request body testing
    Includes sets of invalid field values - out of boundary values,
    nullable and changeable if not possible, fields with incorrect types and etc.
    """
    adcm, test_data_list = prepare_patch_body_data
    for test_data_with_prepared_body in test_data_list:
        test_data, _ = test_data_with_prepared_body
        with flexible_assert_step(title=f"Assert - {test_data.description}"):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)
