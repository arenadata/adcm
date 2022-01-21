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

# pylint: disable=too-many-arguments,unused-argument,too-many-locals

import allure
import pytest
from adcm_client.objects import ADCMClient, Policy

from tests.functional.rbac.conftest import (
    BusinessRoles as BR,
    use_role,
    as_user_objects,
    is_allowed,
    is_denied,
    delete_policy,
    create_policy,
    RbacRoles,
    CLUSTER_VIEW_CONFIG_ROLES,
    PROVIDER_VIEW_CONFIG_ROLES,
    CLUSTER_EDIT_CONFIG_ROLES,
    PROVIDER_EDIT_CONFIG_ROLES,
)


def _build_view_edit_permission_check(allowed_or_denied, get_view_or_edit):
    """Helper to build multiple objects check functions"""

    def check(*objects):
        for adcm_object in objects:
            allowed_or_denied(adcm_object, get_view_or_edit(adcm_object))

    return check


is_allowed_to_view = _build_view_edit_permission_check(is_allowed, BR.view_config_of)
is_allowed_to_edit = _build_view_edit_permission_check(is_allowed, BR.edit_config_of)
is_denied_to_view = _build_view_edit_permission_check(is_denied, BR.view_config_of)
is_denied_to_edit = _build_view_edit_permission_check(is_denied, BR.edit_config_of)


@use_role(CLUSTER_VIEW_CONFIG_ROLES)
def test_view_application_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View application configuration role is ok"""
    cluster, service, component, provider, host = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    user_second_objects = as_user_objects(user_sdk, *second_objects)
    second_service_on_first_cluster = user_sdk.service(id=cluster_via_admin.service_add(name="new_service").id)
    second_component_on_first_cluster = second_service_on_first_cluster.component(name="test_component")

    objects_affected_by_policy = (
        cluster,
        service,
        component,
        second_service_on_first_cluster,
        second_component_on_first_cluster,
    )

    is_allowed_to_view(*objects_affected_by_policy)
    is_denied_to_edit(*objects_affected_by_policy)
    is_denied_to_view(provider, host, *user_second_objects)
    delete_policy(user_policy)
    is_denied_to_view(*objects_affected_by_policy)


@use_role(PROVIDER_VIEW_CONFIG_ROLES)
def test_view_infrastructure_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View infrastructure configuration role is ok"""
    cluster, service, component, provider, host = as_user_objects(user_sdk, *prepare_objects)
    *_, provider_via_admin, _ = prepare_objects
    user_second_objects = as_user_objects(user_sdk, *second_objects)
    second_host_on_first_provider = user_sdk.host(id=provider_via_admin.host_create(fqdn="new_host").id)

    is_allowed_to_view(provider, host)
    is_denied_to_edit(provider, host)
    is_denied_to_view(cluster, service, component, *user_second_objects, second_host_on_first_provider)
    delete_policy(user_policy)
    is_denied_to_view(provider, host)


@use_role(CLUSTER_EDIT_CONFIG_ROLES)
def test_edit_application_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit application configuration role is ok"""
    cluster, service, component, provider, host = as_user_objects(user_sdk, *prepare_objects)
    user_second_objects = as_user_objects(user_sdk, *second_objects)

    is_allowed_to_view(cluster, service, component)
    is_allowed_to_edit(cluster, service, component)
    is_denied_to_edit(*user_second_objects, user_sdk.adcm(), provider, host)
    delete_policy(user_policy)
    is_denied_to_edit(cluster, service, component)
    is_denied_to_view(cluster, service, component)


@use_role(PROVIDER_EDIT_CONFIG_ROLES)
def test_edit_infrastructure_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit infrastructure configuration role is ok"""
    cluster, service, component, provider, host = as_user_objects(user_sdk, *prepare_objects)
    user_second_objects = as_user_objects(user_sdk, *second_objects)

    is_allowed_to_view(provider, host)
    is_allowed_to_edit(provider, host)
    is_denied_to_edit(*user_second_objects, user_sdk.adcm(), cluster, service, component)
    delete_policy(user_policy)
    is_denied_to_edit(provider, host)
    is_denied_to_view(provider, host)


