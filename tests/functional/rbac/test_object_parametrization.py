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

"""Test for the parametrized roles by objects of hierarchy"""

import allure
import pytest
from adcm_client.objects import ADCMClient
from coreapi.exceptions import ErrorMessage

from tests.api.utils.tools import random_string
from tests.functional.rbac.conftest import (
    CLUSTER_VIEW_CONFIG_ROLES,
    PROVIDER_VIEW_CONFIG_ROLES,
    TEST_USER_CREDENTIALS,
    BusinessRoles,
    as_user_objects,
    create_policy,
    delete_policy,
    is_allowed,
    is_denied,
)


def test_lower_cluster_hierarchy(user_sdk: ADCMClient, user, is_denied_to_user, prepare_objects, sdk_client_fs):
    """
    Test that cluster role can be applied to lower cluster objects - services and components
    """
    cluster, service, component, provider, host = prepare_objects
    policy = create_policy(sdk_client_fs, CLUSTER_VIEW_CONFIG_ROLES, objects=[cluster], users=[user], groups=[])
    user_cluster, user_service, user_component = as_user_objects(user_sdk, cluster, service, component)
    is_allowed(user_cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_allowed(user_service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    is_allowed(user_component, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)
    is_denied_to_user(provider, BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS)
    is_denied_to_user(host, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
    delete_policy(policy)

    policy = create_policy(sdk_client_fs, CLUSTER_VIEW_CONFIG_ROLES, objects=[service], users=[user], groups=[])
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_allowed(user_service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    is_allowed(user_component, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)
    is_denied_to_user(provider, BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS)
    is_denied_to_user(host, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
    delete_policy(policy)

    create_policy(sdk_client_fs, CLUSTER_VIEW_CONFIG_ROLES, objects=[component], users=[user], groups=[])
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_denied_to_user(service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    is_allowed(user_component, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)
    is_denied_to_user(provider, BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS)
    is_denied_to_user(host, BusinessRoles.VIEW_HOST_CONFIGURATIONS)


# pylint: disable-next=too-many-locals
def test_service_in_cluster_hierarchy(user, prepare_objects, sdk_client_fs, second_objects):
    """
    Test that service related role can be parametrized by cluster
    """
    cluster_via_admin, *_ = prepare_objects
    cluster_via_admin.service_add(name="new_service")

    service_role = {"id": sdk_client_fs.role(name=BusinessRoles.REMOVE_SERVICE.value.role_name).id}
    cluster_role = {"id": sdk_client_fs.role(name=BusinessRoles.ADD_SERVICE.value.role_name).id}
    common_role = sdk_client_fs.role_create(
        "Common role",
        display_name="Common role",
        child=[service_role, cluster_role],
    )
    sdk_client_fs.policy_create(
        name="Common policy",
        role=common_role,
        objects=[cluster_via_admin],
        user=[user],
        group=[],
    )

    username, password = TEST_USER_CREDENTIALS
    user_sdk = ADCMClient(url=sdk_client_fs.url, user=username, password=password)
    cluster, *_ = as_user_objects(user_sdk, cluster_via_admin)
    second_cluster_via_admin, *_ = second_objects

    for service in cluster.service_list():
        is_allowed(cluster, BusinessRoles.REMOVE_SERVICE, service)
    for service in second_cluster_via_admin.service_list():
        is_denied(service, BusinessRoles.REMOVE_SERVICE, client=user_sdk)


def test_provider_hierarchy(user_sdk: ADCMClient, user, is_denied_to_user, prepare_objects, sdk_client_fs):
    """
    Parametrize role with provider related objects
    """
    cluster, service, component, provider, host = prepare_objects

    policy = create_policy(sdk_client_fs, PROVIDER_VIEW_CONFIG_ROLES, objects=[provider], users=[user], groups=[])

    user_provider, user_host = as_user_objects(user_sdk, provider, host)
    is_allowed(user_provider, BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS)
    is_allowed(user_host, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_denied_to_user(service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    is_denied_to_user(component, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)
    delete_policy(policy)

    create_policy(sdk_client_fs, PROVIDER_VIEW_CONFIG_ROLES, objects=[host], users=[user], groups=[])
    is_denied_to_user(provider, BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS)
    is_allowed(user_host, BusinessRoles.VIEW_HOST_CONFIGURATIONS)
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)
    is_denied_to_user(service, BusinessRoles.VIEW_SERVICE_CONFIGURATIONS)
    is_denied_to_user(component, BusinessRoles.VIEW_COMPONENT_CONFIGURATIONS)


@pytest.mark.extra_rbac()
@pytest.mark.negative()
def test_role_with_two_hierarchy_not_allowed(sdk_client_fs):
    """
    Test that we can not create a new role with childs from different hierarchy
    """
    application_role = {"id": sdk_client_fs.role(name=BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS.value.role_name).id}
    infrastructure_role = {
        "id": sdk_client_fs.role(name=BusinessRoles.VIEW_PROVIDER_CONFIGURATIONS.value.role_name).id,
    }
    generic_role = {"id": sdk_client_fs.role(name=BusinessRoles.VIEW_ADCM_SETTINGS.value.role_name).id}
    with allure.step("Assert that create role with different hierarchy is not possible"), pytest.raises(ErrorMessage):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[application_role, infrastructure_role],
        )
    role = sdk_client_fs.role_create(
        name=random_string(),
        display_name=random_string(),
        child=[application_role],
    )
    with allure.step("Assert that update role to different hierarchy is not possible"), pytest.raises(ErrorMessage):
        role.update(child=[application_role, infrastructure_role])
    with allure.step("Assert that cluster role can be mixed with not parametrized role"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[application_role, generic_role],
        )
    with allure.step("Assert that host role can be mixed with not parametrized role"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[infrastructure_role, generic_role],
        )


@pytest.mark.extra_rbac()
def test_host_and_cluster_roles(sdk_client_fs):
    """
    Test that cluster and host roles is allowed to use together
    """
    cluster_role = {"id": sdk_client_fs.role(name=BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS.value.role_name).id}
    host_role = {"id": sdk_client_fs.role(name=BusinessRoles.REMOVE_HOSTS.value.role_name).id}
    with allure.step("Assert that create role with cluster and host parametrization is allowed"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[cluster_role, host_role],
        )
