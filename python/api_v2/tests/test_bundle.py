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

from datetime import datetime

from cm.bundle import _get_file_hashes
from cm.models import ADCM, Action, Bundle, ConfigLog, ObjectType, Prototype
from django.conf import settings
from django.db.models import F
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
import pytz

from api_v2.tests.base import BaseAPITestCase


class TestBundle(BaseAPITestCase):
    def setUp(self) -> None:
        self.client.login(username="admin", password="admin")

        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"

        self.bundle_1 = self.add_bundle(source_dir=cluster_bundle_1_path)

        cluster_new_bundle_path = self.test_bundles_dir / "cluster_two"

        self.new_bundle_file = self.prepare_bundle_file(source_dir=cluster_new_bundle_path, target_dir=settings.TMP_DIR)

        same_names_bundle_path = self.test_bundles_dir / "cluster_identical_cluster_and_service_names"
        self.same_names_bundle = self.add_bundle(source_dir=same_names_bundle_path)

    def test_list_success(self):
        response = (self.client.v2 / "bundles").get()

        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertEqual(response.json()["count"], 2)

    def test_upload_success(self):
        with open(settings.TMP_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_two").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_cluster_with_ansible_options_success(self):
        new_bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "cluster_with_ansible_options", target_dir=settings.TMP_DIR
        )
        new_bundle_file_old_style = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "cluster_with_ansible_options_dict_style", target_dir=settings.TMP_DIR
        )
        with open(settings.TMP_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        with open(settings.TMP_DIR / new_bundle_file_old_style, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        for bundle in Bundle.objects.filter(name__contains="cluster_ansible_options"):
            prototype_configs = bundle.prototype_set.first().prototypeconfig_set.all()
            for config in prototype_configs:
                if (
                    config.name == "group"
                    and config.subname in ("string", "text")
                    or config.name in ("my_string", "my_text", "structure")
                ):
                    self.assertTrue(config.ansible_options["unsafe"])
                else:
                    self.assertFalse(config.ansible_options["unsafe"])

    def test_upload_wrong_type_of_options_fail(self):
        new_bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "cluster_ansible_options_wrong_type",
            target_dir=settings.TMP_DIR,
        )
        with open(settings.TMP_DIR / new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "INVALID_OBJECT_DEFINITION")
        self.assertIn(
            'Map key "ansible_options" is not allowed here (rule "config_list_integer")', response.json()["desc"]
        )

    def test_upload_duplicate_fail(self):
        with open(settings.TMP_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            with open(settings.TMP_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f_duplicate:
                (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")
                response = (self.client.v2 / "bundles").post(data={"file": f_duplicate}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BUNDLE_ERROR",
                "desc": "Bundle already exists: Bundle with the same content is already "
                f"uploaded {settings.DOWNLOAD_DIR / self.new_bundle_file}",
                "level": "error",
            },
        )

    def test_adcm_6455_upload_sig_fail_and_cleanup(self):
        adcm_config = ConfigLog.objects.get(obj_ref=ADCM.objects.first().config)
        adcm_config.config["global"]["accept_only_verified_bundles"] = True
        adcm_config.save()
        with open(settings.TMP_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            for _ in range(2):
                response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")
                f.seek(0)

                self.assertEqual(response.status_code, HTTP_409_CONFLICT)
                self.assertEqual(response.json()["code"], "BUNDLE_SIGNATURE_VERIFICATION_ERROR")
                self.assertIn(
                    "has signature status 'absent', but 'accept_only_verified_bundles' is enabled. " "Upload rejected.",
                    response.json()["desc"],
                )
        self.assertIsNone(Bundle.objects.filter(name="cluster_two").first())

    def test_upload_fail(self):
        with open(settings.TMP_DIR / self.new_bundle_file, encoding=settings.ENCODING_UTF_8) as f:
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
        bundle_hash = self.bundle_1.hash
        response = self.client.v2[self.bundle_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(Bundle.objects.filter(pk=self.bundle_1.pk).exists(), False)
        self.assertIsNone(_get_file_hashes(path=self.directories["DOWNLOAD_DIR"]).get(bundle_hash))

    def test_delete_not_found_fail(self):
        response = (self.client.v2 / "bundles" / self.get_non_existent_pk(model=Bundle)).delete()

        self.assertEqual(response.status_code, HTTP_404_NOT_FOUND)

    def test_filtering_success(self):
        bundle = self.add_bundle(source_dir=self.test_bundles_dir / "cluster_two")
        prototype_name = bundle.name
        bundle.name = "unique_name_of_cluster"
        bundle.save()
        prototype = Prototype.objects.get(name=prototype_name)
        filters = {
            "id": (bundle.pk, None, 0),
            "display_name": (prototype.display_name, prototype.display_name[2:-1].upper(), "wrong"),
            "product": (prototype.name, None, "wrong"),
        }
        exact_items_found, partial_items_found = 1, 1
        for filter_name, (correct_value, partial_value, wrong_value) in filters.items():
            with self.subTest(filter_name=filter_name):
                response = (self.client.v2 / "bundles").get(query={filter_name: correct_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], exact_items_found)

                response = (self.client.v2 / "bundles").get(query={filter_name: wrong_value})
                self.assertEqual(response.status_code, HTTP_200_OK)
                self.assertEqual(response.json()["count"], 0)

                if partial_value:
                    response = (self.client.v2 / "bundles").get(query={filter_name: partial_value})
                    self.assertEqual(response.status_code, HTTP_200_OK)
                    self.assertEqual(response.json()["count"], partial_items_found)

    def test_ordering_success(self):
        ordering_fields = {
            "prototype__display_name": "displayName",
            "date": "uploadTime",
        }

        def get_response_results(response, ordering_field):
            if ordering_field == "uploadTime":
                return [
                    datetime.fromisoformat(item["uploadTime"][:-1]).replace(tzinfo=pytz.UTC)
                    for item in response.json()["results"]
                ]
            return [item[ordering_field] for item in response.json()["results"]]

        queryset = Bundle.objects.annotate(type=F("prototype__type"), display_name=F("prototype__display_name")).filter(
            type__in=[ObjectType.CLUSTER, ObjectType.PROVIDER]
        )

        for model_field, ordering_field in ordering_fields.items():
            with self.subTest(ordering_field=ordering_field):
                response = (self.client.v2 / "bundles").get(query={"ordering": ordering_field})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(queryset.order_by(model_field).values_list(model_field, flat=True)),
                )

                response = (self.client.v2 / "bundles").get(query={"ordering": f"-{ordering_field}"})
                ordered_result = get_response_results(response, ordering_field)
                self.assertListEqual(
                    ordered_result,
                    list(queryset.order_by(f"-{model_field}").values_list(model_field, flat=True)),
                )

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
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "old", target_dir=settings.TMP_DIR
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_success(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "older", target_dir=settings.TMP_DIR
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_fail(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "newer", target_dir=settings.TMP_DIR
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
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
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "multiple", target_dir=settings.TMP_DIR
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
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
            source_dir=self.test_bundles_dir / "invalid_bundles" / "plain_scripts_and_scripts_jinja",
            target_dir=settings.TMP_DIR,
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")
        self.assertIn('Map key "scripts_jinja" is not allowed here', response.data["desc"])
        self.assertIn('Map key "scripts" is not allowed here', response.data["desc"])

    def test_upload_scripts_jinja_in_job_fail(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "scripts_jinja_in_job", target_dir=settings.TMP_DIR
        )

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "INVALID_OBJECT_DEFINITION")
        self.assertIn('Map key "scripts_jinja" is not allowed here', response.data["desc"])

    def test_upload_scripts_jinja_success(self):
        bundle_file = self.prepare_bundle_file(
            source_dir=self.test_bundles_dir / "actions_with_scripts_jinja", target_dir=settings.TMP_DIR
        )

        self.assertEqual(Action.objects.filter(scripts_jinja="").count(), Action.objects.count())

        with open(settings.TMP_DIR / bundle_file, encoding=settings.ENCODING_UTF_8) as f:
            response = (self.client.v2 / "bundles").post(data={"file": f}, format_="multipart")

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertSetEqual(set(Action.objects.values_list("scripts_jinja", flat=True)), {"", "scripts.j2"})
