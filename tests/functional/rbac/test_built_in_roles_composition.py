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
import json
from typing import List

import allure
from adcm_client.objects import ADCMClient, Role, User

from tests.functional.rbac.conftest import BusinessRoles

ADCM_USER_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.ViewAnyObjectConfiguration,
        BusinessRoles.ViewAnyObjectImport,
        BusinessRoles.ViewAnyObjectHostComponents,
    )
}
SERVICE_ADMIN_ROLES = {
    *ADCM_USER_ROLES,
    BusinessRoles.EditApplicationConfigurations.value.role_name,
    BusinessRoles.ManageImports.value.role_name,
}
CLUSTER_ADMIN_ROLES = SERVICE_ADMIN_ROLES.union(
    {
        role.value.role_name
        for role in (
            BusinessRoles.EditHostComponents,
            BusinessRoles.AddService,
            BusinessRoles.RemoveService,
            BusinessRoles.RemoveHosts,
            BusinessRoles.UpgradeApplicationBundle,
            BusinessRoles.CreateHost,
            BusinessRoles.UploadBundle,
            BusinessRoles.RemoveBundle,
        )
    }
)

PROVIDER_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.UpgradeInfrastructureBundle,
        BusinessRoles.EditInfrastructureConfigurations,
        BusinessRoles.CreateHost,
        BusinessRoles.RemoveHosts,
        BusinessRoles.UploadBundle,
        BusinessRoles.RemoveBundle,
    )
}

BASE_ROLES = {
    'Get ADCM object',
    'Get provider',
    'Get host',
    'Get cluster',
    'Get service',
    'Get component',
    'Get task and jobs',
    'Get stack',
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
            _check_all_roles_are_presented(expected_children, children_roles, default_role)


def _check_all_roles_are_presented(expected_roles: set, found_roles: set, role_name: str):
    """Check if all roles from expected are presented in found roles"""
    not_found_roles = expected_roles.difference(found_roles)
    if not_found_roles:
        allure.attach(
            json.dumps(sorted(found_roles), indent=2),
            name=f'Roles of {role_name}',
            attachment_type=allure.attachment_type.JSON,
        )
        raise AssertionError(
            f'Some roles ({len(not_found_roles)}) were not found for "{role_name}".\n'
            f'Missing roles: {_set_to_string(not_found_roles)}'
        )


def _set_to_string(set_to_convert: set) -> str:
    """Sorts set and converts it to a string (items are separated with commas)"""
    return ", ".join(sorted(set_to_convert))
