# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Various "rich" checks for common assertions"""
import json
import pprint
from typing import Callable, Collection, Optional, TypeVar, Union

import allure
from adcm_client.wrappers.api import ADCMApiError
from adcm_pytest_plugin.utils import catch_failed
from coreapi.exceptions import ErrorMessage
from tests.library.errorcodes import ADCMError

T = TypeVar('T')


def is_superset_of(first: set, second: set, assertion_message: Union[str, Callable], *args, **kwargs) -> None:
    """
    Check if first argument (that should be of type "set") is a superset of second.
    """
    if first.issuperset(second):
        return

    second = set(second)
    allure.attach(pprint.pformat(first), name='Searched set')
    allure.attach(pprint.pformat(second), name='Elements expected to be found')
    allure.attach(pprint.pformat(second.difference(first)), name='Not found elements')

    message = assertion_message if not callable(assertion_message) else assertion_message(*args, **kwargs)
    raise AssertionError(message)


def does_not_intersect(first: set, second: set, assertion_message: Union[str, Callable], *args, **kwargs) -> None:
    """
    Check if there's no intersection between first and second sets.
    """
    intersection = first.intersection(second)
    if not intersection:
        return

    allure.attach(pprint.pformat(intersection), name='Sets intersection')

    message = assertion_message if not callable(assertion_message) else assertion_message(*args, **kwargs)
    raise AssertionError(message)


def is_in_collection(item: T, collection: Collection[T], extra_message: Union[str, Callable] = '', **kwargs) -> None:
    """
    Check if item is a part of collection.
    """
    if item in collection:
        return

    allure.attach(pprint.pformat(collection), name='Collection items')
    message = extra_message if not callable(extra_message) else extra_message(**kwargs)
    raise AssertionError(
        f"Item '{item}' wasn't found in collection, check attachment for more details."
        + (f'Details: {message}' if message else '')
    )


def is_not_in_collection(item: T, collection: Collection[T], extra_message: Union[str, Callable] = '', **kwargs):
    """
    Check if item is not a part of collection.
    """
    if item not in collection:
        return

    allure.attach(pprint.pformat(collection), name='Collection items')
    message = extra_message if not callable(extra_message) else extra_message(**kwargs)
    raise AssertionError(
        f"Item '{item}' was found in collection where it shouldn't be, check attachment for more details."
        + (f'Details: {message}' if message else '')
    )


def is_empty(collection: Collection, extra_message: Union[str, Callable] = '', **kwargs) -> None:
    """
    Check if collection is empty (len == 0)
    """
    if len(collection) == 0:
        return

    allure.attach(pprint.pformat(collection), name='Collection items')
    message = extra_message if not callable(extra_message) else extra_message(**kwargs)
    raise AssertionError(
        "Collection should've been empty, check attachment for more details."
        + (f'Details: {message}' if message else '')
    )


def sets_are_equal(actual: set, expected: set, message: Union[str, Callable] = '', **kwargs) -> None:
    """
    Check if two sets are equal
    """
    if not (isinstance(actual, set) or isinstance(expected, set)):
        raise ValueError('Both "actual" and "expected" arguments should be of set type')
    if actual == expected:
        return

    allure.attach(pprint.pformat(actual), name='"Actual" collection')
    allure.attach(pprint.pformat(expected), name='"Expected" collection')
    message = message if not callable(message) else message(**kwargs)
    raise AssertionError(message)


def dicts_are_equal(actual: dict, expected: dict, message: Union[str, Callable] = '', **kwargs) -> None:
    """
    Check that two dicts are equal (direct comparison with `==`)
    """
    if actual == expected:
        return

    allure.attach(json.dumps(actual, indent=2), name='Actual dictionary', attachment_type=allure.attachment_type.JSON)
    allure.attach(
        json.dumps(expected, indent=2), name='Expected dictionary', attachment_type=allure.attachment_type.JSON
    )
    message = message if not callable(message) else message(**kwargs)
    if not message:
        message = "Two dictionaries aren't equal as was expected.\nCheck step attachments for more details."
    raise AssertionError(message)


def dicts_are_not_equal(first: dict, second: dict, message: Union[str, Callable] = '', **kwargs) -> None:
    """
    Check that two dicts aren't equal (direct comparison with `!=`)
    """
    if first != second:
        return

    allure.attach(pprint.pformat(first), name='First dictionary')
    allure.attach(pprint.pformat(second), name='Second dictionary')
    message = message if not callable(message) else message(**kwargs)
    if not message:
        message = "Two dictionaries are equal, which wasn't expected.\nCheck step attachments for more details."
    raise AssertionError(message)


def expect_api_error(
    operation_name: str,
    operation: Callable,
    *args,
    err_: Optional[ADCMError] = None,
    err_args_: Optional[list] = None,
    **kwargs,
):
    """
    Perform "operation" and expect it to raise an API error.

    If `err_` is provided, raised exception will be checked against it by calling `.equal`
    """
    with allure.step(f'Execute "{operation_name}" and expect it to raise API error "{err_}"'):
        try:
            operation(*args, **kwargs)
        except (ErrorMessage, ADCMApiError) as e:
            if err_:
                err_.equal(e, *(err_args_ or []))
        else:
            raise AssertionError('An API error should be raised')


def expect_no_api_error(operation_name: str, operation: Callable, *args, **kwargs):
    """
    Perform "operation" and expect it to pass without raising an API error
    """
    with allure.step(f'Execute "{operation_name}" and expect it to succeed without API errors'):
        with catch_failed(ErrorMessage, f'Operation should be allowed: {operation_name}'):
            return operation(*args, **kwargs)
