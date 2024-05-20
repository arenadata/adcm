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

from cm.models import Action, Bundle
from django.conf import settings
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from api_v2.tests.base import BaseAPITestCase


class TestBundle(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)

        cluster_new_bundle_path = self.test_bundles_dir / "cluster_two"
        self.new_bundle_file = self.prepare_bundle_file(source_dir=cluster_new_bundle_path)

        same_names_bundle_path = self.test_bundles_dir / "cluster_identical_cluster_and_service_names"
        self.same_names_bundle = self.add_bundle(source_dir=same_names_bundle_path)

    def test_list_success(self):
        response = (self.client.v2 / "bundles").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_upload_success(self):
        with open(settings.DOWNLOAD_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_two").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_duplicate_fail(self):
        with open(settings.DOWNLOAD_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            with open(settings.DOWNLOAD_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f_duplicate:
                (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")
                response = (self.client.v2 / "bundles").post(data={"file": f_duplicate}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

    def test_upload_fail(self):
        with open(settings.DOWNLOAD_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            f.readlines()
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_two").exists(), False)
        self.assertEqual(response.status_code, HTTP_400_BAD_REQUEST)

    def test_retrieve_success(self):
        response = self.client.v2[self.bundle_1].get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.bundle_1.pk)

    def test_retrieve_not_found_fail(self):
        response = (self.client.v2 / "bundles" / self.get_non_existent_pk(model=Bundle)).get()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_delete_success(self):
        response = self.client.v2[self.bundle_1].delete()

        self.assertEqual(Bundle.objects.filter(pk=self.bundle_1.pk).exists(), False)
        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)

    def test_delete_not_found_fail(self):
        response = (self.client.v2 / "bundles" / self.get_non_existent_pk(model=Bundle)).delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_filter_by_display_name_success(self):
        response = (self.client.v2 / "bundles").get(query={"displayName": "product"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_filter_by_product_success(self):
        response = (self.client.v2 / "bundles").get(query={"product": "product"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 1)

    def test_ordering_asc_success(self):
        response = (self.client.v2 / "bundles").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [item["displayName"] for item in response.json()["results"]],
            ["cluster_one", "product"],
        )

    def test_ordering_desc_success(self):
        response = (self.client.v2 / "bundles").get(query={"ordering": "-displayName"})

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertListEqual(
            [item["displayName"] for item in response.json()["results"]],
            ["product", "cluster_one"],
        )

    def test_upload_no_required_component_fail(self):
        initial_bundles_count = Bundle.objects.count()

        bundle_path = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "cluster_with_absent_component_requires"
        )

        with open(settings.DOWNLOAD_DIR / bundle_path, encoding=settings.ENCODING_UTF_8) as bundle_file:
            response = (self.client.v2 / "bundles").post(data={"file": bundle_file}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(Bundle.objects.count(), initial_bundles_count)

    def test_upload_adcm_min_old_version_success(self):
        bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "adcm_min_version" / "old")

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_success(self):
        bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "older")

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_fail(self):
        bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "newer")

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BUNDLE_VERSION_ERROR",
                "desc": "This bundle required ADCM version equal to 10.0.0 or newer.",
                "level": "error",
            },
        )

    def test_upload_adcm_min_version_multiple_fail(self):
        bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "adcm_min_version" / "multiple")

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BUNDLE_VERSION_ERROR",
                "desc": "This bundle required ADCM version equal to 10.0.0 or newer.",
                "level": "error",
            },
        )

    def test_upload_plain_scripts_and_scripts_jinja_fail(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "plain_scripts_and_scripts_jinja"
        )

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")
        self.assertIn('Map key "scripts_jinja" is not allowed here', response.data["desc"])
        self.assertIn('Map key "scripts" is not allowed here', response.data["desc"])

    def test_upload_scripts_jinja_in_job_fail(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "scripts_jinja_in_job"
        )

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")
        self.assertIn('Map key "scripts_jinja" is not allowed here', response.data["desc"])

    def test_upload_scripts_jinja_success(self):
        bundle_file = self.prepare_bundle_file(source_dir=self.test_bundles_dir / "actions_with_scripts_jinja")

        self.assertEqual(Action.objects.filter(scripts_jinja="").count(), Action.objects.count())

        with open(settings.DOWNLOAD_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertSetEqual(set(Action.objects.values_list("scripts_jinja", flat=True)), {"", "scripts.j2"})
