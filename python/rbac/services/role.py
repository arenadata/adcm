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

from typing import List

from rest_framework.exceptions import ValidationError

from rbac.models import Role, RoleTypes
from rbac.utils import update_m2m_field


def set_parametrized_from_child(role, children: List[Role]):
    param_list = []

    for child in children:
        child_params = child.parametrized_by_type
        for child_param in child_params:
            if not check_child_parametrized(child_param, param_list):
                param_list.append(child_param)
    role.parametrized_by_type = param_list
    role.save()


def check_child_parametrized(child_param, param_list) -> bool:
    cluster_hierarchy = {'cluster', 'service', 'component'}
    if ((child_param == 'provider') and bool(cluster_hierarchy & set(param_list))) or (
        (child_param in cluster_hierarchy) and ('provider' in param_list)
    ):
        errors = {'child': ['This children parametrized by types from different hierarchy']}
        raise ValidationError(errors)
    return child_param in param_list


def check_role_child(child: List[Role]) -> None:
    for item in child:
        if not item.built_in:
            errors = {'child': ['Only built-in roles allowed to be included as children.']}
            raise ValidationError(errors)
        if item.type != RoleTypes.business:
            errors = {'child': ['Only business roles allowed to be included as children.']}
            raise ValidationError(errors)


def role_create(built_in=False, type_of_role=RoleTypes.role, **kwargs) -> Role:
    """Creating Role object"""
    child = kwargs.pop('child', [])
    check_role_child(child)
    if 'name' in kwargs:
        name = kwargs.pop('name')
    else:
        name = kwargs['display_name']
    role = Role.objects.create(
        name=name,
        built_in=built_in,
        type=type_of_role,
        module_name='rbac.roles',
        class_name='ParentRole',
        **kwargs,
    )
    set_parametrized_from_child(role, child)
    role.child.add(*child)
    return role


def role_update(role: Role, **kwargs) -> Role:
    """Updating Role object"""
    child = kwargs.pop('child', [])
    check_role_child(child)
    kwargs.pop('name', None)
    for key, value in kwargs.items():
        setattr(role, key, value)
    role.save()

    if child is not None:
        set_parametrized_from_child(role, child)
        update_m2m_field(role.child, child)

    return role
