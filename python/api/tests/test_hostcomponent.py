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

from pathlib import Path

from adcm.tests.base import APPLICATION_JSON, BaseTestCase
from cm.models import HostComponent, ObjectType, Prototype, ServiceComponent
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestHostComponentOrdering(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_files_dir = self.base_dir / "python" / "api" / "tests" / "files"

        self.cluster_pk = self.create_adcm_entity(
            bundle_filepath=self.test_files_dir / "test_cluster_many_components.tar", entity_type=ObjectType.CLUSTER
        )

        self.create_hc()

    def create_adcm_entity(
        self, bundle_filepath: Path | None, entity_type: ObjectType, view_kwargs: dict | None = None
    ):
        if bundle_filepath is not None:
            bundle = self.upload_and_load_bundle(path=bundle_filepath)

        if view_kwargs is None:
            view_kwargs = {}

        match entity_type:
            case ObjectType.CLUSTER:
                viewname = "v1:cluster"
                data = {
                    "prototype_id": Prototype.objects.get(type=ObjectType.CLUSTER).pk,
                    "name": "Test cluster name",
                    "display_name": "Test cluster display_name",
                    "bundle_id": bundle.pk,
                }
            case ObjectType.PROVIDER:
                viewname = "v1:provider"
                data = {
                    "prototype_id": Prototype.objects.get(type=ObjectType.PROVIDER).pk,
                    "name": "Test provider name",
                    "display_name": "Test provider display_name",
                    "bundle_id": bundle.pk,
                }
            case ObjectType.SERVICE:
                viewname = "v1:service"
                data = {"prototype_id": Prototype.objects.get(type=ObjectType.SERVICE).pk}

        response: Response = self.client.post(
            path=reverse(viewname=viewname, kwargs=view_kwargs),
            data=data,
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

        return response.json()["id"]

    def create_hosts(self, count: int) -> list[int]:
        provider_pk = self.create_adcm_entity(
            bundle_filepath=self.test_files_dir / "provider.tar", entity_type=ObjectType.PROVIDER
        )

        host_pks = []

        for host_num in range(count):
            response: Response = self.client.post(
                path=reverse(viewname="v1:host", kwargs={"provider_id": provider_pk}),
                data={"fqdn": f"testhost{host_num}"},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            host_pk = response.json()["id"]

            response: Response = self.client.post(
                path=reverse(viewname="v1:host", kwargs={"cluster_id": self.cluster_pk}),
                data={"host_id": host_pk},
                content_type=APPLICATION_JSON,
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)

            host_pks.append(host_pk)

        return host_pks

    def create_hc(self) -> None:
        service_pk = self.create_adcm_entity(
            bundle_filepath=None, entity_type=ObjectType.SERVICE, view_kwargs={"cluster_id": self.cluster_pk}
        )

        host_pks = self.create_hosts(count=25)
        self.assertEqual(len(host_pks), ServiceComponent.objects.count())

        component_pks = ServiceComponent.objects.order_by("pk").values_list("pk", flat=True)
        hc_data = [
            {"host_id": host_pk, "service_id": service_pk, "component_id": component_pk}
            for host_pk, component_pk in zip(host_pks, component_pks)
        ]

        response: Response = self.client.post(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster_pk}),
            data={"cluster_id": self.cluster_pk, "hc": hc_data},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_hostcomponent_ordering_not_specified_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster_pk}),
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            list1=[hc["id"] for hc in response.json()],
            list2=list(HostComponent.objects.order_by("pk").values_list("pk", flat=True)),
        )

    def test_hostcomponent_ordering_id_ascending_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster_pk}),
            data={"ordering": "id"},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            list1=[hc["id"] for hc in response.json()],
            list2=list(HostComponent.objects.order_by("pk").values_list("pk", flat=True)),
        )

    def test_hostcomponent_ordering_id_descending_success(self):
        response: Response = self.client.get(
            path=reverse(viewname="v1:host-component", kwargs={"cluster_id": self.cluster_pk}),
            data={"ordering": "-id"},
            content_type=APPLICATION_JSON,
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            list1=[hc["id"] for hc in response.json()],
            list2=list(HostComponent.objects.order_by("-pk").values_list("pk", flat=True)),
        )
