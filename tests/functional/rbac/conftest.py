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
from typing import Callable, Collection, List, NamedTuple, Optional, Tuple, Union

import allure
import pytest
from adcm_client.base import (
    BaseAPIObject,
    NoSuchEndpointOrAccessIsDenied,
    ObjectNotFound,
)
from adcm_client.objects import (
    ADCM,
    ADCMClient,
    Bundle,
    Cluster,
    Component,
    Group,
    Host,
    Policy,
    Provider,
    Role,
    Service,
    User,
)
from adcm_client.wrappers.api import AccessIsDenied, ADCMApiWrapper
from adcm_pytest_plugin.utils import catch_failed, random_string
from coreapi.exceptions import ErrorMessage

from tests.functional.maintenance_mode.conftest import MM_IS_OFF, MM_IS_ON
from tests.functional.rbac.checkers import Deny
from tests.functional.tools import ADCMObjects, AnyADCMObject, get_object_represent

# pylint: disable=redefined-outer-name

# Enum names doesn't conform to UPPER_CASE naming style


# def pytest_collection_modifyitems(session, config, items: list):
#     """Ignore adcm_with_dummy_data"""
#     # location[0] includes path (relative?) to a file with the test
#     rbac_dummy_data = tuple(
#         filter(lambda i: 'rbac' in i.location[0] and 'adcm_with_dummy_data' in i.callspec.id, items)
#     )
#     for item in rbac_dummy_data:
#         items.remove(item)


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

    HIDDEN = "hidden"
    BUSINESS = "business"
    ROLE = "role"


class RbacRoles(Enum):
    """
    Pre-defined rbac user roles
    """

    ADCM_USER = "ADCM User"
    SERVICE_ADMINISTRATOR = "Service Administrator"
    CLUSTER_ADMINISTRATOR = "Cluster Administrator"
    PROVIDER_ADMINISTRATOR = "Provider Administrator"


class BusinessRole(NamedTuple):
    """Mapping for business role and func to check role permissions"""

    role_name: str
    method_call: Callable
    check_denied: Optional[Callable] = None


