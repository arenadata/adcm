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

from adcm.tests.base import APPLICATION_JSON, BaseTestCase, BusinessLogicMixin
from cm.models import (
    Cluster,
    Host,
    ObjectConfig,
    ObjectType,
    Prototype,
    Service,
    ServiceComponent,
)
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED

from rbac.models import Group


class PolicyWithServiceAdminRoleTestCase(BaseTestCase, BusinessLogicMixin):
    def setUp(self) -> None:
        super().setUp()

        self.new_user_password = "new_user_password"
        self.new_user_group = Group.objects.create(name="new_group")
        new_user = self.get_new_user(
            username="new_user", password=self.new_user_password, group_pk=self.new_user_group.pk
        )

        self.cluster_bundle = self.upload_and_load_bundle(
            path=self.base_dir / "python" / "rbac" / "tests" / "files" / "service_admin_cluster.tar"
        )
        self.cluster_pk = self.get_cluster_pk()
        self.host_pk = self.get_host_pk()
        self.service = self.get_service()
        self.add_host_to_cluster(
            cluster=Cluster.objects.get(id=self.cluster_pk), host=Host.objects.get(id=self.host_pk)
        )

        self.create_policy(role_name="Service Administrator", obj=self.service, group_pk=self.new_user_group.pk)
        self.another_user_log_in(username=new_user.username, password=self.new_user_password)

        self.group_config_pk = self.get_group_config_pk()

    def get_provider_pk(self):
        provider_bundle = self.upload_and_load_bundle(
            path=self.base_dir / "python" / "rbac" / "tests" / "files" / "service_admin_provider.tar"
        )
        response: Response = self.client.post(
            path=reverse(viewname="v1:provider"),
            data={
                "prototype_id": Prototype.objects.get(bundle=provider_bundle, type=ObjectType.PROVIDER).pk,
                "name": "test_provider",
                "bundle_id": provider_bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return response.json()["id"]

    def get_host_pk(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host", kwargs={"provider_id": self.get_provider_pk()}),
            data={"fqdn": "test-host"},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        return response.json()["id"]

    def get_cluster_pk(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:cluster"),
            data={
                "prototype_id": Prototype.objects.get(bundle=self.cluster_bundle, type=ObjectType.CLUSTER).pk,
                "name": "test_cluster",
                "bundle_id": self.cluster_bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )
        return response.json()["id"]

    def get_service(self):
        response = self.client.post(
            path=reverse(viewname="v1:service", kwargs={"cluster_id": self.cluster_pk}),
            data={"prototype_id": Prototype.objects.get(bundle=self.cluster_bundle, type=ObjectType.SERVICE).pk},
            content_type=APPLICATION_JSON,
        )
        return Service.objects.get(pk=response.json()["id"])

    def create_host_component(self):
        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster_pk}),
            data={
                "cluster_id": self.cluster_pk,
                "hc": [
                    {
                        "component_id": ServiceComponent.objects.first().pk,
                        "host_id": self.host_pk,
                        "service_id": self.service.pk,
                    }
                ],
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def get_group_config_pk(self) -> int:
        response: Response = self.client.post(
            path=reverse(viewname="v1:group-config-list"),
            data={
                "name": "service_group_config",
                "object_id": self.service.pk,
                "object_type": ObjectType.SERVICE,
                "config_id": ObjectConfig.objects.create(current=0, previous=0).pk,
            },
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return response.json()["id"]

    def test_retrieve_config_group_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:group-config-detail", kwargs={"pk": self.group_config_pk}),
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
