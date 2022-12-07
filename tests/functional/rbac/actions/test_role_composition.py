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

"""Check how roles can be included in policies"""

import allure
import pytest
from adcm_client.objects import ADCMClient, Role, User
from adcm_pytest_plugin.utils import catch_failed, random_string
from coreapi.exceptions import ErrorMessage
from tests.functional.rbac.action_role_utils import (
    get_bundle_prefix_for_role_name,
    get_prototype_prefix_for_action_role,
)
from tests.functional.tools import AnyADCMObject
from tests.library.errorcodes import ADCMError

pytestmark = [pytest.mark.extra_rbac]

BAD_REQUEST = ADCMError('400 Bad Request', "")


def test_policy_created_only_on_child_of_composite_action_role(sdk_client_fs, simple_cluster, user):
    """
    Check that policy can be created only based on role that inherits composite action role (business action role)
    """
    bundle = simple_cluster.bundle()
    action_name = 'do_nothing'
    action_display_name = 'Do nothing'
    custom_role_name = 'TestSuperCustomRole'

    hidden_role_name = (
        f'{get_bundle_prefix_for_role_name(bundle)}'
        f'{get_prototype_prefix_for_action_role(bundle.cluster_prototype())}{action_name}'
    )
    hidden_role = sdk_client_fs.role(name=hidden_role_name)
    policy_creation_should_fail(sdk_client_fs, hidden_role, simple_cluster, user)

    business_role = sdk_client_fs.role(name=f'Cluster Action: {action_display_name}')
    policy_creation_should_fail(sdk_client_fs, business_role, simple_cluster, user)

    custom_role = sdk_client_fs.role_create(
        name=custom_role_name, display_name=custom_role_name, child=[{'id': business_role.id}]
    )
    policy_creation_should_succeeded(sdk_client_fs, custom_role, simple_cluster, user)


def policy_creation_should_succeeded(admin_client: ADCMClient, role: Role, adcm_object: AnyADCMObject, user: User):
    """Try to create policy based on give role and expect creation to succeed"""
    with allure.step(f'Create policy based on role "{role.display_name}" and expect it to succeeded'):
        policy_name = f'Test role {random_string(5)}'
        with catch_failed(ErrorMessage, 'Policy should be created'):
            admin_client.policy_create(name=policy_name, role=role, objects=[adcm_object], user=[user])


def policy_creation_should_fail(admin_client: ADCMClient, role: Role, adcm_object: AnyADCMObject, user: User):
    """Try to create policy based on given role and expect creation to fail"""
    with allure.step(f'Create policy based on role "{role.display_name}" and expect it to fail'):
        policy_name = f'Test role {random_string(5)}'
        with pytest.raises(ErrorMessage) as e:
            admin_client.policy_create(name=policy_name, role=role, objects=[adcm_object], user=[user])
        BAD_REQUEST.equal(e, f'Role with type "{role.type}" could not be used in policy')
