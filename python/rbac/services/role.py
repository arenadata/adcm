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
        update_m2m_field(role.child, child)

    return role
