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

"""Test business permissions related to ADCM"""

import pytest
from adcm_client.objects import ADCMClient

from tests.functional.rbac.conftest import (
    BusinessRoles,
    delete_policy,
    is_allowed,
    is_denied,
    use_role,
)

pytestmark = [pytest.mark.extra_rbac]


@use_role(BusinessRoles.VIEW_ADCM_SETTINGS)
def test_view_adcm_settings(user_policy, user_sdk: ADCMClient, prepare_objects, is_denied_to_user):
    """Test that View ADCM Settings role is ok"""
    cluster, *_ = prepare_objects

    is_allowed(user_sdk.adcm(), BusinessRoles.VIEW_ADCM_SETTINGS)
    is_denied_to_user(user_sdk.adcm(), BusinessRoles.EDIT_ADCM_SETTINGS)
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk.adcm(), BusinessRoles.VIEW_ADCM_SETTINGS)


@use_role(BusinessRoles.EDIT_ADCM_SETTINGS)
def test_edit_adcm_settings(user_policy, user_sdk: ADCMClient, prepare_objects, is_denied_to_user):
    """Test that Edit ADCM Settings role is ok"""
    cluster, *_ = prepare_objects
    adcm = user_sdk.adcm()

    is_allowed(adcm, BusinessRoles.VIEW_ADCM_SETTINGS)
    is_allowed(adcm, BusinessRoles.EDIT_ADCM_SETTINGS)
    is_denied_to_user(cluster, BusinessRoles.VIEW_CLUSTER_CONFIGURATIONS)

    delete_policy(user_policy)
    is_denied_to_user(adcm, BusinessRoles.VIEW_ADCM_SETTINGS, is_list=True)
    is_denied_to_user(adcm, BusinessRoles.EDIT_ADCM_SETTINGS)


@use_role(BusinessRoles.VIEW_USERS)
def test_view_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_USERS)
    is_denied(user_sdk, BusinessRoles.CREATE_USER)
    simple_user = sdk_client_fs.user_create(username="test", password="test")
    is_denied_to_user(simple_user, BusinessRoles.EDIT_USER)
    is_denied_to_user(simple_user, BusinessRoles.REMOVE_USER)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_USERS, is_list=True)


@use_role(BusinessRoles.CREATE_USER)
def test_create_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_USERS)
    is_allowed(user_sdk, BusinessRoles.CREATE_USER)
    simple_user = user_sdk.user(username="test")
    is_denied_to_user(simple_user, BusinessRoles.EDIT_USER)
    is_denied_to_user(simple_user, BusinessRoles.REMOVE_USER)

    delete_policy(user_policy)
    sdk_client_fs.user(username="test").delete()
    is_denied(user_sdk, BusinessRoles.VIEW_USERS, is_list=True)
    is_denied(user_sdk, BusinessRoles.CREATE_USER)


@use_role(BusinessRoles.EDIT_USER)
def test_edit_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_USERS)
    is_denied(user_sdk, BusinessRoles.CREATE_USER)
    simple_user = user_sdk.user(id=sdk_client_fs.user_create(username="test", password="test").id)
    is_allowed(simple_user, BusinessRoles.EDIT_USER)
    is_denied_to_user(simple_user, BusinessRoles.REMOVE_USER)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.VIEW_USERS, is_list=True)
    is_denied_to_user(simple_user, BusinessRoles.EDIT_USER)


@use_role(BusinessRoles.REMOVE_USER)
def test_remove_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Remove users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_USERS)
    is_denied(user_sdk, BusinessRoles.CREATE_USER)
    simple_user = user_sdk.user(id=sdk_client_fs.user_create(username="test", password="test").id)
    is_denied_to_user(simple_user, BusinessRoles.EDIT_USER)
    is_allowed(simple_user, BusinessRoles.REMOVE_USER)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_USERS, is_list=True)


@use_role(BusinessRoles.VIEW_GROUPS)
def test_view_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_GROUPS)
    is_denied(user_sdk, BusinessRoles.CREATE_GROUP)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_denied_to_user(simple_group, BusinessRoles.EDIT_GROUP)
    is_denied_to_user(simple_group, BusinessRoles.REMOVE_GROUP)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_GROUPS, is_list=True)


@use_role(BusinessRoles.CREATE_GROUP)
def test_create_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create groups" role is ok"""
    is_allowed(user_sdk, BusinessRoles.VIEW_GROUPS)
    is_allowed(user_sdk, BusinessRoles.CREATE_GROUP)
    simple_group = user_sdk.group(name="test")
    is_denied_to_user(simple_group, BusinessRoles.EDIT_GROUP)
    is_denied_to_user(simple_group, BusinessRoles.REMOVE_GROUP)

    delete_policy(user_policy)
    sdk_client_fs.group(name="test").delete()
    is_denied(user_sdk, BusinessRoles.VIEW_GROUPS, is_list=True)
    is_denied(user_sdk, BusinessRoles.CREATE_GROUP)


@use_role(BusinessRoles.EDIT_GROUP)
def test_edit_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_GROUPS)
    is_denied(user_sdk, BusinessRoles.CREATE_GROUP)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_allowed(simple_group, BusinessRoles.EDIT_GROUP)
    is_denied_to_user(simple_group, BusinessRoles.REMOVE_GROUP)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.VIEW_GROUPS, is_list=True)
    is_denied_to_user(simple_group, BusinessRoles.EDIT_GROUP)


