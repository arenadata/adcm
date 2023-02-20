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

"""Test business permissions related to cluster objects"""

# pylint: disable=too-many-locals
import itertools

import allure
import pytest
from adcm_client.objects import ADCMClient, Policy

from tests.functional.rbac.conftest import (
    CLUSTER_EDIT_CONFIG_ROLES,
    CLUSTER_VIEW_CONFIG_ROLES,
    PROVIDER_EDIT_CONFIG_ROLES,
    PROVIDER_VIEW_CONFIG_ROLES,
)
from tests.functional.rbac.conftest import BusinessRoles as BR  # noqa: N817
from tests.functional.rbac.conftest import (
    RbacRoles,
    as_user_objects,
    check_mm_change_is_allowed,
    create_policy,
    delete_policy,
    is_allowed,
    is_denied,
    use_role,
)

pytestmark = [pytest.mark.extra_rbac]


def _build_view_edit_allow(get_view_or_edit):
    """Helper to build multiple objects check functions"""

    def check(*objects):
        for adcm_object in objects:
            is_allowed(adcm_object, get_view_or_edit(adcm_object))

    return check


def _build_view_edit_deny(get_view_or_edit):
    """Helper to build multiple objects deny check functions"""

    def check(*objects, client=None):
        for adcm_object in objects:
            is_denied(adcm_object, get_view_or_edit(adcm_object), client=client)

    return check


is_allowed_to_view = _build_view_edit_allow(BR.view_config_of)
is_allowed_to_edit = _build_view_edit_allow(BR.edit_config_of)
is_denied_to_view = _build_view_edit_deny(BR.view_config_of)
is_denied_to_edit = _build_view_edit_deny(BR.edit_config_of)


@use_role(CLUSTER_VIEW_CONFIG_ROLES)
def test_view_application_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View application configuration role is ok"""
    cluster, service, component, provider, host = prepare_objects
    second_service_on_first_cluster = cluster.service_add(name="new_service")
    second_component_on_first_cluster = second_service_on_first_cluster.component(name="test_component")

    objects_affected_by_policy = as_user_objects(
        user_sdk,
        cluster,
        service,
        component,
        second_service_on_first_cluster,
        second_component_on_first_cluster,
    )

    is_allowed_to_view(*objects_affected_by_policy)
    is_denied_to_edit(*objects_affected_by_policy, client=user_sdk)
    is_denied_to_view(provider, host, *second_objects, client=user_sdk)
    delete_policy(user_policy)
    is_denied_to_view(*objects_affected_by_policy, client=user_sdk)


@use_role(PROVIDER_VIEW_CONFIG_ROLES)
def test_view_infrastructure_configurations(
    user_policy: Policy,
    user_sdk: ADCMClient,
    prepare_objects,
    second_objects,
):
    """Test that View infrastructure configuration role is ok"""
    cluster, service, component, provider, host = prepare_objects
    second_host_on_first_provider = provider.host_create(fqdn="new-host")

    # second host on first provider will be allowed to view because of provider's permission
    allowed_to_view_objects = as_user_objects(user_sdk, provider, host, second_host_on_first_provider)
    is_allowed_to_view(*allowed_to_view_objects)
    is_denied_to_edit(*allowed_to_view_objects, client=user_sdk)
    is_denied_to_view(cluster, service, component, *second_objects, client=user_sdk)
    delete_policy(user_policy)
    is_denied_to_view(*allowed_to_view_objects, client=user_sdk)


@use_role(CLUSTER_EDIT_CONFIG_ROLES)
def test_edit_application_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit application configuration role is ok"""
    cluster, service, component, provider, host = prepare_objects

    allowed_user_objects = as_user_objects(user_sdk, cluster, service, component)
    is_allowed_to_view(*allowed_user_objects)
    is_allowed_to_edit(*allowed_user_objects)
    is_denied_to_edit(*second_objects, user_sdk.adcm(), provider, host, client=user_sdk)
    delete_policy(user_policy)
    is_denied_to_edit(*allowed_user_objects, client=user_sdk)
    is_denied_to_view(*allowed_user_objects, client=user_sdk)


