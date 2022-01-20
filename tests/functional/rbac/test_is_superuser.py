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

"""Test user that has superuser rights"""

# pylint: disable=redefined-outer-name

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied
from adcm_client.objects import User, ADCMClient
from adcm_client.wrappers.api import AccessIsDenied
from adcm_pytest_plugin.utils import catch_failed

from tests.functional.tools import get_object_represent
from tests.functional.rbac.conftest import as_user_objects, BusinessRoles, is_allowed

SUPERUSER_CREDENTIALS = {'username': 'supausa', 'password': 'youcantcrackme'}


@pytest.fixture()
def superuser(sdk_client_fs: ADCMClient) -> User:
    """Creates user with superuser rights"""
    return sdk_client_fs.user_create(**SUPERUSER_CREDENTIALS, is_superuser=True)


@pytest.fixture()
def superuser_sdk(superuser, adcm_fs) -> ADCMClient:  # pylint: disable=unused-argument
    """Returns ADCMClient for superuser"""
    creds = SUPERUSER_CREDENTIALS
    return ADCMClient(url=adcm_fs.url, user=creds['username'], password=creds['password'])


def test_access(superuser_sdk, prepare_objects, second_objects):
    """Test that superuser has the same access as Admin"""
    superuser_objects = as_user_objects(superuser_sdk, *prepare_objects)
    superuser_second_objects = as_user_objects(superuser_sdk, *second_objects)

    check_access_to_cluster_objects(superuser_objects, superuser_second_objects)
    check_access_to_provider_objects(superuser_objects)
    check_access_to_general_operations(superuser_sdk, superuser_objects)
    check_access_to_actions_launch(superuser_objects)


@allure.step('Check that superuser has access to cluster-related actions')
def check_access_to_cluster_objects(objects, second_objects):
    """Check that superuser has access to cluster"""
    cluster, service, component, _, host = objects
    second_cluster, second_service, *_ = second_objects

    with allure.step('Check access to basic config manipulations'):
        for obj in cluster, service, component:
            is_allowed(obj, BusinessRoles.view_config_of(obj))
            is_allowed(obj, BusinessRoles.edit_config_of(obj))

    with allure.step('Check access to import manipulations'):
        for obj in cluster, service:
            is_allowed(obj, BusinessRoles.ViewImports)
        is_allowed(cluster, BusinessRoles.ManageImports, second_cluster)
        is_allowed(service, BusinessRoles.ManageImports, second_service)

    with allure.step('Check access to host-related cluster manipulations'):
        is_allowed(cluster, BusinessRoles.ViewHostComponents)
        is_allowed(cluster, BusinessRoles.MapHosts, host)
        is_allowed(cluster, BusinessRoles.UnmapHosts, host)
        cluster.host_add(host)
        is_allowed(cluster, BusinessRoles.EditHostComponents, (host, component))

    with allure.step('Check access to manipulations with services'):
        new_service = is_allowed(cluster, BusinessRoles.AddService)
        is_allowed(cluster, BusinessRoles.RemoveService, new_service)

    with allure.step('Check upgrade is available'):
        is_allowed(cluster, BusinessRoles.UpgradeClusterBundle)


@allure.step('Check that superuser has access to provider-related actions')
def check_access_to_provider_objects(objects):
    """Check that superuser has access to provider"""
    *_, provider, host = objects

    with allure.step('Check access to basic config manipulations'):
        is_allowed(provider, BusinessRoles.view_config_of(provider))
        is_allowed(provider, BusinessRoles.edit_config_of(provider))
        is_allowed(host, BusinessRoles.view_config_of(host))
        is_allowed(host, BusinessRoles.edit_config_of(host))

    with allure.step('Check access to manipulations with host'):
        new_host = is_allowed(provider, BusinessRoles.CreateHost)
        is_allowed(new_host, BusinessRoles.RemoveHosts)

    with allure.step('Check upgrade is available'):
        is_allowed(provider, BusinessRoles.UpgradeProviderBundle)


@allure.step('Check that superuser has access to general actions with RBAC and bundles')
def check_access_to_general_operations(client: ADCMClient, objects):  # pylint: disable=too-many-locals
    """Check that superuser has access to RBAC and bundle-related actions"""
    cluster, _, _, provider, _ = objects
    cluster_bundle, provider_bundle = cluster.bundle(), provider.bundle()

    with allure.step('Check access to manipulations with RBAC'):
        for view_role in (
            BusinessRoles.ViewUsers,
            BusinessRoles.ViewGroups,
            BusinessRoles.ViewRoles,
            BusinessRoles.ViewPolicies,
        ):
            is_allowed(client, view_role)

        for create, edit, remove in (
            (BusinessRoles.CreateUser, BusinessRoles.EditUser, BusinessRoles.RemoveUser),
            (BusinessRoles.CreateGroup, BusinessRoles.EditGroup, BusinessRoles.RemoveGroup),
            (BusinessRoles.CreateCustomRoles, BusinessRoles.EditRoles, BusinessRoles.RemoveRoles),
        ):
            new_entity = is_allowed(client, create)
            is_allowed(new_entity, edit)
            is_allowed(new_entity, remove)

        new_policy = is_allowed(
            client,
            BusinessRoles.CreatePolicy,
            user=[client.user()],
            role=BusinessRoles.CreateCustomRoles.value.method_call(client),
        )
        is_allowed(new_policy, BusinessRoles.EditPolicy)
        is_allowed(new_policy, BusinessRoles.RemovePolicy)

    with allure.step('Check access to manipulations with cluster, provider and bundles'):
        new_cluster = is_allowed(cluster_bundle, BusinessRoles.CreateCluster)
        is_allowed(new_cluster, BusinessRoles.RemoveCluster)
        new_hostprovider = is_allowed(provider_bundle, BusinessRoles.CreateHostProvider)
        is_allowed(new_hostprovider, BusinessRoles.RemoveHostProvider)
        new_bundle = is_allowed(client, BusinessRoles.UploadBundle)
        is_allowed(new_bundle, BusinessRoles.RemoveBundle)


@allure.step('Check that superuser is allowed to run actions')
def check_access_to_actions_launch(objects):
    """Check that superuser can run actions"""
    for obj in objects:
        with catch_failed(
            (AccessIsDenied, NoSuchEndpointOrAccessIsDenied),
            f'Superuser should has right to run action on {get_object_represent(obj)}',
        ):
            obj.action(name='no_config').run().wait()
