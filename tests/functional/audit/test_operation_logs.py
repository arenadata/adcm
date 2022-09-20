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

"""Test audit operation logs"""

from typing import Tuple

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied
from adcm_client.objects import ADCMClient, Bundle, Host, User
from adcm_pytest_plugin.steps.actions import run_cluster_action_and_assert_result

from tests.functional.audit.conftest import BUNDLES_DIR, ScenarioArg
from tests.functional.conftest import only_clean_adcm
from tests.functional.rbac.conftest import BusinessRoles, create_policy

# pylint: disable=redefined-outer-name

pytestmark = [only_clean_adcm]

CONTEXT = {
    'simple_user': 'simpler',
    'cluster': {
        'name': 'ADB Cluster',
        'adb_service': {
            'name': 'adb',
            'display_name': 'ADB',
        },
    },
    'adb_service_component': 'one_component',
}


@pytest.fixture()
def adb_bundle(sdk_client_fs) -> Bundle:
    """Upload "adb" bundle"""
    return sdk_client_fs.upload_from_fs(BUNDLES_DIR / 'adb')


@pytest.fixture()
def dummy_host(generic_provider) -> Host:
    """Create host from dummy provider"""
    return generic_provider.host_create('dummy-host')


@pytest.fixture()
def new_user_and_client(sdk_client_fs) -> Tuple[User, ADCMClient]:
    """Create new user and login under it"""
    credentials = dict(username=CONTEXT['simple_user'], password='n2ohvzikj(#*Fhxznc')
    user = sdk_client_fs.user_create(**credentials)
    return user, ADCMClient(url=sdk_client_fs.url, user=credentials['username'], password=credentials['password'])


@pytest.mark.xfail(reason='user is not bonded to action completion audit log')
@pytest.mark.parametrize('parsed_audit_log', [ScenarioArg('simple.yaml', CONTEXT)], indirect=True)
def test_simple_flow(sdk_client_fs, audit_log_checker, adb_bundle, dummy_host, new_user_and_client):
    """Test simple from with cluster objects manipulations"""
    config = {'just_string': 'hoho'}
    with allure.step('Create cluster and add service'):
        cluster = adb_bundle.cluster_create(name=CONTEXT['cluster']['name'])
        cluster.host_add(dummy_host)
        service = cluster.service_add(name=CONTEXT['cluster']['adb_service']['name'])
    with allure.step('Set configuration of cluster objects'):
        component = service.component(name=CONTEXT['adb_service_component'])
        component.config_set_diff(config)
        service.config_set_diff(config)
        cluster.config_set_diff(config)
    cluster.hostcomponent_set((dummy_host, component))
    run_cluster_action_and_assert_result(cluster, 'install', 'failed')
    new_user, new_client = new_user_and_client
    create_policy(sdk_client_fs, BusinessRoles.ViewClusterConfigurations, [cluster], users=[new_user], groups=[])
    new_client.reread()
    with allure.step('Try to change config from unauthorized user'):
        try:
            new_client.cluster(id=cluster.id).config_set_diff(config)
        except NoSuchEndpointOrAccessIsDenied:
            pass
        else:
            raise RuntimeError('An error should be raised on attempt of changing config')
    with allure.step('Delete cluster'):
        cluster.delete()
    audit_log_checker.set_user_map(sdk_client_fs)
    audit_log_checker.check(sdk_client_fs.audit_operation_list())
