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

from cm.models import (
    Bundle,
    Cluster,
    ClusterObject,
    Host,
    HostProvider,
    ObjectType,
    Prototype,
    ServiceComponent,
)
from django.conf import settings
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class PolicyBaseTestCase(BaseTestCase):  # pylint: disable=too-many-instance-attributes
    def setUp(self) -> None:
        super().setUp()

        self.new_user_password = "new_user_password"
        self.new_user = self.get_new_user(username="new_user", password=self.new_user_password)
        self.cluster = self.create_cluster()
        self.provider = self.get_provider()
        host_ids = self.create_hosts()
        self.first_host_pk = host_ids[0]
        self.last_host_pk = host_ids[-1]
        self.add_hosts_to_cluster(host_ids=host_ids)
        self.service_6_proto = Prototype.objects.get(
            bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"),
            name="service_6_manual_add",
            type=ObjectType.SERVICE,
        )
        service_ids = self.get_service_ids()
        self.last_service_pk = service_ids[-1]
        self.host_component = self.get_host_components()
        self.last_component_pk = self.host_component[-1]["component_id"]

    def create_cluster(self) -> Cluster:
        bundle = self.upload_and_load_bundle(
            path=settings.BASE_DIR / "python" / "rbac" / "tests" / "files" / "test_cluster_for_cluster_admin_role.tar"
        )

        response: Response = self.client.post(
            path=reverse(viewname="cluster"),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=ObjectType.CLUSTER).pk,
                "name": "Test Cluster",
                "display_name": "Test Cluster",
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return Cluster.objects.get(pk=response.json()["id"])

    def create_hosts(self) -> list[int]:
        host_ids = []

        for host_num in range(5):
            fqdn = f"host-{host_num}"

            response: Response = self.client.post(
                path=reverse(viewname="host", kwargs={"provider_id": self.provider.pk}),
                data={"fqdn": fqdn},
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            host_ids.append(response.json()["id"])

        return host_ids

    def add_hosts_to_cluster(self, host_ids: list[int]) -> None:
        for host_id in host_ids:
            response: Response = self.client.post(
                path=reverse(viewname="host", kwargs={"cluster_id": self.cluster.pk}),
                data={"host_id": host_id},
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)

    def get_service_ids(self) -> list[int]:
        service_proto_pks = (
            Prototype.objects.filter(
                bundle=Bundle.objects.get(name="test_cluster_for_cluster_admin_role"), type=ObjectType.SERVICE
            )
            .exclude(pk=self.service_6_proto.pk)
            .order_by("id")
            .values_list("pk", flat=True)
        )
        service_ids = []

        for service_proto_pk in service_proto_pks:
            response = self.client.post(
                path=reverse(viewname="service", kwargs={"cluster_id": self.cluster.pk}),
                data={"prototype_id": service_proto_pk},
                content_type=APPLICATION_JSON,
            )

            self.assertEqual(response.status_code, HTTP_201_CREATED)
            service_ids.append(response.json()["id"])

        return service_ids

    def get_host_components(self) -> list[dict]:
        host_pks = [host.pk for host in Host.objects.order_by("id")]
        services = list(ClusterObject.objects.order_by("id"))
        hc_data = []

        for host_pk, service in zip(host_pks, services):
            for component in ServiceComponent.objects.filter(service=service).order_by("id"):
                hc_data.append({"component_id": component.pk, "host_id": host_pk, "service_id": service.pk})

        response: Response = self.client.post(
            path=reverse(viewname="host-component", kwargs={"cluster_id": self.cluster.pk}),
            data={"cluster_id": self.cluster.pk, "hc": hc_data},
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return hc_data

    def get_provider(self) -> HostProvider:
        bundle = self.upload_and_load_bundle(
            path=settings.BASE_DIR / "python" / "rbac" / "tests" / "files" / "provider.tar",
        )

        response: Response = self.client.post(
            path=reverse(viewname="provider"),
            data={
                "prototype_id": Prototype.objects.get(bundle=bundle, type=ObjectType.PROVIDER).pk,
                "name": "Test Provider",
                "display_name": "Test Provider",
                "bundle_id": bundle.pk,
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return HostProvider.objects.get(pk=response.json()["id"])
