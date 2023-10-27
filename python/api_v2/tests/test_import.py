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

from api_v2.tests.base import BaseAPITestCase
from cm.models import ClusterBind
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED


class TestImport(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        export_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_export")
        self.export_cluster = self.add_cluster(bundle=export_bundle, name="cluster_export")
        self.export_service = self.add_service_to_cluster(service_name="service_export", cluster=self.export_cluster)

        import_bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_import")
        self.import_cluster = self.add_cluster(bundle=import_bundle, name="cluster_import")
        self.import_service = self.add_service_to_cluster(service_name="service_import", cluster=self.import_cluster)

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