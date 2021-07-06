"""ADSS Flex field LIST testing"""
# pylint: disable=redefined-outer-name, invalid-name
from copy import deepcopy
from typing import List

import allure
import pytest

from tests.api.test_flex_fields.common import (
    get_expand_test_data,
    get_fields_test_data,
    get_omit_test_data,
)
from tests.test_data.db_filler import DbFiller
from tests.test_data.flex_field_builder import FlexFieldBuilder
from tests.test_data.generators import get_data_for_params_check, TestData
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.methods import Methods
from tests.utils.types import is_fk_or_back_ref, get_fields, is_list_fields

pytestmark = [
    allure.sub_suite("List"),
    pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True),
]


@pytest.fixture(
    params=get_data_for_params_check(method=Methods.LIST, fields_predicate=is_fk_or_back_ref)
)
def prepare_expand_data(request, adss_fs):
    """
    Prepare TestData for testing expand
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=initial_data.request.method
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.url_params = request_data["url_params"]
    body: dict = adss_fs.exec_request(initial_data.request, initial_data.response).json()
    initial_data.response.body = body['results']

    test_data_list = get_expand_test_data(
        adss_fs, endpoint=initial_data.request.endpoint, initial_data=initial_data, depth_level=2
    )
    for test_data in test_data_list:
        test_data.response.body = {**body, 'results': test_data.response.body}
    return adss_fs, test_data_list


@pytest.fixture(params=get_data_for_params_check(Methods.LIST))
def prepare_fields_and_omit_test_data(request, adss_fs):
    """
    Prepare TestData for testing `fields` and `omit` GET-param
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=initial_data.request.method
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.url_params = request_data["url_params"]
    body: dict = adss_fs.exec_request(initial_data.request, initial_data.response).json()
    initial_data.response.body = body['results']

    test_data_list = list(
        filter(
            lambda x: x is not None,
            [
                get_fields_test_data(initial_data),
                get_fields_test_data(initial_data, field_count=2),
                get_omit_test_data(initial_data),
                get_omit_test_data(initial_data, field_count=2),
            ],
        )
    )

    for test_data in test_data_list:
        test_data.response.body = {**body, 'results': test_data.response.body}
    return adss_fs, test_data_list


@pytest.fixture(
    params=get_data_for_params_check(method=Methods.LIST, fields_predicate=is_fk_or_back_ref)
)
def prepare_combinations_test_data(request, adss_fs):
    """
    Prepare TestData list for combinations of `expand`, `fields`, `omit` GET-params
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=initial_data.request.method
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.url_params = request_data["url_params"]
    body: dict = adss_fs.exec_request(initial_data.request, initial_data.response).json()
    initial_data.response.body = body['results']

    test_data_list = [
        get_expand_and_fields_combination_test_data(adss_fs, initial_data),
        get_expand_and_omit_combination_test_data(adss_fs, initial_data),
    ]

    for test_data in test_data_list:
        test_data.response.body = {**body, 'results': test_data.response.body}
    return adss_fs, test_data_list


def get_expand_and_fields_combination_test_data(adss_fs, initial_data) -> TestData:
    """
    Get test data for expand + fields on lower level, e.g expand=cluster&fields=cluster.type
    """
    builder = FlexFieldBuilder(adss_fs, Methods.LIST)
    td: TestData = deepcopy(initial_data)

    fields = get_fields(td.request.endpoint.data_class, predicate=is_fk_or_back_ref)
    expand_field = builder.choose_not_empty_field(
        endpoint=td.request.endpoint, data=td.response.body, fields=fields
    )
    builder.expand_fk_by_chain_if_possible(
        endpoint=td.request.endpoint, body=td.response.body, fields_chain=[expand_field.name]
    )

    fk_fields = get_fields(expand_field.f_type.fk_link, predicate=is_list_fields)
    fk_endpoint = td.request.endpoint.get_child_endpoint_by_fk_name(expand_field.name)
    final_body = []
    only_field = None
    for body in td.response.body:
        only_field = only_field or builder.choose_not_empty_field(
            endpoint=fk_endpoint, data=body[expand_field.name], fields=fk_fields
        )
        expand_field_value = builder.limit_fields(body[expand_field.name], [only_field])
        final_body.append({expand_field.name: expand_field_value})
    td.response.body = final_body
    fields_chain = expand_field.name + '.' + only_field.name
    td.request.url_params['expand'] = expand_field.name
    td.request.url_params['fields'] = fields_chain
    td.description = f"Expand '{expand_field.name}' and only '{fields_chain}'"
    return td


def get_expand_and_omit_combination_test_data(adss_fs, initial_data) -> TestData:
    """
    Get test data for expand + omit on lower level, e.g. expand=cluster&omit=cluster.type
    """
    builder = FlexFieldBuilder(adss_fs, Methods.LIST)
    td: TestData = deepcopy(initial_data)

    fields = get_fields(td.request.endpoint.data_class, predicate=is_fk_or_back_ref)
    expand_field = builder.choose_not_empty_field(
        endpoint=td.request.endpoint, data=td.response.body, fields=fields
    )
    builder.expand_fk_by_chain_if_possible(
        endpoint=td.request.endpoint, body=td.response.body, fields_chain=[expand_field.name]
    )

    fk_fields = get_fields(expand_field.f_type.fk_link, predicate=is_list_fields)
    fk_endpoint = td.request.endpoint.get_child_endpoint_by_fk_name(expand_field.name)
    final_body = []
    omit_field = None
    for body in td.response.body:
        omit_field = omit_field or builder.choose_not_empty_field(
            endpoint=fk_endpoint, data=body[expand_field.name], fields=fk_fields
        )
        expand_field_value = builder.omit_fields(body[expand_field.name], [omit_field])
        body[expand_field.name] = expand_field_value
        final_body.append(body)
    td.response.body = final_body

    fields_chain = expand_field.name + '.' + omit_field.name
    td.request.url_params['expand'] = expand_field.name
    td.request.url_params['omit'] = fields_chain
    td.description = f"Expand '{expand_field.name}' and omit '{fields_chain}'"
    return td


def test_expand(prepare_expand_data):
    """
    Expand fk fields by LIST method and assert result
    Max depth of expanded fields - 2
    """
    adss, test_data_list = prepare_expand_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


def test_fields_and_omit(prepare_fields_and_omit_test_data):
    """
    Expand fk fields by LIST method and assert result
    Max depth of expanded fields - 2
    """
    adss, test_data_list = prepare_fields_and_omit_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


def test_combinations(prepare_combinations_test_data):
    """
    Testing response with combinations of `expand`, `fields` and `omit` GET-params
    """
    adss, test_data_list = prepare_combinations_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)
