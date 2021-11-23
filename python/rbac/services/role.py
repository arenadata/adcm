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

from rest_framework.exceptions import ValidationError

from rbac.models import Role
from rbac.utils import update_m2m_field


def check_role_child(child: list[Role]) -> None:
    for item in child:
        if not item.built_in:
            errors = {'child': ['Only built-in roles allowed to be included as children.']}
            raise ValidationError(errors)
        if item.child.all():
            errors = {
                'child': ['Only 2 levels allowed, so you can’t connect to role who has a child.']
            }
            raise ValidationError(errors)


def role_create(built_in=False, **kwargs) -> Role:
    """Creating Role object"""
    child = kwargs.pop('child', [])
    check_role_child(child)
    role = Role.objects.create(built_in=built_in, **kwargs)
    role.child.add(*child)
    return role


def role_update(role: Role, **kwargs) -> Role:
    """Updating Role object"""
    child = kwargs.pop('child')
    check_role_child(child)
    for key, value in kwargs.items():
        setattr(role, key, value)
    role.save()

    if child is not None:
        update_m2m_field(role.child, child)

    return role
