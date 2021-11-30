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
from dataclasses import field, dataclass
from http import HTTPStatus

import allure
from requests import Response

from tests.api.utils.tools import NotSet


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
    expected_fields_values = {
        key: value for key, value in expected_body.fields.items() if not isinstance(value, NotSet)
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

    if expected_fields_values:
        with allure.step("Fields values should be"):
            actual_fields_values = {key: value for key, value in actual_body.items() if key in expected_fields_values}
            allure.attach(
                json.dumps(expected_fields_values, indent=2),
                name='Expected fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                json.dumps(actual_fields_values or actual_body, indent=2),
                name='Actual fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            try:
                assert actual_fields_values == expected_fields_values, "Response fields values assertion failed!"
            except AssertionError as error:
                raise BodyAssertionError(error) from error
