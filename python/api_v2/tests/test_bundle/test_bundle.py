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

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Any
import tarfile
import unittest

from cm.legacy.bundle import _get_file_hashes
from cm.legacy.services.adcm import adcm_config
from cm.models import ADCM, Action, Bundle, ConfigLog, ObjectType, Prototype
from django.conf import settings
from django.db.models import F
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)
from tests.suites import ADCMDjangoAPISuite
from tests.use_cases import prepare_bundle_file


class TestBundleDelete(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

    def test_delete_success(self):
        cluster_bundle_1_path = self.test_bundles_dir / "cluster_one"
        bundle_1 = self.uc.upload_bundle(src=cluster_bundle_1_path)
        bundle_hash = bundle_1.hash
        response = self.client.v2[bundle_1].delete()

        self.assertEqual(response.status_code, HTTP_204_NO_CONTENT)
        self.assertEqual(Bundle.objects.filter(pk=bundle_1.pk).exists(), False)
        self.assertIsNone(_get_file_hashes(path=self.directories.downloads).get(bundle_hash))


class TestBundle(ADCMDjangoAPISuite):
    @classmethod
    def setUpTestData(cls) -> None:
        cls._initialize_roles_and_adcm()

        cluster_bundle_1_path = cls.test_bundles_dir / "cluster_one"
        cls.bundle_1 = cls.uc.upload_bundle(src=cluster_bundle_1_path)

        cluster_new_bundle_path = cls.test_bundles_dir / "cluster_two"

        cls.test_tmp_dir = settings.TMP_DIR
        cls.new_bundle_file = prepare_bundle_file(source_dir=cluster_new_bundle_path, target_dir=cls.test_tmp_dir)

        same_names_bundle_path = cls.test_bundles_dir / "cluster_identical_cluster_and_service_names"
        cls.same_names_bundle = cls.uc.upload_bundle(src=same_names_bundle_path)

    def setUp(self) -> None:
        super().setUp()

        adcm_config.cache_clear()

    def create_bundle_r(self, bundle_path: Path) -> Response:
        with open(bundle_path, encoding=settings.ENCODING_UTF_8) as bundle_file:
            return (self.client.v2 / "bundles").post(data={"file": bundle_file}, format_="multipart")

    def test_list_success(self):
        response = (self.client.v2 / "bundles").get()

        self.assertEqual(response.status_code, HTTP_200_OK, response.json())
        self.assertEqual(response.json()["count"], 2)

    def test_upload_success(self):
        bundle_path = self.test_tmp_dir / self.new_bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(Bundle.objects.filter(name="cluster_two").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_unsupported_contract_version_fail(self):
        unsupported_bundle = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "unsupported_contract_version",
            target_dir=self.test_tmp_dir,
        )
        expected_err_message = "Unsupported bundle's prototype usage"

        response = self.create_bundle_r(self.test_tmp_dir / unsupported_bundle)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_ERROR")
        self.assertIn(expected_err_message, response.json()["desc"])

    def test_adcm_6555_upload_parsing_errors_fail(self):
        with self.subTest("Too long path for config"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "config_wrong_default_file_long_path"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_VALIDATION_ERROR")
            self.assertIn("can't exceed 4096 bytes in path and 255 bytes in file name", response.json()["desc"])

        with self.subTest("Incorrect path for config"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "config_wrong_default_file_incorrect_path"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_VALIDATION_ERROR")
            self.assertIn("No such file or directory", response.json()["desc"])

        with self.subTest("Mutually exclusive checks for scripts/scripts_jinja."):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "mutually_exclusive_scripts"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn(
                'Exactly one of "scripts" or "scripts_template" must be provided, not multiple nor neither.',
                response.json()["desc"],
            )

        with self.subTest("Empty archive is uploaded"):
            temp_tar = NamedTemporaryFile(suffix=".tar")
            temp_tar.close()

            tar = tarfile.open(name=temp_tar.name, mode="w")
            tar.close()

            response = self.create_bundle_r(Path(temp_tar.name))

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertDictEqual(
                response.json(),
                {
                    "code": "BUNDLE_DEFINITION_ERROR",
                    "desc": "Bundle archive is empty",
                    "level": "error",
                },
            )

        with self.subTest("Incorrect internal script"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "incorrect_internal_script"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn(
                (
                    "'non_existent_internal_script_name' found using 'script' does not match any of the expected tags:"
                    " 'bundle_switch', 'bundle_revert', 'before_upgrade_clean', 'hc_apply'"
                ),
                response.json()["desc"],
            )

        with self.subTest("hc_apply script requires hc_acl"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "hc_apply_without_hc_acl_internal_script"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn('"hc_apply" requires "hc_acl" declaration', response.json()["desc"])

        with self.subTest("Duplicate config"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "action_duplicate_config"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn("Duplicate config", response.json()["desc"])

        with self.subTest("Action has on_success and has not masking"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "action_on_success_without_masking"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn('Action uses "on_success/on_fail" states without "masking"', response.json()["desc"])

        with self.subTest("Duplicated display names of components within 1 service"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "component_display_names"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_VALIDATION_ERROR")
            self.assertIn(
                "Display name for component within one service must be unique. Incorrect definition of component",
                response.json()["desc"],
            )

        with self.subTest("Action has on_success and has not masking"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "hc_acl_without_service"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_VALIDATION_ERROR")
            self.assertIn('"service" field is required in hc_acl for cluster and component', response.json()["desc"])

        with self.subTest("No root definition in bundle"):
            new_bundle_file = prepare_bundle_file(
                source_dir=Path(self.test_bundles_dir / "invalid_bundles" / "no_root_objects"),
                target_dir=self.test_tmp_dir,
            )
            bundle_path = self.test_tmp_dir / new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_ERROR")
            self.assertIn("Unsupported bundle's prototype usage", response.json()["desc"])

    def test_upload_cluster_with_ansible_options_success(self):
        new_bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "cluster_with_ansible_options", target_dir=self.test_tmp_dir
        )
        new_bundle_file_old_style = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "cluster_with_ansible_options_dict_style", target_dir=self.test_tmp_dir
        )
        bundle_path = self.test_tmp_dir / new_bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        bundle_path = self.test_tmp_dir / new_bundle_file_old_style
        response = self.create_bundle_r(bundle_path)

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
        new_bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "cluster_ansible_options_wrong_type",
            target_dir=self.test_tmp_dir,
        )
        bundle_path = self.test_tmp_dir / new_bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["code"], "BUNDLE_DEFINITION_ERROR")
        self.assertIn(
            "ansible_options\n       | extra_forbidden: Extra inputs are not permitted", response.json()["desc"]
        )

    def test_upload_duplicate_fail(self):
        bundle_path = self.test_tmp_dir / self.new_bundle_file
        self.create_bundle_r(bundle_path)
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertDictEqual(
            response.json(),
            {
                "code": "BUNDLE_ERROR",
                "desc": "Bundle already exists. Name: cluster_two, version: 1.0, edition: community",
                "level": "error",
            },
        )

    def test_adcm_6455_upload_sig_fail_and_cleanup(self):
        adcm_config = ConfigLog.objects.get(obj_ref=ADCM.objects.first().config)
        adcm_config.config["global"]["accept_only_verified_bundles"] = True
        adcm_config.save()

        for _ in range(2):
            bundle_path = self.test_tmp_dir / self.new_bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)
            self.assertEqual(response.json()["code"], "BUNDLE_SIGNATURE_VERIFICATION_ERROR")
            self.assertIn(
                "Upload rejected due to failed bundle verification: bundle's signature is 'absent'",
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
                    datetime.fromisoformat(item["uploadTime"][:-1]).replace(tzinfo=timezone.utc)
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
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "old", target_dir=self.test_tmp_dir
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_success(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "older", target_dir=self.test_tmp_dir
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(Bundle.objects.filter(name="cluster_adcm_min_version").exists(), True)
        self.assertEqual(response.status_code, HTTP_201_CREATED)

    def test_upload_adcm_min_version_fail(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "new" / "newer", target_dir=self.test_tmp_dir
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "BUNDLE_DEFINITION_ERROR")
        self.assertIn("This bundle required ADCM version equal to 10.0.0 or newer.", response.data["desc"])

    def test_upload_adcm_min_version_multiple_fail(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "adcm_min_version" / "multiple", target_dir=self.test_tmp_dir
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "BUNDLE_DEFINITION_ERROR")
        self.assertIn("This bundle required ADCM version equal to 10.0.0 or newer.", response.data["desc"])

    def test_upload_plain_scripts_and_scripts_jinja_fail(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "plain_scripts_and_scripts_jinja",
            target_dir=self.test_tmp_dir,
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "BUNDLE_DEFINITION_ERROR")
        self.assertIn(
            'Exactly one of "scripts" or "scripts_template" must be provided, not multiple nor neither.',
            response.data["desc"],
        )

    def test_upload_scripts_template_success(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "actions_with_scripts_template", target_dir=self.test_tmp_dir
        )

        self.assertEqual(Action.objects.filter(scripts_template__isnull=True).count(), Action.objects.count())

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_201_CREATED)
        self.assertEqual(
            Action.objects.filter(
                scripts_template={"engine": {"type": "jinja2"}, "file": {"path": "scripts.j2"}}
            ).count(),
            3,
        )

    def test_upload_hc_apply_scripts(self):
        bundle_file_for_right_hc_apply = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "bundle_hc_apply", target_dir=self.test_tmp_dir
        )
        bundle_file_for_wrong_hc_apply = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "bundle_hc_apply_wrong_definition", target_dir=self.test_tmp_dir
        )

        with self.subTest("hc_apply internal script: correct definition"):
            bundle_path = self.test_tmp_dir / bundle_file_for_right_hc_apply
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_201_CREATED)

            bundle = Bundle.objects.get(name="hc_apply_scripts_cluster")
            prototype = Prototype.objects.get(bundle=bundle, type="cluster")

            subaction = Action.objects.filter(prototype__name=prototype.name)[0].subaction_set.first()

            self.assertEqual("script_1", subaction.name)
            self.assertEqual("hc_apply", subaction.script)
            self.assertListEqual(
                [
                    {"action": "add", "component": "component_1", "service": "service_1"},
                    {"action": "remove", "component": "component_2", "service": "service_2"},
                    {"action": "add", "component": "component_3", "service": "service_2"},
                ],
                subaction.params["rules"],
            )

        with self.subTest("hc_apply internal script: wrong definition"):
            bundle_path = self.test_tmp_dir / bundle_file_for_wrong_hc_apply
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            self.assertEqual(response.data["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertIn(
                (
                    "          service\n"
                    "          | missing: Field required\n"
                    "          component\n"
                    "          | missing: Field required\n"
                    "          action\n"
                    "          | missing: Field required\n"
                    "          ansible_tags\n"
                    "          | unexpected_keyword_argument: Unexpected keyword argument"
                ),
                response.data["desc"],
            )

    def test_upload_unfilled_config_field(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "cluster_with_unfilled_config_field",
            target_dir=self.test_tmp_dir,
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertEqual(response.json()["desc"].count("Value error, the value cannot be empty"), 2)

    @unittest.skip("Unskip after ADCM-7491")
    def test_adcm_7398_upload_provider_bundle_with_templates_fail(self) -> None:
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "provider_groups_v1.0_community",
            target_dir=self.test_tmp_dir,
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        self.assertIn(
            "Errors found in definition of bundle entity:\n actions\n  scripts_template", response.json()["desc"]
        )

    def test_adcm_7395_wrong_template_definition(self):
        with self.subTest("scripts_template"):
            bundle_file = prepare_bundle_file(
                source_dir=self.test_bundles_dir / "invalid_bundles" / "wrong_scripts_template",
                target_dir=self.test_tmp_dir,
            )

            bundle_path = self.test_tmp_dir / bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            response = response.json()
            self.assertEqual(response["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertEqual(response["level"], "error")
            self.assertIn("invalid_template: Expected PythonTemplate | Jinja2Template template", response["desc"])

        with self.subTest("config_template"):
            bundle_file = prepare_bundle_file(
                source_dir=self.test_bundles_dir / "invalid_bundles" / "wrong_config_template",
                target_dir=self.test_tmp_dir,
            )

            bundle_path = self.test_tmp_dir / bundle_file
            response = self.create_bundle_r(bundle_path)

            self.assertEqual(response.status_code, HTTP_409_CONFLICT)

            response = response.json()
            self.assertEqual(response["code"], "BUNDLE_DEFINITION_ERROR")
            self.assertEqual(response["level"], "error")
            self.assertIn("invalid_template: Expected PythonTemplate | Jinja2Template template", response["desc"])

    def test_adcm_7600_incorrect_variant_param_disallowed(self):
        bundle_file = prepare_bundle_file(
            source_dir=self.test_bundles_dir / "invalid_bundles" / "variant_no_dependant_param",
            target_dir=self.test_tmp_dir,
        )

        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)

        response = response.json()
        self.assertEqual(response["code"], "BUNDLE_VALIDATION_ERROR")
        self.assertEqual(response["level"], "error")
        self.assertIn("/my_list_variant", response["desc"])
        self.assertIn("variant", response["desc"])

    def test_adcm_7604_upload_bundle_not_match_config_pattern(self):
        checked_config = "invalid_secrettext"
        error_description = "does not match pattern"
        source_dir = self.test_bundles_dir / "invalid_bundles" / "wrong_pattern_config"

        bundle_file = prepare_bundle_file(source_dir=source_dir, target_dir=self.test_tmp_dir)
        bundle_path = self.test_tmp_dir / bundle_file
        response = self.create_bundle_r(bundle_path)

        self.assertEqual(response.status_code, HTTP_409_CONFLICT)
        response = response.json()
        self.assertEqual(response["code"], "BUNDLE_VALIDATION_ERROR")
        self.assertIn(checked_config, response["desc"])
        self.assertIn(error_description, response["desc"])


class TestBundleContract_V_2_0(ADCMDjangoAPISuite):  # noqa: N801
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tempdir = Path(mkdtemp())

    def upload_bundle(self, path: Path) -> Any:
        endpoint = self.client.v2 / "bundles"

        bundle_file_name = self.prepare_bundle_file(source_dir=path, target_dir=self.tempdir)
        bundle_file = self.tempdir / bundle_file_name

        with bundle_file.open(encoding="utf-8") as file_:
            return endpoint.post(data={"file": file_}, format_="multipart")

    def test_upload_bundle(self):
        bundle_names = ("cluster_simple", "provider_simple")

        for name in bundle_names:
            with self.subTest(name):
                bundle_path = self.test_bundles_dir / "v_2_0" / name

                response = self.upload_bundle(bundle_path)

                self.assertEqual(response.status_code, HTTP_201_CREATED, response.json())
