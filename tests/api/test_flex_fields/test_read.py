"""ADSS Flex field GET testing"""
# pylint: disable=redefined-outer-name, invalid-name
import random
from copy import deepcopy
from typing import List

import allure
import pytest

from tests.api.test_flex_fields.common import (
    get_fields_test_data,
    get_omit_test_data,
    get_expand_test_data,
)
from tests.test_data.db_filler import DbFiller
from tests.test_data.flex_field_builder import FlexFieldBuilder
from tests.test_data.generators import TestData, get_data_for_params_check
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.methods import Methods
from tests.utils.types import get_fields, ForeignKey, BackReferenceFK, is_fk_or_back_ref

pytestmark = [
    allure.sub_suite("Read"),
    pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True),
]


@pytest.fixture(params=get_data_for_params_check())
def prepare_expand_data(request, adss_fs):
    """Prepare expand test data"""
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.GET
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.object_id = request_data["object_id"]
    initial_data.request.url_params = request_data["url_params"]
    initial_data.response.body = adss_fs.exec_request(
        initial_data.request, initial_data.response
    ).json()

    test_data_list = get_expand_test_data(
        adss_fs, endpoint=initial_data.request.endpoint, initial_data=initial_data, depth_level=2
    )
    test_data_list.append(_get_non_fk_field_test_data(initial_data))

    return adss_fs, test_data_list


def _get_non_fk_field_test_data(initial_data: TestData) -> TestData:
    """
    Get test data for expand non fk field
    """
    test_data = deepcopy(initial_data)
    non_fk_fields = get_fields(
        test_data.request.endpoint.data_class,
        predicate=lambda x: not isinstance(x.f_type, (ForeignKey, BackReferenceFK)),
    )
    field_name = random.choice(non_fk_fields).name
    test_data.request.url_params['expand'] = field_name
    test_data.description = f"Expand non fk field '{field_name}'"
    return test_data


def test_expand(prepare_expand_data):
    """
    Expand fk fields and assert result
    Max depth of expanded fields - 2
    """
    adss, test_data_list = prepare_expand_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.fixture(params=get_data_for_params_check())
def prepare_fields_and_omit_test_data(request, adss_fs):
    """
    Prepare TestData for testing `fields` and `omit` GET-param
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.GET
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.object_id = request_data["object_id"]
    initial_data.request.url_params = request_data["url_params"]
    initial_data.response.body = adss_fs.exec_request(
        initial_data.request, initial_data.response
    ).json()

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
    return adss_fs, test_data_list


def test_fields_and_omit(prepare_fields_and_omit_test_data):
    """
    Testing response with `fields` and `omit` GET-params
    """
    adss, test_data_list = prepare_fields_and_omit_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.fixture(params=get_data_for_params_check(fields_predicate=is_fk_or_back_ref))
def prepare_combinations_test_data(request, adss_fs):
    """
    Prepare TestData list for combinations of `expand`, `fields`, `omit` GET-params
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.GET
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.object_id = request_data["object_id"]
    initial_data.request.url_params = request_data["url_params"]
    initial_data.response.body = adss_fs.exec_request(
        initial_data.request, initial_data.response
    ).json()

    test_data_list = [
        _get_expand_and_fields_combination_test_data(adss_fs, initial_data),
        _get_expand_and_omit_combination_test_data(adss_fs, initial_data),
        _get_expand_and_fields_and_omit_combination_test_data(adss_fs, initial_data),
    ]
    return adss_fs, test_data_list


def _get_expand_and_fields_combination_test_data(adss_fs, initial_data) -> TestData:
    """
    Get test data for expand + fields on lower level, e.g expand=cluster&fields=cluster.type
    """
    builder = FlexFieldBuilder(adss_fs, Methods.GET)
    td = deepcopy(initial_data)

    fields = get_fields(td.request.endpoint.data_class, predicate=is_fk_or_back_ref)
    expand_field = builder.choose_not_empty_field(
        endpoint=td.request.endpoint, data=td.response.body, fields=fields
    )
    builder.expand_fk_by_chain_if_possible(
        endpoint=td.request.endpoint, body=td.response.body, fields_chain=[expand_field.name]
    )

    fk_fields = get_fields(expand_field.f_type.fk_link)
    fk_endpoint = td.request.endpoint.get_child_endpoint_by_fk_name(expand_field.name)
    only_field = builder.choose_not_empty_field(
        endpoint=fk_endpoint, data=td.response.body[expand_field.name], fields=fk_fields
    )
    builder.limit_fields(td.response.body[expand_field.name], [only_field])
    expand_field_value = builder.limit_fields(td.response.body[expand_field.name], [only_field])

    td.response.body = {expand_field.name: expand_field_value}
    fields_chain = expand_field.name + '.' + only_field.name
    td.request.url_params['expand'] = expand_field.name
    td.request.url_params['fields'] = fields_chain
    td.description = f"Expand '{expand_field.name}' and only '{fields_chain}'"
    return td


