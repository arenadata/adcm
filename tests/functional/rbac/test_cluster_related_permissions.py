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
# pylint: disable=too-many-arguments,unused-argument
import allure
from adcm_client.objects import ADCMClient, Policy

from tests.functional.rbac.conftest import (
    BusinessRoles,
    use_role,
    as_user_objects,
    is_allowed,
    is_denied,
    delete_policy,
    create_policy,
)


@use_role(BusinessRoles.ViewConfigurations)
def test_view_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View configuration role is ok"""
    user_objects = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    user_second_objects = as_user_objects(user_sdk, second_objects)
    second_service_on_first_cluster = user_sdk.service(id=cluster_via_admin.service_add(name="new_service").id)
    second_component_on_first_cluster = second_service_on_first_cluster.component()
    second_host_on_first_provider = user_sdk.host(id=provider_via_admin.host_create(fqdn="new_host").id)
    for base_object in user_objects:
        is_allowed(base_object, BusinessRoles.ViewConfigurations)
        is_denied(base_object, BusinessRoles.EditConfigurations)
    for base_object in (
        *user_second_objects,
        second_service_on_first_cluster,
        second_component_on_first_cluster,
        second_host_on_first_provider,
    ):
        is_denied(base_object, BusinessRoles.ViewConfigurations)
    delete_policy(user_policy)
    for base_object in user_objects:
        is_denied(base_object, BusinessRoles.ViewConfigurations)


@use_role(BusinessRoles.EditConfigurations)
def test_edit_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit configuration role is ok"""
    user_objects = as_user_objects(user_sdk, prepare_objects)
    user_second_objects = as_user_objects(user_sdk, second_objects)
    for base_object in user_objects:
        is_allowed(base_object, BusinessRoles.EditConfigurations)
    for base_object in [*user_second_objects, user_sdk.adcm()]:
        is_denied(base_object, BusinessRoles.EditConfigurations)
    delete_policy(user_policy)
    for base_object in user_objects:
        is_denied(base_object, BusinessRoles.EditConfigurations)


@use_role(BusinessRoles.ViewImports)
def test_view_imports(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View imports role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, prepare_objects)
    second_cluster, second_service, *_ = as_user_objects(user_sdk, second_objects)
    for base_object in [cluster, service]:
        is_allowed(base_object, BusinessRoles.ViewImports)
        is_denied(base_object, BusinessRoles.ManageImports, second_service)
    for base_object in [second_cluster, second_service]:
        is_denied(base_object, BusinessRoles.ViewImports)
    delete_policy(user_policy)
    for base_object in [cluster, service]:
        is_denied(base_object, BusinessRoles.ViewImports)


