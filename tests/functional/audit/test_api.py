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

"""Test API contract via client"""

from enum import Enum
from pathlib import Path
from typing import Any, Callable, Collection, Tuple, Union

import allure
import pytest
import requests
from adcm_client.audit import LoginResult, ObjectType, OperationResult, OperationType
from adcm_client.objects import ADCMClient, Group, Policy, Role, User
from coreapi.exceptions import ErrorMessage

from tests.functional.audit.conftest import check_failed, make_auth_header
from tests.functional.rbac.conftest import BusinessRoles
from tests.library.assertions import sets_are_equal

# pylint: disable=redefined-outer-name

BUNDLES_DIR = Path(__file__).parent / 'bundles'
NOT_EXISTING_USER = 'nosuchuser'


# pylint: disable-next=too-many-arguments
def _check_audit_logs(
    endpoint: str,
    operation: Callable,
    token: str,
    log_field_name: str,
    filters: Union[Enum, Collection[str]],
    check_field_in_records: Callable[
        [str, Any, Collection], bool
    ] = lambda field_name, expected_value, client_logs: all(
        getattr(o, field_name) == expected_value for o in client_logs
    ),
):
    for filter_value in filters:
        simple_type_filter = filter_value.value if isinstance(filter_value, Enum) else filter_value
        with allure.step(f'Check filter {log_field_name}={simple_type_filter}'):
            plain_argument = {log_field_name: filter_value}
            string_filter_args = {log_field_name: simple_type_filter}
            logs_from_client = operation(**plain_argument)
            assert len(logs_from_client) > 0, 'There should be at least one item'
            result = requests.get(endpoint, params=string_filter_args, headers={'Authorization': f'Token {token}'})
            assert result.status_code == 200, (
                f'Querying {endpoint} with filters {result} should end well, '
                f'not with {result.status_code}: {result.json()}'
            )
            items = result.json()['results']
            assert len(logs_from_client) == len(items), 'Client and direct API call returned different results'
            sets_are_equal(
                set(o.id for o in logs_from_client),
                set(i['id'] for i in items),
                'Objects from API and client should be the same',
            )
            assert check_field_in_records(
                log_field_name, filter_value, logs_from_client
            ), f'All operation should have {log_field_name} {filter_value}'


class TestAuditLogsAPI:
    """Test endpoints for audit logs"""

    @allure.title('Upload bundles, create objects and make some manipulations on them')
    @pytest.fixture()
    def various_adcm_objects(self, sdk_client_fs):
        """Upload bundles, create cluster and provider objects, update their configs (and ADCM), set hostcomponent"""
        adcm = sdk_client_fs.adcm()
        adcm.config_set_diff({'ansible_settings': {'forks': 2}})
        provider_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'provider')
        provider = provider_bundle.provider_create('Test Provider')
        cluster_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'cluster')
        cluster = cluster_bundle.cluster_create('Test Cluster')
        service = cluster.service_add(name='example_service')
        component = service.component()
        host = cluster.host_add(provider.host_create('some-fqdn'))
        for obj in (cluster, service, component, provider, host):
            obj.config_set_diff({})
        for obj in (cluster, service, component, provider, host):
            try:
                obj.config_set_diff({'not-exist': 123})
            except ErrorMessage:
                ...
        cluster.hostcomponent_set((host, component))
        return cluster, service, component, provider, host

    @allure.title('Create RBAC objects and update user and group')
    @pytest.fixture()
    def various_rbac_objects(self, sdk_client_fs) -> Tuple[User, Group, Role, Policy]:
        """Create RBAC objects, update user and group"""
        user: User = sdk_client_fs.user_create(username='simple_user', password='password')
        group: Group = sdk_client_fs.group_create('sortofgroup')
        role = sdk_client_fs.role_create(
            'custom role',
            display_name='custom role',
            child=[{"id": sdk_client_fs.role(name=BusinessRoles.ViewADCMConfigurations.value.role_name).id}],
        )
        policy = sdk_client_fs.policy_create('custom policy', role=role, user=[user])
        user.update(first_name='first', last_name='second')
        group.update(description='something else')
        return user, group, role, policy

    @allure.title('Run successful and failed actions on ADCM objects')
    @pytest.fixture()
    def _run_actions(self, various_adcm_objects):
        for action_name in ('success', 'fail'):
            for obj in various_adcm_objects:
                obj.action(name=action_name).run().wait()

    @allure.title('Run denied actions: ADCM config change')
    @pytest.fixture()
    def _prepare_denied_records(self, post, sdk_client_fs, various_rbac_objects):
        user, *_ = various_rbac_objects
        adcm_config_url = f'adcm/{sdk_client_fs.adcm().id}/config/history'
        admin_headers = make_auth_header(ADCMClient(url=sdk_client_fs.url, user=user.username, password='password'))
        for _ in range(10):
            check_failed(post(adcm_config_url, {'blah': 'blah'}, admin_headers), exact_code=403)

    @allure.title('Delete all objects of all types except user')
    @pytest.fixture()
    def _delete_objects(self, various_adcm_objects, various_rbac_objects, _run_actions, _prepare_denied_records):
        cluster, *_, provider, host = various_adcm_objects
        for obj in various_rbac_objects[1:] + (cluster, host, provider):
            obj.delete()

    @pytest.mark.usefixtures('_delete_objects')
    def test_audit_logs_api_filtering(self, sdk_client_fs):
        """
        Test filtering of audit operation logs.
        Date filtering is out of this test's scope.
        """
        for field_name, filters in (
            ('operation_type', OperationType),
            ('operation_result', OperationResult),
            ('operation_name', ('Bundle uploaded', 'ADCM configuration updated')),
            ('object_type', ObjectType),
            ('object_name', ('Test Cluster', 'simple_user')),
        ):
            self._check_audit_operations_filter(sdk_client_fs, field_name, filters)
        admin_id = sdk_client_fs.me().id
        self._check_audit_operations_filter(
            sdk_client_fs,
            'username',
            ['admin'],
            check_field_in_records=lambda _1, _2, logs: all(o.user_id == admin_id for o in logs),
        )

    def _check_audit_operations_filter(
        self, client: ADCMClient, field_name: str, filters: Union[Enum, Collection[str]], **kwargs
    ) -> None:
        endpoint = f'{client.url}/api/v1/audit/operation/'
        client_func = client.audit_operation_list
        token = client.api_token()
        _check_audit_logs(endpoint, client_func, token, field_name, filters, **kwargs)


