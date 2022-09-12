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
from functools import partial
from operator import methodcaller
from typing import Callable, NamedTuple, Union, List, Tuple, Collection, Optional

import allure
import pytest
from adcm_client.base import NoSuchEndpointOrAccessIsDenied, BaseAPIObject, ObjectNotFound
from adcm_client.objects import (
    ADCMClient,
    User,
    Group,
    Cluster,
    Service,
    Component,
    Provider,
    Host,
    Bundle,
    Role,
    ADCM,
    Policy,
)
from adcm_client.wrappers.api import AccessIsDenied, ADCMApiWrapper
from adcm_pytest_plugin.utils import catch_failed, random_string

from tests.functional.rbac.checkers import Deny
from tests.functional.tools import get_object_represent, AnyADCMObject, ADCMObjects


# pylint: disable=redefined-outer-name,unused-argument

# Enum names doesn't conform to UPPER_CASE naming style


def pytest_collection_modifyitems(session, config, items: list):
    """Ignore adcm_with_dummy_data"""
    # location[0] includes path (relative?) to a file with the test
    rbac_dummy_data = tuple(
        filter(lambda i: 'rbac' in i.location[0] and 'adcm_with_dummy_data' in i.callspec.id, items)
    )
    for item in rbac_dummy_data:
        items.remove(item)


TEST_USER_CREDENTIALS = "test_user", "password"
DATA_DIR = os.path.join(os.path.dirname(__file__), "test_business_permissions_data")


class SDKClients(NamedTuple):
    """Container for admin and user ADCM clients"""

    admin: ADCMClient
    user: ADCMClient


class RoleShortInfo(NamedTuple):
    """Minimal required info for working with role info for most cases"""

    id: int
    name: str
    categories: tuple


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
    check_denied: Optional[Callable] = None


