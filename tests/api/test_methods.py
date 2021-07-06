"""ADSS API methods checks"""
# pylint: disable=redefined-outer-name
from typing import List

import pytest
import allure

from tests.test_data.generators import TestData, get_data_for_methods_check
from tests.test_data.db_filler import DbFiller
from tests.utils.docker import ADSS_DEV_IMAGE

pytestmark = [
    allure.suite("Methods tests"),
    pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True),
]


@pytest.fixture(params=get_data_for_methods_check())
def prepare_data(request, adss_fs):
    """
    Generate request body here since it depends on actual ADSS instance
    and can't be determined when generating
    """
    test_data_list: List[TestData] = request.param
    for test_data in test_data_list:
        request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
            endpoint=test_data.request.endpoint, method=test_data.request.method
        )

        test_data.request.data = request_data["data"]
        test_data.request.object_id = request_data.get("object_id")

    return adss_fs, test_data_list


def test_methods(prepare_data):
    """
    Testing of allowable methods
    Generate request and response pairs depending on allowable and unallowable methods
    for all api endpoints
    """
    adss, test_data_list = prepare_data
    for test_data in test_data_list:
        adss.exec_request(request=test_data.request, expected_response=test_data.response)
