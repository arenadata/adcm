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

from cm.models import ClusterObject, ObjectType
from django.urls import reverse
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

APPLICATION_JSON = "application/json"


class RemoveUserFromPolicyTestCase(PolicyBaseTestCase):
    # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.service = ClusterObject.objects.first()
        self.new_user_2 = self.get_new_user(username="new_user_2", password="new_user_2_password")

        self.new_user_role_name = "new_user_role"
        self.create_role(
            role_name=self.new_user_role_name,
            parametrized_by_type=[ObjectType.CLUSTER],
            children_names=["Edit cluster configurations"],
        )

        self.new_user_2_role_name = "new_user_2_role"
        self.create_role(
            role_name=self.new_user_2_role_name,
            parametrized_by_type=[ObjectType.SERVICE],
            children_names=["Edit service configurations"],
        )

        self.edit_cluster_config_policy_pk = self.create_policy(
            role_name=self.new_user_role_name,
            obj=self.cluster,
            user_pk=self.new_user.pk,
        )
        self.edit_service_config_policy_pk = self.create_policy(
            role_name=self.new_user_2_role_name,
            obj=self.service,
            user_pk=self.new_user_2.pk,
        )

        self.new_user_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        self.new_user_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        self.new_user_2_perms = {perm.codename for perm in self.new_user_2.user_permissions.all()}
        self.new_user_2_perms.update(
            {perm.permission.codename for perm in self.new_user_2.userobjectpermission_set.all()}
        )

    def test_remove_user_from_policy(self):
        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": self.edit_cluster_config_policy_pk}),
            data={
                "user": [{"id": self.new_user_2.pk}],
                "object": [{"name": self.cluster.name, "type": ObjectType.CLUSTER, "id": self.cluster.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        response: Response = self.client.patch(
            path=reverse(viewname="v1:rbac:policy-detail", kwargs={"pk": self.edit_service_config_policy_pk}),
            data={
                "user": [{"id": self.new_user.pk}],
                "object": [{"name": self.service.name, "type": ObjectType.SERVICE, "id": self.service.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_200_OK)

        new_new_user_perms = {perm.codename for perm in self.new_user.user_permissions.all()}
        new_new_user_perms.update({perm.permission.codename for perm in self.new_user.userobjectpermission_set.all()})

        new_new_user_2_perms = {perm.codename for perm in self.new_user_2.user_permissions.all()}
        new_new_user_2_perms.update(
            {perm.permission.codename for perm in self.new_user_2.userobjectpermission_set.all()}
        )

        self.assertEqual(new_new_user_perms, self.new_user_2_perms)
        self.assertEqual(new_new_user_2_perms, self.new_user_perms)