class BusinessRoles(Enum):
    """Complete list of business roles"""

    # ADCM Client root roles

    GetAllClusters = BusinessRole("Get cluster", lambda x, **kwargs: x.cluster(**kwargs))
    GetAllServices = BusinessRole("Get service", lambda x, **kwargs: x.service(**kwargs))
    GetAllComponents = BusinessRole("Get component", lambda x, **kwargs: x.component(**kwargs))
    GetAllProviders = BusinessRole("Get provider", lambda x, **kwargs: x.provider(**kwargs))
    GetAllHosts = BusinessRole("Get host", lambda x, **kwargs: x.host(**kwargs))
    GetCluster = BusinessRole("Get cluster object", lambda x, **kwargs: x.cluster(**kwargs))
    GetService = BusinessRole("Get service object", lambda x, **kwargs: x.service(**kwargs))
    GetComponent = BusinessRole("Get component object", lambda x, **kwargs: x.component(**kwargs))
    GetProvider = BusinessRole("Get provider object", lambda x, **kwargs: x.provider(**kwargs))
    GetHost = BusinessRole("Get host object", lambda x, **kwargs: x.host(**kwargs))
    GetTaskAndJob = BusinessRole("Get task and jobs", lambda x, **kwargs: x.task(**kwargs))

    UploadBundle = BusinessRole("Upload bundle", methodcaller("upload_from_fs", os.path.join(DATA_DIR, "dummy")))

    ViewUsers = BusinessRole("View users", methodcaller("user_list"))
    CreateUser = BusinessRole("Create user", methodcaller("user_create", username="test", password="test"))
    ViewGroups = BusinessRole("View group", methodcaller("group_list"))
    CreateGroup = BusinessRole("Create group", methodcaller("group_create", name="test"))
    ViewRoles = BusinessRole("View roles", methodcaller("role_list"))
    CreateCustomRoles = BusinessRole(
        "Create custom role",
        lambda client: client.role_create(
            name="Custom role",
            display_name="Custom role",
            child=[{"id": 5}],  # business role without parametrization
        ),
    )
    ViewPolicies = BusinessRole("View policy", methodcaller("policy_list"))
    CreatePolicy = BusinessRole(
        "Create policy", lambda x, **kwargs: x.policy_create(name="Test policy", objects=[], **kwargs)
    )

    # ADCM client objects roles (should be checked directly by endpoint)

    ViewAnyObjectConfiguration = BusinessRole(
        "View any object configuration", methodcaller("config"), Deny.ViewConfigOf(ADCMObjects)
    )
    ViewAnyObjectHostComponents = BusinessRole(
        "View any object host-components", methodcaller("hostcomponent"), Deny.ViewHostComponentOf((Cluster, Service))
    )
    ViewAnyObjectImport = BusinessRole(
        "View any object import", methodcaller("imports"), Deny.ViewImportsOf((Cluster, Service))
    )

    ViewClusterConfigurations = BusinessRole(
        "View cluster configurations", methodcaller("config"), Deny.ViewConfigOf(Cluster)
    )
    ViewServiceConfigurations = BusinessRole(
        "View service configurations", methodcaller("config"), Deny.ViewConfigOf(Service)
    )
    ViewComponentConfigurations = BusinessRole(
        "View component configurations", methodcaller("config"), Deny.ViewConfigOf(Component)
    )
    ViewProviderConfigurations = BusinessRole(
        "View provider configurations", methodcaller("config"), Deny.ViewConfigOf(Provider)
    )
    ViewHostConfigurations = BusinessRole("View host configurations", methodcaller("config"), Deny.ViewConfigOf(Host))

    CreateHostProvider = BusinessRole(
        "Create provider", lambda x: x.provider_create(name=f"new_provider {random_string(5)}"), Deny.CreateProvider
    )
    CreateCluster = BusinessRole(
        "Create cluster", lambda x: x.cluster_create(name=f"new cluster {random_string(5)}"), Deny.CreateCluster
    )
    EditClusterConfigurations = BusinessRole(
        "Edit cluster configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Cluster)
    )
    EditServiceConfigurations = BusinessRole(
        "Edit service configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Service)
    )
    EditComponentConfigurations = BusinessRole(
        "Edit component configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Component)
    )
    EditProviderConfigurations = BusinessRole(
        "Edit provider configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Provider)
    )
    EditHostConfigurations = BusinessRole(
        "Edit host configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Host)
    )
    ManageMaintenanceMode = BusinessRole(
        # to change specific values, pass kwargs to call to denial checker
        "Manage Maintenance mode",
        lambda host, mm_flag: host.maintenance_mode_set(mm_flag),
        Deny.Change(Host),
    )

    ViewImports = BusinessRole("View imports", methodcaller("imports"), Deny.ViewImportsOf((Cluster, Service)))
    ManageImports = BusinessRole(
        "Manage imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf((Cluster, Service))
    )
    ManageClusterImports = BusinessRole(
        "Manage cluster imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf(Cluster)
    )
    ManageServiceImports = BusinessRole(
        "Manage service imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf(Service)
    )

    ViewHostComponents = BusinessRole(
        "View host-components", methodcaller("hostcomponent"), Deny.ViewHostComponentOf(Cluster)
    )
    EditHostComponents = BusinessRole(
        "Edit host-components", lambda x, *args: x.hostcomponent_set(*args), Deny.EditHostComponentOf(Cluster)
    )

    AddService = BusinessRole("Add service", methodcaller("service_add", name="new_service"), Deny.AddServiceToCluster)
    RemoveService = BusinessRole(
        "Remove service", lambda x, *args: x.service_delete(*args), Deny.RemoveServiceFromCluster
    )
    RemoveHosts = BusinessRole("Remove hosts", methodcaller("delete"), Deny.Delete(Host))
    MapHosts = BusinessRole("Map hosts", lambda x, *args: x.host_add(*args), Deny.AddHostToCluster)
    UnmapHosts = BusinessRole("Unmap hosts", lambda x, *args: x.host_delete(*args), Deny.RemoveHostFromCluster)

    UpgradeClusterBundle = BusinessRole("Upgrade cluster bundle", lambda x: x.upgrade().do(), Deny.UpgradeCluster)
    UpgradeProviderBundle = BusinessRole("Upgrade provider bundle", lambda x: x.upgrade().do(), Deny.UpgradeProvider)
    CreateHost = BusinessRole(
        "Create host", lambda x: x.host_create(fqdn=f"new_host_{random_string(5)}"), Deny.CreateHost
    )
    RemoveHostProvider = BusinessRole("Remove provider", methodcaller("delete"), Deny.Delete(Provider))
    RemoveCluster = BusinessRole("Remove cluster", methodcaller("delete"), Deny.Delete(Cluster))
    RemoveBundle = BusinessRole("Remove bundle", methodcaller("delete"), Deny.Delete(Bundle))

    ViewADCMSettings = BusinessRole("View ADCM settings", methodcaller("config"), Deny.ViewConfigOf(ADCM))
    EditADCMSettings = BusinessRole(
        "Edit ADCM settings", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(ADCM)
    )

    RemoveUser = BusinessRole("Remove user", methodcaller("delete"), Deny.Delete(User))
    EditUser = BusinessRole("Edit user", lambda x: x.update(first_name=random_string(5)), Deny.Change(User))
    RemoveRoles = BusinessRole("Remove roles", methodcaller("delete"), Deny.Delete(Role))
    EditRoles = BusinessRole("Edit role", lambda x: x.update(display_name=random_string(5)), Deny.Change(Role))
    RemoveGroup = BusinessRole("Remove group", methodcaller("delete"), Deny.Delete(Group))
    EditGroup = BusinessRole("Edit group", lambda x: x.update(name=random_string(5)), Deny.Change(Group))
    RemovePolicy = BusinessRole("Remove policy", methodcaller("delete"), Deny.Delete(Policy))
    EditPolicy = BusinessRole("Edit policy", lambda x: x.update(name=random_string(5)), Deny.Change(Policy))

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
def is_denied_to_user(user_sdk: ADCMClient) -> Callable:
    """Return partially initialized `is_denied` function with `client` argument set to `user_sdk`"""
    return partial(is_denied, client=user_sdk)


