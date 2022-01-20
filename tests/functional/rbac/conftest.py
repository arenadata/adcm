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
"""Common fixtures and steps for rbac testing"""
import itertools
import os
from enum import Enum
from operator import methodcaller
from typing import Callable, NamedTuple, Union, List, Tuple, Collection

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied, BaseAPIObject
from adcm_client.objects import ADCMClient, User, Group, Cluster, Service, Component, Provider, Host
from adcm_client.wrappers.api import AccessIsDenied
from adcm_pytest_plugin.utils import catch_failed, random_string

# pylint: disable=redefined-outer-name,unused-argument

# Enum names doesn't conform to UPPER_CASE naming style
# pylint: disable=invalid-name
from tests.functional.tools import get_object_represent, AnyADCMObject

TEST_USER_CREDENTIALS = "test_user", "password"
DATA_DIR = os.path.join(os.path.dirname(__file__), "test_business_permissions_data")


class SDKClients(NamedTuple):
    """Container for admin and user ADCM clients"""

    admin: ADCMClient
    user: ADCMClient


class RoleType(Enum):
    """
    Possible values of "type" field in Role object
    """

    HIDDEN = 'hidden'
    BUSINESS = 'business'
    ROLE = 'role'


class RbacRoles(Enum):
    """
    Pre-defined rbac user roles
    """

    ADCMUser = "ADCM User"
    ServiceAdministrator = "Service Administrator"
    ClusterAdministrator = "Cluster Administrator"
    ProviderAdministrator = "Provider Administrator"


class BusinessRole(NamedTuple):
    """Mapping for business role and func to check role permissions"""

    role_name: str
    method_call: Callable


class BusinessRoles(Enum):
    """Complete list of business roles"""

    # pylint: disable=invalid-name

    ViewAnyObjectConfiguration = BusinessRole("View any object configuration", methodcaller("config"))
    ViewAnyObjectHostComponents = BusinessRole("View any object host-components", methodcaller("hostcomponent"))
    ViewAnyObjectImport = BusinessRole("View any object import", methodcaller("imports"))

    ViewClusterConfigurations = BusinessRole("View cluster configurations", methodcaller("config"))
    ViewServiceConfigurations = BusinessRole("View service configurations", methodcaller("config"))
    ViewComponentConfigurations = BusinessRole("View component configurations", methodcaller("config"))
    ViewProviderConfigurations = BusinessRole("View provider configurations", methodcaller("config"))
    ViewHostConfigurations = BusinessRole("View host configurations", methodcaller("config"))

    EditClusterConfigurations = BusinessRole("Edit cluster configurations", methodcaller("config_set_diff", {}))
    EditServiceConfigurations = BusinessRole("Edit service configurations", methodcaller("config_set_diff", {}))
    EditComponentConfigurations = BusinessRole("Edit component configurations", methodcaller("config_set_diff", {}))
    EditProviderConfigurations = BusinessRole("Edit provider configurations", methodcaller("config_set_diff", {}))
    EditHostConfigurations = BusinessRole("Edit host configurations", methodcaller("config_set_diff", {}))

    ViewImports = BusinessRole("View imports", methodcaller("imports"))
    ManageImports = BusinessRole("Manage imports", lambda x, *args: x.bind(*args))
    ViewHostComponents = BusinessRole("View host-components", methodcaller("hostcomponent"))
    EditHostComponents = BusinessRole("Edit host-components", lambda x, *args: x.hostcomponent_set(*args))
    AddService = BusinessRole("Add service", methodcaller("service_add", name="new_service"))
    RemoveService = BusinessRole("Remove service", lambda x, *args: x.service_delete(*args))
    RemoveHosts = BusinessRole("Remove hosts", methodcaller("delete"))
    MapHosts = BusinessRole("Map hosts", lambda x, *args: x.host_add(*args))
    UnmapHosts = BusinessRole("Unmap hosts", lambda x, *args: x.host_delete(*args))
    UpgradeClusterBundle = BusinessRole("Upgrade cluster bundle", lambda x: x.upgrade().do())
    UpgradeProviderBundle = BusinessRole("Upgrade provider bundle", lambda x: x.upgrade().do())
    CreateHostProvider = BusinessRole(
        "Create provider", lambda x: x.provider_create(name=f"new_provider {random_string(5)}")
    )
    CreateHost = BusinessRole("Create host", lambda x: x.host_create(fqdn=f"new_host_{random_string(5)}"))
    RemoveHostProvider = BusinessRole("Remove provider", methodcaller("delete"))
    CreateCluster = BusinessRole("Create cluster", lambda x: x.cluster_create(name=f"new_cluster {random_string(5)}"))
    RemoveCluster = BusinessRole("Remove cluster", methodcaller("delete"))
    UploadBundle = BusinessRole("Upload bundle", methodcaller("upload_from_fs", os.path.join(DATA_DIR, "dummy")))
    RemoveBundle = BusinessRole("Remove bundle", methodcaller("delete"))
    ViewADCMSettings = BusinessRole("View ADCM settings", methodcaller("config"))
    EditADCMSettings = BusinessRole("Edit ADCM settings", methodcaller("config_set_diff", {}))
    ViewUsers = BusinessRole("View users", methodcaller("user_list"))
    CreateUser = BusinessRole("Create user", methodcaller("user_create", username="test", password="test"))
    RemoveUser = BusinessRole("Remove user", methodcaller("delete"))
    EditUser = BusinessRole("Edit user", lambda x: x.update(first_name=random_string(5)))
    ViewRoles = BusinessRole("View roles", methodcaller("role_list"))
    CreateCustomRoles = BusinessRole(
        "Create custom role",
        methodcaller("role_create", name="Custom role", display_name="Custom role", child=[{"id": 2}]),
    )
    RemoveRoles = BusinessRole("Remove roles", methodcaller("delete"))
    EditRoles = BusinessRole("Edit role", lambda x: x.update(display_name=random_string(5)))
    ViewGroups = BusinessRole("View group", methodcaller("group_list"))
    CreateGroup = BusinessRole("Create group", methodcaller("group_create", name="test"))
    RemoveGroup = BusinessRole("Remove group", methodcaller("delete"))
    EditGroup = BusinessRole("Edit group", lambda x: x.update(name=random_string(5)))
    ViewPolicies = BusinessRole("View policy", methodcaller("policy_list"))
    CreatePolicy = BusinessRole(
        "Create policy", lambda x, **kwargs: x.policy_create(name="Test policy", objects=[], **kwargs)
    )
    RemovePolicy = BusinessRole("Remove policy", methodcaller("delete"))
    EditPolicy = BusinessRole("Edit policy", lambda x: x.update(name=random_string(5)))

    # aliases for view/edit_config_of funcs
    ViewADCMConfigurations = ViewADCMSettings
    EditADCMConfigurations = EditADCMSettings

    @staticmethod
    def view_config_of(adcm_object) -> RbacRoles:
        """Get view config role by object's class name"""
        return BusinessRoles[f'View{adcm_object.__class__.__name__}Configurations']

    @staticmethod
    def edit_config_of(adcm_object) -> RbacRoles:
        """Get edit config role by object's class name"""
        return BusinessRoles[f'Edit{adcm_object.__class__.__name__}Configurations']


