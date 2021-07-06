"""ADSS API ordering tests"""
# pylint: disable=redefined-outer-name
from copy import deepcopy
from functools import partial
from typing import List

import allure
import pytest

from tests.test_data.db_filler import DbFiller
from tests.test_data.flex_field_builder import FlexFieldBuilder
from tests.test_data.generators import get_data_for_params_check, TestData
from tests.utils.docker import ADSS_DEV_IMAGE
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.tools import nested_get, nested_set, create_dicts_by_chain
from tests.utils.types import get_fields, is_list_fields, is_fk_field_only

pytestmark = [
    allure.suite("Ordering tests"),
    pytest.mark.parametrize("image", [ADSS_DEV_IMAGE], ids=["dev_adss"], indirect=True),
]


@pytest.fixture(params=get_data_for_params_check(method=Methods.LIST))
def prepare_ordering_test_data(request, adss_fs):
    """
    Prepare test data for ordering by simple fields
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
        field_values = [value[field.name] for value in initial_data.response.body['results']]
        if not any(field_values):
            continue
        test_data = deepcopy(initial_data)
        test_data.request.url_params['ordering'] = field.name
        test_data.response.body['results'].sort(
            key=lambda obj: obj[field.name] or 0  # pylint: disable=cell-var-from-loop
        )
        test_data.description = f"Order by '{field.name}' asc"
        test_data_list.append(test_data)

        test_data = deepcopy(initial_data)
        test_data.request.url_params['ordering'] = '-' + field.name
        test_data.response.body['results'].sort(
            key=lambda obj: obj[field.name] or 0, reverse=True  # pylint: disable=cell-var-from-loop
        )
        test_data.description = f"Order by '{field.name}' desc"
        test_data_list.append(test_data)

    return adss_fs, test_data_list


@pytest.fixture(
    params=get_data_for_params_check(method=Methods.LIST, fields_predicate=is_fk_field_only)
)
def prepare_nested_ordering_data(request, adss_fs):
    """
    Prepare test data for nested ordering
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

    test_data_list = _get_nested_ordering_test_data(
        adss_fs, endpoint=initial_data.request.endpoint, initial_data=initial_data, depth_level=2
    )
    return adss_fs, test_data_list


def _get_nested_ordering_test_data(
    adss_fs, endpoint: Endpoints, initial_data: TestData, depth_level=1, prefix=''
):
    """
    Get nested ordering TestData by specified depth for all fk fields many to one
    Every fk field will be expanded. Fk fields will be sorted by id.
    """
    test_data_list = []
    fk_fields = get_fields(endpoint.data_class, predicate=is_fk_field_only)
    for fk_field in fk_fields:
        test_data = deepcopy(initial_data)
        fields_chain_dotted = prefix + '.' + fk_field.name if prefix else fk_field.name
        fields_chain = fields_chain_dotted.split('.')
        fields_chain_underscored = '__'.join(fields_chain) + '__id'

        builder = FlexFieldBuilder(adss=adss_fs, method=initial_data.request.method)
        if not builder.expand_fk_by_chain_if_possible(
            endpoint=initial_data.request.endpoint,
            body=test_data.response.body['results'],
            fields_chain=fields_chain,
        ):
            continue
        expanded_body = deepcopy(test_data.response.body)

        test_data = deepcopy(test_data)
        test_data.request.url_params['expand'] = fields_chain_dotted
        test_data.request.url_params['ordering'] = fields_chain_underscored
        test_data.response.body['results'].sort(key=partial(nested_get, keys=[*fields_chain, 'id']))
        test_data.description = f"Order by '{fields_chain_underscored}' asc"
        test_data_list.append(test_data)

        test_data = deepcopy(test_data)
        test_data.request.url_params['ordering'] = '-' + fields_chain_underscored
        test_data.response.body['results'].reverse()
        test_data.request.url_params['fields'] = fields_chain_dotted + '.id'
        test_data.response.body['results'] = _limit_results_by_fields_chain(
            test_data.response.body['results'], [*fields_chain, 'id']
        )
        test_data.description = f"Order by '{fields_chain_underscored}' desc"
        test_data_list.append(test_data)

        if depth_level > 1:
            test_data = deepcopy(test_data)
            test_data.request.url_params.pop('fields')
            test_data.response.body = deepcopy(expanded_body)
            test_data_list += _get_nested_ordering_test_data(
                adss_fs,
                endpoint=Endpoints.get_by_data_class(fk_field.f_type.fk_link),
                initial_data=test_data,
                prefix=fields_chain_dotted,
                depth_level=depth_level - 1,
            )

    return test_data_list


def _limit_results_by_fields_chain(results: list, fields_chain: list):
    """
    Return list of results only with fields from chain
    """
    limited_results = []
    for result in results:
        limited_result = create_dicts_by_chain(fields_chain)
        nested_set(limited_result, fields_chain, nested_get(result, fields_chain))
        limited_results.append(limited_result)
    return limited_results


def test_ordering(prepare_ordering_test_data):
    """
    Test asc and desc ordering by all simple fields
    """
    adss, test_data_list = prepare_ordering_test_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)


def test_nested_ordering(prepare_nested_ordering_data):
    """
    Test ordering by all many to one foreign keys with depth = 2
    """
    adss, test_data_list = prepare_nested_ordering_data
    for test_data in test_data_list:
        with allure.step(f'Assert - {test_data.description}'):
            adss.exec_request(request=test_data.request, expected_response=test_data.response)
