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

"""Test cases of permissions deleting"""

import allure
from adcm_client.objects import ADCMClient
from tests.functional.rbac.conftest import (
    CLUSTER_VIEW_CONFIG_ROLES,
    BusinessRoles,
    create_policy,
    is_allowed,
    is_denied,
)


def test_remove_user_from_policy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user loses access if user removed from policy user list
    """
    cluster_via_admin, *_ = prepare_objects
    policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[user],
        groups=[],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)
    with allure.step("Remove user from policy"):
        policy.update(user=[{"id": sdk_client_fs.user(username="admin").id}])
    is_denied(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, client=user_sdk)


def test_remove_group_from_policy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user loses access if group with user removed from policy group list
    """
    cluster_via_admin, *_ = prepare_objects
    group = sdk_client_fs.group_create("test_group", user=[{"id": user.id}])
    empty_group = sdk_client_fs.group_create("empty_group")
    policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[],
        groups=[group],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Remove group from policy"):
        policy.update(group=[{"id": empty_group.id}])
    is_denied(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, client=user_sdk)


def test_remove_user_from_group(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user loses access if user removed from group with policy
    """
    cluster_via_admin, *_ = prepare_objects
    group = sdk_client_fs.group_create("test_group", user=[{"id": user.id}])
    create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[],
        groups=[group],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Remove user from group"):
        group.update(user=[])
    is_denied(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, client=user_sdk)


def test_remove_object_from_policy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user loses access if object changed from policy
    """
    cluster_via_admin, service_via_admin, *_ = prepare_objects
    policy = create_policy(
        sdk_client_fs,
        [BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS],
        objects=[cluster_via_admin],
        users=[user],
        groups=[],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    service = user_sdk.service(id=service_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Change policy object from cluster to service"):
        policy.update(object=[{"id": service_via_admin.id, "type": "service"}])
    is_denied(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, client=user_sdk)
    is_allowed(service, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)


def test_change_child_role(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user loses access if change policy role
    """
    cluster_via_admin, *_ = prepare_objects

    policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[user],
        groups=[],
    )

    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)

    with allure.step("Change role from 'View configuration' to 'View imports'"):
        role = sdk_client_fs.role_create(
            name="Another role",
            display_name="Another role",
            child=[{"id": sdk_client_fs.role(name=BusinessRoles.VIEW_IMPORTS.value.role_name).id}],
        )
        policy.update(role={"id": role.id})
    is_allowed(cluster, BusinessRoles.VIEW_IMPORTS)
    is_denied(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS, client=user_sdk)


def test_remove_user_from_policy_but_still_in_group(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user is still have access if user removed from policy but is in group
    """
    cluster_via_admin, *_ = prepare_objects
    group = sdk_client_fs.group_create("test_group", user=[{"id": user.id}])
    policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[user],
        groups=[group],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Remove user from policy"):
        policy.update(user=[{"id": sdk_client_fs.user(username="admin").id}])
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)


def test_remove_group_with_user_but_still_in_another_group(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user is still have access if removed group with user but user is in another group
    """
    cluster_via_admin, *_ = prepare_objects
    group = sdk_client_fs.group_create("test_group", user=[{"id": user.id}])
    another_group = sdk_client_fs.group_create("another_group", user=[{"id": user.id}])
    policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[],
        groups=[group, another_group],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Remove user from group"):
        policy.update(group=[{"id": another_group.id}])
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)


def test_remove_another_object_from_policy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user is still have access if object removed from policy but exists high-level object
    """
    cluster_via_admin, service_via_admin, *_ = prepare_objects
    policy = create_policy(
        sdk_client_fs,
        CLUSTER_VIEW_CONFIG_ROLES,
        objects=[cluster_via_admin, service_via_admin],
        users=[user],
        groups=[],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    service = user_sdk.service(id=service_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_allowed(service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    with allure.step("Remove object from policy"):
        policy.update(object=[{"id": cluster.id, "type": "cluster"}])
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_allowed(service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)


def test_remove_policy_but_exists_same_policy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Test that user is still have access if removed policy, but we still have another policy with the same rights
    """
    cluster_via_admin, *_ = prepare_objects
    create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[user],
        groups=[],
    )
    second_policy = create_policy(
        sdk_client_fs,
        BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS,
        objects=[cluster_via_admin],
        users=[user],
        groups=[],
    )
    cluster = user_sdk.cluster(id=cluster_via_admin.id)
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    with allure.step("Remove second policy"):
        second_policy.delete()
    is_allowed(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