def _get_expand_and_omit_combination_test_data(adss_fs, initial_data) -> TestData:
    """
    Get test data for expand + omit on lower level, e.g. expand=cluster&omit=cluster.type
    """
    builder = FlexFieldBuilder(adss_fs, Methods.GET)
    td = deepcopy(initial_data)

    fields = get_fields(td.request.endpoint.data_class, predicate=is_fk_or_back_ref)
    expand_field = builder.choose_not_empty_field(
        endpoint=td.request.endpoint, data=td.response.body, fields=fields
    )
    builder.expand_fk_by_chain_if_possible(
        endpoint=td.request.endpoint, body=td.response.body, fields_chain=[expand_field.name]
    )

    fk_fields = get_fields(expand_field.f_type.fk_link)
    fk_endpoint = td.request.endpoint.get_child_endpoint_by_fk_name(expand_field.name)
    omit_field = builder.choose_not_empty_field(
        endpoint=fk_endpoint, data=td.response.body[expand_field.name], fields=fk_fields
    )
    td.response.body[expand_field.name] = builder.omit_fields(
        td.response.body[expand_field.name], [omit_field]
    )

    fields_chain = expand_field.name + '.' + omit_field.name
    td.request.url_params['expand'] = expand_field.name
    td.request.url_params['omit'] = fields_chain
    td.description = f"Expand '{expand_field.name}' and omit '{fields_chain}'"
    return td


def _get_expand_and_fields_and_omit_combination_test_data(adss_fs, initial_data) -> TestData:
    """
    Get test data for expand + fields + omit on lower level,
    e.g expand=cluster&omit=cluster.type&fields=cluster
    """
    builder = FlexFieldBuilder(adss_fs, Methods.GET)
    td = deepcopy(initial_data)

    fields = get_fields(td.request.endpoint.data_class, predicate=is_fk_or_back_ref)
    expand_field = builder.choose_not_empty_field(
        endpoint=td.request.endpoint, data=td.response.body, fields=fields
    )
    builder.expand_fk_by_chain_if_possible(
        endpoint=td.request.endpoint, body=td.response.body, fields_chain=[expand_field.name]
    )

    fk_fields = get_fields(expand_field.f_type.fk_link)
    fk_endpoint = td.request.endpoint.get_child_endpoint_by_fk_name(expand_field.name)
    omit_field = builder.choose_not_empty_field(
        endpoint=fk_endpoint, data=td.response.body[expand_field.name], fields=fk_fields
    )
    td.response.body = builder.limit_fields(td.response.body, [expand_field])
    td.response.body[expand_field.name] = builder.omit_fields(
        td.response.body[expand_field.name], [omit_field]
    )

    fields_chain = expand_field.name + '.' + omit_field.name
    td.request.url_params['expand'] = expand_field.name
    td.request.url_params['omit'] = fields_chain
    td.request.url_params['fields'] = expand_field.name
    td.description = (
        f"Expand '{expand_field.name}', only '{expand_field.name}' fields "
        f"and omit '{fields_chain}'"
    )
    return td


def test_combinations(prepare_combinations_test_data):
    """
    Testing response with combinations of `expand`, `fields` and `omit` GET-params
    """
    adss, test_data_list = prepare_combinations_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


@pytest.fixture(params=get_data_for_params_check())
def prepare_special_cases_test_data(request, adss_fs):
    """
    Prepare datasets with special cases
    `expand`, `fields` and `omit` with non-existent fields
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.GET
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.object_id = request_data["object_id"]
    initial_data.request.url_params = request_data["url_params"]
    initial_data.response.body = adss_fs.exec_request(
        initial_data.request, initial_data.response
    ).json()

    expand_non_existent = deepcopy(initial_data)
    expand_non_existent.request.url_params['expand'] = 'non_existent_field'
    expand_non_existent.description = "Expand non-existent field"

    only_non_existent = deepcopy(initial_data)
    only_non_existent.request.url_params['fields'] = 'non_existent_field'
    only_non_existent.response.body = {}
    only_non_existent.description = "Only non-existent field"

    omit_non_existent = deepcopy(initial_data)
    omit_non_existent.request.url_params['omit'] = 'non_existent_field'
    omit_non_existent.description = "Omit non-existent field"

    return adss_fs, [expand_non_existent, only_non_existent, omit_non_existent]


def test_special_cases(prepare_special_cases_test_data):
    """
    Testing response of special cases
    `expand`, `fields` and `omit` with non-existent fields
    """
    adss, test_data_list = prepare_special_cases_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)