class BusinessRoles(Enum):
    """Complete list of business roles"""

    # ADCM Client root roles

    GET_ALL_CLUSTERS = BusinessRole("Get cluster", lambda x, **kwargs: x.cluster(**kwargs))
    GET_ALL_SERVICES = BusinessRole("Get service", lambda x, **kwargs: x.service(**kwargs))
    GET_ALL_COMPONENTS = BusinessRole("Get component", lambda x, **kwargs: x.component(**kwargs))
    GET_ALL_PROVIDERS = BusinessRole("Get provider", lambda x, **kwargs: x.provider(**kwargs))
    GET_ALL_HOSTS = BusinessRole("Get host", lambda x, **kwargs: x.host(**kwargs))
    GET_CLUSTER = BusinessRole("Get cluster object", lambda x, **kwargs: x.cluster(**kwargs))
    GET_SERVICE = BusinessRole("Get service object", lambda x, **kwargs: x.service(**kwargs))
    GET_COMPONENT = BusinessRole("Get component object", lambda x, **kwargs: x.component(**kwargs))
    GET_PROVIDER = BusinessRole("Get provider object", lambda x, **kwargs: x.provider(**kwargs))
    GET_HOST = BusinessRole("Get host object", lambda x, **kwargs: x.host(**kwargs))
    GET_TASK_AND_JOB = BusinessRole("Get task and jobs", lambda x, **kwargs: x.task(**kwargs))

    UPLOAD_BUNDLE = BusinessRole("Upload bundle", methodcaller("upload_from_fs", os.path.join(DATA_DIR, "dummy")))

    VIEW_USERS = BusinessRole("View users", methodcaller("user_list"))
    CREATE_USER = BusinessRole("Create user", methodcaller("user_create", username="test", password="test"))
    VIEW_GROUPS = BusinessRole("View group", methodcaller("group_list"))
    CREATE_GROUP = BusinessRole("Create group", methodcaller("group_create", name="test"))
    VIEW_ROLES = BusinessRole("View roles", methodcaller("role_list"))
    CREATE_CUSTOM_ROLES = BusinessRole(
        "Create custom role",
        lambda client: client.role_create(
            name="Custom role",
            display_name="Custom role",
            child=[{"id": 5}],  # business role without parametrization
        ),
    )
    VIEW_POLICIES = BusinessRole("View policy", methodcaller("policy_list"))
    CREATE_POLICY = BusinessRole(
        "Create policy", lambda x, **kwargs: x.policy_create(name="Test policy", objects=[], **kwargs)
    )

    # ADCM client objects roles (should be checked directly by endpoint)

    VIEW_ANY_OBJECT_CONFIGURATION = BusinessRole(
        "View any object configuration", methodcaller("config"), Deny.ViewConfigOf(ADCMObjects)
    )
    VIEW_ANY_OBJECT_HOST_COMPONENTS = BusinessRole(
        "View any object host-components", methodcaller("hostcomponent"), Deny.ViewHostComponentOf((Cluster, Service))
    )
    VIEW_ANY_OBJECT_IMPORT = BusinessRole(
        "View any object import", methodcaller("imports"), Deny.ViewImportsOf((Cluster, Service))
    )

    VIEW_CLUSTER_CONFIGURATIONS = BusinessRole(
        "View cluster configurations", methodcaller("config"), Deny.ViewConfigOf(Cluster)
    )
    VIEW_SERVICE_CONFIGURATIONS = BusinessRole(
        "View service configurations", methodcaller("config"), Deny.ViewConfigOf(Service)
    )
    VIEW_COMPONENT_CONFIGURATIONS = BusinessRole(
        "View component configurations", methodcaller("config"), Deny.ViewConfigOf(Component)
    )
    VIEW_PROVIDER_CONFIGURATIONS = BusinessRole(
        "View provider configurations", methodcaller("config"), Deny.ViewConfigOf(Provider)
    )
    VIEW_HOST_CONFIGURATIONS = BusinessRole("View host configurations", methodcaller("config"), Deny.ViewConfigOf(Host))

    CREATE_HOST_PROVIDER = BusinessRole(
        "Create provider", lambda x: x.provider_create(name=f"new_provider {random_string(5)}"), Deny.CreateProvider
    )
    CREATE_CLUSTER = BusinessRole(
        "Create cluster", lambda x: x.cluster_create(name=f"new cluster {random_string(5)}"), Deny.CreateCluster
    )
    EDIT_CLUSTER_CONFIGURATIONS = BusinessRole(
        "Edit cluster configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Cluster)
    )
    EDIT_SSERVICE_CONFIGURATIONS = BusinessRole(
        "Edit service configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Service)
    )
    EDIT_COMPONENT_CONFIGURATIONS = BusinessRole(
        "Edit component configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Component)
    )
    EDIT_PROVIDER_CONFIGURATIONS = BusinessRole(
        "Edit provider configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Provider)
    )
    EDIT_HOST_CONFIGURATIONS = BusinessRole(
        "Edit host configurations", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(Host)
    )
    # checks for this role won't work, check fixture that creates changing MM Business roles
    MANAGE_MAINTENANCE_MODE = BusinessRole(
        # to change specific values, pass kwargs to call to denial checker
        "Manage cluster Maintenance mode",
        lambda host, mm_flag: host.maintenance_mode_set(
            mm_flag
        ),  # it won't work with new MM, check corresponding tests
        Deny.Change(Host),  # it won't work with new MM, check corresponding tests
    )

    VIEW_IMPORTS = BusinessRole("View imports", methodcaller("imports"), Deny.ViewImportsOf((Cluster, Service)))
    MANAGE_IMPORTS = BusinessRole(
        "Manage imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf((Cluster, Service))
    )
    MANAGE_CLUSTER_IMPORTS = BusinessRole(
        "Manage cluster imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf(Cluster)
    )
    MANAGE_SERVICE_IMPORTS = BusinessRole(
        "Manage service imports", lambda x, *args: x.bind(*args), Deny.ManageImportsOf(Service)
    )

    VIEW_HOST_COMPONENTS = BusinessRole(
        "View host-components", methodcaller("hostcomponent"), Deny.ViewHostComponentOf(Cluster)
    )
    EDIT_HOST_COMPONENTS = BusinessRole(
        "Edit host-components", lambda x, *args: x.hostcomponent_set(*args), Deny.EditHostComponentOf(Cluster)
    )

    ADD_SERVICE = BusinessRole("Add service", methodcaller("service_add", name="new_service"), Deny.AddServiceToCluster)
    REMOVE_SERVICE = BusinessRole(
        "Remove service", lambda x, *args: x.service_delete(*args), Deny.RemoveServiceFromCluster
    )
    REMOVE_HOSTS = BusinessRole("Remove hosts", methodcaller("delete"), Deny.Delete(Host))
    MAP_HOSTS = BusinessRole("Map hosts", lambda x, *args: x.host_add(*args), Deny.AddHostToCluster)
    UNMAP_HOSTS = BusinessRole("Unmap hosts", lambda x, *args: x.host_delete(*args), Deny.RemoveHostFromCluster)

    UPGRADE_CLUSTER_BUNDLE = BusinessRole("Upgrade cluster bundle", lambda x: x.upgrade().do(), Deny.UpgradeCluster)
    UPGRADE_PROVIDER_BUNDLE = BusinessRole("Upgrade provider bundle", lambda x: x.upgrade().do(), Deny.UpgradeProvider)
    CREATE_HOST = BusinessRole(
        "Create host", lambda x: x.host_create(fqdn=f"new-host-{random_string(5)}"), Deny.CreateHost
    )
    REMOVE_HOST_PROVIDER = BusinessRole("Remove provider", methodcaller("delete"), Deny.Delete(Provider))
    REMOVE_CLUSTER = BusinessRole("Remove cluster", methodcaller("delete"), Deny.Delete(Cluster))
    REMOVE_BUNDLE = BusinessRole("Remove bundle", methodcaller("delete"), Deny.Delete(Bundle))

    VIEW_ADCM_SETTINGS = BusinessRole("View ADCM settings", methodcaller("config"), Deny.ViewConfigOf(ADCM))
    EDIT_ADCM_SETTINGS = BusinessRole(
        "Edit ADCM settings", methodcaller("config_set_diff", {}), Deny.ChangeConfigOf(ADCM)
    )

    REMOVE_USER = BusinessRole("Remove user", methodcaller("delete"), Deny.Delete(User))
    EDIT_USER = BusinessRole("Edit user", lambda x: x.update(first_name=random_string(5)), Deny.Change(User))
    REMOVE_ROLES = BusinessRole("Remove roles", methodcaller("delete"), Deny.Delete(Role))
    EDIT_ROLES = BusinessRole("Edit role", lambda x: x.update(display_name=random_string(5)), Deny.Change(Role))
    REMOVE_GROUP = BusinessRole("Remove group", methodcaller("delete"), Deny.Delete(Group))
    EDIT_GROUP = BusinessRole("Edit group", lambda x: x.update(name=random_string(5)), Deny.Change(Group))
    REMOVE_POLICY = BusinessRole("Remove policy", methodcaller("delete"), Deny.Delete(Policy))
    EDIT_POLICY = BusinessRole("Edit policy", lambda x: x.update(name=random_string(5)), Deny.Change(Policy))

    # aliases for view/edit_config_of funcs
    VIEW_ADCM_CONFIGURATIONS = VIEW_ADCM_SETTINGS
    EDIT_ADCM_CONFIGURATIONS = EDIT_ADCM_SETTINGS

    @staticmethod
    def view_config_of(adcm_object) -> RbacRoles:
        """Get view config role by object's class name"""
        return BusinessRoles[f"View{adcm_object.__class__.__name__}Configurations"]

    @staticmethod
    def edit_config_of(adcm_object) -> RbacRoles:
        """Get edit config role by object's class name"""
        return BusinessRoles[f"Edit{adcm_object.__class__.__name__}Configurations"]


