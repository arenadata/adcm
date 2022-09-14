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

"""
Test audit operations with "operation_type == CREATE"
"""

from pathlib import Path

import allure
import pytest
from adcm_client.objects import ADCMClient

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    NEW_USER,
    check_failed,
    check_succeed,
    make_auth_header,
    parametrize_audit_scenario_parsing,
)
from tests.functional.rbac.conftest import BusinessRoles, create_policy
from tests.library.audit.checkers import AuditLogChecker

# pylint: disable=redefined-outer-name


class CreateOperation:
    """List of endpoints for convenience"""

    # UPLOAD
    LOAD = 'stack/load'
    UPLOAD = 'stack/upload'
    # CREATE CLUSTER/PROVIDER objects
    CLUSTER = 'cluster'
    PROVIDER = 'provider'
    HOST = 'host'
    HOST_FROM_PROVIDER = 'provider/{provider_id}/host'
    # GROUP CONFIG
    GROUP_CONFIG = 'group-config'
    # RBAC
    USER = 'rbac/user'
    ROLE = 'rbac/role'
    GROUP = 'rbac/group'
    POLICY = 'rbac/policy'


@pytest.fixture()
def new_user_client(sdk_client_fs) -> ADCMClient:
    """Create new user"""
    user = sdk_client_fs.user_create(**NEW_USER)
    return ADCMClient(url=sdk_client_fs.url, user=user.username, password=NEW_USER['password'])


@pytest.mark.parametrize(
    'bundle_archives',
    [
        [
            str(BUNDLES_DIR / 'create' / bundle_dir)
            for bundle_dir in ('incorrect_cluster', 'incorrect_provider', 'cluster', 'provider')
        ]
    ],
    indirect=True,
)
@parametrize_audit_scenario_parsing('create_load_upload.yaml', NEW_USER)
def test_bundle_upload_load(audit_log_checker, post, bundle_archives, sdk_client_fs, new_user_client):
    """Test audit logs for CREATE operations: stack/upload and stack/load"""
    incorrect_cluster_bundle, incorrect_provider_bundle, cluster_bundle, provider_bundle = tuple(
        map(Path, bundle_archives)
    )
    unauthorized_user_creds = make_auth_header(new_user_client)
    with allure.step('Upload and load incorrect bundles (as unauthorized and authorized user)'):
        for bundle_path in (incorrect_cluster_bundle, incorrect_provider_bundle):
            with bundle_path.open('rb') as f:
                check_failed(post(CreateOperation.UPLOAD, files={'file': f}, headers=unauthorized_user_creds), 403)
            with bundle_path.open('rb') as f:
                check_succeed(post(CreateOperation.UPLOAD, files={'file': f}))
            check_failed(
                post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}, headers=unauthorized_user_creds), 403
            )
            check_failed(post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}))
    with allure.step('Upload and load correct bundles (as unauthorized and authorized user)'):
        for bundle_path in (cluster_bundle, provider_bundle):
            with bundle_path.open('rb') as f:
                check_failed(post(CreateOperation.UPLOAD, files={'file': f}, headers=unauthorized_user_creds), 403)
            with bundle_path.open('rb') as f:
                check_succeed(post(CreateOperation.UPLOAD, files={'file': f}))
            check_failed(
                post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}, headers=unauthorized_user_creds), 403
            )
            check_succeed(post(CreateOperation.LOAD, {'bundle_file': bundle_path.name}))
    with allure.step('Load/Upload with incorrect data in request (as unauthorized and authorized user)'):
        check_failed(post(CreateOperation.UPLOAD, files={'wrongkey': 'sldkj'}, headers=unauthorized_user_creds), 403)
        check_failed(post(CreateOperation.LOAD, {'bundle': 'somwthign'}, headers=unauthorized_user_creds), 403)
        check_failed(post(CreateOperation.UPLOAD, files={'wrongkey': 'sldkj'}))
        check_failed(post(CreateOperation.LOAD, {'bundle': 'somwthign'}))
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list())


