"""ADCM API PUT body tests"""
# pylint: disable=redefined-outer-name, invalid-name
from copy import deepcopy
from typing import List

import allure
import pytest

from tests.api.testdata.generators import (
    get_positive_data_for_put_body_check,
    get_negative_data_for_put_body_check,
    TestData,
    TestDataWithPreparedBody,
)
from tests.api.testdata.db_filler import DbFiller
from tests.api.utils.api_objects import ADCMTestApiWrapper, ExpectedBody
from tests.api.utils.tools import not_set

from tests.api.utils.types import get_fields
from tests.api.utils.methods import Methods

pytestmark = [
    allure.suite("PUT"),
]


@pytest.fixture()
def prepare_put_body_data(request, adcm_api_fs: ADCMTestApiWrapper):
    """
    Fixture for preparing test data for PUT request, depending on generated test datasets
    """
    test_data_list: List[TestDataWithPreparedBody] = request.param
    dbfiller = DbFiller(adcm=adcm_api_fs)
    valid_data = dbfiller.generate_valid_request_data(
        endpoint=test_data_list[0].test_data.request.endpoint, method=Methods.PUT
    )
    full_item = deepcopy(valid_data["full_item"])
    changed_fields = deepcopy(valid_data["changed_fields"])
    final_test_data_list: List[TestData] = []
    for test_data_with_prepared_values in test_data_list:
        test_data, prepared_field_values = deepcopy(test_data_with_prepared_values)
        test_data.request.data = deepcopy(full_item)
        for field in get_fields(test_data.request.endpoint.data_class):
            if field.name in prepared_field_values:
                if not prepared_field_values[field.name].drop_key:

                    if prepared_field_values[field.name].unchanged_value is False:
                        current_field_value = full_item[field.name]
                        changed_field_value = changed_fields.get(field.name, None)
                        test_data.request.data[field.name] = prepared_field_values[
                            field.name
                        ].return_value(dbfiller, current_field_value, changed_field_value)

                else:
                    if field.name in test_data.request.data:
                        del test_data.request.data[field.name]
            else:
                # When we want to drop some fields, but leave others with:
                #  - changed value if fields are changeable
                #  - value as is
                if field.name in changed_fields:
                    test_data.request.data[field.name] = changed_fields[field.name]

        test_data.request.object_id = valid_data["object_id"]
        final_test_data_list.append(test_data)

    return adcm_api_fs, final_test_data_list


@pytest.mark.parametrize(
    "prepare_put_body_data", get_positive_data_for_put_body_check(), indirect=True
)
def test_put_body_positive(prepare_put_body_data):
    """
    Positive cases of PUT request body testing
    Includes sets of correct field values - boundary values, nullable if possible.
    """
    adcm, test_data_list = prepare_put_body_data
    for test_data in test_data_list:
        # Set expected response fields values
        test_data.response.body = ExpectedBody()
        for field in get_fields(test_data.request.endpoint.data_class):
            test_data.response.body.fields[field.name] = not_set
            if expected_field_value := test_data.request.data.get(field.name):
                test_data.response.body.fields[field.name] = expected_field_value
        with allure.step(f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.mark.parametrize(
    "prepare_put_body_data", get_negative_data_for_put_body_check(), indirect=True
)
@allure.issue(
    name="Error message changing non-changeable fields",
    url="https://arenadata.atlassian.net/browse/ADSS-186",
)
def test_put_body_negative(prepare_put_body_data, flexible_assert_step):
    """
    Negative cases of PUT request body testing
    Includes sets of invalid field values - out of boundary values,
    nullable and required if not possible, fields with incorrect types and etc.
    """
    adcm, test_data_list = prepare_put_body_data
    for test_data in test_data_list:
        with flexible_assert_step(title=f'Assert - {test_data.description}'):
            adcm.exec_request(request=test_data.request, expected_response=test_data.response)
