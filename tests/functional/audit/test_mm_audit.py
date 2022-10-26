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

import pytest
import allure
import requests
from adcm_client.objects import ADCMClient, Cluster, Bundle

from tests.functional.audit.conftest import (BUNDLES_DIR, parametrize_audit_scenario_parsing,
                                             NEW_USER, make_auth_header, check_succeed)
from tests.functional.conftest import only_clean_adcm
from tests.functional.maintenance_mode.conftest import (CLUSTER_WITH_MM_NAME, DEFAULT_SERVICE_NAME,
                                                        ANOTHER_SERVICE_NAME, add_hosts_to_cluster, hosts, provider)

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]


@pytest.fixture()
def cluster_with_mm_audit(sdk_client_fs: ADCMClient) -> Cluster:
    """
    Upload cluster bundle with allowed MM,
    create and return cluster with default service
    """
    bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster_mm_allowed')
    cluster = bundle.cluster_create(CLUSTER_WITH_MM_NAME)
    cluster.service_add(name=DEFAULT_SERVICE_NAME)
    return cluster


class TestMmAudit:
    """Test cluster and host objects updates"""

    client: ADCMClient
    new_user_creds: dict
    admin_creds: dict

    pytestmark = [pytest.mark.usefixtures('_init')]

    @pytest.fixture()
    def _init(self, sdk_client_fs, unauthorized_creds) -> None:
        """Bind all required "context" to an instance"""
        self.client = sdk_client_fs
        self.admin_creds = make_auth_header(sdk_client_fs)
        self.new_user_creds = unauthorized_creds

    @parametrize_audit_scenario_parsing("mm_audit.yaml", NEW_USER)
    @pytest.mark.parametrize("method", ["patch"])  # pylint: disable-next=too-many-arguments
    def test_mm_audit(self, sdk_client_fs, audit_log_checker, method: str, hosts, cluster_with_mm_audit, post):
        """Test to check audit logs for service and components in maintenance mode"""
        first_host, second_host, *_ = hosts
        cluster = cluster_with_mm_audit
        first_service = cluster.service(name=DEFAULT_SERVICE_NAME)
        first_component = first_service.component(name='first_component')
        second_component = first_service.component(name='second_component')
        second_service = cluster.service_add(name=ANOTHER_SERVICE_NAME)
        second_service_components = second_service.component_list()

        add_hosts_to_cluster(cluster, (first_host, second_host))
        cluster.hostcomponent_set(
            (first_host, first_component),
            (second_host, second_component),
            (second_host, second_service_components[0]),
            (second_host, second_service_components[1]),
        )

        # /api/v1/cluster/{cluster_id}/
        url = f'{sdk_client_fs.url}/api/v1/cluster/{cluster.id}/'
        body = {"maintenance_mode": True, "description": f"Cluster changed to mm"}

        with allure.step(f'Update cluster via {method.upper()} {url} with body: {body}'):
            check_succeed(getattr(requests, method)(url, json=body, headers=make_auth_header(sdk_client_fs)))
        # body = {"name": "____"}
        # with allure.step(f'Fail updating cluster via {method.upper()} {url} with body: {body}'):
        #     check_failed(getattr(requests, method)(url, json=body, headers=self.admin_creds), exact_code=400)

        # /api/v1/cluster/{cluster_id}/service/{service_id}/
        url_service = f'{sdk_client_fs.url}/api/v1/cluster/{cluster.id}/service/{second_service.id}/'
        body = {"maintenance_mode": True, "description": "Service changed to mm"}
        with allure.step(f'Update cluster service via {method.upper()} {url_service} with body: {body}'):
            check_succeed(getattr(requests, method)(url_service, json=body, headers=self.admin_creds))

        # /api/v1/service/{service_id}/component/{component_id}/
        url_component = f'{sdk_client_fs.url}/api/v1/service/{first_service.id}/component/{first_component.id}/'
        body = {"maintenance_mode": True, "description": f"Component changed to mm"}
        with allure.step(f'Update cluster service via {method.upper()} {url_component} with body: {body}'):
            check_succeed(getattr(requests, method)(url_component, json=body, headers=make_auth_header(sdk_client_fs)))

        #/api/v1/host
        url_host = f'{sdk_client_fs.url}/api/v1/host/{first_host.id}/'
        body = {"maintenance_mode": True, "description": f"Host changed to mm"}
        with allure.step(f'Update cluster service via {method.upper()} {url_host} with body: {body}'):
            check_succeed(getattr(requests, method)(url_host, json=body, headers=make_auth_header(sdk_client_fs)))

        audit_log_checker.set_user_map(sdk_client_fs)
        audit_log_checker.check(sdk_client_fs.audit_operation_list())
