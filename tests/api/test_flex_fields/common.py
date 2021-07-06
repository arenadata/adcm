"""Common methods for flex field tests"""
import random
from copy import deepcopy
from typing import List, Optional

from tests.test_data.flex_field_builder import FlexFieldBuilder
from tests.test_data.generators import TestData
from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.types import get_fields, is_fk_or_back_ref, is_list_fields


def get_expand_test_data(
    adss_fs, endpoint: Endpoints, initial_data: TestData, depth_level=1, prefix=''
) -> List[TestData]:
    """
    Get TestData list for specified depth of expands fk fields
    :param adss_fs - instance of adss
    :param endpoint - endpoint of current level recursion
    :param initial_data - initial valid TestData without GET-param and expanded expected body
    :param depth_level - level of nesting for expand fk fields
    :param prefix - prepared value of `expand` GET-param from previous level. E.g - cluster.type
    """
    test_data_list = []
    fk_fields = get_fields(endpoint.data_class, predicate=is_fk_or_back_ref)
    for fk_field in fk_fields:
        test_data = deepcopy(initial_data)
        fields_chain_dotted = prefix + '.' + fk_field.name if prefix else fk_field.name
        fields_chain = fields_chain_dotted.split('.')
        fk_endpoint = Endpoints.get_by_data_class(fk_field.f_type.fk_link)

        builder = FlexFieldBuilder(adss=adss_fs, method=initial_data.request.method)
        can_be_expanded = builder.expand_fk_by_chain_if_possible(
            endpoint=initial_data.request.endpoint,
            body=test_data.response.body,
            fields_chain=fields_chain,
        )
        if not can_be_expanded:
            continue

        test_data.request.url_params['expand'] = fields_chain_dotted
        test_data.description = f"Expand '{fields_chain_dotted}'"
        test_data_list.append(test_data)
        if depth_level > 1:
            test_data_list += get_expand_test_data(
                adss_fs,
                endpoint=fk_endpoint,
                initial_data=test_data,
                prefix=fields_chain_dotted,
                depth_level=depth_level - 1,
            )

    return test_data_list


def get_fields_test_data(initial_data: TestData, field_count=1) -> Optional[TestData]:
    """
    Get test data for only random `field_count` fields
    """
    test_data = deepcopy(initial_data)
    predicate = is_list_fields if initial_data.request.method == Methods.LIST else None
    fields = get_fields(test_data.request.endpoint.data_class, predicate=predicate)
    if field_count > len(fields):
        return None
    fields = random.sample(fields, field_count)
    fields_value = ','.join([field.name for field in fields])
    test_data.request.url_params['fields'] = fields_value
    test_data.response.body = FlexFieldBuilder.limit_fields(test_data.response.body, fields)
    test_data.description = f"Only field(s) '{fields_value}'"
    return test_data


def get_omit_test_data(initial_data: TestData, field_count=1) -> Optional[TestData]:
    """
    Get test data for omit random `field_count` fields
    """
    test_data = deepcopy(initial_data)
    predicate = is_list_fields if initial_data.request.method == Methods.LIST else None
    fields = get_fields(test_data.request.endpoint.data_class, predicate=predicate)
    if field_count > len(fields):
        return None
    fields = random.sample(fields, field_count)
    fields_value = ','.join([field.name for field in fields])
    test_data.request.url_params['omit'] = fields_value
    test_data.response.body = FlexFieldBuilder.omit_fields(test_data.response.body, fields)
    test_data.description = f"Omit field(s) '{fields_value}'"
    return test_data