@use_role(BusinessRoles.REMOVE_GROUP)
def test_remove_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Remove groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_GROUPS)
    is_denied(user_sdk, BusinessRoles.CREATE_GROUP)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_denied_to_user(simple_group, BusinessRoles.EDIT_GROUP)
    is_allowed(simple_group, BusinessRoles.REMOVE_GROUP)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.VIEW_GROUPS, is_list=True)


@use_role(BusinessRoles.VIEW_ROLES)
def test_view_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View roles" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_ROLES)
    is_denied(user_sdk, BusinessRoles.VIEW_USERS, is_list=True)
    is_denied(user_sdk, BusinessRoles.VIEW_GROUPS, is_list=True)
    is_denied(user_sdk, BusinessRoles.VIEW_POLICIES, is_list=True)
    is_denied(user_sdk, BusinessRoles.CREATE_CUSTOM_ROLES)

    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_denied_to_user(custom_role, BusinessRoles.EDIT_ROLES)
    is_denied_to_user(custom_role, BusinessRoles.REMOVE_ROLES)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_ROLES, is_list=True)


@use_role(BusinessRoles.CREATE_CUSTOM_ROLES)
def test_create_custom_role(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create custom role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_ROLES)
    is_allowed(user_sdk, BusinessRoles.CREATE_CUSTOM_ROLES)
    custom_role = user_sdk.role(name="Custom role")
    is_denied_to_user(custom_role, BusinessRoles.EDIT_ROLES)
    is_denied_to_user(custom_role, BusinessRoles.REMOVE_ROLES)

    delete_policy(user_policy)
    sdk_client_fs.role(id=custom_role.id).delete()
    is_denied(user_sdk, BusinessRoles.CREATE_CUSTOM_ROLES)


@use_role(BusinessRoles.EDIT_ROLES)
def test_edit_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_ROLES)
    is_denied(user_sdk, BusinessRoles.CREATE_CUSTOM_ROLES)

    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_allowed(custom_role, BusinessRoles.EDIT_ROLES)
    is_denied_to_user(custom_role, BusinessRoles.REMOVE_ROLES)

    delete_policy(user_policy)
    is_denied_to_user(custom_role, BusinessRoles.EDIT_ROLES)


@use_role(BusinessRoles.REMOVE_ROLES)
def test_remove_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Remove role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.VIEW_ROLES)
    is_denied(user_sdk, BusinessRoles.CREATE_CUSTOM_ROLES)

    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_denied(custom_role, BusinessRoles.EDIT_ROLES, client=user_sdk)
    is_allowed(custom_role, BusinessRoles.REMOVE_ROLES)

    delete_policy(user_policy)
    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    is_denied(user_sdk, BusinessRoles.VIEW_ROLES, is_list=True)


@use_role(BusinessRoles.VIEW_POLICIES)
def test_view_policies(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "View policies" role is ok"""
    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.VIEW_POLICIES)
    is_denied(user_sdk, BusinessRoles.CREATE_POLICY, role=custom_role, user=[user])

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_POLICIES, is_list=True)


@use_role(BusinessRoles.CREATE_POLICY)
def test_create_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Create policy" role is ok"""
    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.VIEW_POLICIES)
    is_allowed(user_sdk, BusinessRoles.CREATE_POLICY, role=custom_role, user=[user])
    policy = user_sdk.policy(name="Test policy")
    is_denied(policy, BusinessRoles.EDIT_POLICY, client=user_sdk)
    is_denied(policy, BusinessRoles.REMOVE_POLICY, client=user_sdk)

    delete_policy(user_policy)
    sdk_client_fs.policy(id=policy.id).delete()
    is_denied(user_sdk, BusinessRoles.CREATE_POLICY, role=custom_role, user=[user])


@use_role(BusinessRoles.EDIT_POLICY)
def test_edit_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Edit policy" role is ok"""
    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.VIEW_POLICIES)
    is_denied(user_sdk, BusinessRoles.CREATE_POLICY, role=custom_role, user=[user])
    custom_policy = user_sdk.policy(
        id=sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user]).id,
    )
    is_allowed(custom_policy, BusinessRoles.EDIT_POLICY)
    is_denied(custom_policy, BusinessRoles.REMOVE_POLICY, client=user_sdk)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.VIEW_POLICIES, is_list=True)
    is_denied(custom_policy, BusinessRoles.EDIT_POLICY, client=user_sdk)


@use_role(BusinessRoles.REMOVE_POLICY)
def test_remove_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Remove policy" role is ok"""
    BusinessRoles.CREATE_CUSTOM_ROLES.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.VIEW_POLICIES)
    is_denied(user_sdk, BusinessRoles.CREATE_POLICY, role=custom_role, user=[user])
    custom_policy = user_sdk.policy(
        id=sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user]).id,
    )
    is_denied(custom_policy, BusinessRoles.EDIT_POLICY, client=user_sdk)
    is_allowed(custom_policy, BusinessRoles.REMOVE_POLICY)

    delete_policy(user_policy)
    sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user])
    is_denied(user_sdk, BusinessRoles.VIEW_POLICIES, is_list=True)
