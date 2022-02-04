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
from adcm_client.objects import ADCMClient, Role, User

from tests.library.assertions import is_superset_of
from tests.functional.rbac.conftest import BusinessRoles

pytestmark = [pytest.mark.full]

ADCM_USER_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GetCluster,
        BusinessRoles.GetService,
        BusinessRoles.GetComponent,
        BusinessRoles.GetProvider,
        BusinessRoles.GetHost,
        BusinessRoles.GetTaskAndJob,
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
        BusinessRoles.GetTaskAndJob,
        BusinessRoles.EditServiceConfigurations,
        BusinessRoles.EditComponentConfigurations,
        BusinessRoles.ViewHostConfigurations,
        BusinessRoles.ManageServiceImports,
    )
}

CLUSTER_ADMIN_ROLES = SERVICE_ADMIN_ROLES.union(
    {
        role.value.role_name
        for role in (
            BusinessRoles.GetCluster,
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
        )
    }
)

PROVIDER_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GetProvider,
        BusinessRoles.GetHost,
        BusinessRoles.GetTaskAndJob,
        BusinessRoles.UpgradeProviderBundle,
        BusinessRoles.EditProviderConfigurations,
        BusinessRoles.EditHostConfigurations,
        BusinessRoles.CreateHost,
        BusinessRoles.RemoveHosts,
        BusinessRoles.UploadBundle,
        BusinessRoles.RemoveBundle,
    )
}

BASE_ROLES = {
    'Get ADCM object',
    'Get stack',
    'Get bundle',
    'Get concerns',
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


def test_default_role(user: User, sdk_client_fs: ADCMClient):
    """
    Check that newly created user has role "ADCM User"
    """
    policies = sdk_client_fs.policy_list()
    user_policies = tuple(filter(lambda p: user.id in (u.id for u in p.user_list()), policies))
    with allure.step('Check default user policy and roles'):
        assert len(user_policies) == 1, 'User should have default policy after creation'
        role_children = {r.name for r in user_policies[0].role().child_list()}
        assert role_children == BASE_ROLES, (
            f'Default roles should be {_set_to_string(BASE_ROLES)}.\n'
            f'But the following were found: {_set_to_string(role_children)}.'
        )


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