CLUSTER_VIEW_CONFIG_ROLES = (
    BusinessRoles.ViewClusterConfigurations,
    BusinessRoles.ViewServiceConfigurations,
    BusinessRoles.ViewComponentConfigurations,
)
CLUSTER_EDIT_CONFIG_ROLES = (
    BusinessRoles.EditClusterConfigurations,
    BusinessRoles.EditServiceConfigurations,
    BusinessRoles.EditComponentConfigurations,
)
PROVIDER_VIEW_CONFIG_ROLES = (BusinessRoles.ViewProviderConfigurations, BusinessRoles.ViewHostConfigurations)
PROVIDER_EDIT_CONFIG_ROLES = (BusinessRoles.EditProviderConfigurations, BusinessRoles.EditHostConfigurations)


@pytest.fixture()
@allure.title("Create test user")
def user(sdk_client_fs) -> User:
    """Create user for testing"""
    return sdk_client_fs.user_create(*TEST_USER_CREDENTIALS)


@pytest.fixture()
def user_sdk(user, adcm_fs) -> ADCMClient:
    """Returns ADCMClient object from adcm_client with testing user"""
    username, password = TEST_USER_CREDENTIALS
    return ADCMClient(url=adcm_fs.url, user=username, password=password)


@pytest.fixture()
def clients(sdk_client_fs, user_sdk) -> SDKClients:
    """Get "container" with admin and user clients"""
    return SDKClients(sdk_client_fs, user_sdk)


@pytest.fixture()
def user_policy(request, user, sdk_client_fs, prepare_objects):
    """
    Create testing role and policy
    Parametrize this fixture with `use_role` decorator
    """
    return create_policy(sdk_client_fs, request.param, objects=prepare_objects, users=[user], groups=[])


