"""Methods for get endpoints data"""
from tests.api.utils.endpoints import Endpoints
from tests.api.utils.methods import Methods
from tests.api.utils.api_objects import Request, ExpectedResponse

from tests.api.utils.api_objects import ADCMTestApiWrapper


def get_endpoint_data(adcm: ADCMTestApiWrapper, endpoint: Endpoints) -> list:
    """
    Fetch endpoint data with LIST method
    Data of LIST method excludes links to related objects and huge fields
    """
    if Methods.LIST not in endpoint.methods:
        raise AttributeError(
            f"Method {Methods.LIST.name} is not available for endpoint {endpoint.path}"
        )
    res = adcm.exec_request(
        request=Request(endpoint=endpoint, method=Methods.LIST),
        expected_response=ExpectedResponse(status_code=Methods.LIST.value.default_success_code),
    )
    if isinstance(res.json(), list):
        return res.json()
    else:
        # New endpoints always return a response with pagination.
        # In the future all endpoints will return that
        return res.json().get("results")


def get_object_data(adcm: ADCMTestApiWrapper, endpoint: Endpoints, object_id: int) -> dict:
    """
    Fetch full object data includes huge field and links to related objects
    """
    res = adcm.exec_request(
        request=Request(endpoint=endpoint, method=Methods.GET, object_id=object_id),
        expected_response=ExpectedResponse(status_code=Methods.GET.value.default_success_code),
    )
    return res.json()
