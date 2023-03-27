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

"""Checker for checking if performing some actions is truly denied"""

import json
import re
from collections.abc import Callable, Collection
from functools import partial
from urllib import parse

import allure
import requests
from adcm_client.base import ObjectNotFound
from adcm_client.objects import (
    ADCM,
    ADCMClient,
    Bundle,
    Cluster,
    Component,
    Group,
    Host,
    Policy,
    Provider,
    Role,
    Service,
    User,
)

from tests.functional.tools import AnyADCMObject, AnyRBACObject
from tests.library.consts import HTTPMethod

RoleTargetObject = AnyADCMObject | AnyRBACObject | Bundle | ADCM
RoleTargetType = type[RoleTargetObject]


class ForbiddenCallChecker:
    """
    Helper class to build a checker that ensures that
    interaction with an ADCM object is truly forbidden via direct calls to API
    """

    _API_ROOT = "/api/v1/"

    # this regex should match word characters between { and } that ends in "id"
    _format_id_arg_regexp = re.compile(r"{(\w*id)}")
    _method_map = {
        ADCM: "adcm/{id}/",
        Bundle: "stack/bundle/{id}/",
        Cluster: "cluster/{id}/",
        Service: "cluster/{cluster_id}/service/{id}/",
        Component: "cluster/{cluster_id}/service/{service_id}/component/{id}/",
        Provider: "provider/{id}/",
        Host: "provider/{provider_id}/host/{id}/",
        User: "rbac/user/{id}/",
        Group: "rbac/group/{id}/",
        Role: "rbac/role/{id}/",
        Policy: "rbac/policy/{id}/",
        # add new entries here (jobs, tasks)
    }

    # Here the function is stored that will form required URL part (before suffix)
    # for the object that was passed to `__call__` function
    # First argument is adcm_object, it's better to allow passing kwargs
    _build_resource_path: Callable[..., str]
    is_of_correct_type: Callable[[RoleTargetObject], bool]

    def __init__(
        self,
        object_type: RoleTargetType | Collection[RoleTargetType],
        endpoint_suffix: str,
        method: HTTPMethod,
        *,
        special_case: str | None = None,
    ):
        if special_case:
            # rework to switch maybe if you have time
            # and maybe add enum to list all possible cases not in string form
            special_cases = {
                "create-from-bundle": self._build_create_from_bundle_resource_path,
                "host-on-cluster": self._build_resource_path_for_host_on_cluster,
                "upgrade": self._build_resource_path_for_upgrade,
            }
            self._build_resource_path = special_cases[special_case]
        else:
            self._build_resource_path = self._build_default_resource_path
        if isinstance(object_type, Collection):
            self.is_of_correct_type = lambda obj: obj.__class__ in object_type
        else:
            self.is_of_correct_type = lambda obj: obj.__class__ == object_type
        self.object_type = object_type
        self.url_suffix = endpoint_suffix.lstrip("/")
        self.method = method

    def __call__(self, client: ADCMClient, adcm_object: AnyADCMObject, *args, **kwargs):
        """
        Try to access the resource / perform an action by:
        1. Building URL for a given object
        2. Requesting this URL with one of HTTP methods with authorization from `client` argument
        3. Raise an AssertionError if response was 500
        4. Raise an AssertionError if response wasn't 403 (because it's Forbidden checker)

        P.S. kwargs are passed to API call method
        """
        resource_path = self._build_resource_path(adcm_object)
        path_without_base_url = f"{self._API_ROOT}{resource_path}".replace("//", "/")
        url = parse.urljoin(client.url, path_without_base_url)
        call_api_method = getattr(requests, self.method.value)
        with allure.step(f"Send {self.method.name} request to {path_without_base_url}"):
            response: requests.Response = call_api_method(
                url,
                headers={
                    "Authorization": f"Token {client.api_token()}",
                    "Content-Type": "application/json",
                },
                **kwargs,
            )
        if (status_code := response.status_code) >= 500:
            raise AssertionError(f"Unhandled exception on {self.method.name} call to {url} check logs")
        # if request is forbidden or object is present (404 with "correct" URL)
        if status_code == 403 or (
            status_code == 404
            and not (response.headers["Content-Type"] == "text/html" and "Not Found" in response.text)
        ):
            return
        try:
            body = json.dumps(response.json(), indent=4)
            attachment_type = allure.attachment_type.JSON
        except requests.exceptions.JSONDecodeError:
            body = response.text
            attachment_type = allure.attachment_type.HTML
        allure.attach(name=f"Response on call to {url}", body=body, attachment_type=attachment_type)
        raise AssertionError(
            f"Unexpected status code, call to {url} should be denied, but status code was {status_code}",
        )

    def _build_default_resource_path(self, adcm_object: RoleTargetObject, **_) -> str:
        """Build resource path string for "basic" entities and actions"""
        self._raise_on_incorrect_type(adcm_object)
        infix_template = self._method_map[adcm_object.__class__]
        template_format_arguments = {
            format_arg: getattr(adcm_object, format_arg)
            for format_arg in self._format_id_arg_regexp.findall(infix_template)
        }
        return f"{infix_template.format(**template_format_arguments)}{self.url_suffix}/"

    def _build_resource_path_for_host_on_cluster(self, adcm_object: Host, **_):
        """Build resource path string for host that belongs to a cluster"""
        if not isinstance(adcm_object, Host) or not adcm_object.cluster_id:
            raise ValueError(f"Object {adcm_object} should be of type Host and be bond to a cluster")
        return f"cluster/{adcm_object.cluster_id}/host/{adcm_object.id}/"

    def _build_resource_path_for_upgrade(self, adcm_object, **_):
        """Build resource path for an upgrade action assuming there's available upgrade with id=1"""
        self._raise_on_incorrect_type(adcm_object)
        # upgrade only for cluster, provider, so nothing but id matters
        object_suffix = self._method_map[adcm_object.__class__].format(id=adcm_object.id)
        # we assume that it's always the first
        return f"{object_suffix}upgrade/1/do/"

    def _build_create_from_bundle_resource_path(self, adcm_object, **_):
        """Build resource for creating entities from the bundle object"""
        self._raise_on_incorrect_type(adcm_object)
        try:
            adcm_object.cluster_prototype()
            return "cluster/"
        except ObjectNotFound:
            return "provider/"

    def _raise_on_incorrect_type(self, adcm_object):
        """
        Raise ValueError if object type is incorrect, because it means that you've passed incorrect object to call
        """
        if not self.is_of_correct_type(adcm_object):
            raise ValueError(f"Object {adcm_object} should be of type {self.object_type}")


