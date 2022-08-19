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
from adwp_base.errors import AdwpEx

from rbac.models import Role
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


# pylint: disable=protected-access
@pytest.mark.django_db
def test_max_length():
    role = Role.objects.create(name='name', class_name='class', module_name='module')
    name_max_length = role._meta.get_field('name').max_length
    assert name_max_length == 160
    class_name_max_length = role._meta.get_field('class_name').max_length
    assert class_name_max_length == 32
    module_name_max_length = role._meta.get_field('module_name').max_length
    assert module_name_max_length == 32


@pytest.mark.django_db
def test_default():
    role = Role.objects.create()
    assert role.name == ''
    assert role.description == ''
    assert role.child.exists() is False
    assert role.permissions.exists() is False
    assert role.module_name == ''
    assert role.class_name == ''
    assert role.init_params == {}
    assert role.built_in is True
    assert role.parametrized_by_type == []
