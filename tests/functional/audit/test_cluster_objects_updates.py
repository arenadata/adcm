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

"""Test audit of cluster objects' updates: imports, binds, etc."""

from typing import Optional, Tuple

import allure
import pytest
import requests
from adcm_client.objects import ADCMClient, Bundle, Cluster

from tests.functional.audit.conftest import BUNDLES_DIR, NEW_USER, check_failed, check_succeed, make_auth_header
from tests.functional.rbac.conftest import BusinessRoles, create_policy
from tests.library.audit.checkers import AuditLogChecker

# pylint: disable=redefined-outer-name

FQDN = 'some-fqdn'
IMPORT_SERVICE = 'importer_service'
EXPORT_SERVICE = 'exporter_service'


@pytest.fixture()
def bundle_with_license(sdk_client_fs) -> Bundle:
    """Upload bundle with license"""
    return sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'update' / 'with_license')


@pytest.fixture()
def import_bundle(sdk_client_fs) -> Bundle:
    """Upload import bundle"""
    return sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'update' / 'import')


@pytest.fixture()
def import_export_clusters(sdk_client_fs, import_bundle) -> Tuple[Cluster, Cluster]:
    """Create clusters from import and export bundles and add services to them"""
    import_cluster = import_bundle.cluster_create('Import')
    import_cluster.service_add(name=IMPORT_SERVICE)
    export_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'update' / 'export')
    export_cluster = export_bundle.cluster_create('Export')
    export_cluster.service_add(name=EXPORT_SERVICE)
    return import_cluster, export_cluster


@pytest.fixture()
def grant_cluster_view_permissions(sdk_client_fs, import_export_clusters, new_user_client) -> None:
    """Grant view config permissions on import cluster and service"""
    import_cluster, *_ = import_export_clusters
    create_policy(
        sdk_client_fs,
        [BusinessRoles.ViewClusterConfigurations, BusinessRoles.ViewServiceConfigurations],
        [import_cluster, import_cluster.service()],
        [sdk_client_fs.user(id=new_user_client.me().id)],
        [],
        use_all_objects=True,
    )


