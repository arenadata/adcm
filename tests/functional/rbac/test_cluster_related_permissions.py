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
from adcm_client.objects import ADCMClient, Policy

from tests.functional.rbac.conftest import (
    BusinessRoles,
    use_role,
    as_user_objects,
    is_allowed,
    is_denied,
    delete_policy,
)


@use_role(BusinessRoles.ViewConfigurations)
def test_view_configurations(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View configuration role is ok"""
    user_objects = as_user_objects(user_sdk, prepare_objects)
    user_second_objects = as_user_objects(user_sdk, second_objects)
    for base_object in user_objects:
        is_allowed(base_object, BusinessRoles.ViewConfigurations)
        is_denied(base_object, BusinessRoles.EditConfigurations)
    for base_object in user_second_objects:
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


@use_role(BusinessRoles.ViewStatus)
def test_view_status(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View status role is ok"""
    user_objects = as_user_objects(user_sdk, prepare_objects)
    user_second_objects = as_user_objects(user_sdk, second_objects)
    for base_object in user_objects:
        is_allowed(base_object, BusinessRoles.ViewStatus)
    for base_object in user_second_objects:
        is_denied(base_object, BusinessRoles.ViewStatus)
    delete_policy(user_policy)
    for base_object in user_objects:
        is_denied(base_object, BusinessRoles.ViewStatus)


@use_role(BusinessRoles.ViewImports)
def test_view_imports(user_policy: Policy, user_sdk: ADCMClient, prepare_objects, second_objects):
    """Test that View imports role is ok"""
    cluster, service, *_ = as_user_objects(user_sdk, prepare_objects)
    second_cluster, second_service, *_ = as_user_objects(user_sdk, second_objects)
    for base_object in [cluster, service]:
        is_allowed(base_object, BusinessRoles.ViewImports)
    for base_object in [second_cluster, second_service]:
        is_denied(base_object, BusinessRoles.ViewImports)
    delete_policy(user_policy)
    for base_object in [cluster, service]:
        is_denied(base_object, BusinessRoles.ViewImports)
