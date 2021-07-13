"""Some asserts with allure steps"""
import json
from http import HTTPStatus

import allure
from requests import Response


class BodyAssertionError(AssertionError):
    """Raised when body is not as expected"""


@allure.step("Response status code should be equal {status_code}")
def status_code_should_be(response: Response, status_code=HTTPStatus.OK):
    """Assert response status code"""
    assert (
        response.status_code == status_code
    ), f"Expecting status code {status_code} but got {response.status_code}"


@allure.step("Response body should be")
def body_should_be(response: Response, expected_body=None):
    """Assert response body and attach it"""
    actual_body = response.json()
    allure.attach(
        json.dumps(expected_body, indent=2),
        name='Expected body',
        attachment_type=allure.attachment_type.JSON,
    )
    allure.attach(
        json.dumps(actual_body, indent=2),
        name='Actual body',
        attachment_type=allure.attachment_type.JSON,
    )
    try:
        assert actual_body == expected_body, "Response body assertion failed!"
    except AssertionError as error:
        raise BodyAssertionError(error) from error
