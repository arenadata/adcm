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
    create_policy,
    BusinessRoles,
    as_user_objects,
    is_allowed,
    delete_policy,
    is_denied,
)


def test_cluster_hierarchy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Parametrize role with cluster related objects
    """
    cluster, service, component, provider, host = as_user_objects(user_sdk, prepare_objects)
    policy = create_policy(
        sdk_client_fs, BusinessRoles.ViewApplicationConfigurations, objects=[cluster], users=[user], groups=[]
    )
    is_allowed(cluster, BusinessRoles.ViewApplicationConfigurations)
    is_allowed(service, BusinessRoles.ViewApplicationConfigurations)
    is_allowed(component, BusinessRoles.ViewApplicationConfigurations)
    is_denied(provider, BusinessRoles.ViewInfrastructureConfigurations)
    is_denied(host, BusinessRoles.ViewInfrastructureConfigurations)
    delete_policy(policy)

    policy = create_policy(
        sdk_client_fs, BusinessRoles.ViewApplicationConfigurations, objects=[service], users=[user], groups=[]
    )
    is_denied(cluster, BusinessRoles.ViewApplicationConfigurations)
    is_allowed(service, BusinessRoles.ViewApplicationConfigurations)
    is_allowed(component, BusinessRoles.ViewApplicationConfigurations)
    is_denied(provider, BusinessRoles.ViewInfrastructureConfigurations)
    is_denied(host, BusinessRoles.ViewInfrastructureConfigurations)
    delete_policy(policy)

    create_policy(
        sdk_client_fs, BusinessRoles.ViewApplicationConfigurations, objects=[component], users=[user], groups=[]
    )
    is_denied(cluster, BusinessRoles.ViewApplicationConfigurations)
    is_denied(service, BusinessRoles.ViewApplicationConfigurations)
    is_allowed(component, BusinessRoles.ViewApplicationConfigurations)
    is_denied(provider, BusinessRoles.ViewInfrastructureConfigurations)
    is_denied(host, BusinessRoles.ViewInfrastructureConfigurations)


def test_provider_hierarchy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Parametrize role with provider related objects
    """
    cluster, service, component, provider, host = as_user_objects(user_sdk, prepare_objects)

    policy = create_policy(
        sdk_client_fs, BusinessRoles.ViewInfrastructureConfigurations, objects=[provider], users=[user], groups=[]
    )
    is_allowed(provider, BusinessRoles.ViewInfrastructureConfigurations)
    is_allowed(host, BusinessRoles.ViewInfrastructureConfigurations)
    is_denied(cluster, BusinessRoles.ViewApplicationConfigurations)
    is_denied(service, BusinessRoles.ViewApplicationConfigurations)
    is_denied(component, BusinessRoles.ViewApplicationConfigurations)
    delete_policy(policy)

    create_policy(
        sdk_client_fs, BusinessRoles.ViewInfrastructureConfigurations, objects=[host], users=[user], groups=[]
    )
    is_denied(provider, BusinessRoles.ViewInfrastructureConfigurations)
    is_allowed(host, BusinessRoles.ViewInfrastructureConfigurations)
    is_denied(cluster, BusinessRoles.ViewApplicationConfigurations)
    is_denied(service, BusinessRoles.ViewApplicationConfigurations)
    is_denied(component, BusinessRoles.ViewApplicationConfigurations)


def test_role_with_two_hierarchy_not_allowed(sdk_client_fs):
    """
    Test that we can not create a new role with childs from different hierarchy
    """
    application_role = {"id": sdk_client_fs.role(name=BusinessRoles.ViewApplicationConfigurations.value.role_name).id}
    infrastructure_role = {
        "id": sdk_client_fs.role(name=BusinessRoles.ViewInfrastructureConfigurations.value.role_name).id
    }
    generic_role = {"id": sdk_client_fs.role(name=BusinessRoles.ViewADCMSettings.value.role_name).id}
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
    with allure.step("Assert that application role can be mixed with not parametrized role"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[application_role, generic_role],
        )
    with allure.step("Assert that infrastructure role can be mixed with not parametrized role"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[infrastructure_role, generic_role],
        )


def test_host_and_cluster_roles(sdk_client_fs):
    """
    Test that cluster and host roles is allowed to use together
    """
    cluster_role = {"id": sdk_client_fs.role(name=BusinessRoles.ViewApplicationConfigurations.value.role_name).id}
    host_role = {"id": sdk_client_fs.role(name=BusinessRoles.RemoveHosts.value.role_name).id}
    with allure.step("Assert that create role with cluster and host parametrization is allowed"):
        sdk_client_fs.role_create(
            name=random_string(),
            display_name=random_string(),
            child=[cluster_role, host_role],
        )
