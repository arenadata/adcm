"""ADCM API methods checks"""
# pylint: disable=redefined-outer-name
from typing import List

import pytest
import allure

from tests.api.testdata.generators import TestData, get_data_for_methods_check
from tests.api.testdata.db_filler import DbFiller

pytestmark = [
    allure.suite("API Methods tests"),
]


@pytest.fixture(params=get_data_for_methods_check())
def prepare_data(request, adcm_api_fs):
    """
    Generate request body here since it depends on actual ADCM instance
    and can't be determined when generating
    """
    test_data_list: List[TestData] = request.param
    for test_data in test_data_list:
        request_data = DbFiller(adcm=adcm_api_fs).generate_valid_request_data(
            endpoint=test_data.request.endpoint, method=test_data.request.method
        )

        test_data.request.data = request_data["data"]
        test_data.request.object_id = request_data.get("object_id")

    return adcm_api_fs, test_data_list


def test_methods(prepare_data):
    """
    Testing of allowable methods
    Generate request and response pairs depending on allowable and unallowable methods
    for all api endpoints
    """
    adcm, test_data_list = prepare_data
    for test_data in test_data_list:
        adcm.exec_request(request=test_data.request, expected_response=test_data.response)
