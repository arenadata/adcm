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
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT

from rbac.tests.test_policy.base import PolicyBaseTestCase

APPLICATION_JSON = "application/json"


class DeletePolicyTestCase(PolicyBaseTestCase):
    def test_delete_policy(self):
        provider_role_name = "test_role_provider"
        cluster_role_name = "test_role_cluster"
        self.create_role(
            role_name=provider_role_name,
            parametrized_by_type=[ObjectType.PROVIDER],
            children_names=["Provider Action: action"],
        )
        self.create_role(
            role_name=cluster_role_name,
            parametrized_by_type=[ObjectType.CLUSTER],
            children_names=["Cluster Action: action_1_success"],
        )

        provider_policy_pk = self.create_policy(
            role_name=provider_role_name, obj=self.provider, group_pk=self.new_user_group.pk
        )
        provider_perms = {perm.codename for perm in self.new_user_group.permissions.all()}
        provider_perms.update(
            {perm.permission.codename for perm in self.new_user_group.groupobjectpermission_set.all()}
        )

        self.create_policy(role_name=cluster_role_name, obj=self.cluster, group_pk=self.new_user_group.pk)
        cluster_perms = {perm.codename for perm in self.new_user_group.permissions.all()}
        cluster_perms.update({perm.permission.codename for perm in self.new_user_group.groupobjectpermission_set.all()})
        cluster_perms = cluster_perms - provider_perms
        cluster_perms.add("view_action")

        response: Response = self.client.delete(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": provider_policy_pk}),
        )

        group_perms = {perm.codename for perm in self.new_user_group.permissions.all()}
        group_perms.update({perm.permission.codename for perm in self.new_user_group.groupobjectpermission_set.all()})

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertSetEqual(group_perms, cluster_perms)