@use_role(BusinessRoles.ManageImports)
def test_manage_imports(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Manage imports role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, service_via_admin, *_ = prepare_objects
    second_cluster, second_service, *_ = as_user_objects(user_sdk, second_objects)

    for base_object in [cluster, service]:
        is_allowed(base_object, BusinessRoles.ViewImports)
        is_allowed(base_object, BusinessRoles.ManageImports, second_service)
    for base_object in [second_cluster, second_service]:
        is_denied(base_object, BusinessRoles.ViewImports)
    delete_policy(user_policy)
    _ = (bind.delete() for bind in cluster_via_admin.bind_list())
    _ = (bind.delete() for bind in service_via_admin.bind_list())
    for base_object in [cluster, service]:
        is_denied(base_object, BusinessRoles.ViewImports)
        is_denied(base_object, BusinessRoles.ManageImports, second_service)


@use_role(BusinessRoles.ViewHostComponents)
def test_view_hostcomponents(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View host-components role is ok"""
    cluster, _, component, _, host = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_, host_via_admin = prepare_objects
    second_cluster, *_ = as_user_objects(user_sdk, second_objects)
    cluster_via_admin.host_add(host_via_admin)

    is_allowed(cluster, BusinessRoles.ViewHostComponents)
    is_denied(second_cluster, BusinessRoles.ViewHostComponents)
    is_denied(cluster, BusinessRoles.EditHostComponents, (host, component))
    delete_policy(user_policy)
    is_denied(cluster, BusinessRoles.ViewHostComponents)


@use_role(BusinessRoles.EditHostComponents)
def test_edit_hostcomponents(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Edit host-components role is ok"""
    cluster, _, component, _, host = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_, host_via_admin = prepare_objects
    second_cluster, _, second_component, _, second_host = as_user_objects(user_sdk, second_objects)
    second_cluster_via_admin, *_, second_host_via_admin = second_objects

    cluster_via_admin.host_add(host_via_admin)
    second_cluster_via_admin.host_add(second_host_via_admin)

    is_allowed(cluster, BusinessRoles.ViewHostComponents)
    is_allowed(cluster, BusinessRoles.EditHostComponents, (host, component))
    is_denied(second_cluster, BusinessRoles.ViewHostComponents)
    is_denied(second_cluster, BusinessRoles.EditHostComponents, (second_host, second_component))
    delete_policy(user_policy)
    is_denied(cluster, BusinessRoles.ViewHostComponents)
    is_denied(cluster, BusinessRoles.EditHostComponents)


@use_role(BusinessRoles.AddService)
def test_add_service(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Add service role is ok"""
    cluster, *_ = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_cluster, *_ = as_user_objects(user_sdk, second_objects)

    is_allowed(cluster, BusinessRoles.AddService)
    added_service = cluster.service(name="new_service")
    is_denied(cluster, BusinessRoles.RemoveService, added_service)
    is_denied(second_cluster, BusinessRoles.AddService)
    cluster_via_admin.service(name="new_service").delete()
    delete_policy(user_policy)
    is_denied(cluster, BusinessRoles.AddService)


@use_role(BusinessRoles.RemoveService)
def test_remove_service(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Remove service role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_ = prepare_objects
    second_cluster, second_service, *_ = as_user_objects(user_sdk, second_objects)
    second_cluster_via_admin, *_ = second_objects

    is_denied(cluster, BusinessRoles.AddService)
    is_allowed(cluster, BusinessRoles.RemoveService, service)
    is_denied(second_cluster, BusinessRoles.RemoveService, second_service)

    added_second_service = second_cluster_via_admin.service_add(name="new_service")
    is_denied(cluster, BusinessRoles.RemoveService, added_second_service)

    delete_policy(user_policy)
    added_service = cluster_via_admin.service_add(name="test_service")
    is_denied(cluster, BusinessRoles.RemoveService, added_service)


@use_role(BusinessRoles.RemoveHosts)
def test_remove_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove hosts role is ok"""
    *_, host = as_user_objects(user_sdk, prepare_objects)
    *_, second_host = as_user_objects(user_sdk, second_objects)

    is_allowed(host, BusinessRoles.RemoveHosts)
    is_denied(second_host, BusinessRoles.RemoveHosts)
    with allure.step("Assert that policy is valid after object removing"):
        user_policy.reread()

    new_policy = create_policy(sdk_client_fs, user, BusinessRoles.RemoveHosts, second_host)
    delete_policy(new_policy)
    is_denied(second_host, BusinessRoles.RemoveHosts)


@use_role(BusinessRoles.MapHosts)
def test_map_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Map hosts role is ok"""
    cluster, *_, host = as_user_objects(user_sdk, prepare_objects)
    *_, provider_via_admin, _ = prepare_objects
    second_cluster, *_, second_host = as_user_objects(user_sdk, second_objects)

    new_host = provider_via_admin.host_create(fqdn="new_host")
    is_allowed(cluster, BusinessRoles.MapHosts, host)
    is_denied(cluster, BusinessRoles.UnmapHosts, host)
    is_denied(second_cluster, BusinessRoles.MapHosts, second_host)

    delete_policy(user_policy)

    is_denied(cluster, BusinessRoles.MapHosts, new_host)


@use_role(BusinessRoles.UnmapHosts)
def test_unmap_hosts(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Unmap hosts role is ok"""
    cluster, *_, host = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    second_cluster, *_, second_host = as_user_objects(user_sdk, second_objects)
    second_cluster_via_admin, *_ = second_objects

    is_denied(cluster, BusinessRoles.MapHosts, host)
    is_denied(host, BusinessRoles.RemoveHosts)
    cluster_via_admin.host_add(host)
    is_allowed(cluster, BusinessRoles.UnmapHosts, host)

    second_cluster_via_admin.host_add(second_host)
    is_denied(second_cluster, BusinessRoles.UnmapHosts, second_host)

    delete_policy(user_policy)

    new_host = provider_via_admin.host_create(fqdn="new_host")
    cluster_via_admin.host_add(new_host)
    is_denied(cluster, BusinessRoles.UnmapHosts, new_host)


@use_role(BusinessRoles.UpgradeBundle)
def test_upgrade_bundle(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Upgrade bundle role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, prepare_objects)
    cluster_via_admin, *_, provider_via_admin, _ = prepare_objects
    second_cluster = user_sdk.cluster(id=cluster_via_admin.bundle().cluster_create(name="Second cluster").id)
    second_provider = user_sdk.provider(id=provider_via_admin.bundle().provider_create(name="Second provider").id)

    is_allowed(cluster, BusinessRoles.UpgradeBundle)
    is_allowed(provider, BusinessRoles.UpgradeBundle)
    is_denied(second_cluster, BusinessRoles.UpgradeBundle)
    is_denied(second_provider, BusinessRoles.UpgradeBundle)

    new_policy = create_policy(sdk_client_fs, user, BusinessRoles.UpgradeBundle, second_cluster, second_provider)
    delete_policy(new_policy)
    is_denied(second_cluster, BusinessRoles.UpgradeBundle)
    is_denied(second_provider, BusinessRoles.UpgradeBundle)


@use_role(BusinessRoles.CreateHostProvider)
def test_create_provider(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create provider role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, prepare_objects)
    *_, second_provider, _ = as_user_objects(user_sdk, second_objects)

    is_allowed(provider.bundle(), BusinessRoles.CreateHostProvider)
    is_allowed(second_provider.bundle(), BusinessRoles.CreateHostProvider)
    is_denied(provider, BusinessRoles.CreateHost)
    is_denied(user_sdk.provider_list()[-1], BusinessRoles.CreateHost)
    is_denied(cluster.bundle(), BusinessRoles.CreateHostProvider)

    delete_policy(user_policy)
    is_denied(provider.bundle(), BusinessRoles.CreateHostProvider)


@use_role(BusinessRoles.CreateHost)
def test_create_host(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create host role is ok"""
    cluster, *_, provider, host = as_user_objects(user_sdk, prepare_objects)
    *_, second_provider, second_host = as_user_objects(user_sdk, second_objects)

    is_allowed(provider, BusinessRoles.CreateHost)
    is_denied(host, BusinessRoles.RemoveHosts)
    is_denied(cluster, BusinessRoles.MapHosts, host)
    is_denied(second_provider, BusinessRoles.CreateHost)
    is_denied(second_host, BusinessRoles.RemoveHosts)

    delete_policy(user_policy)
    is_denied(provider, BusinessRoles.CreateHost)


@use_role(BusinessRoles.RemoveHostProvider)
def test_remove_provider(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove provider role is ok"""
    *_, provider, host = as_user_objects(user_sdk, prepare_objects)
    *_, second_provider, _ = as_user_objects(user_sdk, second_objects)

    is_denied(host, BusinessRoles.RemoveHosts)
    is_allowed(provider, BusinessRoles.RemoveHostProvider)
    is_denied(second_provider, BusinessRoles.RemoveHostProvider)

    new_policy = create_policy(sdk_client_fs, user, BusinessRoles.UpgradeBundle, second_provider)
    delete_policy(new_policy)
    is_denied(second_provider, BusinessRoles.RemoveHostProvider)


@use_role(BusinessRoles.CreateCluster)
def test_create_cluster(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that Create cluster role is ok"""
    cluster, *_, provider, _ = as_user_objects(user_sdk, prepare_objects)

    is_allowed(cluster.bundle(), BusinessRoles.CreateCluster)
    is_denied(provider.bundle(), BusinessRoles.CreateHostProvider)
    is_denied(cluster, BusinessRoles.RemoveCluster)

    delete_policy(user_policy)
    is_denied(cluster.bundle(), BusinessRoles.CreateCluster)


@use_role(BusinessRoles.RemoveCluster)
def test_remove_cluster(user_policy, user_sdk: ADCMClient, prepare_objects, second_objects, sdk_client_fs, user):
    """Test that Remove cluster role is ok"""
    cluster, *_ = as_user_objects(user_sdk, prepare_objects)
    second_cluster, *_ = as_user_objects(user_sdk, second_objects)

    is_denied(cluster.bundle(), BusinessRoles.CreateCluster)
    is_allowed(cluster, BusinessRoles.RemoveCluster)
    is_denied(second_cluster, BusinessRoles.RemoveCluster)

    new_policy = create_policy(sdk_client_fs, user, BusinessRoles.UpgradeBundle, second_cluster)
    delete_policy(new_policy)
    is_denied(second_cluster, BusinessRoles.RemoveCluster)


@use_role(BusinessRoles.UploadBundle)
def test_upload_bundle(user_policy, user_sdk: ADCMClient, sdk_client_fs):
    """Test that Upload bundle role is ok"""

    is_allowed(user_sdk, BusinessRoles.UploadBundle)
    is_denied(user_sdk.bundle(), BusinessRoles.RemoveBundle)

    delete_policy(user_policy)
    sdk_client_fs.bundle().delete()
    is_denied(user_sdk, BusinessRoles.UploadBundle)


@use_role(BusinessRoles.RemoveBundle)
def test_remove_bundle(user_policy, user_sdk: ADCMClient, sdk_client_fs):
    """Test that Remove bundle role is ok"""

    is_denied(user_sdk, BusinessRoles.UploadBundle)
    BusinessRoles.UploadBundle.value.method_call(sdk_client_fs)
    is_allowed(user_sdk.bundle(), BusinessRoles.RemoveBundle)

    delete_policy(user_policy)
    BusinessRoles.UploadBundle.value.method_call(sdk_client_fs)
    is_denied(user_sdk, BusinessRoles.RemoveBundle)
