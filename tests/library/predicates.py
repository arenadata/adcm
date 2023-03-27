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

from collections.abc import Callable, Collection
from typing import Any, TypeVar

T = TypeVar("T")
PredicateOfOne = Callable[[T], bool]


def attr_is(attribute: str, value: Any) -> PredicateOfOne:
    return lambda object_with_attr: getattr(object_with_attr, attribute) == value


def attr_in(attribute: str, collection: Collection) -> PredicateOfOne:
    return lambda object_with_attr: getattr(object_with_attr, attribute) in collection


def name_is(expected_name: str) -> PredicateOfOne:
    return lambda object_with_name: object_with_name.name == expected_name


def name_in(names: Collection[str]) -> PredicateOfOne:
    return lambda object_with_name: object_with_name.name in names


def name_key_is(expected_name: str) -> PredicateOfOne:
    return lambda object_with_name: object_with_name.get("name") == expected_name


def display_name_key_is(expected_name: str) -> PredicateOfOne:
    return lambda object_with_name: object_with_name.get("display_name") == expected_name


def username_is(expected: str) -> PredicateOfOne:
    return lambda object_with_username: object_with_username.username == expected


def display_name_is(display_name: str) -> PredicateOfOne:
    return lambda object_with_display_name: object_with_display_name.display_name == display_name
