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
Test config update/restore audit operations
"""

from functools import partial
from operator import attrgetter, itemgetter
from random import randint
from typing import Callable, Literal, Optional, Tuple, Union

import allure
import pytest
import requests
from adcm_client.audit import OperationResult
from adcm_client.objects import ADCM, ADCMClient, Cluster, Component, GroupConfig, Host, Provider, Service
from adcm_pytest_plugin.utils import random_string

from tests.functional.audit.conftest import (
    BUNDLES_DIR,
    NEW_USER,
    check_failed,
    check_succeed,
    make_auth_header,
    parametrize_audit_scenario_parsing,
)
from tests.functional.conftest import only_clean_adcm
from tests.functional.rbac.conftest import BusinessRoles as BR
from tests.functional.rbac.conftest import create_policy
from tests.functional.tools import ClusterRelatedObject, ProviderRelatedObject, get_object_represent

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

ObjectWithConfig = Union[ADCM, ClusterRelatedObject, ProviderRelatedObject]

CONFIG_HISTORY_SUFFIX = 'config/history/'
SERVICE_NAME = 'service_for_updates'
COMPONENT_NAME = 'component_for_updates'
FQDN = 'host-0'

expect_400 = partial(check_failed, exact_code=400)
expect_403 = partial(check_failed, exact_code=403)


@pytest.fixture()
def basic_objects(sdk_client_fs) -> Tuple[Cluster, Service, Component, Provider, Host]:
    """Create cluster, provider and host, add service"""
    cluster = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'update' / 'cluster').cluster_create('Cluster for Updates')
    service = cluster.service_add(name=SERVICE_NAME)
    provider = sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'update' / 'provider').provider_create('Provider for Updates')
    return cluster, service, service.component(), provider, provider.host_create('host-0')


@pytest.fixture()
def grant_view_config_permissions_on_adcm_objects(sdk_client_fs, basic_objects, new_user_client):
    """Create policies that allow new user to get ADCM objects (via View Configuration) and ADCM itself"""
    cluster, service, component, provider, host = basic_objects
    user = sdk_client_fs.user(id=new_user_client.me().id)
    create_policy(
        sdk_client_fs,
        [BR.ViewClusterConfigurations, BR.ViewServiceConfigurations, BR.ViewComponentConfigurations],
        [cluster, service, component],
        users=[user],
        groups=[],
        use_all_objects=True,
    )
    create_policy(
        sdk_client_fs,
        [BR.ViewProviderConfigurations, BR.ViewHostConfigurations],
        [provider, host],
        users=[user],
        groups=[],
        use_all_objects=True,
    )
    create_policy(sdk_client_fs, BR.ViewADCMSettings, [sdk_client_fs.adcm()], users=[user], groups=[])


@pytest.fixture()
def group_configs(basic_objects) -> Tuple[GroupConfig, GroupConfig, GroupConfig]:
    """Create group configs for cluster, service and component"""
    cluster, service, component, *_ = basic_objects
    return (
        cluster.group_config_create('cluster-group'),
        service.group_config_create('service-group'),
        component.group_config_create('component-group'),
    )


@parametrize_audit_scenario_parsing('update_restore_config.yaml', NEW_USER)
@pytest.mark.usefixtures('grant_view_config_permissions_on_adcm_objects')
def test_update_config(basic_objects, audit_log_checker, sdk_client_fs, unauthorized_creds):
    """
    Test audit of config updates on (for results: SUCCESS, FAIL, DENIED):

    - root /api/v1/config-log/
    - direct objects /api/v1/{object_type}/{object_id}/config/history/
    - from parent objects like
         /api/v1/cluster/{c_id}/service/{id}/config/history/
         /api/v1/cluster/{c_id}/host/{id}/config/history/

    And config restore from direct and "from parent" urls.
    """
    cluster, *_, host = basic_objects
    cluster.host_add(host)
    host.reread()
    adcm = sdk_client_fs.adcm()
    drop_from_id = max(*tuple(map(attrgetter('id'), sdk_client_fs.audit_operation_list())))

    def get_correct_adcm_config():
        config = adcm.config(full=True)
        config['description'] = f'Update ADCM config {random_string(4)}'
        config['config']['ansible_settings']['forks'] = 2
        return config

    _check_object_config_update(sdk_client_fs, adcm, unauthorized_creds, get_correct_config=get_correct_adcm_config)
    _check_object_config_restore(
        sdk_client_fs, adcm, unauthorized_creds, get_correct_attrs=lambda: adcm.config(full=True)['attr']
    )
    for obj in basic_objects:
        _check_object_config_update(sdk_client_fs, obj, unauthorized_creds)
        _check_object_config_restore(sdk_client_fs, obj, unauthorized_creds)
    audit_log_checker.set_user_map(sdk_client_fs)
    operations_to_check = tuple(
        filter(lambda o: o.id > drop_from_id, sdk_client_fs.audit_operation_list(paging={'limit': 200}))
    )
    audit_log_checker.check(operations_to_check)


@parametrize_audit_scenario_parsing('update_config_of_group_config.yaml', NEW_USER)
@pytest.mark.usefixtures(
    'grant_view_config_permissions_on_adcm_objects', 'basic_objects'
)  # pylint: disable-next=too-many-locals
def test_update_config_of_group_config(group_configs, audit_log_checker, sdk_client_fs, unauthorized_creds):
    """
    Test audit of group config info/configuration UPDATE operations.
    """
    admin_creds = make_auth_header(sdk_client_fs)
    for group_config in group_configs:
        # pylint: disable-next=unnecessary-lambda-assignment
        drop_object_id = lambda b: {**b, 'object_id': 'hello there'}  # noqa: E731
        with allure.step(f'Update group config info of {group_config.object_type}'):
            for result, credentials, check_response, change_body in (
                (OperationResult.SUCCESS, admin_creds, check_succeed, lambda b: {**b, 'description': 'Changed'}),
                (OperationResult.FAIL, admin_creds, expect_400, drop_object_id),
                (OperationResult.DENIED, unauthorized_creds, expect_403, drop_object_id),
            ):
                update_via = partial(
                    update_group_config_info, sdk_client_fs, group_config, body_mutator=change_body, headers=credentials
                )
                with allure.step(f'Change group config info with result: {result.value}'):
                    check_response(update_via(method='PUT'))
                    check_response(update_via(method='PATCH'))

        default_config = group_config.config(full=True)['config']
        default_attr = group_config.config(full=True)['attr']
        correct_config = {
            'config': {**default_config, 'param_1': random_string(4)},
            'attr': {**default_attr, 'group_keys': {**default_attr['group_keys'], 'param_1': True}},
        }
        incorrect_config = {'config': {**default_config, 'param_1': random_string(4)}, 'attr': {**default_attr}}

        with allure.step(
            f'Update config of group config of {group_config.object_type} with result: {OperationResult.SUCCESS}'
        ):
            check_succeed(update_group_config(group_config, correct_config, headers=admin_creds))
        with allure.step(f'Change group config of {group_config.object_type} with result: {OperationResult.FAIL}'):
            expect_400(update_group_config(group_config, incorrect_config, headers=admin_creds))
        with allure.step(f'Change group config of {group_config.object_type} with result: {OperationResult.DENIED}'):
            expect_403(update_group_config(group_config, incorrect_config, headers=unauthorized_creds))
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list())


@parametrize_audit_scenario_parsing(
    'add_delete_host_group_config.yaml', {'username': NEW_USER['username'], 'host': FQDN}
)
@pytest.mark.usefixtures('grant_view_config_permissions_on_adcm_objects')  # pylint: disable-next=too-many-arguments
def test_add_remove_hosts_from_group_config(
    group_configs, basic_objects, audit_log_checker, sdk_client_fs, post, delete, unauthorized_creds
):
    """
    Test audit of host manipulations with group configs: addition/deletion.
    """
    cluster, _, component, _, host = basic_objects
    cluster.hostcomponent_set((cluster.host_add(host), component))
    host.reread()

    for group_config in group_configs:
        group_hosts_path = f'group-config/{group_config.id}/host'
        with allure.step(f'Successfully add host to {group_config.object_type} group config'):
            check_succeed(post(group_hosts_path, {'id': host.id}))
        with allure.step(f'Fail to add host to {group_config.object_type} group config'):
            expect_400(post(group_hosts_path, {'id': 4030}))
        with allure.step(f'Denied add/delete host requests to/from {group_config.object_type} group config'):
            expect_403(post(group_hosts_path, {'id': 403}, headers=unauthorized_creds))
            expect_403(delete(group_hosts_path, host.id, headers=unauthorized_creds))
        with allure.step(f'Successfully remove host from {group_config.object_type} group config'):
            check_succeed(delete(group_hosts_path, host.id))
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list(paging={'limit': 100}))


# !===== STEPS =====!


def _check_object_config_update(
    client: ADCMClient,
    object_with_config: ObjectWithConfig,
    unauthorized_creds: dict,
    get_correct_config=lambda: {'config': {'param_1': random_string(4), 'param_2': None, 'param_3': None}, 'attr': {}},
    get_incorrect_config=lambda: {'config': {'param_2': randint(0, 50)}, 'attr': {}},
):
    admin_credentials = make_auth_header(client)
    with allure.step(f'Update config of {get_object_represent(object_with_config)}'):
        for result, check_response, get_config, credentials in (
            (OperationResult.SUCCESS, check_succeed, get_correct_config, admin_credentials),
            (OperationResult.FAIL, expect_400, get_incorrect_config, admin_credentials),
            (OperationResult.DENIED, expect_403, get_incorrect_config, unauthorized_creds),
        ):
            with allure.step(f'Run config update that will have result {result.value}'):
                with allure.step('config-log'):
                    check_response(
                        update_config_from_root(client, object_with_config, get_config(), headers=credentials)
                    )
                with allure.step('object config history'):
                    url = get_plain_object_url(client, object_with_config, CONFIG_HISTORY_SUFFIX)
                    check_response(update_config_from_url(url, get_config(), headers=credentials))
                if not isinstance(object_with_config, (Service, Component, Host)):
                    continue
                with allure.step('from parent object'):
                    url = get_object_from_parent_url(client, object_with_config, CONFIG_HISTORY_SUFFIX)
                    check_response(update_config_from_url(url, get_config(), headers=credentials))
                if isinstance(object_with_config, Host):
                    with allure.step('from cluster context'):
                        url = get_host_from_cluster_url(client, object_with_config, CONFIG_HISTORY_SUFFIX)
                        check_response(update_config_from_url(url, get_config(), headers=credentials))


def _check_object_config_restore(
    client: ADCMClient,
    object_with_config: ObjectWithConfig,
    unauthorized_creds: dict,
    get_correct_attrs=lambda: {},
    get_incorrect_attrs=lambda: None,
):
    def get_restore_suffix():
        object_with_config.reread()
        current_config_id = object_with_config.config(full=True)['id']
        # We take as granted that there are multiple configs
        config_id = next(
            map(
                itemgetter('id'),
                filter(lambda c: c['id'] != current_config_id, object_with_config.config_history(full=True)),
            )
        )
        return f'{CONFIG_HISTORY_SUFFIX}{config_id}/restore/'

    admin_credentials = make_auth_header(client)
    with allure.step(f'Restore config of {get_object_represent(object_with_config)}'):
        for result, check_response, get_config, credentials in (
            (OperationResult.FAIL, expect_400, get_incorrect_attrs, admin_credentials),
            (OperationResult.DENIED, expect_403, get_incorrect_attrs, unauthorized_creds),
            (OperationResult.SUCCESS, check_succeed, get_correct_attrs, admin_credentials),
        ):
            with allure.step(f'Run config restore that will have result {result.value}'):
                with allure.step('object config history'):

                    url = get_plain_object_url(client, object_with_config, get_restore_suffix())
                    check_response(restore_config_from_url(url, get_config(), headers=credentials))
                if not isinstance(object_with_config, (Service, Component, Host)):
                    continue
                with allure.step('from parent object'):
                    url = get_object_from_parent_url(client, object_with_config, get_restore_suffix())
                    check_response(restore_config_from_url(url, get_config(), headers=credentials))
                if isinstance(object_with_config, Host):
                    with allure.step('from cluster context'):
                        url = get_host_from_cluster_url(client, object_with_config, get_restore_suffix())
                        check_response(restore_config_from_url(url, get_config(), headers=credentials))


def update_config_from_root(client: ADCMClient, obj: ObjectWithConfig, config: dict, **post_kwargs):
    """
    Update config from object by calling POST on `/api/v1/config-log/`.
    `config` should contain both "config" and "attr" keys.
    """
    url = f'{client.url}/api/v1/config-log/'
    body = {'obj_ref': _get_obj_ref(client, obj), 'description': f'Config {random_string(4)}', **config}
    with allure.step(f'Update config from "root" via POST {url} with data: {body}'):
        return requests.post(url, json=body, **post_kwargs)


def update_config_from_url(url: str, config: dict, **post_kwargs):
    """
    Update config by POSTing given URL.
    `config` should contain both "config" and "attr" keys.
    """
    body = {'description': f'Config {random_string(4)}', **config}
    with allure.step(f'Update config via POST {url} with data: {body}'):
        return requests.post(url, json=body, **post_kwargs)


def restore_config_from_url(url: str, attr: Optional[dict], **patch_kwargs):
    """Restore config by PATCHing given URL"""
    body = {'description': f'Restored config {random_string(4)}', 'attr': attr}
    with allure.step(f'Restore config via PATCH {url} with data: {body}'):
        return requests.patch(url, json=body, **patch_kwargs)


def update_group_config_info(
    client: ADCMClient,
    group_config: GroupConfig,
    method: Literal['PUT', 'PATCH'],
    body_mutator: Callable[[dict], dict],
    **request_kwargs,
):
    """Update group config info with changed by `body_mutator` data"""
    url = f'{client.url}/api/v1/group-config/{group_config.id}/'
    body = body_mutator(requests.get(url, headers=make_auth_header(client)).json())
    with allure.step(f'Update group config info via {method} {url} with data: {body}'):
        return getattr(requests, method.lower())(url, json=body, **request_kwargs)


def update_group_config(group_config: GroupConfig, config: dict, **post_kwargs):
    """update group config configuration"""
    url = f'{group_config.config(full=True)["url"].rsplit("/", maxsplit=2)[0]}/'
    body = {'description': f'New group config {random_string(4)}', **config}
    with allure.step(f'Update configuration of config group via POST {url} with data: {body}'):
        return requests.post(url, json=body, **post_kwargs)


# !===== UTILS =====!


def get_plain_object_url(client: ADCMClient, obj: ObjectWithConfig, suffix: str = '') -> str:
    """
    Get URL for object with given suffix.
    URL will be like '{base_url}/api/v1/{object_type}/{id}/{suffix}'.
    """
    return f'{client.url}/api/v1/{obj.__class__.__name__.lower()}/{obj.id}/{suffix}'


def get_object_from_parent_url(client: ADCMClient, obj: Union[Service, Component, Host], suffix: str = '') -> str:
    """
    Get URL for object from its parent with given suffix.
    URL will be like '{base_url}/api/v1/{parent_type}/{parent_id}/{object_type}/{id}/{suffix}'.
    """
    object_path = {
        Service: lambda o: f'cluster/{o.cluster_id}/service/{o.id}',
        Component: lambda o: f'cluster/{o.cluster_id}/service/{o.service_id}/component/{o.id}',
        Host: lambda o: f'provider/{o.provider_id}/host/{o.id}',
    }[obj.__class__](obj)
    return f'{client.url}/api/v1/{object_path}/{suffix}'


def get_host_from_cluster_url(client: ADCMClient, host: Host, suffix: str = '') -> str:
    """Get URL for host from the cluster it's bonded to"""
    if host.cluster_id is None:
        raise RuntimeError(f'Host {host.fqdn} should be bonded to a cluster')
    return f'{client.url}/api/v1/cluster/{host.cluster_id}/host/{host.id}/{suffix}'


def _get_obj_ref(client: ADCMClient, obj: ObjectWithConfig):
    auth_headers = make_auth_header(client)
    current_config = requests.get(
        f'{client.url}/api/v1/{obj.__class__.__name__.lower()}/{obj.id}/config/current/', headers=auth_headers
    ).json()
    config_log = requests.get(f'{client.url}/api/v1/config-log/{current_config["id"]}', headers=auth_headers).json()
    return config_log['obj_ref']
