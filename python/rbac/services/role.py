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

from adwp_base.errors import AdwpEx
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError

from rbac.models import Role, RoleTypes
from rbac.utils import update_m2m_field


def set_parametrized_from_child(role, children: List[Role]):
    param_set = set()
    cluster_hierarchy = {'cluster', 'service', 'component'}
    provider_hierarchy = {'provider'}

    for child in children:
        param_set.update(child.parametrized_by_type)
        if param_set.intersection(provider_hierarchy) and param_set.intersection(cluster_hierarchy):
            msg = {'This children parametrized by types from different hierarchy'}
            raise AdwpEx('ROLE_ERROR', msg)
    role.parametrized_by_type = list(param_set)
    role.save()


def check_role_child(child: List[Role]) -> None:
    if not child:
        errors = {'child': ['Roles without children make not sense']}
        raise ValidationError(errors)
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
    name = kwargs.pop('name', '')
    if name == '':
        name = kwargs['display_name']
    try:
        role = Role.objects.create(
            name=name,
            built_in=built_in,
            type=type_of_role,
            module_name='rbac.roles',
            class_name='ParentRole',
            **kwargs,
        )
    except IntegrityError as exc:
        raise AdwpEx('ROLE_CREATE_ERROR', msg=f'Role creation failed with error {exc}') from exc
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
    try:
        role.save()
    except IntegrityError as exc:
        raise AdwpEx('ROLE_UPDATE_ERROR', msg=f'Role update failed with error {exc}') from exc

    if child is not None:
        set_parametrized_from_child(role, child)
        update_m2m_field(role.child, child)

    return role