CLUSTER_VIEW_CONFIG_ROLES = (
    BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
    BusinessRoles.VIEW_SERVICE_CONFIGURATIONS,
    BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS,
)
CLUSTER_EDIT_CONFIG_ROLES = (
    BusinessRoles.EDIT_CLUSTER_CONFIGURATIONS,
    BusinessRoles.EDIT_SSERVICE_CONFIGURATIONS,
    BusinessRoles.EDIT_COMPONENT_CONFIGURATIONS,
)
PROVIDER_VIEW_CONFIG_ROLES = (BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
PROVIDER_EDIT_CONFIG_ROLES = (BusinessRoles.EDIT_PROVIDER_CONFIGURATIONS, BusinessRoles.EDIT_HOST_CONFIGURATIONS)


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
    host = provider.host_create("Second-Host")
    return cluster, service, component, provider, host


@pytest.fixture()
def mm_changing_roles(api_client) -> tuple[BusinessRole, BusinessRole, BusinessRole]:
    """
    Prepare utility roles for checking changing MM on various objects: service, component, host
    """

    def change_service_mm(*_, object_id: int, value: str, user_token: str) -> None:
        with api_client.logged_as_another_user(token=user_token):
            api_client.service.change_maintenance_mode(object_id, value)

    def change_component_mm(*_, object_id: int, value: str, user_token: str) -> None:
        with api_client.logged_as_another_user(token=user_token):
            api_client.component.change_maintenance_mode(object_id, value)

    def change_host_mm(*_, object_id: int, value: str, user_token: str) -> None:
        with api_client.logged_as_another_user(token=user_token):
            api_client.host.change_maintenance_mode(object_id, value)

    return (
        BusinessRole("Manage service MM", change_service_mm, change_service_mm),
        BusinessRole("Manage component MM", change_component_mm, change_component_mm),
        BusinessRole("Manage host MM", change_host_mm, change_host_mm),
    )


def get_as_client_object(api: ADCMApiWrapper, obj: AnyADCMObject, **kwargs):
    """Get representation of an object from perspective of given user (client)"""
    return obj.__class__(api, id=obj.id, **kwargs)


def as_user_objects(user_sdk: ADCMClient, *objects: AnyADCMObject) -> Tuple[AnyADCMObject, ...]:
    """Get prepared objects via tested user sdk"""
    api = user_sdk._api  # pylint: disable=protected-access
    objects_repr = ", ".join(get_object_represent(obj) for obj in objects)
    username = user_sdk.me().username
    with allure.step(f"Get object from perspective of {username}: {objects_repr}"):
        with catch_failed(ObjectNotFound, f"Failed to get one of following objects for {username}: {objects_repr}"):
            return tuple((get_as_client_object(api, obj) for obj in objects))


@allure.step("Delete policy")
def delete_policy(policy):
    """Delete policy"""
    policy.delete()


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
            is_superuser = base_object._client.rbac.me.read()["is_superuser"]  # pylint: disable=protected-access
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
                except (AccessIsDenied, NoSuchEndpointOrAccessIsDenied, ObjectNotFound, ErrorMessage):
                    pass
                else:
                    raise AssertionError(f"{role.role_name} on {object_represent} should not be allowed")
        else:
            role.check_denied(client, base_object, **kwargs)


def check_mm_change_is_denied(
    obj: Service | Component | Host,
    denial_method: Union[BusinessRoles, BusinessRole],
    user_client: ADCMClient,
    new_mm_value: str = MM_IS_ON,
    old_mm_value: str = MM_IS_OFF,
):
    """
    Check that change maintenance mode is disallowed to the user
    and the value is the same
    """
    is_denied(
        obj,
        denial_method,
        client=user_client,
        object_id=obj.id,
        value=new_mm_value,
        user_token=user_client.api_token(),
    )
    obj.reread()
    assert (
        obj.maintenance_mode == old_mm_value
    ), f'{obj.__class__.__name__} maintenance mode should be intact and be equal to "{old_mm_value}"'


def check_mm_change_is_allowed(
    obj: Service | Component | Host,
    allow_method: Union[BusinessRoles, BusinessRole],
    user_client: ADCMClient,
    new_mm_value: str = MM_IS_ON,
):
    """
    Check that change maintenance mode is allowed to the user
    and the value changed
    """
    is_allowed(obj, allow_method, object_id=obj.id, value=new_mm_value, user_token=user_client.api_token())
    obj.reread()
    assert obj.maintenance_mode == new_mm_value, f'{obj.__class__.__name__} maintenance mode should be "{new_mm_value}"'


def extract_role_short_info(role: Role) -> RoleShortInfo:
    """Convert API Role object to RoleShortInfo"""
    return RoleShortInfo(role.id, role.name, tuple(role.category))
