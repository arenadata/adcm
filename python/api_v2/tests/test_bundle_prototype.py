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
# pylint: disable=too-many-lines
import json
import os
import shutil
import tarfile
from pathlib import Path

from api_v2.tests.base import BaseAPITestCase
from cm.bundle import prepare_bundle
from cm.models import Bundle, Prototype
from django.conf import settings
from django.test import Client
from rest_framework.reverse import reverse
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)


def upload_license(bundle_hash: str, src_path: Path) -> None:
    Path(settings.BUNDLE_DIR / bundle_hash).mkdir(parents=True, exist_ok=True)
    for file in src_path.glob("EULA.txt"):
        if file != settings.BUNDLE_DIR / bundle_hash / file.name:
            shutil.copy2(file, settings.BUNDLE_DIR / bundle_hash / file.name)


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        for file in os.listdir(source_dir):
            tar.add(source_dir / file, arcname=file)


class TestBundlePrototype(BaseAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.client.login(username="admin", password="admin")
        test_data_path = settings.BASE_DIR / "python" / "api_v2" / "tests" / "files"
        self.cluster_bundle_path = test_data_path / "test_bundle"
        self.cluster_bundle_anouther_version_path = test_data_path / "test_bundle_different_version"

    def test_prototype_list(self):
        response = self.client.get("/api/v2/prototypes/")
        self.assertGreater(len(response.data["results"]), 1)
        self.assertEqual(response.status_code, HTTP_200_OK)

    def test_prototype_versions(self):
        response = self.client.get("/api/v2/prototypes/versions/")
        self.assertGreater(len(json.loads(response.content)), 1)
        self.assertEqual(response.status_code, HTTP_200_OK)
        mandatory_fields = ("id", "version", "is_license_accepted", "bundle_id")
        prototype_fields = json.loads(response.content)[0]
        prototype_versions = prototype_fields["versions"][0]
        for field in mandatory_fields:
            self.assertIn(field, prototype_versions)
        self.assertIn("name", prototype_fields)

    def test_prototype_different_versions(self):
        upload_license("test_bundle", self.cluster_bundle_path)
        prepare_bundle(bundle_file="test_bundle", bundle_hash="test_bundle", path=self.cluster_bundle_path)
        upload_license("test_bundle", self.cluster_bundle_anouther_version_path)
        prepare_bundle(
            bundle_file="test_bundle", bundle_hash="test_bundle", path=self.cluster_bundle_anouther_version_path
        )
        response = self.client.get("/api/v2/prototypes/versions/")
        prototype = [c for c in json.loads(response.content) if c["name"] == "cluster_with_license_one"][0]
        self.assertEqual(len(prototype["versions"]), 2)
        self.assertEqual([v["version"] for v in prototype["versions"]], ["1.5", "1.0"])

    def test_prototype_details(self):
        proto = Prototype.objects.first()
        last_proto = Prototype.objects.all().order_by("-pk")[0]
        response = self.client.get(
            path=reverse(viewname="v2:prototype-detail", args=(proto.id,)),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        mandatory_fields = ("id", "name", "display_name", "description", "type", "bundle_id", "license")
        for field in mandatory_fields:
            self.assertIn(field, json.loads(response.content))
        self.assertIn("status", json.loads(response.content)["license"])
        self.assertIn("text", json.loads(response.content)["license"])
        response = self.client.get(
            path=reverse(viewname="v2:prototype-detail", args=(last_proto.id + 1,)),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_accept_license(self):
        upload_license("test_bundle_license", self.cluster_bundle_path)
        bundle = prepare_bundle(
            bundle_file="test_bundle_license", bundle_hash="test_bundle_license", path=self.cluster_bundle_path
        )
        proto_unaccepted = Prototype.objects.filter(bundle=bundle.pk).first()
        self.assertEqual(proto_unaccepted.is_license_accepted, False)
        self.assertEqual(proto_unaccepted.license, "unaccepted")
        response = self.client.post(
            path=reverse(viewname="v2:license-accept", kwargs={"prototype_prototype_id": proto_unaccepted.pk}), data={}
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        proto_accepted = Prototype.objects.filter(bundle=bundle.pk).first()
        self.assertEqual(proto_accepted.is_license_accepted, True)
        self.assertEqual(proto_accepted.license, "accepted")

    def test_bundle_list(self):
        params_http_200 = {
            "limit": 1,
            "offset": 0,
            "bundle_name": "test_bundle",
            "sort_column": "name",
            "product": "cluster",
        }

        for parameter, value in params_http_200.items():
            response = self.client.get(f"/api/v2/bundles/?{parameter}={value}")
            self.assertEqual(response.status_code, HTTP_200_OK)

        response = self.client.get("/api/v2/bundles/?sort_column=-name")
        first_bundle, last_bundle = response.data["results"][0], response.data["results"][-1]
        self.assertEqual(first_bundle["name"], "provider")
        self.assertEqual(last_bundle["name"], "ADCM")
        response = self.client.get("/api/v2/bundles/?product=cluster_one")
        self.assertEqual(response.data["results"][0]["name"], "cluster_one")

    def test_upload_bundle(self):
        upload_license("cluster_upload", src_path=self.cluster_bundle_path)
        make_tarfile(settings.BUNDLE_DIR / "cluster_upload.tar", settings.BUNDLE_DIR / "cluster_upload")

        with open(settings.BUNDLE_DIR / "cluster_upload.tar", mode="rb") as f:
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
            )
            self.assertEqual(response.status_code, HTTP_201_CREATED)
            response = self.client.post(
                path=reverse(viewname="v2:bundle-list"),
                data={"file": f},
            )
            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_bundle_details(self):
        bundle = Bundle.objects.first()
        last_bundle = Prototype.objects.all().order_by("-pk")[0]
        response = self.client.get(
            path=reverse(viewname="v2:bundle-detail", args=(bundle.id,)),
        )
        self.assertEqual(response.status_code, HTTP_200_OK)
        for field in ("id", "name", "display_name", "version", "edition", "upload_time"):
            self.assertIn(field, json.loads(response.content))
        response = self.client.get(
            path=reverse(viewname="v2:bundle-detail", args=(last_bundle.id + 1,)),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_bundle_delete(self):
        upload_license("test_delete_bundle", src_path=self.cluster_bundle_path)
        bundle = prepare_bundle(
            bundle_file="test_delete_bundle", bundle_hash="test_delete_bundle", path=self.cluster_bundle_path
        )
        response = self.client.delete(
            path=reverse(viewname="v2:bundle-detail", args=(bundle.id,)),
        )
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        response = self.client.delete(
            path=reverse(viewname="v2:bundle-detail", args=(bundle.id,)),
        )
        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)
