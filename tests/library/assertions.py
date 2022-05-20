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
import pprint
from typing import Callable, Union, Collection, TypeVar

import allure

T = TypeVar('T')  # pylint: disable=invalid-name


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

    allure.attach(pprint.pformat(actual), name='Actual dictionary')
    allure.attach(pprint.pformat(expected), name='Expected dictionary')
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
