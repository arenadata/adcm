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

"""Methods for get endpoints data"""

from tests.api.utils.api_objects import ADCMTestApiWrapper, ExpectedResponse, Request
from tests.api.utils.endpoints import Endpoints
from tests.api.utils.methods import Methods


def get_endpoint_data(adcm: ADCMTestApiWrapper, endpoint: Endpoints) -> list:
    """
    Fetch endpoint data with LIST method
    Data of LIST method excludes links to related objects and huge fields
    """
    if Methods.LIST not in endpoint.methods:
        raise AttributeError(f"Method {Methods.LIST.name} is not available for endpoint {endpoint.path}")
    res = adcm.exec_request(
        request=Request(endpoint=endpoint, method=Methods.LIST),
        expected_response=ExpectedResponse(status_code=Methods.LIST.value.default_success_code),
    )
    result = res.json()
    # New endpoints always return a response with pagination.
    # In the future all endpoints will return that
    if not isinstance(result, list):
        result = result.get("results")
    if endpoint.endpoint.filter_predicate is None:
        return result
    # This one is used for API endpoints with more than one data class associated with its path
    return [item for item in result if endpoint.endpoint.filter_predicate(item)]


def get_object_data(adcm: ADCMTestApiWrapper, endpoint: Endpoints, object_id: int) -> dict:
    """
    Fetch full object data includes huge field and links to related objects
    """
    res = adcm.exec_request(
        request=Request(endpoint=endpoint, method=Methods.GET, object_id=object_id),
        expected_response=ExpectedResponse(status_code=Methods.GET.value.default_success_code),
    )
    return res.json()
