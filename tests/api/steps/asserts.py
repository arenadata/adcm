"""Some asserts with allure steps"""
import json
from dataclasses import field, dataclass
from http import HTTPStatus

import allure
from requests import Response


@dataclass
class ExpectedBody:
    """
    In POST PATCH PUT cases we check only changed or created fields
    and response body contains other fields (without checking their values)
    """
    fields: list = field(default_factory=list)
    fields_values: dict = field(default_factory=dict)


class BodyAssertionError(AssertionError):
    """Raised when body is not as expected"""


@allure.step("Response status code should be equal {status_code}")
def status_code_should_be(response: Response, status_code=HTTPStatus.OK):
    """Assert response status code"""
    assert (
        response.status_code == status_code
    ), f"Expecting status code {status_code} but got {response.status_code}"


@allure.step("Response body should be")
def body_should_be(response: Response, expected_body: ExpectedBody):
    """Assert response body and attach it"""
    actual_body: dict = response.json()
    if expected_body.fields:
        with allure.step("Body should contains fields"):
            try:
                assert set(actual_body.keys()) == set(expected_body.fields), (
                    f"Response body fields assertion failed! "
                    f"Body fields are not as expected: {', '.join(expected_body.fields)}"
                )
            except AssertionError as error:
                raise BodyAssertionError(error) from error

    if expected_body.fields_values:
        with allure.step("Fields values should be"):
            actual_fields_values = {
                key: value
                for key, value in actual_body.items()
                if key in expected_body.fields_values
            }
            allure.attach(
                json.dumps(expected_body.fields_values, indent=2),
                name='Expected fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            allure.attach(
                json.dumps(actual_fields_values or actual_body, indent=2),
                name='Actual fields values',
                attachment_type=allure.attachment_type.JSON,
            )
            try:
                assert actual_fields_values == expected_body.fields_values, (
                    "Response fields values assertion failed!"
                )
            except AssertionError as error:
                raise BodyAssertionError(error) from error