@use_role(BR.ViewImports)
def test_view_imports(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View imports role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, *prepare_objects)
    second_cluster, second_service, *_ = as_user_objects(user_sdk, *second_objects)
    for base_object in [cluster, service]:
        is_allowed(base_object, BR.ViewImports)
        is_denied(base_object, BR.ManageImports, second_service)
    for base_object in [second_cluster, second_service]:
        is_denied(base_object, BR.ViewImports)
    delete_policy(user_policy)
    for base_object in [cluster, service]:
        is_denied(base_object, BR.ViewImports)


@use_role(BR.ManageImports)
def test_manage_imports(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Manage imports role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, service_via_admin, *_ = prepare_objects
    second_cluster, second_service, *_ = as_user_objects(user_sdk, *second_objects)

    for base_object in [cluster, service]:
        is_allowed(base_object, BR.ViewImports)
        is_allowed(base_object, BR.ManageImports, second_service)
    for base_object in [second_cluster, second_service]:
        is_denied(base_object, BR.ViewImports)
    delete_policy(user_policy)
    _ = (bind.delete() for bind in cluster_via_admin.bind_list())
    _ = (bind.delete() for bind in service_via_admin.bind_list())
    for base_object in [cluster, service]:
        is_denied(base_object, BR.ViewImports)
        is_denied(base_object, BR.ManageImports, second_service)


@use_role(BR.ViewHostComponents)
def test_view_hostcomponents(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View host-components role is ok"""
    cluster, _, component, _, host = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_, host_via_admin = prepare_objects
    second_cluster, *_ = as_user_objects(user_sdk, *second_objects)
    cluster_via_admin.host_add(host_via_admin)

    is_allowed(cluster, BR.ViewHostComponents)
    is_denied(second_cluster, BR.ViewHostComponents)
    is_denied(cluster, BR.EditHostComponents, (host, component))
    delete_policy(user_policy)
    is_denied(cluster, BR.ViewHostComponents)


@use_role(BR.EditHostComponents)
def test_edit_hostcomponents(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit host-components role is ok"""
    cluster, _, component, _, host = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_, host_via_admin = prepare_objects
    second_cluster, _, second_component, _, second_host = as_user_objects(user_sdk, *second_objects)
    second_cluster_via_admin, *_, second_host_via_admin = second_objects

    cluster_via_admin.host_add(host_via_admin)
    second_cluster_via_admin.host_add(second_host_via_admin)

    is_allowed(cluster, BR.ViewHostComponents)
    is_allowed(cluster, BR.EditHostComponents, (host, component))
    is_denied(second_cluster, BR.ViewHostComponents)
    is_denied(second_cluster, BR.EditHostComponents, (second_host, second_component))
    delete_policy(user_policy)
    is_denied(cluster, BR.ViewHostComponents)
    is_denied(cluster, BR.EditHostComponents)


@use_role(BR.AddService)
def test_add_service(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Add service role is ok"""
    cluster, *_ = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_cluster, *_ = as_user_objects(user_sdk, *second_objects)

    is_allowed(cluster, BR.AddService)
    added_service = cluster.service(name="new_service")
    is_denied(cluster, BR.RemoveService, added_service)
    is_denied(second_cluster, BR.AddService)
    cluster_via_admin.service(name="new_service").delete()
    delete_policy(user_policy)
    is_denied(cluster, BR.AddService)


@use_role(BR.RemoveService)
def test_remove_service(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Remove service role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_cluster, second_service, *_ = as_user_objects(user_sdk, *second_objects)
    second_cluster_via_admin, *_ = second_objects

    is_denied(cluster, BR.AddService)
    is_allowed(cluster, BR.RemoveService, service)
    is_denied(second_cluster, BR.RemoveService, second_service)

    added_second_service = second_cluster_via_admin.service_add(name="new_service")
    is_denied(cluster, BR.RemoveService, added_second_service)

    delete_policy(user_policy)
    added_service = cluster_via_admin.service_add(name="test_service")
    is_denied(cluster, BR.RemoveService, added_service)


@use_role(BR.RemoveHosts)
def test_remove_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove hosts role is ok"""
    *_, host = as_user_objects(user_sdk, *prepare_objects)
    *_, second_host = as_user_objects(user_sdk, *second_objects)

    is_allowed(host, BR.RemoveHosts)
    is_denied(second_host, BR.RemoveHosts)
    with allure.step("Assert that policy is valid after object removing"):
        user_policy.reread()

    new_policy = create_policy(sdk_client_fs, BR.RemoveHosts, objects=[second_host], users=[user], groups=[])
    delete_policy(new_policy)
    is_denied(second_host, BR.RemoveHosts)


@use_role(BR.MapHosts)
def test_map_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Map hosts role is ok"""
    cluster, *_, host = as_user_objects(user_sdk, *prepare_objects)
    *_, provider_via_admin, _ = prepare_objects
    second_cluster, *_, second_host = as_user_objects(user_sdk, *second_objects)

    new_host = provider_via_admin.host_create(fqdn="new_host")
    is_allowed(cluster, BR.MapHosts, host)
    is_denied(cluster, BR.UnmapHosts, host)
    is_denied(second_cluster, BR.MapHosts, second_host)

    delete_policy(user_policy)

    is_denied(cluster, BR.MapHosts, new_host)


@use_role(BR.UnmapHosts)
def test_unmap_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Unmap hosts role is ok"""
    cluster, *_, host = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    second_cluster, *_, second_host = as_user_objects(user_sdk, *second_objects)
    second_cluster_via_admin, *_ = second_objects

    is_denied(cluster, BR.MapHosts, host)
    is_denied(host, BR.RemoveHosts)
    cluster_via_admin.host_add(host)
    is_allowed(cluster, BR.UnmapHosts, host)

    second_cluster_via_admin.host_add(second_host)
    is_denied(second_cluster, BR.UnmapHosts, second_host)

    delete_policy(user_policy)

    new_host = provider_via_admin.host_create(fqdn="new_host")
    cluster_via_admin.host_add(new_host)
    is_denied(cluster, BR.UnmapHosts, new_host)


@use_role(BR.UpgradeClusterBundle)
@pytest.mark.usefixtures("second_objects")
def test_upgrade_application_bundle(user_policy, user_sdk: ADCMClient, prepare_objects, sdk_client_fs, user):
    """Test that Upgrade application bundle role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_cluster = user_sdk.cluster(id=cluster_via_admin.bundle().cluster_create(name="Second cluster").id)

    is_allowed(cluster, BR.UpgradeClusterBundle)
    is_denied(provider, BR.UpgradeClusterBundle)
    is_denied(second_cluster, BR.UpgradeClusterBundle)

    new_policy = create_policy(
        sdk_client_fs, BR.UpgradeClusterBundle, objects=[second_cluster], users=[user], groups=[]
    )
    delete_policy(new_policy)
    is_denied(second_cluster, BR.UpgradeClusterBundle)


@use_role(BR.UpgradeProviderBundle)
@pytest.mark.usefixtures("second_objects")
def test_upgrade_infrastructure_bundle(user_policy, user_sdk: ADCMClient, prepare_objects, sdk_client_fs, user):
    """Test that Upgrade infrastructure bundle role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, *prepare_objects)
    *_, provider_via_admin, _ = prepare_objects
    second_provider = user_sdk.provider(id=provider_via_admin.bundle().provider_create(name="Second provider").id)

    is_allowed(provider, BR.UpgradeProviderBundle)
    is_denied(cluster, BR.UpgradeProviderBundle)
    is_denied(second_provider, BR.UpgradeProviderBundle)

    new_policy = create_policy(
        sdk_client_fs, BR.UpgradeProviderBundle, objects=[second_provider], users=[user], groups=[]
    )
    delete_policy(new_policy)
    is_denied(second_provider, BR.UpgradeProviderBundle)


@use_role(BR.CreateHostProvider)
def test_create_provider(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create provider role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, *prepare_objects)
    *_, second_provider, _ = as_user_objects(user_sdk, *second_objects)

    is_allowed(provider.bundle(), BR.CreateHostProvider)
    is_allowed(second_provider.bundle(), BR.CreateHostProvider)
    is_denied(provider, BR.CreateHost)
    is_denied(user_sdk.provider_list()[-1], BR.CreateHost)
    is_denied(cluster.bundle(), BR.CreateCluster)

    delete_policy(user_policy)
    is_denied(provider.bundle(), BR.CreateHostProvider)


@use_role(BR.CreateHost)
def test_create_host(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create host role is ok"""
    cluster, *_, provider, host = as_user_objects(user_sdk, *prepare_objects)
    *_, second_provider, second_host = as_user_objects(user_sdk, *second_objects)

    is_allowed(provider, BR.CreateHost)
    is_denied(host, BR.RemoveHosts)
    is_denied(cluster, BR.MapHosts, host)
    is_denied(second_provider, BR.CreateHost)
    is_denied(second_host, BR.RemoveHosts)

    delete_policy(user_policy)
    is_denied(provider, BR.CreateHost)


@use_role(BR.RemoveHostProvider)
def test_remove_provider(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove provider role is ok"""
    *_, provider, host = as_user_objects(user_sdk, *prepare_objects)
    *_, host_via_admin = prepare_objects
    *_, second_provider, _ = as_user_objects(user_sdk, *second_objects)
    *_, second_host_via_admin = second_objects

    is_denied(host, BR.RemoveHosts)
    host_via_admin.delete()
    second_host_via_admin.delete()
    is_allowed(provider, BR.RemoveHostProvider)
    is_denied(second_provider, BR.RemoveHostProvider)

    new_policy = create_policy(sdk_client_fs, BR.RemoveHostProvider, objects=[second_provider], users=[user], groups=[])
    delete_policy(new_policy)
    is_denied(second_provider, BR.RemoveHostProvider)


@use_role(BR.CreateCluster)
def test_create_cluster(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create cluster role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, *prepare_objects)

    is_allowed(cluster.bundle(), BR.CreateCluster)
    is_denied(provider.bundle(), BR.CreateHostProvider)
    is_denied(cluster, BR.RemoveCluster)

    delete_policy(user_policy)
    is_denied(cluster.bundle(), BR.CreateCluster)


@use_role(BR.RemoveCluster)
def test_remove_cluster(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove cluster role is ok"""
    cluster, *_ = as_user_objects(user_sdk, *prepare_objects)
    second_cluster, *_ = as_user_objects(user_sdk, *second_objects)

    is_denied(cluster.bundle(), BR.CreateCluster)
    is_allowed(cluster, BR.RemoveCluster)
    is_denied(second_cluster, BR.RemoveCluster)

    new_policy = create_policy(sdk_client_fs, BR.RemoveCluster, objects=[second_cluster], users=[user], groups=[])
    delete_policy(new_policy)
    is_denied(second_cluster, BR.RemoveCluster)


@use_role(BR.UploadBundle)
def test_upload_bundle(user_policy, user_sdk: ADCMClient, sdk_client_fs):
    """Test that Upload bundle role is ok"""

    is_allowed(user_sdk, BR.UploadBundle)
    is_denied(user_sdk.bundle(), BR.RemoveBundle)

    delete_policy(user_policy)
    sdk_client_fs.bundle_list()[-1].delete()
    is_denied(user_sdk, BR.UploadBundle)


@use_role(BR.RemoveBundle)
def test_remove_bundle(user_policy, user_sdk: ADCMClient, sdk_client_fs):
    """Test that Remove bundle role is ok"""

    is_denied(user_sdk, BR.UploadBundle)
    BR.UploadBundle.value.method_call(sdk_client_fs)
    is_allowed(user_sdk.bundle_list()[-1], BR.RemoveBundle)

    delete_policy(user_policy)
    BR.UploadBundle.value.method_call(sdk_client_fs)
    is_denied(user_sdk.bundle_list()[-1], BR.RemoveBundle)


def test_service_administrator(user, user_sdk: ADCMClient, sdk_client_fs, prepare_objects, second_objects):
    """Test that service administrator role grants access to single service and its components"""
    cluster, service, component, *provider_objects = as_user_objects(user_sdk, *prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_service_on_first_cluster = user_sdk.service(id=cluster_via_admin.service_add(name="new_service").id)
    second_cluster, second_service, second_component, *second_provider_objects = as_user_objects(
        user_sdk, *second_objects
    )

    role = sdk_client_fs.role(name=RbacRoles.ServiceAdministrator.value)
    sdk_client_fs.policy_create(
        name=f"Policy with role {role.name}", role=role, objects=[service], user=[user], group=[]
    )

    is_allowed_to_view(service, component)
    is_allowed_to_edit(service, component)
    is_denied_to_view(
        cluster,
        second_cluster,
        second_service,
        second_component,
        second_service_on_first_cluster,
        *provider_objects,
        *second_provider_objects,
    )


def test_cluster_administrator(user, user_sdk: ADCMClient, sdk_client_fs, prepare_objects, second_objects):
    """Test that cluster administrator role grants access to single cluster and related services and components"""
    cluster, service, component, *provider_objects = as_user_objects(user_sdk, *prepare_objects)
    second_cluster, second_service, second_component, *second_provider_objects = as_user_objects(
        user_sdk, *second_objects
    )

    role = sdk_client_fs.role(name=RbacRoles.ClusterAdministrator.value)
    sdk_client_fs.policy_create(
        name=f"Policy with role {role.name}", role=role, objects=[cluster], user=[user], group=[]
    )

    is_allowed_to_view(cluster, service, component)
    is_allowed_to_edit(cluster, service, component)
    is_denied_to_view(second_cluster, second_service, second_component, *provider_objects, *second_provider_objects)


def test_provider_administrator(user, user_sdk: ADCMClient, sdk_client_fs, prepare_objects, second_objects):
    """Test that provider administrator role grants access to single provider and its hosts"""
    cluster, service, component, hostprovider, host = as_user_objects(user_sdk, *prepare_objects)
    second_cluster, second_service, second_component, *second_provider_objects = as_user_objects(
        user_sdk, *second_objects
    )

    role = sdk_client_fs.role(name=RbacRoles.ProviderAdministrator.value)
    sdk_client_fs.policy_create(
        name=f"Policy with role {role.name}", role=role, objects=[hostprovider], user=[user], group=[]
    )

    is_allowed_to_view(hostprovider, host)
    is_allowed_to_edit(hostprovider, host)
    is_denied_to_view(
        cluster, service, component, second_cluster, second_service, second_component, *second_provider_objects
    )


def test_any_object_roles(clients, user, prepare_objects):
    """Test that ViewAnyObject... default roles works as expected with ADCM User"""
    cluster, *_ = user_objects = as_user_objects(clients.user, *prepare_objects)

    @allure.step("Check user has no access to any of objects")
    def check_has_no_rights():
        is_denied(cluster, BR.ViewAnyObjectImport)
        is_denied(cluster, BR.ViewAnyObjectHostComponents)
        is_denied_to_view(*user_objects)
        is_denied_to_edit(*user_objects)

    check_has_no_rights()

    policy = clients.admin.policy_create(
        name="ADCM User for a User",
        role=clients.admin.role(name=RbacRoles.ADCMUser.value),
        objects=[],
        user=[user],
    )

    is_allowed(cluster, BR.ViewAnyObjectImport)
    is_allowed(cluster, BR.ViewAnyObjectHostComponents)
    is_allowed_to_view(*user_objects)
    is_denied_to_edit(*user_objects)

    delete_policy(policy)

    check_has_no_rights()
