"""Methods for generate test data"""
# pylint: disable=invalid-name

from collections import ChainMap
from http import HTTPStatus
from typing import NamedTuple, List, Optional

import allure
import attr
import pytest
from _pytest.mark.structures import ParameterSet

from tests.api.utils.api_objects import Request, ExpectedResponse
from tests.api.utils.endpoints import Endpoints
from tests.api.utils.methods import Methods
from tests.api.utils.tools import fill_lists_by_longest
from tests.api.utils.types import (
    get_fields,
    BaseType,
    PreparedFieldValue,
)


class MaxRetriesError(Exception):
    """Raise when limit of retries exceeded"""


@attr.dataclass(repr=False)
class TestData:  # pylint: disable=too-few-public-methods
    """Pair of request and expected response for api tests"""

    request: Request
    response: ExpectedResponse
    description: Optional[str] = None

    def __repr__(self):
        return (
            f"{self.request.method.name} {self.request.endpoint.path} "
            f"and expect {self.response.status_code} status code. at {hex(id(self))}"
        )


class TestDataWithPreparedBody(NamedTuple):
    """
    Class for separating request body and data needed to send and assert it
    """

    test_data: TestData
    test_body: dict


def _fill_pytest_param(
    value: List[TestDataWithPreparedBody] or List[TestData],
    endpoint: Endpoints,
    method: Methods,
    positive=True,
    addition=None,
) -> ParameterSet:
    """
    Create pytest.param for each test data set
    """
    marks = []
    if positive:
        marks.append(pytest.mark.positive)
        positive_str = "positive"
    else:
        marks.append(pytest.mark.negative)
        positive_str = "negative"
    if endpoint.spec_link:
        marks.append(allure.link(url=endpoint.spec_link, name="Endpoint spec"))
    param_id = f"{endpoint.path}_{method.name}_{positive_str}"
    if addition:
        param_id += f"_{addition}"
    return pytest.param(value, marks=marks, id=param_id)


def get_data_for_methods_check():
    """
    Get test data for allowed methods test
    """
    test_data = []
    for endpoint in Endpoints:
        for method in Methods:
            request = Request(
                method=method,
                endpoint=endpoint,
            )
            if method in endpoint.methods:
                response = ExpectedResponse(status_code=method.default_success_code)
            else:
                response = ExpectedResponse(status_code=HTTPStatus.METHOD_NOT_ALLOWED)

            test_data.append(
                _fill_pytest_param(
                    [TestData(request=request, response=response)],
                    endpoint=endpoint,
                    method=method,
                    positive=response.status_code != HTTPStatus.METHOD_NOT_ALLOWED,
                )
            )
    return test_data


def get_data_for_params_check(method=Methods.GET, fields_predicate=None):
    """
    Get test data for GET-request params check, such as flex fields, filtering and ordering
    """
    test_data = []
    for endpoint in Endpoints:
        if method not in endpoint.methods:
            continue
        if not get_fields(endpoint.data_class, predicate=fields_predicate):
            continue
        request = Request(method=method, endpoint=endpoint)
        response = ExpectedResponse(status_code=method.default_success_code)
        test_data.append(
            _fill_pytest_param(
                [TestData(request=request, response=response)],
                endpoint=endpoint,
                method=method,
                positive=True,
            )
        )
    return test_data


def get_positive_data_for_post_body_check():
    """
    Generates positive datasets for POST method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.POST in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_special_body_datasets(
                            endpoint,
                            desc="All POSTable=True fields with special valid values",
                            method=Methods.POST,
                            positive_case=True,
                        ),
                        _get_datasets(
                            endpoint,
                            desc="All POSTable=True fields with valid values",
                            field_conditions=lambda x: not x.postable,
                            value_properties={"drop_key": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Only Required=True AND POSTable=True fields with valid values",
                            field_conditions=lambda x: not x.postable
                            or (not x.required and not x.custom_required),
                            value_properties={"drop_key": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="POSTable=True fields with valid values without fields "
                            "with (Default!=null) OR (Default=null AND Nullable=True)",
                            field_conditions=lambda x: x.default_value
                            or (x.default_value is None and x.nullable),
                            value_properties={"drop_key": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Some values for fields with POSTable=False and Required=False",
                            field_conditions=lambda x: not x.postable and not x.required,
                            value_properties={"generated_value": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Null values for fields with POSTable=True and Nullable=True",
                            field_conditions=lambda x: x.postable and x.nullable,
                            value_properties={"value": None},
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.POST, test_sets, positive=True)


def get_negative_data_for_post_body_check():
    """
    Generates negative datasets for POST method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.POST in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_datasets(
                            endpoint,
                            desc="Drop fields with Required=True AND POSTable=True",
                            field_conditions=lambda x: x.postable and x.required,
                            value_properties={
                                "error_message": BaseType.error_message_required,
                                "drop_key": True,
                            },
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Drop fields with "
                            "Default=null AND Nullable=False AND Required=False",
                            field_conditions=lambda x: x.default_value is None
                            and (not x.required and not x.nullable and not x.dynamic_nullable),
                            value_properties={
                                "error_message": BaseType.error_message_not_be_null,
                                "drop_key": True,
                            },
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Null values for fields with Nullable=False",
                            field_conditions=lambda x: not x.nullable
                            and (x.postable or x.required)
                            and not x.dynamic_nullable,
                            value_properties={
                                "value": None,
                                "error_message": BaseType.error_message_not_be_null,
                            },
                        ),
                        _get_special_body_datasets(
                            endpoint,
                            desc="Invalid POSTable=True field types and values",
                            method=Methods.POST,
                            positive_case=False,
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.POST, test_sets, positive=False)


