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

"""Generic helpers for RBAC actions testing"""

from typing import Union, List

import allure
from adcm_client.objects import ADCMClient, Policy
from adcm_pytest_plugin.utils import random_string

from tests.functional.rbac.conftest import BusinessRole
from tests.functional.tools import AnyADCMObject


def action_business_role(adcm_object: AnyADCMObject, action_display_name: str) -> BusinessRole:
    """Construct BusinessRole that allows to run action"""
    role_name = f'{adcm_object.prototype().type.capitalize()} Action: {action_display_name}'
    return BusinessRole(
        role_name, lambda user_obj, *args, **kwargs: user_obj.action(display_name=action_display_name).run(**kwargs)
    )


@allure.step("Create policy that allows to run action")
def create_action_policy(
    client: ADCMClient,
    adcm_object: Union[AnyADCMObject, List[AnyADCMObject]],
    *business_roles: BusinessRole,
    user=None,
    group=None,
) -> Policy:
    """Create policy based on business roles"""
    if not (user or group):
        raise ValueError("Either user or group should be provided to create policy")
    user = user or []
    group = group or []
    child_roles = [{'id': client.role(name=role.role_name).id} for role in business_roles]
    role_name = f"Test Action Role {random_string(6)}"
    action_parent_role = client.role_create(name=role_name, display_name=role_name, child=child_roles)
    return client.policy_create(
        name=f"Test Action Policy {role_name[-6:]}",
        role=action_parent_role,
        objects=adcm_object if isinstance(adcm_object, list) else [adcm_object],
        user=user if isinstance(user, list) else [user],
        group=group if isinstance(group, list) else [group],
    )
