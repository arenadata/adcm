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


import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied
from adcm_client.objects import ADCMClient, Role
from adcm_client.wrappers.api import AccessIsDenied
from adcm_pytest_plugin.utils import catch_failed

from tests.functional.rbac.conftest import BusinessRoles
from tests.library.assertions import is_superset_of

pytestmark = [pytest.mark.extra_rbac]

ADCM_USER_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GET_ALL_CLUSTERS,
        BusinessRoles.GET_ALL_SERVICES,
        BusinessRoles.GET_ALL_COMPONENTS,
        BusinessRoles.GET_ALL_PROVIDERS,
        BusinessRoles.GET_ALL_HOSTS,
        BusinessRoles.VIEW_ANY_OBJECT_CONFIGURATION,
        BusinessRoles.VIEW_ANY_OBJECT_IMPORT,
        BusinessRoles.VIEW_ANY_OBJECT_HOST_COMPONENTS,
    )
}

SERVICE_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GET_SERVICE,
        BusinessRoles.GET_COMPONENT,
        BusinessRoles.GET_HOST,
        BusinessRoles.EDIT_SERVICE_CONFIGURATIONS,
        BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS,
        BusinessRoles.VIEW_HOST_CONFIGURATIONS,
        BusinessRoles.MANAGE_SERVICE_IMPORTS,
        BusinessRoles.VIEW_HOST_COMPONENTS,
    )
}

CLUSTER_ADMIN_ROLES = SERVICE_ADMIN_ROLES.union(
    {
        role.value.role_name
        for role in (
            BusinessRoles.MANAGE_CLUSTER_IMPORTS,
            BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS,
            BusinessRoles.EDIT_HOST_CONFIGURATIONS,
            BusinessRoles.MAP_HOSTS,
            BusinessRoles.UNMAP_HOSTS,
            BusinessRoles.EDIT_HOST_COMPONENTS,
            BusinessRoles.ADD_SERVICE,
            BusinessRoles.REMOVE_SERVICE,
            BusinessRoles.UPGRADE_CLUSTER_BUNDLE,
            BusinessRoles.UPLOAD_BUNDLE,
            BusinessRoles.REMOVE_BUNDLE,
            BusinessRoles.CREATE_HOST,
            BusinessRoles.REMOVE_HOSTS,
        )
    },
)

PROVIDER_ADMIN_ROLES = {
    role.value.role_name
    for role in (
        BusinessRoles.GET_PROVIDER,
        BusinessRoles.GET_HOST,
        BusinessRoles.UPGRADE_PROVIDER_BUNDLE,
        BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS,
        BusinessRoles.EDIT_HOST_CONFIGURATIONS,
        BusinessRoles.CREATE_HOST,
        BusinessRoles.REMOVE_HOSTS,
        BusinessRoles.UPLOAD_BUNDLE,
        BusinessRoles.REMOVE_BUNDLE,
    )
}


def get_children_business_roles(role: Role) -> list[str]:
    """
    Get children roles "recursively"
    """
    result = []
    for child in role.child_list():
        result.append(child.name)
        result += get_children_business_roles(child)
    return result


@pytest.mark.usefixtures("prepare_objects")
def test_default_role(clients):
    """
    Check that newly created user has role "ADCM User"
    """
    user_client = clients.user
    assert user_client.bundle_list(), "Default user should see bundles in bundle list"
    with catch_failed(
        (AccessIsDenied, NoSuchEndpointOrAccessIsDenied),
        "Default user should be able to view ADCM objects",
    ):
        user_client.adcm()
    for object_type in ("cluster", "service", "component", "provider", "host"):
        assert (
            len(getattr(user_client, f"{object_type}_list")()) == 0
        ), f"List of {object_type} should be empty to default user"


def test_composition(sdk_client_fs: ADCMClient):
    """Check that default roles have all required permissions"""
    for default_role, expected_children in (
        ("Cluster Administrator", CLUSTER_ADMIN_ROLES),
        ("Service Administrator", SERVICE_ADMIN_ROLES),
        ("Provider Administrator", PROVIDER_ADMIN_ROLES),
        ("ADCM User", ADCM_USER_ROLES),
    ):
        with allure.step(f'Check rules for role "{default_role}"'):
            children_roles = set(get_children_business_roles(sdk_client_fs.role(name=default_role)))
            is_superset_of(
                children_roles,
                expected_children,
                "Some of expected roles were not found.\nCheck attachment for more details.",
            )


def _set_to_string(set_to_convert: set) -> str:
    """Sorts set and converts it to a string (items are separated with commas)"""
    return ", ".join(sorted(set_to_convert))