def get_positive_data_for_patch_body_check():
    """
    Generates positive datasets for PATCH method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.PATCH in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_datasets(
                            endpoint,
                            desc="Object as is (all fields) "
                            "without any changes in field set or values",
                            field_conditions=lambda x: True,
                            value_properties={"unchanged_value": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Empty body",
                            field_conditions=lambda x: True,
                            value_properties={"drop_key": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="All Changeable=True fields with valid changed values",
                            field_conditions=lambda x: x.changeable,
                            value_properties={"generated_value": True},
                        ),
                        _get_special_body_datasets(
                            endpoint,
                            desc="All Changeable=True fields with special valid values",
                            method=Methods.PATCH,
                            positive_case=True,
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.PATCH, test_sets, positive=True)


def get_negative_data_for_patch_body_check():
    """
    Generates negative datasets for PUT method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.PATCH in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_datasets(
                            endpoint,
                            desc="Changed values for all Changeable=False fields",
                            field_conditions=lambda x: (not x.changeable)
                            and (x.required or x.postable),
                            value_properties={
                                "generated_value": True,
                                "error_message": BaseType.error_message_cannot_be_changed,
                            },
                        ),
                        _get_special_body_datasets(
                            endpoint,
                            desc="All Changeable=True fields with invalid changed values",
                            method=Methods.PATCH,
                            positive_case=False,
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.PATCH, test_sets, positive=False)


