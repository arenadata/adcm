"""Module contains api objects for executing and checking requests"""
from urllib.parse import urlencode
from http import HTTPStatus

import allure
import attr
import requests

from .endpoints import Endpoints
from .methods import Methods
from .tools import attach_request_log
from ..steps.asserts import status_code_should_be, body_should_be


@attr.dataclass
class Request:  # pylint: disable=too-few-public-methods
    """Request for a specific endpoint"""

    method: Methods
    endpoint: Endpoints
    object_id: int = None
    url_params: dict = {}
    headers: dict = {}
    data: dict = {}


@attr.dataclass
class ExpectedResponse:  # pylint: disable=too-few-public-methods
    """Response to be expected. Checking the status code and body if present"""

    status_code: int
    body: dict = None


class ADSSApi:
    """ADSS api wrapper"""

    __slots__ = ("_url", "_token")

    _api_prefix = "/api/v1"

    def __init__(self, url="http://localhost:8000"):
        self._url = url
        self._token = None

    @property
    def _base_url(self):
        return f"{self._url}{self._api_prefix}"

    @allure.step("Login to API")
    def login(self, username, password):
        """
        Get API token and save it to class property
        """
        with allure.step("Send POST /token/"):
            auth_resp = requests.post(
                self._base_url + "/token/", json={"username": username, "password": password}
            )
            attach_request_log(auth_resp)
            status_code_should_be(response=auth_resp, status_code=HTTPStatus.OK)

        self._token = auth_resp.json()["token"]

    def exec_request(self, request: Request, expected_response: ExpectedResponse):
        """
        Execute HTTP request based on "request" argument.
        Assert response params amd values based on "expected_response" argument.
        """
        url = self.get_url_for_endpoint(
            endpoint=request.endpoint, method=request.method, object_id=request.object_id
        )
        url_params = request.url_params.copy()

        step_name = f"Send {request.method.name} {url.replace(self._base_url, '')}"
        if url_params:
            step_name += f"?{urlencode(url_params)}"
        with allure.step(step_name):
            response = request.method.function(
                url=url,
                params=url_params,
                json=request.data,
                headers={**request.headers, **{"Authorization": f"Token {self._token}"}},
            )

            attach_request_log(response)

            status_code_should_be(response=response, status_code=expected_response.status_code)

            if expected_response.body is not None:
                body_should_be(response=response, expected_body=expected_response.body)

        return response

    def get_url_for_endpoint(self, endpoint: Endpoints, method: Methods, object_id: int):
        """
        Return direct link for endpoint object
        """
        if "{id}" in method.url_template:
            if object_id is None:
                raise ValueError("Request template requires 'id', but 'request.object_id' is None")
            url = method.url_template.format(name=endpoint.path, id=object_id)
        else:
            url = method.url_template.format(name=endpoint.path)

        return f"{self._base_url}{url}"

    def get_auth_token(self):
        """
        Return auth token of ADSSApi object
        ATTENTION! Value may not match one required to execute request, if _token changed
        """
        return self._token

    def set_auth_token(self, auth_token):
        """
        Override auth token for ADSSApi object
        ATTENTION! Overwrites only for this class object.
                   API of ADSS application will require auth token that it generated.
        """
        self._token = auth_token