@use_role(PROVIDER_EDIT_CONFIG_ROLES)
def test_edit_infrastructure_configurations(
    user_policy: Policy,
    user_sdk: ADCMClient,
    prepare_objects,
    second_objects,
):
    """Test that Edit infrastructure configuration role is ok"""
    cluster, service, component, provider, host = prepare_objects

    allowed_user_objects = as_user_objects(user_sdk, provider, host)
    is_allowed_to_view(*allowed_user_objects)
    is_allowed_to_edit(*allowed_user_objects)
    is_denied_to_edit(*second_objects, user_sdk.adcm(), cluster, service, component, client=user_sdk)
    delete_policy(user_policy)
    is_denied_to_edit(*allowed_user_objects, client=user_sdk)
    is_denied_to_view(*allowed_user_objects, client=user_sdk)


@use_role(BR.VIEW_IMPORTS)
def test_view_imports(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that View imports role is ok"""
    admin_cluster_second, admin_service_second, *_ = second_objects
    cluster, service = as_user_objects(user_sdk, *prepare_objects[:2])
    for base_object in (cluster, service):
        is_allowed(base_object, BR.VIEW_IMPORTS)
        is_denied_to_user(base_object, BR.MANAGE_IMPORTS)
    for base_object in (admin_cluster_second, admin_service_second):
        is_denied_to_user(base_object, BR.VIEW_IMPORTS)
    delete_policy(user_policy)
    for base_object in (cluster, service):
        is_denied_to_user(base_object, BR.VIEW_IMPORTS)


@use_role(BR.MANAGE_IMPORTS)
def test_manage_imports(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Manage imports role is ok"""
    admin_cluster, admin_service, *_ = prepare_objects
    cluster, service = as_user_objects(user_sdk, admin_cluster, admin_service)
    admin_cluster_second, admin_service_second, *_ = second_objects

    for base_object in [cluster, service]:
        is_allowed(base_object, BR.VIEW_IMPORTS)
        is_allowed(base_object, BR.MANAGE_IMPORTS, admin_service_second)
    for base_object in [admin_cluster_second, admin_service_second]:
        is_denied_to_user(base_object, BR.VIEW_IMPORTS)
    delete_policy(user_policy)
    for bind in itertools.chain(admin_cluster.bind_list(), admin_service.bind_list()):
        bind.delete()
    for base_object in [admin_cluster, admin_service]:
        is_denied_to_user(base_object, BR.VIEW_IMPORTS)
        is_denied_to_user(base_object, BR.MANAGE_IMPORTS, admin_service_second)


@use_role(BR.VIEW_HOST_COMPONENTS)
def test_view_hostcomponents(
    user_policy: Policy,
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
):
    """Test that View host-components role is ok"""
    cluster_via_admin, *_, host_via_admin = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin, *_ = second_objects
    cluster_via_admin.host_add(host_via_admin)

    is_allowed(cluster, BR.VIEW_HOST_COMPONENTS)
    is_denied_to_user(second_cluster_via_admin, BR.VIEW_HOST_COMPONENTS)
    is_denied_to_user(cluster, BR.EDIT_HOST_COMPONENTS)
    delete_policy(user_policy)
    is_denied_to_user(cluster, BR.VIEW_HOST_COMPONENTS)


@use_role(BR.EDIT_HOST_COMPONENTS)
def test_edit_hostcomponents(
    user_policy: Policy,
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
):
    """Test that Edit host-components role is ok"""

    cluster_via_admin, _, component_via_admin, _, host_via_admin = prepare_objects
    second_cluster_via_admin, *_, second_host_via_admin = second_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)

    cluster_via_admin.host_add(host_via_admin)
    second_cluster_via_admin.host_add(second_host_via_admin)

    is_allowed(cluster, BR.VIEW_HOST_COMPONENTS)
    is_allowed(cluster, BR.EDIT_HOST_COMPONENTS, (host_via_admin, component_via_admin))
    is_denied_to_user(second_cluster_via_admin, BR.VIEW_HOST_COMPONENTS)
    is_denied_to_user(second_cluster_via_admin, BR.EDIT_HOST_COMPONENTS)
    delete_policy(user_policy)
    is_denied_to_user(cluster, BR.VIEW_HOST_COMPONENTS)
    is_denied_to_user(cluster, BR.EDIT_HOST_COMPONENTS)


