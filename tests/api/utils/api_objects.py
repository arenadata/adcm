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

"""Module contains api objects for executing and checking requests"""
from dataclasses import dataclass, field
from typing import Optional, Union
from urllib.parse import urlencode

import allure
from adcm_client.wrappers.api import ADCMApiWrapper

from tests.api.steps.asserts import ExpectedBody, body_should_be, status_code_should_be
from tests.api.utils.endpoints import Endpoints
from tests.api.utils.methods import Methods
from tests.api.utils.tools import attach_request_log


@dataclass
class Request:
    """Request for a specific endpoint"""

    method: Methods
    endpoint: Endpoints
    object_id: Optional[int] = None
    url_params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    data: dict = field(default_factory=dict)


@dataclass
class ExpectedResponse:
    """
    Response to be expected.
    Checking the status code and body or some fields values if present
    """

    status_code: int
    body: Optional[ExpectedBody] = None


class ADCMTestApiWrapper:
    """ADCM api wrapper for API tests"""

    def __init__(self, adcm_api_wrapper: ADCMApiWrapper):
        self._api_wrapper = adcm_api_wrapper

    @property
    def _base_url(self):
        return f"{self._api_wrapper.url}/api/v1"

    def exec_request(self, request: Request, expected_response: ExpectedResponse):
        """
        Execute HTTP request based on "request" argument.
        Assert response params amd values based on "expected_response" argument.
        """
        url = self.get_url_for_endpoint(endpoint=request.endpoint, method=request.method, object_id=request.object_id)
        url_params = request.url_params.copy()
        if request.method == Methods.LIST:
            url_params.update({"limit": 200})

        step_name = f"Send {request.method.name} {url.replace(self._base_url, '')}"
        if url_params:
            step_name += f"?{urlencode(url_params)}"
        with allure.step(step_name):
            response = request.method.function(
                url=url,
                params=url_params,
                json=request.data,
                headers={
                    **request.headers,
                    **{"Authorization": f"Token {self._api_wrapper.api_token}"},
                },
            )

            attach_request_log(response)

            status_code_should_be(response=response, status_code=expected_response.status_code)

            if expected_response.body is not None:
                body_should_be(response=response, expected_body=expected_response.body)

        return response

    def get_url_for_endpoint(self, endpoint: Endpoints, method: Methods, object_id: Union[int, dict]):
        """
        Return direct link for endpoint object.
        object_id can be dict if it's complex "object" id like `{'id': 4, 'url': 'blahblah.com'}`
        """
        if "{id}" in method.url_template:
            if object_id is None:
                raise ValueError("Request template requires 'id', but 'request.object_id' is None")
            real_id = object_id if isinstance(object_id, int) else object_id["id"]
            url = method.url_template.format(name=endpoint.path, id=real_id)
        else:
            url = method.url_template.format(name=endpoint.path)

        return f"{self._base_url}{url}"

    def get_auth_token(self):
        """
        Return auth token of ADCMTestApiWrapper object
        ATTENTION! Value may not match one required to execute request, if _token changed
        """
        return self._api_wrapper.api_token

    def set_auth_token(self, auth_token):
        """
        Override auth token for ADCMTestApiWrapper object
        ATTENTION! Overwrites only for this class object.
                   API of ADCM application will require auth token that it generated.
        """
        self._api_wrapper.api_token = auth_token
