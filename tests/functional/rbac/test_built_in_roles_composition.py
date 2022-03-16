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

"""Test composition of built-in ADCM roles"""

from typing import List

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied
from adcm_client.objects import ADCMClient, Role
from adcm_client.wrappers.api import AccessIsDenied
from adcm_pytest_plugin.utils import catch_failed

from tests.library.assertions import is_superset_of
from tests.functional.rbac.conftest import BusinessRoles

pytestmark = [pytest.mark.extra_rbac]

ADCM_USER_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GetAllClusters,
        BusinessRoles.GetAllServices,
        BusinessRoles.GetAllComponents,
        BusinessRoles.GetAllProviders,
        BusinessRoles.GetAllHosts,
        BusinessRoles.ViewAnyObjectConfiguration,
        BusinessRoles.ViewAnyObjectImport,
        BusinessRoles.ViewAnyObjectHostComponents,
    )
}

SERVICE_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GetService,
        BusinessRoles.GetComponent,
        BusinessRoles.GetHost,
        BusinessRoles.EditServiceConfigurations,
        BusinessRoles.EditComponentConfigurations,
        BusinessRoles.ViewHostConfigurations,
        BusinessRoles.ManageServiceImports,
        BusinessRoles.ViewHostComponents,
    )
}

CLUSTER_ADMIN_ROLES = SERVICE_ADMIN_ROLES.union(
    {
        role.value.role_name
        for role in (
            BusinessRoles.ManageClusterImports,
            BusinessRoles.EditClusterConfigurations,
            BusinessRoles.EditHostConfigurations,
            BusinessRoles.MapHosts,
            BusinessRoles.UnmapHosts,
            BusinessRoles.EditHostComponents,
            BusinessRoles.AddService,
            BusinessRoles.RemoveService,
            BusinessRoles.UpgradeClusterBundle,
            BusinessRoles.UploadBundle,
            BusinessRoles.RemoveBundle,
            BusinessRoles.CreateHost,
            BusinessRoles.RemoveHosts,
        )
    }
)

PROVIDER_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GetProvider,
        BusinessRoles.GetHost,
        BusinessRoles.UpgradeProviderBundle,
        BusinessRoles.EditProviderConfigurations,
        BusinessRoles.EditHostConfigurations,
        BusinessRoles.CreateHost,
        BusinessRoles.RemoveHosts,
        BusinessRoles.UploadBundle,
        BusinessRoles.RemoveBundle,
    )
}


def get_children_business_roles(role: Role) -> List[str]:
    """
    Get children roles "recursively"
    """
    result = []
    for child in role.child_list():
        result.append(child.name)
        result += get_children_business_roles(child)
    return result


@pytest.mark.usefixtures('prepare_objects')
def test_default_role(clients):
    """
    Check that newly created user has role "ADCM User"
    """
    user_client = clients.user
    assert user_client.bundle_list(), 'Default user should see bundles in bundle list'
    with catch_failed(
        (AccessIsDenied, NoSuchEndpointOrAccessIsDenied), 'Default user should be able to view ADCM objects'
    ):
        user_client.adcm()
    for object_type in ('cluster', 'service', 'component', 'provider', 'host'):
        assert (
            len(getattr(user_client, f'{object_type}_list')()) == 0
        ), f'List of {object_type} should be empty to default user'


def test_composition(sdk_client_fs: ADCMClient):
    """Check that default roles have all required permissions"""
    for default_role, expected_children in (
        ('Cluster Administrator', CLUSTER_ADMIN_ROLES),
        ('Service Administrator', SERVICE_ADMIN_ROLES),
        ('Provider Administrator', PROVIDER_ADMIN_ROLES),
        ('ADCM User', ADCM_USER_ROLES),
    ):
        with allure.step(f'Check rules for role "{default_role}"'):
            children_roles = set(get_children_business_roles(sdk_client_fs.role(name=default_role)))
            is_superset_of(
                children_roles,
                expected_children,
                'Some of expected roles were not found.\nCheck attachment for more details.',
            )


def _set_to_string(set_to_convert: set) -> str:
    """Sorts set and converts it to a string (items are separated with commas)"""
    return ", ".join(sorted(set_to_convert))