@pytest.mark.parametrize('parse_with_context', ['create_rbac_entities.yaml'], indirect=True)
def test_rbac_create_operations(parse_with_context, rbac_create_data, post, sdk_client_fs):
    """Test audit logs for CREATE of RBAC objects"""
    audit_checker = AuditLogChecker(parse_with_context(rbac_create_data))
    with allure.step('Create user, try to create its duplicate and make it as an unauthorized user'):
        user_info = rbac_create_data.pop('user')
        check_succeed(post(CreateOperation.USER, user_info))
        new_user_auth_header = make_auth_header(
            ADCMClient(url=sdk_client_fs.url, user=user_info['username'], password=user_info['password'])
        )
        check_failed(post(CreateOperation.USER, user_info))
        check_failed(post(CreateOperation.USER, user_info, headers=new_user_auth_header), 403)

    for object_type, create_data in rbac_create_data.items():
        with allure.step(f'Create {object_type}, try to create its duplicate and make it as an unauthorized user'):
            check_succeed(post(getattr(CreateOperation, object_type.upper()), create_data))
            check_failed(post(getattr(CreateOperation, object_type.upper()), create_data))
            check_failed(
                post(getattr(CreateOperation, object_type.upper()), create_data, headers=new_user_auth_header), 403
            )
    audit_checker.set_user_map(sdk_client_fs)
    audit_checker.check(sdk_client_fs.audit_operation_list())


@parametrize_audit_scenario_parsing('create_adcm_entities.yaml', NEW_USER)  # pylint: disable-next=too-many-locals
def test_create_adcm_objects(audit_log_checker, post, new_user_client, sdk_client_fs):
    """
    Test audit logs for CREATE of ADCM objects:
    - cluster
    - provider
    - host (from `host/` and from `provider/{id}/host/`)
    - group config (on cluster, service and component)
    """
    new_user = sdk_client_fs.user(id=new_user_client.me().id)
    new_user_creds = make_auth_header(new_user_client)
    cluster_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'create' / 'cluster')
    provider_bundle = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'create' / 'provider')
    with allure.step('Create cluster, try to create cluster from incorrect prototype and without permissions'):
        cluster_proto_id = cluster_bundle.cluster_prototype().id
        cluster_create_args = (CreateOperation.CLUSTER, {'prototype_id': cluster_proto_id, 'name': 'cluster'})
        check_succeed(post(*cluster_create_args))
        check_failed(post(CreateOperation.CLUSTER, {'prototype_id': 1000, 'name': 'cluster'}), 404)
        check_failed(post(*cluster_create_args, headers=new_user_creds), 403)
    with allure.step('Create provider, try to create provider from incorrect prototype and without permissions'):
        provider_proto_id = provider_bundle.provider_prototype().id
        provider_create_args = (CreateOperation.PROVIDER, {'prototype_id': provider_proto_id, 'name': 'provider'})
        check_succeed(post(*provider_create_args))
        check_failed(post(CreateOperation.PROVIDER, {'prototype_id': 1000, 'name': 'provider'}), 404)
        check_failed(post(*provider_create_args, headers=new_user_creds), 403)

        provider = sdk_client_fs.provider()
    with allure.step('Create host from root and from provider'):
        host_from_provider_args = {'data': {'fqdn': 'host-from-provider'}, 'path_fmt': {'provider_id': provider.id}}
        check_succeed(post(CreateOperation.HOST_FROM_PROVIDER, **host_from_provider_args))
        host_prototype_id = provider.host().prototype_id
        host_from_root_args = {
            'data': {'fqdn': 'host-from-root', 'prototype_id': host_prototype_id, 'provider_id': provider.id}
        }
        check_succeed(post(CreateOperation.HOST, **host_from_root_args))
    with allure.step('Try to incorrectly create host from root and from provider'):
        check_failed(post(CreateOperation.HOST_FROM_PROVIDER, **host_from_provider_args), 409)
        check_failed(post(CreateOperation.HOST, **host_from_root_args), 409)
    with allure.step('Try to create hosts without permissions'):
        create_policy(  # need it to be able to create host from provider's context
            sdk_client_fs, BusinessRoles.ViewProviderConfigurations, [provider], [new_user], []
        )
        check_failed(post(CreateOperation.HOST_FROM_PROVIDER, **host_from_provider_args, headers=new_user_creds), 403)
        check_failed(post(CreateOperation.HOST, **host_from_root_args, headers=new_user_creds), 403)
    with allure.step(
        'Create group config for cluster, service and component, '
        'try to make their duplicates and create with wrong user'
    ):
        component = (service := (cluster := sdk_client_fs.cluster()).service_add(name='service')).component()
        for obj in (cluster, service, component):
            obj_type = obj.__class__.__name__.lower()
            group_name = f'{obj_type}-group'
            data = {'object_id': obj.id, 'object_type': obj_type, 'name': group_name}
            check_succeed(post(CreateOperation.GROUP_CONFIG, data))
            check_failed(post(CreateOperation.GROUP_CONFIG, data), 400)
            check_failed(post(CreateOperation.GROUP_CONFIG, data, headers=new_user_creds), 403)
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list())