@use_role(BR.ADD_SERVICE)
def test_add_service(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Add service role is ok"""
    cluster_via_admin, *_ = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin, *_ = second_objects

    is_allowed(cluster, BR.ADD_SERVICE)
    added_service = cluster.service(name="new_service")
    is_denied_to_user(added_service, BR.REMOVE_SERVICE, added_service)
    is_denied_to_user(second_cluster_via_admin, BR.ADD_SERVICE)
    cluster_via_admin.service(name="new_service").delete()
    delete_policy(user_policy)
    is_denied_to_user(cluster, BR.ADD_SERVICE)


@use_role(BR.REMOVE_SERVICE)
def test_remove_service(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Remove service role is ok"""
    cluster_via_admin, service_via_admin, *_ = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin, second_service_via_admin, *_ = second_objects

    is_denied_to_user(cluster_via_admin, BR.ADD_SERVICE)
    is_allowed(cluster, BR.REMOVE_SERVICE, service_via_admin)
    is_denied_to_user(service_via_admin, BR.REMOVE_SERVICE)

    second_cluster_via_admin.service_add(name="new_service")
    is_denied_to_user(second_service_via_admin, BR.REMOVE_SERVICE)

    delete_policy(user_policy)
    cluster_via_admin.service_add(name="test_service")
    is_denied_to_user(service_via_admin, BR.REMOVE_SERVICE)


@use_role(BR.REMOVE_HOSTS)
def test_remove_hosts(
    user_policy: Policy,
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
    sdk_client_fs,
    user,
):
    """Test that Remove hosts role is ok"""
    *_, admin_host = prepare_objects
    *_, admin_host_second = second_objects
    *_, host = as_user_objects(user_sdk, admin_host)

    is_allowed(host, BR.REMOVE_HOSTS)
    is_denied_to_user(admin_host_second, BR.REMOVE_HOSTS)
    with allure.step("Assert that policy is valid after object removing"):
        user_policy.reread()

    new_policy = create_policy(sdk_client_fs, BR.REMOVE_HOSTS, objects=[admin_host_second], users=[user], groups=[])
    delete_policy(new_policy)
    is_denied_to_user(admin_host_second, BR.REMOVE_HOSTS)


@use_role(BR.MAP_HOSTS)
def test_map_hosts(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Map hosts role is ok"""
    admin_cluster, *_, admin_host = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, admin_cluster)
    admin_cluster_second, *_, admin_provider, _ = second_objects

    admin_provider.host_create(fqdn="new-host")
    is_allowed(cluster, BR.MAP_HOSTS, admin_host)
    admin_host.reread()
    is_denied_to_user(admin_host, BR.UNMAP_HOSTS)
    is_denied_to_user(admin_cluster_second, BR.MAP_HOSTS)

    delete_policy(user_policy)

    is_denied_to_user(cluster, BR.MAP_HOSTS)


@use_role(BR.UNMAP_HOSTS)
def test_unmap_hosts(user_policy: Policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Unmap hosts role is ok"""
    cluster_via_admin, *_, provider_via_admin, host_via_admin = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin, *_, second_host_via_admin = second_objects

    is_denied_to_user(cluster, BR.MAP_HOSTS)
    is_denied_to_user(host_via_admin, BR.REMOVE_HOSTS)
    cluster_via_admin.host_add(host_via_admin)
    host, *_ = as_user_objects(user_sdk, host_via_admin)
    is_allowed(cluster, BR.UNMAP_HOSTS, host)

    second_cluster_via_admin.host_add(second_host_via_admin)
    second_host_via_admin.reread()
    is_denied_to_user(second_host_via_admin, BR.UNMAP_HOSTS)

    delete_policy(user_policy)

    new_host = provider_via_admin.host_create(fqdn="new-host")
    cluster_via_admin.host_add(new_host)
    new_host.reread()
    is_denied_to_user(new_host, BR.UNMAP_HOSTS)


@use_role(BR.UPGRADE_CLUSTER_BUNDLE)
@pytest.mark.usefixtures("second_objects")
def test_upgrade_application_bundle(
    user_policy,  # pylint: disable=unused-argument
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    sdk_client_fs,
    user,
):
    """Test that Upgrade application bundle role is ok"""
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin = cluster_via_admin.bundle().cluster_create(name="Second cluster")

    is_allowed(cluster, BR.UPGRADE_CLUSTER_BUNDLE)
    is_denied_to_user(provider_via_admin, BR.UPGRADE_PROVIDER_BUNDLE)
    is_denied_to_user(second_cluster_via_admin, BR.UPGRADE_CLUSTER_BUNDLE)

    new_policy = create_policy(
        sdk_client_fs,
        BR.UPGRADE_CLUSTER_BUNDLE,
        objects=[second_cluster_via_admin],
        users=[user],
        groups=[],
    )
    delete_policy(new_policy)
    is_denied_to_user(second_cluster_via_admin, BR.UPGRADE_CLUSTER_BUNDLE)


@use_role(BR.UPGRADE_PROVIDER_BUNDLE)
@pytest.mark.usefixtures("second_objects")
def test_upgrade_infrastructure_bundle(
    user_policy,  # pylint: disable=unused-argument
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    sdk_client_fs,
    user,
):
    """Test that Upgrade infrastructure bundle role is ok"""
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    provider, *_ = as_user_objects(user_sdk, provider_via_admin)
    second_provider_via_admin = provider_via_admin.bundle().provider_create(name="Second provider")

    is_allowed(provider, BR.UPGRADE_PROVIDER_BUNDLE)
    is_denied_to_user(cluster_via_admin, BR.UPGRADE_CLUSTER_BUNDLE)
    is_denied_to_user(second_provider_via_admin, BR.UPGRADE_PROVIDER_BUNDLE)

    new_policy = create_policy(
        sdk_client_fs,
        BR.UPGRADE_PROVIDER_BUNDLE,
        objects=[second_provider_via_admin],
        users=[user],
        groups=[],
    )
    delete_policy(new_policy)
    is_denied_to_user(second_provider_via_admin, BR.UPGRADE_PROVIDER_BUNDLE)


@use_role(BR.CREATE_HOST_PROVIDER)
def test_create_provider(user_policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Create provider role is ok"""
    cluster, *_, provider, _ = prepare_objects
    *_, second_provider, _ = second_objects
    provider_bundle_first, provider_bundle_second = as_user_objects(
        user_sdk,
        provider.bundle(),
        second_provider.bundle(),
    )

    is_allowed(provider_bundle_first, BR.CREATE_HOST_PROVIDER)
    is_allowed(provider_bundle_second, BR.CREATE_HOST_PROVIDER)
    is_denied_to_user(provider, BR.CREATE_HOST)
    is_denied_to_user(provider, BR.CREATE_HOST)
    is_denied_to_user(cluster.bundle(), BR.CREATE_CLUSTER)

    delete_policy(user_policy)
    is_denied_to_user(provider.bundle(), BR.CREATE_HOST_PROVIDER)


@use_role(BR.CREATE_HOST)
def test_create_host(user_policy, user_sdk: ADCMClient, is_denied_to_user, prepare_objects, second_objects):
    """Test that Create host role is ok"""
    admin_cluster, *_, admin_provider, admin_host = prepare_objects
    provider, *_ = as_user_objects(user_sdk, admin_provider)
    *_, admin_second_provider, admin_second_host = second_objects

    is_allowed(provider, BR.CREATE_HOST)
    is_denied_to_user(admin_host, BR.REMOVE_HOSTS)
    is_denied_to_user(admin_cluster, BR.MAP_HOSTS, admin_host)
    is_denied_to_user(admin_second_provider, BR.CREATE_HOST)
    is_denied_to_user(admin_second_host, BR.REMOVE_HOSTS)

    delete_policy(user_policy)
    is_denied_to_user(admin_provider, BR.CREATE_HOST)


@use_role(BR.REMOVE_HOST_PROVIDER)
def test_remove_provider(
    user_policy,  # pylint: disable=unused-argument
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
    sdk_client_fs,
    user,
):
    """Test that Remove provider role is ok"""
    *_, provider_via_admin, host_via_admin = prepare_objects
    provider, *_ = as_user_objects(user_sdk, provider_via_admin)

    *_, second_provider_via_admin, second_host_via_admin = second_objects

    is_denied_to_user(host_via_admin, BR.REMOVE_HOSTS)
    host_via_admin.delete()
    second_host_via_admin.delete()
    is_allowed(provider, BR.REMOVE_HOST_PROVIDER)
    is_denied_to_user(second_provider_via_admin, BR.REMOVE_HOST_PROVIDER)

    new_policy = create_policy(
        sdk_client_fs,
        BR.REMOVE_HOST_PROVIDER,
        objects=[second_provider_via_admin],
        users=[user],
        groups=[],
    )
    user_sdk.reread()
    delete_policy(new_policy)
    is_denied_to_user(second_provider_via_admin, BR.REMOVE_HOST_PROVIDER)


@use_role(BR.CREATE_CLUSTER)
def test_create_cluster(
    user_policy,
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
):  # pylint: disable=unused-argument
    """Test that Create cluster role is ok"""
    cluster, *_, provider, _ = prepare_objects
    cluster_bundle, *_ = as_user_objects(user_sdk, cluster.bundle())

    is_allowed(cluster_bundle, BR.CREATE_CLUSTER)
    is_denied_to_user(provider.bundle(), BR.CREATE_HOST_PROVIDER)
    is_denied_to_user(cluster, BR.REMOVE_CLUSTER)

    delete_policy(user_policy)
    is_denied_to_user(cluster_bundle, BR.CREATE_CLUSTER)


@use_role(BR.REMOVE_CLUSTER)
def test_remove_cluster(
    user_policy,  # pylint: disable=unused-argument
    user_sdk: ADCMClient,
    is_denied_to_user,
    prepare_objects,
    second_objects,
    sdk_client_fs,
    user,
):
    """Test that Remove cluster role is ok"""
    admin_cluster, *_ = prepare_objects
    admin_cluster_second, *_ = second_objects
    cluster, *_ = as_user_objects(user_sdk, admin_cluster)

    is_denied_to_user(admin_cluster.bundle(), BR.CREATE_CLUSTER)
    is_allowed(cluster, BR.REMOVE_CLUSTER)
    is_denied_to_user(admin_cluster_second, BR.REMOVE_CLUSTER)

    new_policy = create_policy(
        sdk_client_fs,
        BR.REMOVE_CLUSTER,
        objects=[admin_cluster_second],
        users=[user],
        groups=[],
    )
    delete_policy(new_policy)
    is_denied_to_user(admin_cluster_second, BR.REMOVE_CLUSTER)


@use_role(BR.UPLOAD_BUNDLE)
def test_upload_bundle(clients, user_policy, is_denied_to_user):
    """Test that Upload bundle role is ok"""

    is_allowed(clients.user, BR.UPLOAD_BUNDLE)
    is_denied_to_user(clients.admin.bundle(), BR.REMOVE_BUNDLE)

    delete_policy(user_policy)
    clients.admin.bundle_list()[-1].delete()
    is_denied(clients.user, BR.UPLOAD_BUNDLE)


@use_role(BR.REMOVE_BUNDLE)
def test_remove_bundle(user_policy, user_sdk: ADCMClient, sdk_client_fs, is_denied_to_user):
    """Test that Remove bundle role is ok"""

    is_denied(user_sdk, BR.UPLOAD_BUNDLE)
    BR.UPLOAD_BUNDLE.value.method_call(sdk_client_fs)
    is_allowed(user_sdk.bundle_list()[-1], BR.REMOVE_BUNDLE)

    delete_policy(user_policy)
    BR.UPLOAD_BUNDLE.value.method_call(sdk_client_fs)
    is_denied_to_user(user_sdk.bundle_list()[-1], BR.REMOVE_BUNDLE)


def test_service_administrator(user, user_sdk: ADCMClient, sdk_client_fs, prepare_objects, second_objects):
    """Test that service administrator role grants access to single service and its components"""
    cluster, service, component, *provider_objects = prepare_objects
    second_service_on_first_cluster = cluster.service_add(name="new_service")

    role = sdk_client_fs.role(name=RbacRoles.SERVICE_ADMINISTRATOR.value)
    sdk_client_fs.policy_create(
        name=f"Policy with role {role.name}",
        role=role,
        objects=[service],
        user=[user],
        group=[],
    )
    user_sdk.reread()

    allowed_user_objects = as_user_objects(user_sdk, service, component)
    is_allowed_to_view(*allowed_user_objects)
    is_allowed_to_edit(*allowed_user_objects)
    is_denied_to_view(cluster, second_service_on_first_cluster, *second_objects, *provider_objects, client=user_sdk)


def test_cluster_administrator(user, mm_changing_roles, clients, prepare_objects, second_objects):
    """Test that cluster administrator role grants access to single cluster and related services and components"""
    cluster, service, component, provider, host = prepare_objects

    cluster.host_add(host)

    role = clients.admin.role(name=RbacRoles.CLUSTER_ADMINISTRATOR.value)
    clients.admin.policy_create(
        name=f"Policy with role {role.name}",
        role=role,
        objects=[cluster],
        user=[user],
        group=[],
    )
    clients.user.reread()

    allowed_user_objects = *_, user_service, user_component, user_host = as_user_objects(
        clients.user,
        cluster,
        service,
        component,
        host,
    )
    is_allowed_to_view(*allowed_user_objects)
    is_allowed_to_edit(*allowed_user_objects)
    is_denied_to_view(*second_objects, provider, client=clients.user)

    service_role, component_role, host_role = mm_changing_roles
    check_mm_change_is_allowed(user_host, host_role, clients.user)
    check_mm_change_is_allowed(user_service, service_role, clients.user)
    check_mm_change_is_allowed(user_component, component_role, clients.user)


def test_provider_administrator(user, user_sdk: ADCMClient, sdk_client_fs, prepare_objects, second_objects):
    """Test that provider administrator role grants access to single provider and its hosts"""
    cluster, service, component, hostprovider, host = prepare_objects
    second_cluster, second_service, second_component, *second_provider_objects = second_objects

    role = sdk_client_fs.role(name=RbacRoles.PROVIDER_ADMINISTRATOR.value)
    sdk_client_fs.policy_create(
        name=f"Policy with role {role.name}",
        role=role,
        objects=[hostprovider],
        user=[user],
        group=[],
    )
    user_sdk.reread()

    user_hostprovider, user_host = as_user_objects(user_sdk, hostprovider, host)
    is_allowed_to_view(user_hostprovider, user_host)
    is_allowed_to_edit(user_hostprovider, user_host)
    is_denied_to_view(
        cluster,
        service,
        component,
        second_cluster,
        second_service,
        second_component,
        *second_provider_objects,
        client=user_sdk,
    )


def test_any_object_roles(clients, user, is_denied_to_user, prepare_objects):
    """Test that ViewAnyObject... default roles works as expected with ADCM User"""
    admin_cluster, *_ = prepare_objects

    @allure.step("Check user has no access to any of objects")
    def check_has_no_rights():
        is_denied_to_user(admin_cluster, BR.VIEW_ANY_OBJECT_IMPORT, client=clients.user)
        is_denied_to_user(admin_cluster, BR.VIEW_ANY_OBJECT_HOST_COMPONENTS, client=clients.user)
        is_denied_to_view(*prepare_objects, client=clients.user)
        is_denied_to_edit(*prepare_objects, client=clients.user)

    check_has_no_rights()

    policy = clients.admin.policy_create(
        name="ADCM User for a User",
        role=clients.admin.role(name=RbacRoles.ADCM_USER.value),
        objects=[],
        user=[user],
    )

    cluster, *_ = as_user_objects(clients.user, admin_cluster)

    is_allowed(cluster, BR.VIEW_ANY_OBJECT_IMPORT)
    is_allowed(cluster, BR.VIEW_ANY_OBJECT_HOST_COMPONENTS)
    is_allowed_to_view(*as_user_objects(clients.user, *prepare_objects))
    is_denied_to_edit(*prepare_objects, client=clients.user)

    delete_policy(policy)

    check_has_no_rights()
