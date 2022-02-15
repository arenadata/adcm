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
from functools import partial
from typing import Type, Collection, Union, Callable, Optional
from urllib import parse

import allure
import requests
from adcm_client.base import ObjectNotFound
from adcm_client.objects import (
    ADCMClient,
    Cluster,
    Service,
    Component,
    Provider,
    Host,
    User,
    Group,
    Role,
    Policy,
    Bundle,
    ADCM,
)

from tests.library.consts import HTTPMethod
from tests.functional.tools import AnyADCMObject, AnyRBACObject

RoleTargetObject = Union[AnyADCMObject, AnyRBACObject, Bundle, ADCM]
RoleTargetType = Type[RoleTargetObject]


class ForbiddenCallChecker:  # pylint: disable=too-few-public-methods
    """Helper to check that certain interaction with an ADCM object is truly forbidden via API"""

    _API_ROOT = '/api/v1/'

    # this regex should match word characters between { and } that ends in "id"
    _format_id_arg_regexp = re.compile(r'{(\w*id)}')
    _method_map = {
        ADCM: 'adcm/{id}/',
        Bundle: 'stack/bundle/{id}/',
        Cluster: 'cluster/{id}/',
        Service: 'cluster/{cluster_id}/service/{id}/',
        Component: 'cluster/{cluster_id}/service/{service_id}/component/{id}/',
        Provider: 'provider/{id}/',
        Host: 'provider/{provider_id}/host/{id}/',
        User: 'rbac/user/{id}/',
        Group: 'rbac/group/{id}/',
        Role: 'rbac/role/{id}/',
        Policy: 'rbac/policy/{id}/',
        # TODO jobs, tasks?
    }

    # first argument is adcm_object, should allow passing kwargs
    _get_infix: Callable[..., str]
    is_of_correct_type: Callable[[RoleTargetObject], bool]

    def __init__(
        self,
        object_type: Union[RoleTargetType, Collection[RoleTargetType]],
        endpoint_suffix: str,
        method: HTTPMethod,
        *,
        special_case: Optional[str] = None,
    ):
        if special_case:
            # rework to switch maybe if you have time
            # and maybe add enum to list all possible cases not in string form
            __special_cases = {
                'create-from-bundle': self._format_create_from_bundle_infix,
                'host-on-cluster': self._format_host_on_cluster_infix,
                'upgrade': self._format_infix_for_upgrade,
            }
            self._get_infix = __special_cases[special_case]
        else:
            self._get_infix = self._format_infix
        if isinstance(object_type, Collection):
            self.is_of_correct_type = lambda obj: obj.__class__ in object_type
        else:
            self.is_of_correct_type = lambda obj: obj.__class__ == object_type
        self.object_type = object_type
        self.url_suffix = endpoint_suffix.lstrip('/')
        self.method = method

    def __call__(self, client: ADCMClient, adcm_object: AnyADCMObject, *args, **kwargs):
        suffix = f'{self._get_infix(adcm_object, client=client)}{self.url_suffix}/'
        url = parse.urljoin(client.url, f'{self._API_ROOT}{suffix}')
        call_api_method = getattr(requests, self.method.value)
        with allure.step(f'Send {self.method.name} request to {url}'):
            response: requests.Response = call_api_method(
                url,
                headers={
                    'Authorization': f'Token {client.api_token()}',
                    'Content-Type': 'application/json',
                },
            )
        if (status_code := response.status_code) >= 500:
            raise AssertionError(f'Unhandled exception on {self.method.name} call to {url} check logs')
        if status_code != 403:
            try:
                body = json.dumps(response.json(), indent=4)
                attachment_type = allure.attachment_type.JSON
            except requests.exceptions.JSONDecodeError:
                body = response.text
                attachment_type = allure.attachment_type.HTML
            allure.attach(name=f'Response on call to {url}', body=body, attachment_type=attachment_type)
            raise AssertionError(
                f'Unexpected status code, call to {url} should be denied, but status code was {status_code}'
            )

    def _format_infix(self, adcm_object: RoleTargetObject, **_) -> str:
        self._raise_on_incorrect_type(adcm_object)
        infix_template = self._method_map[adcm_object.__class__]
        template_format_arguments = {
            format_arg: getattr(adcm_object, format_arg)
            for format_arg in self._format_id_arg_regexp.findall(infix_template)
        }
        return infix_template.format(**template_format_arguments)

    def _format_host_on_cluster_infix(self, adcm_object: Host, **_):  # pylint: disable=no-self-use
        if not isinstance(adcm_object, Host) or not adcm_object.cluster_id:
            raise ValueError(f'Object {adcm_object} should be of type Host and be bond to a cluster')
        return f'cluster/{adcm_object.cluster_id}/host/{adcm_object.id}/'

    def _format_infix_for_upgrade(self, adcm_object, **_):
        self._raise_on_incorrect_type(adcm_object)
        # upgrade only for cluster, provider, so nothing but id matters
        object_suffix = self._method_map[adcm_object.__class__].format(id=adcm_object.id)
        # we assume that it's always the first
        return f'{object_suffix}upgrade/1/do'

    def _format_create_from_bundle_infix(self, adcm_object, **_):
        self._raise_on_incorrect_type(adcm_object)
        try:
            adcm_object.cluster_prototype()
            return 'cluster/'
        except ObjectNotFound:
            return 'provider/'

    def _raise_on_incorrect_type(self, adcm_object):
        if not self.is_of_correct_type(adcm_object):
            raise ValueError(f'Object {adcm_object} should be of type {self.object_type}')


def _deny_endpoint_call(endpoint: str, method: HTTPMethod):
    return partial(ForbiddenCallChecker, endpoint_suffix=endpoint, method=method)


class Deny:  # pylint: disable=too-few-public-methods
    """Description of possible "deny" checks"""

    ViewConfigOf = _deny_endpoint_call('config', HTTPMethod.GET)
    ChangeConfigOf = _deny_endpoint_call('config/history', HTTPMethod.POST)
    AddServiceToCluster = ForbiddenCallChecker(Cluster, '', HTTPMethod.POST)
    RemoveServiceFromCluster = ForbiddenCallChecker(Cluster, '', HTTPMethod.DELETE)
    AddHostToCluster = ForbiddenCallChecker(Cluster, 'host', HTTPMethod.POST)
    RemoveHostFromCluster = ForbiddenCallChecker(Host, '', HTTPMethod.DELETE, special_case='host-on-cluster')
    Delete = _deny_endpoint_call('', HTTPMethod.DELETE)
    ViewImportsOf = _deny_endpoint_call('import', HTTPMethod.GET)
    ManageImportsOf = _deny_endpoint_call('bind', HTTPMethod.POST)
    ViewHostComponentOf = _deny_endpoint_call('hostcomponent', HTTPMethod.GET)
    EditHostComponentOf = _deny_endpoint_call('hostcomponent', HTTPMethod.POST)
    # here we let special case to fully build suffix
    CreateCluster = ForbiddenCallChecker(Bundle, '', HTTPMethod.POST, special_case='create-from-bundle')
    CreateProvider = ForbiddenCallChecker(Bundle, '', HTTPMethod.POST, special_case='create-from-bundle')
    CreateHost = ForbiddenCallChecker(Provider, 'host', HTTPMethod.POST)
    UpgradeProvider = ForbiddenCallChecker(Provider, '', HTTPMethod.POST, special_case='upgrade')
    UpgradeCluster = ForbiddenCallChecker(Cluster, '', HTTPMethod.POST, special_case='upgrade')
    Change = _deny_endpoint_call('', HTTPMethod.PUT)  # change user, role, etc