@pytest.fixture()
def clients(sdk_client_fs, user_sdk) -> SDKClients:
    """Get "container" with admin and user clients"""
    return SDKClients(sdk_client_fs, user_sdk)


@pytest.fixture()
def user_policy(request, user, sdk_client_fs, user_sdk, prepare_objects):
    """
    Create testing role and policy
    Parametrize this fixture with `use_role` decorator
    """
    policy = create_policy(sdk_client_fs, request.param, objects=prepare_objects, users=[user], groups=[])
    user_sdk.reread()
    return policy


def use_role(role: Union[BusinessRoles, Collection[BusinessRoles]]):
    """Decorate test func to prepare test user with required business role"""
    return pytest.mark.parametrize("user_policy", [role], indirect=True)


@pytest.fixture()
def cluster_bundle(sdk_client_fs):
    """Uploaded cluster bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "cluster"))


@pytest.fixture()
def provider_bundle(sdk_client_fs) -> Bundle:
    """Uploaded provider bundle"""
    return sdk_client_fs.upload_from_fs(os.path.join(DATA_DIR, "provider"))


@pytest.fixture()
def prepare_objects(sdk_client_fs, cluster_bundle, provider_bundle):
    """
    Prepare adcm objects
    Created objects should be used as a `parametrized_by_type` values on policy with tested role
    """
    cluster = cluster_bundle.cluster_create("Cluster")
    service = cluster.service_add(name="test_service")
    component = service.component(name="test_component")
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


def get_as_client_object(api: ADCMApiWrapper, obj: AnyADCMObject, **kwargs):
    """Get representation of an object from perspective of given user (client)"""
    return obj.__class__(api, id=obj.id, **kwargs)


def as_user_objects(user_sdk: ADCMClient, *objects: AnyADCMObject) -> Tuple[AnyADCMObject, ...]:
    """Get prepared objects via tested user sdk"""
    api = user_sdk._api  # pylint: disable=protected-access
    objects_repr = ", ".join(get_object_represent(obj) for obj in objects)
    username = user_sdk.me().username
    with allure.step(f'Get object from perspective of {username}: {objects_repr}'):
        with catch_failed(ObjectNotFound, f"Failed to get one of following objects for {username}: {objects_repr}"):
            return tuple((get_as_client_object(api, obj) for obj in objects))


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
    role_name = f"Testing {random_string(5)}"
    if isinstance(permission, Role):
        role = permission
    else:
        for perm in [permission] if isinstance(permission, BusinessRoles) else permission:
            business_role_name = perm.value.role_name
            business_role = sdk_client.role(name=business_role_name)
            child.append({"id": business_role.id})
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
    base_object: Union[BaseAPIObject, ADCMClient],
    business_role: Union[BusinessRole, BusinessRoles],
    *args,
    raise_on_superuser: bool = True,
    **kwargs,
):
    """
    Assert that role is allowed on object.
    """
    if raise_on_superuser:
        if isinstance(base_object, ADCMClient):
            is_superuser = base_object.me().is_superuser
        else:
            is_superuser = base_object._client.rbac.me.read()['is_superuser']  # pylint: disable=protected-access
        if is_superuser:
            raise ValueError(
                "Object that is passed to `is_allowed` method should be an object representative "
                "from a perspective of regular user, not a superuser.\n"
                "If you want to check if the interaction is allowed to a superuser, "
                "pass `False` to `raise_on_superuser` keyword argument."
            )
    role: BusinessRole = business_role.value if isinstance(business_role, BusinessRoles) else business_role
    with allure.step(f"Assert that {role.role_name} on {get_object_represent(base_object)} is allowed"), catch_failed(
        (AccessIsDenied, NoSuchEndpointOrAccessIsDenied),
        f"{role.role_name} on {get_object_represent(base_object)} should be allowed",
    ):
        return role.method_call(base_object, *args, **kwargs)


def is_denied(
    base_object: Union[BaseAPIObject, ADCMClient],
    business_role: Union[BusinessRole, BusinessRoles],
    *args,
    client: Optional[ADCMClient] = None,
    is_list: bool = False,
    **kwargs,
):
    """
    Assert that role is denied on object.

    You may find confusing how `is_allowed` and `is_denied` not mirroring themselves.
    At first, they were: both were based purely on ADCM client and admin-user objects from it.
    But now "getting" object is a part of permission system,
      so we can't "get any object from user client and perform an action on it"
      to check if action is truly denied, because we'll fail on receiving an object.
    So we check the denial of "direct" action via API it this action is performed on another object,
      rather than on ADCM client itself,
      to be sure that we're not checking only the "not allowed via client" situation.

    `is_list` marks if called resource is "list" to check if list is empty (equal to access is denied)
    """
    role: BusinessRole = business_role.value if isinstance(business_role, BusinessRoles) else business_role
    object_is_client = isinstance(base_object, ADCMClient)
    # either `base_object` should be ADCMClient or both role.check_denied and client should be presented
    # notice that priority is given to the first part
    if not (object_is_client or (role.check_denied and client)):
        raise ValueError(
            "You shouldn't try to check if the role actions is denied on objects that are not of type ADCMClient "
            "without providing denial checker.\n"
            "When you pass `business_role` with denial checker, you must also provide `client` argument to check "
            "against which ADCMClient to check denial.\n"
            "To understand motivation behind this please check documentation of `is_denied` method."
        )
    object_represent = get_object_represent(base_object)
    with allure.step(f"Assert that {role.role_name} on {object_represent} is denied"):
        if object_is_client:
            if is_list:
                assert (
                    len(role.method_call(base_object, *args, **kwargs)) == 0
                ), f"{role.role_name} on {object_represent} should not be allowed: items were found in response body"
            else:
                try:
                    role.method_call(base_object, *args, **kwargs)
                except (AccessIsDenied, NoSuchEndpointOrAccessIsDenied, ObjectNotFound):
                    pass
                else:
                    raise AssertionError(f"{role.role_name} on {object_represent} should not be allowed")
        else:
            role.check_denied(client, base_object, **kwargs)


def extract_role_short_info(role: Role) -> RoleShortInfo:
    """Convert API Role object to RoleShortInfo"""
    return RoleShortInfo(role.id, role.name, tuple(role.category))
