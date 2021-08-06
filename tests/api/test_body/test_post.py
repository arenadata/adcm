"""ADCM API POST body tests"""
# pylint: disable=redefined-outer-name
from typing import List
from copy import deepcopy

import allure
import pytest

from tests.api.testdata.generators import (
    get_positive_data_for_post_body_check,
    get_negative_data_for_post_body_check,
    TestData,
    TestDataWithPreparedBody,
)
from tests.api.testdata.db_filler import DbFiller

from tests.api.utils.methods import Methods
from tests.api.utils.tools import not_set
from tests.api.utils.types import get_fields

from tests.api.utils.api_objects import ADCMTestApiWrapper, ExpectedBody

pytestmark = [
    allure.suite("POST"),
]


@pytest.fixture()
def prepare_post_body_data(request, adcm_api_fs: ADCMTestApiWrapper):
    """
    Fixture for preparing test data for POST request, depending on generated test datasets
    """
    test_data_list: List[TestDataWithPreparedBody] = request.param
    valid_request_data = DbFiller(adcm=adcm_api_fs).generate_valid_request_data(
        endpoint=test_data_list[0].test_data.request.endpoint, method=Methods.POST
    )
    final_test_data_list: List[TestData] = []
    for test_data_with_prepared_values in test_data_list:
        test_data, prepared_field_values = test_data_with_prepared_values
        test_data.request.data = deepcopy(valid_request_data["data"])
        for field in get_fields(test_data.request.endpoint.data_class):
            if field.name in prepared_field_values:
                if not prepared_field_values[field.name].drop_key:

                    valid_field_value = None
                    if field.name in test_data.request.data:
                        valid_field_value = test_data.request.data[field.name]
                    test_data.request.data[field.name] = prepared_field_values[
                        field.name
                    ].return_value(valid_field_value)

                else:
                    if field.name in test_data.request.data:
                        del test_data.request.data[field.name]
        final_test_data_list.append(test_data)

    return adcm_api_fs, final_test_data_list


@pytest.mark.parametrize(
    "prepare_post_body_data", get_positive_data_for_post_body_check(), indirect=True
)
def test_post_body_positive(prepare_post_body_data):
    """
    Positive cases of request body testing
    Includes sets of correct field values - boundary values, nullable and required if possible.
    """
    adcm, test_data_list = prepare_post_body_data
    for test_data in test_data_list:
        # Set expected response fields values
        test_data.response.body = ExpectedBody()
        for field in get_fields(test_data.request.endpoint.data_class):
            test_data.response.body.fields[field.name] = not_set
            if (expected_field_value := test_data.request.data.get(field.name)) and field.postable:
                test_data.response.body.fields[field.name] = expected_field_value
        with allure.step(f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.mark.parametrize(
    "prepare_post_body_data", get_negative_data_for_post_body_check(), indirect=True
)
def test_post_body_negative(prepare_post_body_data, flexible_assert_step):
    """
    Negative cases of request body testing
    Includes sets of invalid field values - out of boundary values,
    nullable and required if not possible, fields with incorrect types and etc.
    """
    adcm, test_data_list = prepare_post_body_data
    for test_data in test_data_list:
        with flexible_assert_step(title=f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)