class TestClusterUpdates:
    """Test "basic" updates of cluster and bundle"""

    client: ADCMClient
    new_user_creds: dict
    admin_creds: dict

    pytestmark = [pytest.mark.usefixtures('init')]

    @pytest.fixture()
    def init(self, sdk_client_fs, unauthorized_creds) -> None:
        """Bind all required "context" to an instance"""
        self.client = sdk_client_fs
        self.admin_creds = make_auth_header(sdk_client_fs)
        self.new_user_creds = unauthorized_creds

    @pytest.mark.parametrize(
        'parse_with_context', ['plain_service_add.yaml'], indirect=True
    )  # pylint: disable-next=too-many-arguments
    def test_plain_service_add(self, import_bundle, parse_with_context, post, delete, new_user_client):
        """Test adding service from /api/v1/service/"""
        new_user = self.client.user(id=new_user_client.me().id)
        path = 'service'
        cluster = import_bundle.cluster_create('Cluster')
        data = {'cluster_id': cluster.id, 'prototype_id': import_bundle.service_prototype().id}
        with allure.step('Add service'):
            check_succeed(post(path, data))
        with allure.step('Fail to add service'):
            check_failed(post(path, data), exact_code=409)
        with allure.step('Get denied trying to add service'):
            check_failed(post(path, data, self.new_user_creds), exact_code=403)
        service = cluster.service()
        display_name = service.display_name
        create_policy(self.client, [BusinessRoles.ViewServiceConfigurations], [service], [new_user], [])
        with allure.step('Get denied trying to remove service'):
            check_failed(delete(path, service.id, headers=self.new_user_creds), exact_code=403)
        with allure.step('Remove service'):
            check_succeed(delete(path, service.id))
        with allure.step('Fail to remove service'):
            check_failed(delete(path, service.id), exact_code=404)
        checker = AuditLogChecker(
            parse_with_context(
                {'cluster_name': cluster.name, 'service_display_name': display_name, 'username': NEW_USER['username']}
            )
        )
        checker.set_user_map(self.client)
        checker.check(self.client.audit_operation_list())

    @pytest.mark.parametrize(
        'parse_with_context', ['cluster_updates.yaml'], indirect=True
    )  # pylint: disable-next=too-many-arguments
    def test_cluster_service_updates(
        self,
        bundle_with_license,
        import_bundle,
        parse_with_context,
        generic_provider,
        new_user_client,
    ):
        """
        Test update operations with cluster, service and bundle:

        - Bundle license accept
        - Service added
        - Service removed
        - Host added to cluster
        - Cluster's hostcomponent set
        - Host removed from cluster
        """
        new_user = self.client.user(id=new_user_client.me().id)
        self._accept_license(bundle_with_license, import_bundle)
        cluster = bundle_with_license.cluster_create('Cluster')
        host = generic_provider.host_create('first')
        create_policy(self.client, [BusinessRoles.ViewClusterConfigurations], [cluster], [new_user], [])
        self._add_service(cluster)
        create_policy(self.client, [BusinessRoles.ViewServiceConfigurations], [cluster.service()], [new_user], [])
        self._remove_service(cluster)
        self._add_host(cluster, host)
        with allure.step('Return service back'):
            service = cluster.service_add(name='service_name')
        create_policy(self.client, [BusinessRoles.ViewComponentConfigurations], [service.component()], [new_user], [])
        self._set_hostcomponent(cluster, host)
        new_host = generic_provider.host_create('second')
        with allure.step('Add another host to a cluster'):
            cluster.host_add(new_host)
        create_policy(self.client, [BusinessRoles.ViewHostConfigurations], [new_host], [new_user], [])
        new_host.reread()
        self._remove_host(new_host)
        checker = AuditLogChecker(
            parse_with_context(
                {
                    'cluster_name': cluster.name,
                    'service_display_name': service.display_name,
                    'host_1': host.fqdn,
                    'host_2': new_host.fqdn,
                    'username': NEW_USER['username'],
                }
            )
        )
        checker.set_user_map(self.client)
        checker.check(self.client.audit_operation_list())

    def _accept_license(self, bundle: Bundle, bundle_wo_license: Bundle):
        url = f'{self.client.url}/api/v1/stack/bundle/{bundle.id}/license/accept/'
        with allure.step(f'Deny accepting license via PUT {url}'):
            check_failed(requests.put(url, headers=self.new_user_creds), exact_code=403)
        with allure.step(f'Accept license via PUT {url}'):
            check_succeed(requests.put(url, headers=self.admin_creds))
        url = f'{self.client.url}/api/v1/stack/bundle/{bundle_wo_license.id}/license/accept/'
        with allure.step(f'Fail accepting license via PUT {url}'):
            check_failed(requests.put(url, headers=self.admin_creds), exact_code=409)

    def _add_service(self, cluster):
        service_proto_id = requests.get(cluster.serviceprototype, headers=self.admin_creds).json()[0]['id']
        url = f'{self.client.url}/api/v1/cluster/{cluster.id}/service/'
        data = {'prototype_id': service_proto_id}
        with allure.step(f'Add service via POST {url} with data: {data}'):
            check_succeed(requests.post(url, json=data, headers=self.admin_creds))
        with allure.step(f'Fail to add service via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.admin_creds), exact_code=409)
        with allure.step(f'Get denied trying to add service via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.new_user_creds), exact_code=403)

    def _add_host(self, cluster, host):
        url = f'{self.client.url}/api/v1/cluster/{cluster.id}/host/'
        data = {'host_id': host.id}
        with allure.step(f'Add host to cluster via POST {url} with data: {data}'):
            check_succeed(requests.post(url, json=data, headers=self.admin_creds))
        with allure.step(f'Fail to add host to cluster via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.admin_creds), 409)
        with allure.step(f'Get denied trying to add host to cluster via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.new_user_creds), 403)

    def _set_hostcomponent(self, cluster, host):
        component = (service := cluster.service()).component()
        url = f'{self.client.url}/api/v1/cluster/{cluster.id}/hostcomponent/'
        data = {'hc': [{'service_id': service.id, 'component_id': component.id, 'host_id': host.id}]}
        with allure.step(f'Set HC via POST {url} with data: {data}'):
            check_succeed(requests.post(url, json=data, headers=self.admin_creds))
        data = {}
        with allure.step(f'Fail to set HC via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.admin_creds), exact_code=400)
        with allure.step(f'Get denied to set HC via POST {url} with data: {data}'):
            check_failed(requests.post(url, json=data, headers=self.new_user_creds), exact_code=403)

    def _remove_service(self, cluster):
        service = cluster.service()
        url = f'{self.client.url}/api/v1/cluster/{cluster.id}/service/{service.id}/'
        with allure.step(f'Get denied to remove service via DELETE {url}'):
            check_failed(requests.delete(url, headers=self.new_user_creds), exact_code=403)
        with allure.step(f'Remove service via DELETE {url}'):
            check_succeed(requests.delete(url, headers=self.admin_creds))
        url = f'{self.client.url}/api/v1/cluster/{cluster.id}/service/302/'
        with allure.step(f'Remove service via DELETE {url}'):
            check_failed(requests.delete(url, headers=self.admin_creds), exact_code=404)

    def _remove_host(self, host):
        url = f'{self.client.url}/api/v1/cluster/{host.cluster_id}/host/{host.id}/'
        with allure.step(f'Get denied trying to remove host via DELETE {url}'):
            check_failed(requests.delete(url, headers=self.new_user_creds), exact_code=403)
        with allure.step(f'Remove host via DELETE {url}'):
            check_succeed(requests.delete(url, headers=self.admin_creds))
        url = f'{self.client.url}/api/v1/cluster/{host.cluster_id}/host/543/'
        with allure.step(f'Fail to delete host via DELETE {url}'):
            check_failed(requests.delete(url, headers=self.admin_creds), exact_code=404)


class TestImportAudit:
    """Test audit of imports (binds)"""

    client: ADCMClient
    new_user_creds: dict
    admin_creds: dict

    @pytest.fixture()
    def init(self, sdk_client_fs, unauthorized_creds):
        """Bind common stuff to this instance"""
        self.client = sdk_client_fs
        self.new_user_creds = unauthorized_creds
        self.admin_creds = make_auth_header(self.client)

    @pytest.mark.parametrize('parse_with_context', ['import_updates.yaml'], indirect=True)
    @pytest.mark.usefixtures('grant_cluster_view_permissions', 'init')
    def test_import_updates(self, import_export_clusters, parse_with_context):
        """
        Test update operations related to import/exports:

        - Cluster import added
        - Cluster import removed
        - Service import added
        - Service import removed
        """
        import_cluster, export_cluster = import_export_clusters
        clusters_url = f'{self.client.url}/api/v1/cluster/'
        self._perform_binds(clusters_url, import_cluster, export_cluster)
        self._remove_binds(clusters_url, import_cluster)
        self._update_imports(import_cluster, export_cluster)
        export_service_dn = export_cluster.service().display_name
        checker = AuditLogChecker(
            parse_with_context(
                {
                    'import_cluster': import_cluster.name,
                    'import_service': f'{import_cluster.name}/{import_cluster.service().display_name}',
                    'cluster_import_success_msg': export_cluster.name,
                    'service_import_success_msg': f'{export_cluster.name}/{export_service_dn}',
                    'username': NEW_USER['username'],
                }
            )
        )
        checker.set_user_map(self.client)
        checker.check(self.client.audit_operation_list())

    def _update_imports(self, import_cluster, export_cluster):
        cluster_import_id = import_cluster.imports()[0]['id']
        import_service = import_cluster.service()
        service_import_id = import_service.imports()[0]['id']
        export_service = export_cluster.service()
        cluster_import_path = f'/api/v1/cluster/{import_cluster.id}/import/'
        base_url = self.client.url
        import_path = f'{base_url}/api/v1/cluster/{import_cluster.id}/service/{import_service.id}/import/'
        with allure.step('Update cluster/service imports'):
            data = {'bind': [{'import_id': cluster_import_id, 'export_id': {'cluster_id': export_cluster.id}}]}
            check_succeed(requests.post(f'{self.client.url}{cluster_import_path}', json=data, headers=self.admin_creds))
            data = {
                'bind': [
                    {
                        'import_id': service_import_id,
                        'export_id': {'cluster_id': export_cluster.id, 'service_id': export_service.id},
                    }
                ]
            }
            check_succeed(requests.post(import_path, json=data, headers=self.admin_creds))
        with allure.step('Fail to update cluster/service imports'):
            check_failed(
                requests.post(f'{base_url}{cluster_import_path}', json={}, headers=self.admin_creds), exact_code=400
            )
            check_failed(requests.post(import_path, json={}, headers=self.admin_creds), exact_code=400)
        with allure.step('Performed denied cluster/service imports updates'):
            check_failed(
                requests.post(f'{base_url}{cluster_import_path}', json={}, headers=self.new_user_creds),
                exact_code=403,
            )
            check_failed(requests.post(import_path, json={}, headers=self.new_user_creds), exact_code=403)

    def _perform_binds(self, clusters_url: str, import_cluster, export_cluster):
        export_service = export_cluster.service()
        import_service = import_cluster.service()
        cluster_bind_url = f'{clusters_url}{import_cluster.id}/bind/'
        service_bind_url = f'{clusters_url}{import_cluster.id}/service/{import_service.id}/bind/'
        bind = self._bind
        with allure.step('Bind cluster and service'):
            check_succeed(bind(cluster_bind_url, export_cluster.id, headers=self.admin_creds))
            check_succeed(bind(service_bind_url, export_cluster.id, export_service.id, headers=self.admin_creds))
        with allure.step('Fail to bind cluster and service'):
            check_failed(bind(cluster_bind_url, None, headers=self.admin_creds), exact_code=400)
            check_failed(bind(service_bind_url, None, headers=self.admin_creds), exact_code=400)
        with allure.step('Perform denied cluster/service binding'):
            check_failed(bind(cluster_bind_url, None, headers=self.new_user_creds), exact_code=403)
            check_failed(bind(service_bind_url, None, headers=self.new_user_creds), exact_code=403)

    def _remove_binds(self, clusters_url, import_cluster):
        import_service = import_cluster.service()
        cluster_bind_url = f'{clusters_url}{import_cluster.id}/bind/'
        service_bind_url = f'{clusters_url}{import_cluster.id}/service/{import_service.id}/bind/'
        cluster_bind_id = requests.get(cluster_bind_url, headers=self.admin_creds).json()[0]['id']
        service_bind_id = requests.get(service_bind_url, headers=self.admin_creds).json()[0]['id']
        unbind = self._unbind
        with allure.step('Perform denied cluster/service bind deletion'):
            check_failed(unbind(f'{cluster_bind_url}{cluster_bind_id}/', headers=self.new_user_creds), exact_code=403)
            check_failed(unbind(f'{service_bind_url}{service_bind_id}/', headers=self.new_user_creds), exact_code=403)
        with allure.step('Unbind cluster/service bind deletion'):
            check_succeed(unbind(f'{cluster_bind_url}{cluster_bind_id}/', headers=self.admin_creds))
            check_succeed(unbind(f'{service_bind_url}{service_bind_id}/', headers=self.admin_creds))
        with allure.step('Fail to remove binds from cluster/service'):
            check_failed(unbind(f'{cluster_bind_url}411/', headers=self.admin_creds), exact_code=404)
            check_failed(unbind(f'{service_bind_url}411/', headers=self.admin_creds), exact_code=404)

    def _bind(
        self, url: str, cluster_id: Optional[int], service_id: Optional[int] = None, **kwargs
    ) -> requests.Response:
        body = {
            **({'export_cluster_id': cluster_id} if cluster_id else {}),
            **({'export_service_id': service_id} if service_id else {}),
        }
        with allure.step(f'Create bind via POST {url} with body: {body}'):
            return requests.post(url, json=body, **kwargs)

    @allure.step('Remove bind via DELETE {url}')
    def _unbind(self, url: str, **kwargs) -> requests.Response:
        return requests.delete(url, **kwargs)