class TestAuditLoginAPI:
    """Test endpoints for login audit records"""

    @pytest.fixture()
    def users(self, sdk_client_fs) -> Tuple[dict, dict]:
        """Create basic users for login with their credentials"""
        user_1_creds = {'username': 'Bababa', 'password': 'Bebebe'}
        user_2_creds = {'username': 'Augo', 'password': 'Goauel'}
        sdk_client_fs.user_create(**user_1_creds)
        sdk_client_fs.user_create(**user_2_creds)
        return user_1_creds, user_2_creds

    @pytest.fixture()
    def successful_logins(self, sdk_client_fs, users) -> None:
        """Make successful logins"""
        for creds in users:
            self._login(sdk_client_fs, **creds)

    @pytest.fixture()
    def failed_logins(self, sdk_client_fs, users) -> Tuple[dict, dict]:
        """Create required users and make failed logins"""
        user_does_not_exist = {'username': NOT_EXISTING_USER, 'password': 'klfjwoevzlxm02()#U)F('}
        deactivated_user = {'username': 'ohno', 'password': 'imdonneeeee'}
        user = sdk_client_fs.user_create(**deactivated_user)
        user.update(is_active=False)
        self._login(sdk_client_fs, **deactivated_user)
        for creds in users:
            self._login(sdk_client_fs, **{**creds, 'password': 'it is jut wrong'})
        self._login(sdk_client_fs, **user_does_not_exist)
        return deactivated_user, user_does_not_exist

    @pytest.mark.usefixtures('successful_logins', 'failed_logins')
    def test_audit_login_api_filtering(self, sdk_client_fs, users):
        """Test audit log list filtering: by operation result and username"""
        self._check_login_list_filtering(sdk_client_fs, 'login_result', LoginResult)
        self._check_login_list_filtering(
            sdk_client_fs,
            'username',
            [u['username'] for u in users],
            check_field_in_records=lambda _, expected_value, client_logs: all(
                o.user_id == sdk_client_fs.user(username=expected_value).id for o in client_logs
            ),
        )
        with allure.step('Check that filtering by non existing user returns 0 records'):
            assert (
                len(sdk_client_fs.audit_login_list(username=NOT_EXISTING_USER)) == 0
            ), f'Audit login records for username {NOT_EXISTING_USER} should be 0, because there is no such user'

    def _check_login_list_filtering(
        self, client: ADCMClient, field_name: str, filters: Union[Enum, Collection[str]], **kwargs
    ):
        endpoint = f'{client.url}/api/v1/audit/login/'
        client_func = client.audit_login_list
        token = client.api_token()
        _check_audit_logs(endpoint, client_func, token, field_name, filters, **kwargs)

    def _login(self, client, username, password):
        requests.post(f'{client.url}/api/v1/rbac/token/', json={'username': username, 'password': password})
