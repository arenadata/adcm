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


@use_role(BusinessRoles.ViewADCMSettings)
def test_view_adcm_settings(user_policy, user_sdk: ADCMClient, prepare_objects, is_denied_to_user):
    """Test that View ADCM Settings role is ok"""
    cluster, *_ = prepare_objects

    is_allowed(user_sdk.adcm(), BusinessRoles.ViewADCMSettings)
    is_denied_to_user(user_sdk.adcm(), BusinessRoles.EditADCMSettings)
    is_denied_to_user(cluster, BusinessRoles.ViewClusterConfigurations)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk.adcm(), BusinessRoles.ViewADCMSettings)


@use_role(BusinessRoles.EditADCMSettings)
def test_edit_adcm_settings(user_policy, user_sdk: ADCMClient, prepare_objects, is_denied_to_user):
    """Test that Edit ADCM Settings role is ok"""
    cluster, *_ = prepare_objects
    adcm = user_sdk.adcm()

    is_allowed(adcm, BusinessRoles.ViewADCMSettings)
    is_allowed(adcm, BusinessRoles.EditADCMSettings)
    is_denied_to_user(cluster, BusinessRoles.ViewClusterConfigurations)

    delete_policy(user_policy)
    is_denied_to_user(adcm, BusinessRoles.ViewADCMSettings, is_list=True)
    is_denied_to_user(adcm, BusinessRoles.EditADCMSettings)


@use_role(BusinessRoles.ViewUsers)
def test_view_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewUsers)
    is_denied(user_sdk, BusinessRoles.CreateUser)
    simple_user = sdk_client_fs.user_create(username="test", password="test")
    is_denied_to_user(simple_user, BusinessRoles.EditUser)
    is_denied_to_user(simple_user, BusinessRoles.RemoveUser)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewUsers, is_list=True)


@use_role(BusinessRoles.CreateUser)
def test_create_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewUsers)
    is_allowed(user_sdk, BusinessRoles.CreateUser)
    simple_user = user_sdk.user(username="test")
    is_denied_to_user(simple_user, BusinessRoles.EditUser)
    is_denied_to_user(simple_user, BusinessRoles.RemoveUser)

    delete_policy(user_policy)
    sdk_client_fs.user(username="test").delete()
    is_denied(user_sdk, BusinessRoles.ViewUsers, is_list=True)
    is_denied(user_sdk, BusinessRoles.CreateUser)


@use_role(BusinessRoles.EditUser)
def test_edit_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewUsers)
    is_denied(user_sdk, BusinessRoles.CreateUser)
    simple_user = user_sdk.user(id=sdk_client_fs.user_create(username="test", password="test").id)
    is_allowed(simple_user, BusinessRoles.EditUser)
    is_denied_to_user(simple_user, BusinessRoles.RemoveUser)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.ViewUsers, is_list=True)
    is_denied_to_user(simple_user, BusinessRoles.EditUser)


@use_role(BusinessRoles.RemoveUser)
def test_remove_users(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Remove users" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewUsers)
    is_denied(user_sdk, BusinessRoles.CreateUser)
    simple_user = user_sdk.user(id=sdk_client_fs.user_create(username="test", password="test").id)
    is_denied_to_user(simple_user, BusinessRoles.EditUser)
    is_allowed(simple_user, BusinessRoles.RemoveUser)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewUsers, is_list=True)


@use_role(BusinessRoles.ViewGroups)
def test_view_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewGroups)
    is_denied(user_sdk, BusinessRoles.CreateGroup)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_denied_to_user(simple_group, BusinessRoles.EditGroup)
    is_denied_to_user(simple_group, BusinessRoles.RemoveGroup)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewGroups, is_list=True)


@use_role(BusinessRoles.CreateGroup)
def test_create_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create groups" role is ok"""
    is_allowed(user_sdk, BusinessRoles.ViewGroups)
    is_allowed(user_sdk, BusinessRoles.CreateGroup)
    simple_group = user_sdk.group(name="test")
    is_denied_to_user(simple_group, BusinessRoles.EditGroup)
    is_denied_to_user(simple_group, BusinessRoles.RemoveGroup)

    delete_policy(user_policy)
    sdk_client_fs.group(name="test").delete()
    is_denied(user_sdk, BusinessRoles.ViewGroups, is_list=True)
    is_denied(user_sdk, BusinessRoles.CreateGroup)


@use_role(BusinessRoles.EditGroup)
def test_edit_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewGroups)
    is_denied(user_sdk, BusinessRoles.CreateGroup)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_allowed(simple_group, BusinessRoles.EditGroup)
    is_denied_to_user(simple_group, BusinessRoles.RemoveGroup)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.ViewGroups, is_list=True)
    is_denied_to_user(simple_group, BusinessRoles.EditGroup)