def use_role(role: Union[BusinessRoles, Collection[BusinessRoles]]):
    """Decorate test func to prepare test user with required business role"""
    return pytest.mark.parametrize("user_policy", [role], indirect=True)


@pytest.fixture()
def prepare_objects(sdk_client_fs):
    """
    Prepare adcm objects
    Created objects should be used as a `parametrized_by_type` values on policy with tested role
    """
    cluster_bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "cluster"))
    cluster = cluster_bundle.cluster_create("Cluster")
    service = cluster.service_add(name="test_service")
    component = service.component(name="test_component")
    provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "provider"))
    provider = provider_bundle.provider_create("Provider")
    host = provider.host_create("Host")
    return cluster, service, component, provider, host


@pytest.fixture()
def second_objects(sdk_client_fs):
    """
    Prepare second adcm objects
    Its objects should not be allowed on tested user
    """
    cluster_bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "second_cluster"))
    cluster = cluster_bundle.cluster_create("Second Cluster")
    service = cluster.service_add(name="test_service")
    component = service.component()
    provider_bundle = sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "second_provider"))
    provider = provider_bundle.provider_create("Second Provider")
    host = provider.host_create("Second_Host")
    return cluster, service, component, provider, host


def as_user_objects(user_sdk: ADCMClient, *objects: AnyADCMObject) -> Tuple[AnyADCMObject, ...]:
    """Get prepared objects via tested user sdk"""
    return tuple((obj.__class__(user_sdk._api, id=obj.id) for obj in objects))  # pylint: disable=protected-access


@allure.step("Delete policy")
def delete_policy(policy):
    """Delete policy"""
    policy.delete()


# pylint: disable-next=too-many-arguments
def create_policy(
    sdk_client,
    permission: Union[BusinessRoles, List[BusinessRoles]],
    objects: list,
    users: List[User],
    groups: List[Group],
    use_all_objects=False,
):
    """Create a new policy for the user and role"""
    obj_dict = {
        "cluster": list(filter(lambda x: isinstance(x, Cluster), objects)),
        "service": list(filter(lambda x: isinstance(x, Service), objects)),
        "component": list(filter(lambda x: isinstance(x, Component), objects)),
        "provider": list(filter(lambda x: isinstance(x, Provider), objects)),
        "host": list(filter(lambda x: isinstance(x, Host), objects)),
    }
    child = []
    for perm in [permission] if isinstance(permission, BusinessRoles) else permission:
        role_name = perm.value.role_name
        business_role = sdk_client.role(name=role_name)
        child.append({"id": business_role.id})
    role_name = f"Testing {random_string(5)}"
    role = sdk_client.role_create(
        name=role_name,
        display_name=role_name,
        child=child,
    )
    if use_all_objects:
        suitable_objects = objects
    elif role.parametrized_by_type:
        suitable_objects = list(itertools.chain(*[obj_dict[obj_type] for obj_type in role.parametrized_by_type]))
        with allure.step(f"Suitable policy objects: {suitable_objects}"):
            pass
        assert suitable_objects, "Could not find suitable policy objects"
    else:
        suitable_objects = []
    policy = sdk_client.policy_create(
        name=f"Policy with role {role_name}", role=role, objects=suitable_objects, user=users, group=groups
    )
    return policy


def is_allowed(
    base_object: Union[BaseAPIObject, ADCMClient], business_role: Union[BusinessRole, BusinessRoles], *args, **kwargs
):
    """
    Assert that role is allowed on object
    """
    role: BusinessRole = business_role.value if isinstance(business_role, BusinessRoles) else business_role
    with allure.step(f"Assert that {role.role_name} on {get_object_represent(base_object)} is allowed"), catch_failed(
        (AccessIsDenied, NoSuchEndpointOrAccessIsDenied),
        f"{role.role_name} on {get_object_represent(base_object)} should be allowed",
    ):
        return role.method_call(base_object, *args, **kwargs)


def is_denied(
    base_object: Union[BaseAPIObject, ADCMClient], business_role: Union[BusinessRole, BusinessRoles], *args, **kwargs
):
    """
    Assert that role is denied on object
    """
    role: BusinessRole = business_role.value if isinstance(business_role, BusinessRoles) else business_role
    with allure.step(f"Assert that {role.role_name} on {get_object_represent(base_object)} is denied"):
        try:
            role.method_call(base_object, *args, **kwargs)
        except (AccessIsDenied, NoSuchEndpointOrAccessIsDenied):
            pass
        else:
            raise AssertionError(f"{role.role_name} on {get_object_represent(base_object)} should not be allowed")
