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
from cm.models import Bundle


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


def cook_perm(app, codename, model):
    content = ContentType(app_label=app, model=model)
    content.save()
    perm = Permission(codename=f'{codename}_{model}', content_type=content)
    perm.save()
    return perm


def clear_perm_cache(user):
    delattr(user, '_perm_cache')
    delattr(user, '_user_perm_cache')
    delattr(user, '_group_perm_cache')


@pytest.mark.django_db
def test_policy():
    user = cook_user('Joe')
    r = Role(
        name='add',
        module_name='rbac.roles',
        class_name='ModelRole',
    )
    r.save()
    perm = cook_perm('adcm', 'add', 'host')
    r.permissions.add(perm)
    p = Policy(role=r)
    p.save()
    p.user.add(user)

    # assert perm not in user.user_permissions.all()
    assert not user.has_perm('adcm.add_host')
    clear_perm_cache(user)

    p.apply()
    # assert perm in user.user_permissions.all()
    assert user.has_perm('adcm.add_host')

    clear_perm_cache(user)
    p.apply()
    assert user.has_perm('adcm.add_host')


@pytest.mark.django_db
def test_object_policy():
    user = cook_user('Joe')
    r = Role(
        name='view',
        module_name='rbac.roles',
        class_name='ObjectRole',
    )
    r.save()
    perm = Permission.objects.get(codename='view_bundle')
    r.permissions.add(perm)
    p = Policy(role=r)
    p.save()
    p.user.add(user)

    b1 = Bundle(name='ADH', version='1.0')
    b1.save()

    b2 = Bundle(name='ADH', version='2.0')
    b2.save()

    p.add_object(b1)
    assert not user.has_perm('cm.view_bundle', b1)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)

    p.apply()

    assert user.has_perm('cm.view_bundle', b1)
    assert not user.has_perm('cm.view_bundle', b2)
