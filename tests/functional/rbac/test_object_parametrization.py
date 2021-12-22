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
from adcm_client.objects import ADCMClient

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
    policy = create_policy(sdk_client_fs, BusinessRoles.ViewConfigurations, objects=[cluster], users=[user], groups=[])
    is_allowed(cluster, BusinessRoles.ViewConfigurations)
    is_allowed(service, BusinessRoles.ViewConfigurations)
    is_allowed(component, BusinessRoles.ViewConfigurations)
    is_denied(provider, BusinessRoles.ViewConfigurations)
    is_denied(host, BusinessRoles.ViewConfigurations)
    delete_policy(policy)

    policy = create_policy(sdk_client_fs, BusinessRoles.ViewConfigurations, objects=[service], users=[user], groups=[])
    is_denied(cluster, BusinessRoles.ViewConfigurations)
    is_allowed(service, BusinessRoles.ViewConfigurations)
    is_allowed(component, BusinessRoles.ViewConfigurations)
    is_denied(provider, BusinessRoles.ViewConfigurations)
    is_denied(host, BusinessRoles.ViewConfigurations)
    delete_policy(policy)

    create_policy(sdk_client_fs, BusinessRoles.ViewConfigurations, objects=[component], users=[user], groups=[])
    is_denied(cluster, BusinessRoles.ViewConfigurations)
    is_denied(service, BusinessRoles.ViewConfigurations)
    is_allowed(component, BusinessRoles.ViewConfigurations)
    is_denied(provider, BusinessRoles.ViewConfigurations)
    is_denied(host, BusinessRoles.ViewConfigurations)


def test_provider_hierarchy(user_sdk: ADCMClient, user, prepare_objects, sdk_client_fs):
    """
    Parametrize role with provider related objects
    """
    cluster, service, component, provider, host = as_user_objects(user_sdk, prepare_objects)

    policy = create_policy(sdk_client_fs, BusinessRoles.ViewConfigurations, objects=[provider], users=[user], groups=[])
    is_allowed(provider, BusinessRoles.ViewConfigurations)
    is_allowed(host, BusinessRoles.ViewConfigurations)
    is_denied(cluster, BusinessRoles.ViewConfigurations)
    is_denied(service, BusinessRoles.ViewConfigurations)
    is_denied(component, BusinessRoles.ViewConfigurations)
    delete_policy(policy)

    create_policy(sdk_client_fs, BusinessRoles.ViewConfigurations, objects=[host], users=[user], groups=[])
    is_denied(provider, BusinessRoles.ViewConfigurations)
    is_allowed(host, BusinessRoles.ViewConfigurations)
    is_denied(cluster, BusinessRoles.ViewConfigurations)
    is_denied(service, BusinessRoles.ViewConfigurations)
    is_denied(component, BusinessRoles.ViewConfigurations)
