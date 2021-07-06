"""ADSS filtering testing"""
# pylint: disable=redefined-outer-name

from copy import deepcopy
from typing import List

import allure
import pytest

from tests.api.test_flex_fields.common import (
    FlexFieldBuilder,
)
from tests.test_data.db_filler import DbFiller
from tests.test_data.generators import TestData, get_data_for_params_check
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.types import get_fields, is_list_fields, is_fk_field_only

pytestmark = [
    allure.suite("Filtering tests"),
    pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True),
]


@pytest.fixture(
    params=get_data_for_params_check(method=Methods.LIST, fields_predicate=is_fk_field_only)
)
def prepare_simple_filtering_data(request, adss_fs):
    """
    Prepare TestData for testing simple filtering
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.LIST
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.url_params = request_data["url_params"]
    body: dict = adss_fs.exec_request(initial_data.request, initial_data.response).json()
    initial_data.response.body = body

    test_data_list = []
    for field in get_fields(initial_data.request.endpoint.data_class, predicate=is_list_fields):
        field_values = [
            value[field.name]
            for value in initial_data.response.body['results']
            if value[field.name] is not None
        ]
        if len(field_values) == 0:
            continue
        for field_value in set(field_values):
            test_data = deepcopy(initial_data)
            expected_response_body = [
                obj
                for obj in initial_data.response.body["results"]
                if obj[field.name] == field_value
            ]
            test_data.response.body = {
                "count": len(expected_response_body),
                "next": None,
                "previous": None,
                "results": expected_response_body,
            }

            test_data.request.url_params[field.name] = field_value
            test_data.description = f"Filter list by '{field.name}={field_value}'"
            test_data_list.append(test_data)

    return adss_fs, test_data_list


@pytest.fixture(
    params=get_data_for_params_check(method=Methods.LIST, fields_predicate=is_fk_field_only)
)
def prepare_nested_filtering_data(request, adss_fs):
    """
    Prepare test data for nested filtering
    """
    test_data_list: List[TestData] = request.param
    initial_data = test_data_list[0]
    request_data = DbFiller(adss=adss_fs).generate_valid_request_data(
        endpoint=initial_data.request.endpoint, method=Methods.LIST
    )
    initial_data.response.body = request_data["data"]
    initial_data.request.url_params = request_data["url_params"]
    body: dict = adss_fs.exec_request(initial_data.request, initial_data.response).json()
    initial_data.response.body = body

    test_data_list = _get_nested_filtering_test_data(
        adss_fs, endpoint=initial_data.request.endpoint, initial_data=initial_data, depth_level=2
    )
    return adss_fs, test_data_list


def _get_nested_filtering_test_data(
    adss_fs, endpoint: Endpoints, initial_data: TestData, depth_level=1, prefix=''
):  # pylint: disable=too-many-locals
    """
    Get nested filtering TestData by specified depth for all fk fields many to one
    Every fk field will be expanded. Fk fields will be filtered by allowed to filtering field value.
    """
    test_data_list = []
    fk_fields = get_fields(endpoint.data_class, predicate=is_fk_field_only)
    for fk_field in fk_fields:
        test_data = deepcopy(initial_data)
        fields_chain_dotted = prefix + '.' + fk_field.name if prefix else fk_field.name
        fields_chain = fields_chain_dotted.split('.')

        fk_endpoint = Endpoints.get_by_data_class(fk_field.f_type.fk_link)
        builder = FlexFieldBuilder(adss=adss_fs, method=initial_data.request.method)
        can_be_expanded = builder.expand_fk_by_chain_if_possible(
            endpoint=initial_data.request.endpoint,
            body=test_data.response.body['results'],
            fields_chain=fields_chain,
        )
        if not can_be_expanded:
            continue
        test_data.request.url_params['expand'] = fields_chain_dotted

        # Get all fields allowed for filtering
        allowed_to_filtering_fields = _get_allowed_to_filtering_fields(fields_chain, initial_data)

        for allowed_to_filtering_field in allowed_to_filtering_fields:
            field_values = _get_unique_field_values(
                fields_chain, test_data, allowed_to_filtering_field.name
            )
            for field_value in field_values:
                nested_test_data = deepcopy(test_data)
                # Get expected response body after filtering
                expected_response_body = _get_expected_filtered_response_body(
                    fields_chain,
                    nested_test_data,
                    allowed_to_filtering_field.name,
                    field_value,
                )

                fields_chain_underscored = (
                    '__'.join(fields_chain) + f'__{allowed_to_filtering_field.name}'
                )
                nested_test_data.request.url_params[fields_chain_underscored] = field_value
                nested_test_data.response.body = {
                    "count": len(expected_response_body),
                    "next": None,
                    "previous": None,
                    "results": expected_response_body,
                }

                nested_test_data.description = (
                    f"Expand {fields_chain_dotted} and filter by "
                    f"'{fields_chain_underscored}={field_value}'"
                )
                test_data_list.append(nested_test_data)
        if depth_level > 1:
            test_data_list += _get_nested_filtering_test_data(
                adss_fs,
                endpoint=fk_endpoint,
                initial_data=test_data,
                prefix=fields_chain_dotted,
                depth_level=depth_level - 1,
            )

    return test_data_list


def _get_allowed_to_filtering_fields(fields_chain, initial_data):
    """
    Returns list of allowed to filtering fields from expanded field
    """
    chain = deepcopy(fields_chain)

    def _get_allowed_to_filtering_by_fields_chain(data_class):
        expand_field = [field for field in get_fields(data_class) if field.name == chain[0]]
        if len(chain) > 1:
            del chain[0]
            return _get_allowed_to_filtering_by_fields_chain(expand_field[0].f_type.fk_link)
        return get_fields(expand_field[0].f_type.fk_link, predicate=is_list_fields)

    return _get_allowed_to_filtering_by_fields_chain(initial_data.request.endpoint.data_class)


def _get_unique_field_values(fields_chain, test_data, filtering_field_name):
    """
    Returns field values of some response object.
    This values need for filtering list of objects
    """
    field_values = []
    resp_objects = test_data.response.body["results"]
    for resp_object in resp_objects:
        chain = deepcopy(fields_chain)
        chain.append(filtering_field_name)

        if (allowed_value := _get_value_by_fields_chain(resp_object, chain)) is not None:
            field_values.append(allowed_value)

    return set(field_values)


def _get_expected_filtered_response_body(
    fields_chain, test_data, filtering_field_name, filtering_field_value
):
    """
    Returns expected list of objects after filtering by existing field value
    """
    expected_objects = []
    resp_objects = test_data.response.body["results"]
    for resp_object in resp_objects:
        chain = deepcopy(fields_chain)
        chain.append(filtering_field_name)

        if _get_value_by_fields_chain(resp_object, chain) == filtering_field_value:
            expected_objects.append(resp_object)

    return expected_objects


def _get_value_by_fields_chain(resp_object, entry_chain):
    """
    Get value of last field in chain
    """
    if isinstance(resp_object[entry_chain[0]], dict):
        remaining_parts = entry_chain.pop(0)
        return _get_value_by_fields_chain(resp_object[remaining_parts], entry_chain)
    return resp_object[entry_chain[0]]


def test_simple_filtering(prepare_simple_filtering_data):
    """
    Filter by each field of int or string type in response
    """
    adss, test_data_list = prepare_simple_filtering_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


def test_filtering_by_nested_expanded_fields(prepare_nested_filtering_data):
    """
    If there are fields to expand:
        For each of this fields:
            Expand it and request filtering by field in nested expanded fields
    """
    adss, test_data_list = prepare_nested_filtering_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)
