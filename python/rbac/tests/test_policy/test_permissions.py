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

from django.contrib.auth.models import Group, Permission
from guardian.models import UserObjectPermission
from rbac.models import Group as RBACGroup
from rbac.models import Policy
from rbac.roles import assign_user_or_group_perm
from rbac.tests.test_policy.base import PolicyBaseTestCase


class RemovePermissionsTestCase(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.create_policy(role_name="Cluster Administrator", user_pk=self.new_user.pk)
        self.policy = Policy.objects.first()
        self.policy.group.add(RBACGroup.objects.create(name="test_group_1"))

        assign_user_or_group_perm(
            policy=self.policy,
            permission=Permission.objects.filter(codename="add_group")[0],
            obj=Group.objects.create(name="test_group_2"),
        )

    def test_remove_permissions(self):
        model_permission_codenames = {
            policy_permission.permission.codename for policy_permission in self.policy.model_perm.all()
        }
        user_object_permissions = {
            user_object_permission.permission.codename for user_object_permission in self.policy.user_object_perm.all()
        }
        group_object_permissions = {
            group_object_permission.permission.codename
            for group_object_permission in self.policy.group_object_perm.all()
        }

        self.assertTrue(model_permission_codenames)
        self.assertTrue(user_object_permissions)
        self.assertTrue(group_object_permissions)

        self.policy.remove_permissions()

        self.policy.refresh_from_db()

        model_permission_codenames = {
            policy_permission.permission.codename for policy_permission in self.policy.model_perm.all()
        }
        user_object_permissions = {
            user_object_permission.permission.codename for user_object_permission in self.policy.user_object_perm.all()
        }
        group_object_permissions = {
            group_object_permission.permission.codename
            for group_object_permission in self.policy.group_object_perm.all()
        }

        self.assertFalse(model_permission_codenames)
        self.assertFalse(user_object_permissions)
        self.assertFalse(group_object_permissions)


class AssignPermissionsTestCase(PolicyBaseTestCase):
    def test_assign_permissions(self):
        self.create_policy(role_name="Cluster Administrator", user_pk=self.new_user.pk)

        self.assertTrue(UserObjectPermission.objects.all())
