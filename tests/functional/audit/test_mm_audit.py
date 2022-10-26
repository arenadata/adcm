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

"""Test designed to check audit on mm"""
from typing import Optional

import pytest
import allure
import requests
from adcm_client.objects import ADCMClient, Cluster, Service, Component, Host

from tests.functional.audit.conftest import (parametrize_audit_scenario_parsing,
                                             make_auth_header, check_succeed, check_failed)
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (DEFAULT_SERVICE_NAME, ANOTHER_SERVICE_NAME, add_hosts_to_cluster,
                                                        hosts, provider, cluster_with_mm)

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]
API_METHOD = "patch"


def change_service_mm(client: ADCMClient, cluster: Cluster, service: Service, new_user_client: ADCMClient) -> None:
    """Method to change service to maintenance mode"""
    url = f'{client.url}/api/v1/cluster/{cluster.id}/service/{service.id}/'

    body = {"maintenance_mode": "on"}
    with allure.step(f'Deny updating service via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, headers=make_auth_header(client)))
        # TODO: check that service does not have mm

    body = {"maintenance_mode": True}
    with allure.step(f'Succes update service via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(client)))

    with allure.step(f'Fail updating cluster via {API_METHOD.upper()} {url} with body: {body} with wrong user'):
        check_failed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(new_user_client)),
                     exact_code=404)


def change_component_mm(client: ADCMClient, service: Service, component: Component, new_user_client: ADCMClient) -> None:
    """Method to change component to maintenance mode"""
    url = f'{client.url}/api/v1/service/{service.id}/component/{component.id}/'

    body = {"maintenance_mode": "on"}
    with allure.step(f'Deny updating component via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(client)))
        # TODO: check that service does not have mm

    body = {"maintenance_mode": True}
    with allure.step(f'Update component via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(client)))

    with allure.step(f'Fail updating cluster via {API_METHOD.upper()} {url} with body: {body} with wrong user'):
        check_failed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(new_user_client)),
                     exact_code=404)


def change_host_mm(client: ADCMClient, host: Host, new_user_client: ADCMClient) -> None:
    """Method to change host to maintenance mode"""
    url = f'{client.url}/api/v1/host/{host.id}/'

    body = {"maintenance_mode": "on"}
    with allure.step(f'Deny updating component via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(client)))
        # TODO: check that service does not have mm

    body = {"maintenance_mode": True}
    with allure.step(f'Update host via {API_METHOD.upper()} {url} with body: {body}'):
        check_succeed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(client)))

    with allure.step(f'Fail updating host via {API_METHOD.upper()} {url} with body: {body} with wrong user'):
        check_failed(getattr(requests, API_METHOD)(url, json=body, headers=make_auth_header(new_user_client)),
                     exact_code=404)


@parametrize_audit_scenario_parsing("mm_audit.yaml")
def test_mm_audit(sdk_client_fs, audit_log_checker, hosts, cluster_with_mm, post, new_user_client):
    """Test to check audit logs for service and components in maintenance mode"""
    first_host, *_ = hosts
    first_service = cluster_with_mm.service(name=DEFAULT_SERVICE_NAME)
    first_component = first_service.component(name='first_component')
    second_service = cluster_with_mm.service_add(name=ANOTHER_SERVICE_NAME)

    add_hosts_to_cluster(cluster_with_mm, (first_host,))

    change_service_mm(client=sdk_client_fs, cluster=cluster_with_mm, service=second_service,
                      new_user_client=new_user_client)
    change_component_mm(client=sdk_client_fs, service=first_service, component=first_component,
                        new_user_client=new_user_client)
    change_host_mm(client=sdk_client_fs, host=first_host, new_user_client=new_user_client)

    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(list(sdk_client_fs.audit_operation_list()))
