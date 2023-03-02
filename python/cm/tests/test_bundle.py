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

import json
from pathlib import Path

from cm.adcm_config import ansible_decrypt
from cm.api import delete_host_provider
from cm.bundle import delete_bundle
from cm.errors import AdcmEx
from cm.models import ConfigLog
from cm.tests.test_upgrade import (
    cook_cluster,
    cook_cluster_bundle,
    cook_provider,
    cook_provider_bundle,
)
from django.conf import settings
from django.db import IntegrityError
from django.db.transaction import TransactionManagementError
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import APPLICATION_JSON, BaseTestCase


class TestBundle(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.files_dir = settings.BASE_DIR / "python" / "cm" / "tests" / "files"

    def test_bundle_upload_duplicate_upgrade_fail(self):
        with self.assertRaises(TransactionManagementError) as raises_context:
            self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_duplicated.tar"))

        # we expect here IntegrityError, but unittest do not raise it directly,
        # so check context of TransactionManagementError

        self.assertIsInstance(raises_context.exception.__context__, IntegrityError)

    def test_bundle_upload_upgrade_different_upgrade_name_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_name.tar"))

    def test_bundle_upload_upgrade_different_from_edition_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_from_edition.tar"))

    def test_bundle_upload_upgrade_different_min_version_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_min_version.tar"))

    def test_bundle_upload_upgrade_different_max_strict_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_max_strict.tar"))

    def test_bundle_upload_upgrade_different_state_available_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_state_available.tar"))

    def test_bundle_upload_upgrade_different_state_on_success_success(self):
        self.upload_and_load_bundle(path=Path(self.files_dir, "test_upgrade_different_state_on_success.tar"))

    def test_secretfile(self):
        bundle, cluster, config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(
                settings.BASE_DIR,
                "python/cm/tests/files/config_cluster_secretfile_secretmap.tar",
            ),
        )

        with open(Path(settings.BUNDLE_DIR, bundle.hash, "secretfile"), encoding=settings.ENCODING_UTF_8) as f:
            secret_file_bundle_content = f.read()

        self.assertNotIn(settings.ANSIBLE_VAULT_HEADER, secret_file_bundle_content)

        with open(
            Path(settings.FILE_DIR, f"cluster.{cluster.pk}.secretfile."),
            encoding=settings.ENCODING_UTF_8,
        ) as f:
            secret_file_content = f.read()

        self.assertEqual(secret_file_bundle_content, secret_file_content)

        new_content = "new content"
        config_log.config["secretfile"] = "new content"

        response: Response = self.client.post(
            path=reverse("config-log-list"),
            data={"obj_ref": cluster.config.pk, "config": json.dumps(config_log.config)},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        new_config_log = ConfigLog.objects.filter(obj_ref=cluster.config).order_by("pk").last()

        self.assertEqual(new_content, new_config_log.config["secretfile"])

    def test_secretfile_update_config(self):
        _, cluster, _ = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(
                settings.BASE_DIR,
                "python/cm/tests/files/test_secretfile_update_config.tar",
            ),
        )

        secretfile_bundle_content = "aaa"
        response: Response = self.client.post(
            path=reverse("config-history", kwargs={"cluster_id": cluster.pk}),
            params={"view": "interface"},
            data={
                "config": {
                    "password": "aaa",
                    "secrettext": "aaa",
                    "secretmap": {"aaa": "aaa"},
                    "secretfile": secretfile_bundle_content,
                    "group": {
                        "password": "aaa",
                        "secrettext": "aaa",
                        "secretmap": {"aaa": "aaa"},
                        "secretfile": "bbb",
                    },
                },
                "attr": {},
            },
            content_type=APPLICATION_JSON,
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        with open(
            Path(settings.FILE_DIR, f"cluster.{cluster.pk}.secretfile."),
            encoding=settings.ENCODING_UTF_8,
        ) as f:
            secret_file_content = f.read()

        self.assertEqual(secretfile_bundle_content, secret_file_content)

    def test_secretmap(self):
        _, cluster, config_log = self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(
                settings.BASE_DIR,
                "python/cm/tests/files/config_cluster_secretfile_secretmap.tar",
            ),
        )

        self.assertIn(settings.ANSIBLE_VAULT_HEADER, config_log.config["secretmap"]["key"])
        self.assertEqual("value", ansible_decrypt(config_log.config["secretmap"]["key"]))

        new_value = "new value"
        config_log.config["secretmap"]["key"] = "new value"

        response: Response = self.client.post(
            path=reverse("config-log-list"),
            data={"obj_ref": cluster.config.pk, "config": json.dumps(config_log.config)},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        new_config_log = ConfigLog.objects.filter(obj_ref=cluster.config).order_by("pk").last()

        self.assertIn(settings.ANSIBLE_VAULT_HEADER, new_config_log.config["secretmap"]["key"])
        self.assertEqual(new_value, ansible_decrypt(new_config_log.config["secretmap"]["key"]))

    def test_secretmap_no_default(self):
        self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(
                settings.BASE_DIR,
                "python/cm/tests/files/test_secret_config_v10_community.tar",
            ),
        )

    def test_secretmap_no_default1(self):
        self.upload_bundle_create_cluster_config_log(
            bundle_path=Path(
                settings.BASE_DIR,
                "python/cm/tests/files/test_secret_config_v12_community.tar",
            ),
        )

    def test_cluster_bundle_deletion(self):
        bundle = cook_cluster_bundle("1.0")
        cook_cluster(bundle, "TestCluster")
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, "BUNDLE_CONFLICT")

    def test_provider_bundle_deletion(self):
        bundle = cook_provider_bundle("1.0")
        provider = cook_provider(bundle, "TestProvider")
        try:
            delete_bundle(bundle)
        except AdcmEx as e:
            self.assertEqual(e.code, "BUNDLE_CONFLICT")

        try:
            delete_host_provider(provider)
        except AdcmEx as e:
            self.assertEqual(e.code, "PROVIDER_CONFLICT")
