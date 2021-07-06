"""Methods for get endpoints data"""
from random import choice

import allure

from tests.utils.endpoints import Endpoints
from tests.utils.methods import Methods
from tests.utils.api_objects import Request, ExpectedResponse, ADSSApi

DUMMY_HANDLER = choice(["dummy_backup_handler", "dummy_restore_handler"])


def get_endpoint_data(adss: ADSSApi, endpoint: Endpoints) -> list:
    """
    Fetch endpoint data with LIST method
    Data of LIST method excludes links to related objects and huge fields
    """
    if Methods.LIST not in endpoint.methods:
        raise AttributeError(
            f"Method {Methods.LIST.name} is not available for endpoint {endpoint.path}"
        )
    res = adss.exec_request(
        request=Request(endpoint=endpoint, method=Methods.LIST),
        expected_response=ExpectedResponse(status_code=Methods.LIST.value.default_success_code),
    )
    if endpoint == Endpoints.Handler:
        with allure.step(f"Return handler with name '{DUMMY_HANDLER}' as LIST response"):
            for handler in res.json()['results']:
                if handler["name"] == DUMMY_HANDLER:
                    return [handler]
            raise AttributeError(
                f"{DUMMY_HANDLER} not found in list of handlers. "
                f"Handlers: {' ,'.join([handler['name'] for handler in res.json()['results']])}"
            )
    return res.json()['results']


def get_object_data(adss: ADSSApi, endpoint: Endpoints, object_id: int) -> dict:
    """
    Fetch full object data includes huge field and links to related objects
    """
    res = adss.exec_request(
        request=Request(endpoint=endpoint, method=Methods.GET, object_id=object_id),
        expected_response=ExpectedResponse(status_code=Methods.GET.value.default_success_code),
    )
    return res.json()
