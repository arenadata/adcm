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

from cm.models import ObjectType
from django.urls import reverse
from rbac.roles import Role, RoleTypes
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

APPLICATION_JSON = "application/json"


class DeletePolicyTestCase(PolicyBaseTestCase):
    def test_delete_policy(self):
        provider_action_role = Role.objects.get(name="Provider Action: action")
        cluster_action_role = Role.objects.get(name="Cluster Action: action_1_success")

        provider_role_name = "test_role_provider"
        provider_role = Role.objects.create(
            name=provider_role_name,
            display_name=provider_role_name,
            type=RoleTypes.ROLE,
            module_name="rbac.roles",
            class_name="ParentRole",
            parametrized_by_type=[ObjectType.PROVIDER],
        )

        cluster_role_name = "test_role_cluster"
        cluster_role = Role.objects.create(
            name=cluster_role_name,
            display_name=cluster_role_name,
            type=RoleTypes.ROLE,
            module_name="rbac.roles",
            class_name="ParentRole",
            parametrized_by_type=[ObjectType.CLUSTER],
        )

        provider_role.child.add(provider_action_role)
        cluster_role.child.add(cluster_action_role)

        provider_policy_pk = self.create_policy(role_name=provider_role_name, user_pk=self.new_user.pk)
        provider_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        provider_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.create_policy(role_name=cluster_role_name, user_pk=self.new_user.pk)
        cluster_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        cluster_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})
        cluster_perms = cluster_perms - provider_perms
        cluster_perms.add("view_action")

        response: Response = self.client.delete(
            path=reverse(viewname="rbac:policy-detail", kwargs={"pk": provider_policy_pk}),
        )

        user_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        user_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertSetEqual(user_perms, cluster_perms)