@use_role(BusinessRoles.RemoveGroup)
def test_remove_groups(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Remove groups" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewGroups)
    is_denied(user_sdk, BusinessRoles.CreateGroup)
    simple_group = user_sdk.group(id=sdk_client_fs.group_create(name="test").id)
    is_denied_to_user(simple_group, BusinessRoles.EditGroup)
    is_allowed(simple_group, BusinessRoles.RemoveGroup)

    delete_policy(user_policy)
    is_denied_to_user(user_sdk, BusinessRoles.ViewGroups, is_list=True)


@use_role(BusinessRoles.ViewRoles)
def test_view_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "View roles" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewRoles)
    is_denied(user_sdk, BusinessRoles.ViewUsers, is_list=True)
    is_denied(user_sdk, BusinessRoles.ViewGroups, is_list=True)
    is_denied(user_sdk, BusinessRoles.ViewPolicies, is_list=True)
    is_denied(user_sdk, BusinessRoles.CreateCustomRoles)

    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_denied_to_user(custom_role, BusinessRoles.EditRoles)
    is_denied_to_user(custom_role, BusinessRoles.RemoveRoles)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewRoles, is_list=True)


@use_role(BusinessRoles.CreateCustomRoles)
def test_create_custom_role(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Create custom role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewRoles)
    is_allowed(user_sdk, BusinessRoles.CreateCustomRoles)
    custom_role = user_sdk.role(name="Custom role")
    is_denied_to_user(custom_role, BusinessRoles.EditRoles)
    is_denied_to_user(custom_role, BusinessRoles.RemoveRoles)

    delete_policy(user_policy)
    sdk_client_fs.role(id=custom_role.id).delete()
    is_denied(user_sdk, BusinessRoles.CreateCustomRoles)


@use_role(BusinessRoles.EditRoles)
def test_edit_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient, is_denied_to_user):
    """Test that "Edit role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewRoles)
    is_denied(user_sdk, BusinessRoles.CreateCustomRoles)

    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_allowed(custom_role, BusinessRoles.EditRoles)
    is_denied_to_user(custom_role, BusinessRoles.RemoveRoles)

    delete_policy(user_policy)
    is_denied_to_user(custom_role, BusinessRoles.EditRoles)


@use_role(BusinessRoles.RemoveRoles)
def test_remove_roles(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Remove role" role is ok"""

    is_allowed(user_sdk, BusinessRoles.ViewRoles)
    is_denied(user_sdk, BusinessRoles.CreateCustomRoles)

    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = user_sdk.role(name="Custom role")
    is_denied(custom_role, BusinessRoles.EditRoles, client=user_sdk)
    is_allowed(custom_role, BusinessRoles.RemoveRoles)

    delete_policy(user_policy)
    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    is_denied(user_sdk, BusinessRoles.ViewRoles, is_list=True)


@use_role(BusinessRoles.ViewPolicies)
def test_view_policies(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "View policies" role is ok"""
    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.ViewPolicies)
    is_denied(user_sdk, BusinessRoles.CreatePolicy, role=custom_role, user=[user])

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewPolicies, is_list=True)


@use_role(BusinessRoles.CreatePolicy)
def test_create_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Create policy" role is ok"""
    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.ViewPolicies)
    is_allowed(user_sdk, BusinessRoles.CreatePolicy, role=custom_role, user=[user])
    policy = user_sdk.policy(name="Test policy")
    is_denied(policy, BusinessRoles.EditPolicy, client=user_sdk)
    is_denied(policy, BusinessRoles.RemovePolicy, client=user_sdk)

    delete_policy(user_policy)
    sdk_client_fs.policy(id=policy.id).delete()
    is_denied(user_sdk, BusinessRoles.CreatePolicy, role=custom_role, user=[user])


@use_role(BusinessRoles.EditPolicy)
def test_edit_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Edit policy" role is ok"""
    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.ViewPolicies)
    is_denied(user_sdk, BusinessRoles.CreatePolicy, role=custom_role, user=[user])
    custom_policy = user_sdk.policy(
        id=sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user]).id
    )
    is_allowed(custom_policy, BusinessRoles.EditPolicy)
    is_denied(custom_policy, BusinessRoles.RemovePolicy, client=user_sdk)

    delete_policy(user_policy)
    is_denied(user_sdk, BusinessRoles.ViewPolicies, is_list=True)
    is_denied(custom_policy, BusinessRoles.EditPolicy, client=user_sdk)


@use_role(BusinessRoles.RemovePolicy)
def test_remove_policy(user_policy, user_sdk: ADCMClient, sdk_client_fs: ADCMClient):
    """Test that "Remove policy" role is ok"""
    BusinessRoles.CreateCustomRoles.value.method_call(sdk_client_fs)
    custom_role = sdk_client_fs.role(name="Custom role")
    user = sdk_client_fs.user(username="test_user")

    is_allowed(user_sdk, BusinessRoles.ViewPolicies)
    is_denied(user_sdk, BusinessRoles.CreatePolicy, role=custom_role, user=[user])
    custom_policy = user_sdk.policy(
        id=sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user]).id
    )
    is_denied(custom_policy, BusinessRoles.EditPolicy, client=user_sdk)
    is_allowed(custom_policy, BusinessRoles.RemovePolicy)

    delete_policy(user_policy)
    sdk_client_fs.policy_create(name="Test policy", objects=[], role=custom_role, user=[user])
    is_denied(user_sdk, BusinessRoles.ViewPolicies, is_list=True)
