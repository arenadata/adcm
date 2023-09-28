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


from cm.models import ClusterObject, Host, ServiceComponent
from django.urls import reverse
from rbac.models import Group
from rbac.tests.test_policy.base import PolicyBaseTestCase
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON


class ClusterAdminServiceAdminHostcomponentTestCase(PolicyBaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.new_user_group_2 = Group.objects.create(name="new_group_2")
        self.new_user_2 = self.get_new_user(
            username="new_user_2", password=self.new_user_password, group_pk=self.new_user_group_2.pk
        )
        self.service = ClusterObject.objects.get(prototype__name="service_1")

        self.create_policy(role_name="Cluster Administrator", obj=self.cluster, group_pk=self.new_user_group.pk)
        self.create_policy(role_name="Service Administrator", obj=self.service, group_pk=self.new_user_group_2.pk)

    def test_cluster_admin_can_change_host_config(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": self.provider.pk}),
            data={"fqdn": "new-host"},
            content_type=APPLICATION_JSON,
        )
        host = Host.objects.get(pk=response.json()["id"])

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"cluster_id": self.cluster.pk}),
            data={"host_id": host.pk},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIn(
            "cm.add_configlog",
            {f"{perm.content_type.app_label}.{perm.codename}" for perm in self.new_user_group.permissions.all()},
        )

        component = ServiceComponent.objects.get(prototype__name="component_1_1")
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={
                "cluster_id": self.cluster.pk,
                "hc": [{"component_id": component.pk, "host_id": host.pk, "service_id": self.service.pk}],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertIn(
            "cm.add_configlog",
            {f"{perm.content_type.app_label}.{perm.codename}" for perm in self.new_user_group.permissions.all()},
        )

        with self.another_user_logged_in(username=self.new_user.username, password=self.new_user_password):
            response: Response = self.client.post(
                path=reverse(viewname="v1:config-history", kwargs={"host_id": host.pk}),
                data={"config": {"string": "new_string"}},
                content_type=APPLICATION_JSON,
            )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
