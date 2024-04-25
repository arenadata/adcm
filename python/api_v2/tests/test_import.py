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
import asyncio

from adcm.tests.base import APPLICATION_JSON
from asgiref.sync import sync_to_async
from cm.models import ClusterBind
from django.test import AsyncClient
from django.urls import reverse
from rbac.models import User
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN

from api_v2.tests.base import BaseAPITestCase


class TestImport(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        self.test_user_credentials = {"username": "test_user_username", "password": "test_user_password"}
        self.test_user = self.create_user(**self.test_user_credentials)

        export_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_export")
        self.export_cluster = self.add_cluster(bundle=export_bundle, name="cluster_export")
        self.export_service = self.add_services_to_cluster(
            service_names=["service_export"], cluster=self.export_cluster
        ).get()

        import_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_import")
        self.import_cluster = self.add_cluster(bundle=import_bundle, name="cluster_import")
        self.import_service = self.add_services_to_cluster(
            service_names=["service_import"], cluster=self.import_cluster
        ).get()
        self.import_service_2 = self.add_services_to_cluster(
            service_names=["service_import_2"], cluster=self.import_cluster
        ).get()
        self.aclient = AsyncClient()
        self.aclient.force_login(User.objects.get(username="admin"))

    def test_cluster_imports_list_success(self):
        response = self.client.get(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk})
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.assertDictEqual(
            response.json()["results"][0],
            {
                "cluster": {
                    "id": self.export_cluster.pk,
                    "name": self.export_cluster.name,
                    "status": "down",
                    "state": self.export_cluster.state,
                },
                "importCluster": {
                    "id": self.export_cluster.pk,
                    "isMultiBind": False,
                    "isRequired": False,
                    "prototype": {
                        "id": self.export_cluster.prototype.pk,
                        "name": self.export_cluster.prototype.name,
                        "displayName": self.export_cluster.prototype.display_name,
                        "version": self.export_cluster.prototype.version,
                    },
                },
                "importServices": [
                    {
                        "id": self.export_service.pk,
                        "name": self.export_service.name,
                        "displayName": self.export_service.display_name,
                        "version": self.export_service.version,
                        "isRequired": False,
                        "isMultiBind": False,
                        "prototype": {
                            "id": self.export_service.prototype.pk,
                            "name": self.export_service.prototype.name,
                            "displayName": self.export_service.prototype.display_name,
                            "version": self.export_service.prototype.version,
                        },
                    }
                ],
                "binds": [],
            },
        )

    def test_service_imports_list_success(self):
        response = self.client.get(
            path=reverse(
                viewname="v2:service-import-list",
                kwargs={"cluster_pk": self.import_cluster.pk, "service_pk": self.import_service.pk},
            )
        )

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)
        self.maxDiff = None
        self.assertDictEqual(
            response.json()["results"][0],
            {
                "cluster": {
                    "id": self.export_cluster.pk,
                    "name": self.export_cluster.name,
                    "status": "down",
                    "state": self.export_cluster.state,
                },
                "importCluster": {
                    "id": self.export_cluster.pk,
                    "isMultiBind": False,
                    "isRequired": False,
                    "prototype": {
                        "id": self.export_cluster.prototype.pk,
                        "name": self.export_cluster.prototype.name,
                        "displayName": self.export_cluster.prototype.display_name,
                        "version": self.export_cluster.prototype.version,
                    },
                },
                "importServices": [
                    {
                        "id": self.export_service.pk,
                        "name": self.export_service.name,
                        "displayName": self.export_service.display_name,
                        "version": self.export_service.version,
                        "isRequired": False,
                        "isMultiBind": False,
                        "prototype": {
                            "id": self.export_service.prototype.pk,
                            "name": self.export_service.prototype.name,
                            "displayName": self.export_service.prototype.display_name,
                            "version": self.export_service.prototype.version,
                        },
                    }
                ],
                "binds": [],
            },
        )

    def test_cluster_imports_create_success(self):
        response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[
                {"source": {"id": self.export_cluster.pk, "type": "cluster"}},
                {"source": {"id": self.export_service.pk, "type": "service"}},
            ],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(ClusterBind.objects.count(), len(data[0]["binds"]))
        self.assertListEqual(
            [
                {"id": ClusterBind.objects.first().pk, "source": {"id": self.export_cluster.pk, "type": "cluster"}},
                {"id": ClusterBind.objects.last().pk, "source": {"id": self.export_service.pk, "type": "service"}},
            ],
            data[0]["binds"],
        )

    def test_cluster_imports_create_empty_success(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        response = self.client.post(
            path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
            data=[],
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertFalse(ClusterBind.objects.exists())

    def test_another_cluster_imports_model_permission_list_success(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object import"):
            response = self.client.get(
                path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                data=[],
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_another_cluster_imports_object_permission_list_success(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.import_cluster, role_name="View imports"):
            response = self.client.get(
                path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                data=[],
            )

            self.assertEqual(response.status_code, HTTP_200_OK)

    def test_adcm_5488_another_cluster_imports_object_permission_create_success(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.import_cluster, role_name="Manage imports"):
            with self.grant_permissions(to=self.test_user, on=self.export_cluster, role_name="View imports"):
                response = self.client.post(
                    path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                    data=[
                        {"source": {"id": self.export_cluster.pk, "type": "cluster"}},
                        {"source": {"id": self.export_service.pk, "type": "service"}},
                    ],
                )

                self.assertEqual(response.status_code, HTTP_201_CREATED)
                data = response.json()
                self.assertEqual(len(data), 1)
                self.assertEqual(ClusterBind.objects.count(), len(data[0]["binds"]))
                self.assertListEqual(
                    [
                        {
                            "id": ClusterBind.objects.first().pk,
                            "source": {"id": self.export_cluster.pk, "type": "cluster"},
                        },
                        {
                            "id": ClusterBind.objects.last().pk,
                            "source": {"id": self.export_service.pk, "type": "service"},
                        },
                    ],
                    data[0]["binds"],
                )

    def test_another_cluster_imports_create_denied(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.import_cluster, role_name="Map hosts"):
            response = self.client.post(
                path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                data=[],
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_role_imports_create_denied(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            response = self.client.post(
                path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                data=[],
            )

            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_and_object_role_imports_create_denied(self):
        ClusterBind.objects.create(cluster=self.import_cluster, source_cluster=self.export_cluster)

        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            with self.grant_permissions(to=self.test_user, on=self.import_cluster, role_name="Map hosts"):
                response = self.client.post(
                    path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                    data=[],
                )

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_another_service_imports_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            with self.grant_permissions(to=self.test_user, on=self.import_service_2, role_name="Service Administrator"):
                with self.grant_permissions(
                    to=self.test_user, on=self.import_service, role_name="View service configurations"
                ):
                    response = self.client.get(
                        path=reverse(
                            viewname="v2:service-import-list",
                            kwargs={"cluster_pk": self.import_cluster.pk, "service_pk": self.import_service.pk},
                        )
                    )

                    self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_role_service_imports_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=[], role_name="View any object host-components"):
            with self.grant_permissions(to=self.test_user, on=self.import_service_2, role_name="Service Administrator"):
                with self.grant_permissions(
                    to=self.test_user, on=self.import_service, role_name="View service configurations"
                ):
                    response = self.client.get(
                        path=reverse(
                            viewname="v2:service-import-list",
                            kwargs={"cluster_pk": self.import_cluster.pk, "service_pk": self.import_service.pk},
                        )
                    )

                    self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_model_and_object_role_service_imports_list_denied(self):
        self.client.login(**self.test_user_credentials)
        with self.grant_permissions(to=self.test_user, on=self.import_service_2, role_name="Service Administrator"):
            with self.grant_permissions(
                to=self.test_user, on=self.import_service, role_name="View service configurations"
            ):
                response = self.client.get(
                    path=reverse(
                        viewname="v2:service-import-list",
                        kwargs={"cluster_pk": self.import_cluster.pk, "service_pk": self.import_service.pk},
                    )
                )

                self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    async def test_adcm_5295_cluster_imports_no_requests_race_success(self):
        async def import_list():
            resp = await self.aclient.post(
                path=reverse(viewname="v2:cluster-import-list", kwargs={"cluster_pk": self.import_cluster.pk}),
                data=[{"source": {"id": self.export_service.pk, "type": "service"}}],
                content_type=APPLICATION_JSON,
            )
            count = await sync_to_async(ClusterBind.objects.count)()
            return resp, count

        responses = await asyncio.gather(*[import_list()] * 1000)

        for response, clusterbinds in responses:
            self.assertEqual(clusterbinds, 1)
            self.assertEqual(response.status_code, HTTP_201_CREATED)