def get_positive_data_for_put_body_check():
    """
    Generates positive datasets for PUT method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.PUT in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_datasets(
                            endpoint,
                            desc="Object as is (all fields) "
                            "without any changes in field set or values",
                            field_conditions=lambda x: True,
                            value_properties={"unchanged_value": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Only Required=True fields with changed values",
                            field_conditions=lambda x: not x.required,
                            value_properties={"drop_key": True},
                        ),
                        _get_datasets(
                            endpoint,
                            desc="All Changeable=True fields with valid changed values",
                            field_conditions=lambda x: not x.changeable and not x.required,
                            value_properties={"drop_key": True},
                        ),
                        _get_special_body_datasets(
                            endpoint,
                            desc="All Changeable=True fields with special valid values",
                            method=Methods.PUT,
                            positive_case=True,
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.PUT, test_sets, positive=True)


def get_negative_data_for_put_body_check():
    """
    Generates negative datasets for PUT method
    """
    test_sets = []
    for endpoint in Endpoints:
        if Methods.PUT in endpoint.methods:
            test_sets.append(
                (
                    endpoint,
                    [
                        _get_datasets(
                            endpoint,
                            desc="Drop fields with Required=True",
                            field_conditions=lambda x: x.required,
                            value_properties={
                                "drop_key": True,
                                "error_message": BaseType.error_message_required,
                            },
                        ),
                        _get_datasets(
                            endpoint,
                            desc="Changed values for all Changeable=False fields",
                            field_conditions=lambda x: not x.changeable
                            and (x.required or x.postable),
                            value_properties={
                                "generated_value": True,
                                "error_message": BaseType.error_message_cannot_be_changed,
                            },
                        ),
                        _get_special_body_datasets(
                            endpoint,
                            desc="All Changeable=True fields with invalid changed values",
                            method=Methods.PUT,
                            positive_case=False,
                        ),
                    ],
                )
            )
    return get_data_for_body_check(Methods.PUT, test_sets, positive=False)


def get_data_for_body_check(method: Methods, endpoints_with_test_sets: List[tuple], positive: bool):
    """
    Collect test sets for body testing
    Each test set is set of data params where values is PreparedFieldValue instances
    :param method:
    :param endpoints_with_test_sets:
    :param positive: collect positive or negative datasets
        Negative datasets additionally checks of response body for correct errors.
        In positive cases it doesn't make sense
    """
    test_data = []
    for endpoint, test_groups in endpoints_with_test_sets:
        for test_group, group_name in test_groups:
            values: List[TestDataWithPreparedBody] = []
            for test_set in test_group:
                status_code = method.default_success_code if positive else HTTPStatus.BAD_REQUEST
                # It makes no sense to check with all fields if test_set contains only one field
                if positive or len(test_set) > 1:
                    values.append(
                        _prepare_test_data_with_all_fields(endpoint, method, status_code, test_set)
                    )

                if not positive:
                    values.extend(
                        _prepare_test_data_with_one_by_one_fields(
                            endpoint, method, status_code, test_set
                        )
                    )
            if positive:
                for value in values:
                    test_data.append(
                        _fill_pytest_param(
                            [value],
                            endpoint=endpoint,
                            method=method,
                            positive=positive,
                            addition=group_name,
                        )
                    )
            elif values:
                test_data.append(
                    _fill_pytest_param(
                        values,
                        endpoint=endpoint,
                        method=method,
                        positive=positive,
                        addition=group_name,
                    )
                )
    return test_data


def _prepare_test_data_with_all_fields(
    endpoint: Endpoints, method: Methods, status_code: int, test_set: dict
) -> TestDataWithPreparedBody:
    request = Request(method=method, endpoint=endpoint)
    response = ExpectedResponse(status_code=status_code)

    return TestDataWithPreparedBody(
        test_data=TestData(
            request=request,
            response=response,
            description=f"All fields without body checks - {_step_description(test_set)}",
        ),
        test_body=test_set,
    )


def _step_description(test_set: dict):
    first_item = next(iter(test_set.values()))
    if first_item.generated_value is True:
        return "Generated value: " + ', '.join(test_set.keys())
    if first_item.unchanged_value is True:
        return "Unchanged value: " + ', '.join(test_set.keys())
    if first_item.drop_key is True:
        return "Missing in request: " + ', '.join(test_set.keys())
    return "Special values: " + ', '.join(test_set.keys())


def _prepare_test_data_with_one_by_one_fields(
    endpoint: Endpoints, method: Methods, status_code: int, test_set: dict
) -> List[TestDataWithPreparedBody]:
    test_data_list = []
    for param_name, param_value in test_set.items():
        request_data = {}
        if not param_value.error_messages:
            continue
        body = {param_name: param_value.get_error_data()}
        request_data[param_name] = param_value
        request = Request(method=method, endpoint=endpoint)
        response = ExpectedResponse(status_code=status_code, body=body)
        test_data_list.append(
            TestDataWithPreparedBody(
                test_data=TestData(
                    request=request,
                    response=response,
                    description=f'{param_name}: {param_value.error_messages}',
                ),
                test_body=request_data,
            )
        )
    return test_data_list


def _get_datasets(
    endpoint: Endpoints,
    desc,
    field_conditions,
    value_properties: dict,
) -> (list, str):
    """Generic dataset creator for editing request data later"""
    dataset = {}
    if "generated_value" in value_properties and "value" in value_properties:
        raise ValueError("'generated_value', 'value' properties are not compatible")
    for field in get_fields(endpoint.data_class):
        if field_conditions(field):
            dataset[field.name] = PreparedFieldValue(
                value=value_properties.get("value", None),
                unchanged_value=value_properties.get("unchanged_value", False),
                generated_value=value_properties.get("generated_value", False),
                error_messages=[value_properties.get("error_message", None)],
                drop_key=value_properties.get("drop_key", False),
                f_type=field.f_type,
            )
    return [dataset] if dataset else [], desc


def _get_special_body_datasets(
    endpoint: Endpoints, desc, method: Methods, positive_case: bool
) -> (list, str):
    """Get datasets with based on special values for fields"""
    datasets = []
    special_values = {}
    field_condition = False
    for field in get_fields(endpoint.data_class):
        if method == Methods.POST:
            field_condition = field.postable
        if method in [Methods.PATCH, Methods.PUT]:
            field_condition = field.changeable
        if field_condition:
            if positive_case:
                special_values[field.name] = field.f_type.get_positive_values()
            else:
                # Since Json does not have an invalid value,
                # in case when this is the only field in a negative case,
                # we do not include it in the tests.
                # For example: PATCH and PUT methods in MountPoint
                negative_values = get_fields(
                    endpoint.data_class,
                    predicate=lambda x: x.f_type.get_negative_values()
                    and (  # noqa: W504
                        x.changeable if method in [Methods.PATCH, Methods.PUT] else x.postable
                    ),
                )
                if negative_values:
                    special_values[field.name] = (
                        field.f_type.get_negative_values()
                        if field.f_type.get_negative_values()
                        else [PreparedFieldValue(generated_value=True, f_type=field.f_type)]
                    )
    if special_values:
        fill_lists_by_longest(special_values.values())
        for name, values in special_values.copy().items():
            special_values[name] = [{name: value} for value in values]
        for values in zip(*special_values.values()):
            datasets.append(dict(ChainMap(*values)))
    return datasets, desc
