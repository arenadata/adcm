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

"""Some asserts with allure steps"""
import json
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Dict

import allure
from requests import Response
from tests.api.utils.tools import NotEqual, NotSet


@dataclass
class ExpectedBody:
    """
    In POST PATCH PUT cases we check only changed or created fields
    and response body contains other fields (without checking their values)
    """

    fields: dict = field(default_factory=dict)


class BodyAssertionError(AssertionError):
    """Raised when body is not as expected"""


@allure.step("Response status code should be equal {status_code}")
def status_code_should_be(response: Response, status_code=HTTPStatus.OK):
    """Assert response status code"""
    assert response.status_code == status_code, f"Expecting status code {status_code} but got {response.status_code}"


@allure.step("Response body should be")
def body_should_be(response: Response, expected_body: ExpectedBody):
    """Assert response body and attach it"""
    actual_body: dict = response.json()
    expected_values = {
        key: value for key, value in expected_body.fields.items() if not isinstance(value, (NotSet, NotEqual))
    }
    unexpected_values: Dict[str, NotEqual] = {
        key: value for key, value in expected_body.fields.items() if isinstance(value, NotEqual)
    }
    with allure.step("Body should contains fields"):
        try:
            actual_set = set(actual_body.keys())
            expected_set = set(expected_body.fields.keys())
            assert actual_set == expected_set, (
                f"Response body fields assertion failed! "
                f"Body fields are not as expected.\n"
                f"Actual is {', '.join(actual_set)}\n"
                f"But expected {','.join(expected_set)}"
            )
        except AssertionError as error:
            raise BodyAssertionError(error) from error

    if expected_values:
        with allure.step("Fields values should be"):
            actual_values = {key: value for key, value in actual_body.items() if key in expected_values}

            allure.attach(
                json.dumps(expected_values, indent=2),
                name='Expected fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                json.dumps(actual_values or actual_body, indent=2),
                name='Actual fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            try:
                assert actual_values == expected_values, "Response fields values assertion failed!"
            except AssertionError as error:
                if _clean_values(actual_values) != _clean_values(expected_values):
                    raise BodyAssertionError(error) from error
    if unexpected_values:
        with allure.step("Fields values should NOT be"):
            actual_values = {key: value for key, value in actual_body.items() if key in unexpected_values}
            allure.attach(
                json.dumps(unexpected_values, indent=2, cls=NotEqual.Encoder),
                name='Unexpected fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                json.dumps(actual_values or actual_body, indent=2),
                name='Actual fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            try:
                for key, value in unexpected_values.items():
                    assert value.value != actual_values.get(key), f"Response field {key} has unexpected value"
            except AssertionError as error:
                # maybe we want to check it above
                if _clean_values(actual_values) == _clean_values(unexpected_values):
                    raise BodyAssertionError(error) from error


def _clean_values(to_clean: dict):
    """Make lists and dicts cleaner to compare"""
    # it's an awful way to do it, but otherwise we should ignore all lists
    dict_to_clean = dict(**to_clean)
    for key, value in dict_to_clean.items():
        if isinstance(value, list) and len(value) > 0:
            if isinstance(value[0], dict):
                dicts_in_list = [_clean_values(v) for v in value]
                # we suppose that all keys are the same
                keys = list(value[0].keys())
                keys.sort()
                dict_to_clean[key] = set(tuple((k, d[k]) for k in keys) for d in dicts_in_list)
            else:
                value.sort()
        elif isinstance(value, dict):
            dict_to_clean[key] = _clean_values(value)
    return dict_to_clean