def _deny_endpoint_call(endpoint: str, method: HTTPMethod):
    return partial(ForbiddenCallChecker, endpoint_suffix=endpoint, method=method)


class Deny:
    """Description of possible "deny" checks"""

    ViewConfigOf = _deny_endpoint_call("config/current", HTTPMethod.GET)
    ChangeConfigOf = _deny_endpoint_call("config/history", HTTPMethod.POST)
    AddServiceToCluster = ForbiddenCallChecker(Cluster, "service", HTTPMethod.POST)
    RemoveServiceFromCluster = ForbiddenCallChecker(Service, "", HTTPMethod.DELETE)
    AddHostToCluster = ForbiddenCallChecker(Cluster, "host", HTTPMethod.POST)
    RemoveHostFromCluster = ForbiddenCallChecker(Host, "", HTTPMethod.DELETE, special_case="host-on-cluster")
    Delete = _deny_endpoint_call("", HTTPMethod.DELETE)
    ViewImportsOf = _deny_endpoint_call("import", HTTPMethod.GET)
    ManageImportsOf = _deny_endpoint_call("bind", HTTPMethod.POST)
    ViewHostComponentOf = _deny_endpoint_call("hostcomponent", HTTPMethod.GET)
    EditHostComponentOf = _deny_endpoint_call("hostcomponent", HTTPMethod.POST)
    # here we let special case to fully build suffix
    CreateCluster = ForbiddenCallChecker(Bundle, "", HTTPMethod.POST, special_case="create-from-bundle")
    CreateProvider = ForbiddenCallChecker(Bundle, "", HTTPMethod.POST, special_case="create-from-bundle")
    CreateHost = ForbiddenCallChecker(Provider, "host", HTTPMethod.POST)
    UpgradeProvider = ForbiddenCallChecker(Provider, "", HTTPMethod.POST, special_case="upgrade")
    UpgradeCluster = ForbiddenCallChecker(Cluster, "", HTTPMethod.POST, special_case="upgrade")
    Change = _deny_endpoint_call("", HTTPMethod.PUT)  # change user, role, etc
    PartialChange = _deny_endpoint_call("", HTTPMethod.PATCH)  # change host (for example)
