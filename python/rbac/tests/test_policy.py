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

import pytest

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from adwp_base.errors import AdwpEx

from rbac.models import Role, Policy
from rbac.roles import ModelRole


@pytest.mark.django_db
def test_role_class():
    r = Role(module_name='qwe')
    with pytest.raises(AdwpEx) as e:
        r.get_role_obj()
    assert e.value.error_code == 'ROLE_MODULE_ERROR'

    r = Role(module_name='rbac', class_name='qwe')
    with pytest.raises(AdwpEx) as e:
        r.get_role_obj()
    assert e.value.error_code == 'ROLE_CLASS_ERROR'

    r = Role(module_name='rbac.roles', class_name='ModelRole')
    obj = r.get_role_obj()
    assert isinstance(obj, ModelRole)


def cook_user(name):
    user = User(username='Joe', is_active=True, is_superuser=False)
    user.save()
    return user


def cook_perm(model, codename):
    content = ContentType(app_label='adcm', model=model)
    content.save()
    perm = Permission(codename=f'{codename}_{model}', content_type=content)
    perm.save()
    return perm


@pytest.mark.django_db
def test_policy():
    user = cook_user('Joe')
    r = Role(
        name='add',
        module_name='rbac.roles',
        class_name='ModelRole',
    )
    r.save()
    perm = cook_perm('host', 'add')
    r.permissions.add(perm)
    p = Policy(role=r)
    p.save()
    p.user.add(user)

    assert perm not in user.user_permissions.all()
    p.apply()
    assert perm in user.user_permissions.all()
    # assert user.has_perm(perm)
