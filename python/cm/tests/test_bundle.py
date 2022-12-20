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
import os
from contextlib import contextmanager
from pathlib import Path
from tarfile import TarFile

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED

from adcm.tests.base import BaseTestCase
from cm.adcm_config import ansible_decrypt
from cm.api import delete_host_provider
from cm.bundle import delete_bundle
from cm.errors import AdcmEx
from cm.models import Bundle, ConfigLog
from cm.tests.test_upgrade import (
    cook_cluster,
    cook_cluster_bundle,
    cook_provider,
    cook_provider_bundle,
)


class TestBundle(BaseTestCase):
    bundle_config_template = """
- type: cluster
  name: Monitoring
  version: 666
  edition: community
  description: Monitoring and Control Software

  upgrade:
    - name: {upg1_name}
      description: test upg1 description
      from_edition:{upg1_from_edition}
      versions:
        min: "{upg1_min_version}"
        max_strict: "{upg1_max_strict}"
      scripts:
        - name: {upg1_script1_name}
          script: monitoring/bundle_pre_check.yaml
          script_type: ansible
          on_fail: running
        - name: {upg1_script2_name}
          script: bundle_switch
          script_type: internal
        - name: {upg1_script3_name}
          script: monitoring/bundle_post_upgrade.yaml
          params:
            ansible_tags: install
          script_type: ansible
      states:
        available: {upg1_state_available}
        on_success: {upg1_state_on_success}
    - name: {upg2_name}
      from_edition:{upg2_from_edition}
      versions:
        min: "{upg2_min_version}"
        max_strict: "{upg2_max_strict}"
      scripts:
        - name: {upg2_script1_name}
          script: monitoring/bundle_pre_check.yaml
          script_type: ansible
          on_fail: running
        - name: {upg2_script2_name}
          script: bundle_switch
          script_type: internal
        - name: {upg2_script3_name}
          script: monitoring/bundle_post_upgrade.yaml
          params:
            ansible_tags: install
          script_type: ansible
      states:
        available: {upg2_state_available}
        on_success: {upg2_state_on_success}
"""

    def setUp(self) -> None:
        super().setUp()

        self.files_dir = os.path.join(settings.BASE_DIR, "python", "cm", "tests", "files")
        os.makedirs(self.files_dir, exist_ok=True)
        self.tar_write_cfg = {}

    @contextmanager
    def make_bundle_from_str(self, bundle_content: str, filename: str) -> str:
        tmp_filepath = os.path.join(self.files_dir, "config.yaml")
        with open(tmp_filepath, "wt", encoding=settings.ENCODING_UTF_8) as config:
            config.write(bundle_content)

        bundle_filepath = os.path.join(self.files_dir, filename)
        with TarFile.open(
            name=bundle_filepath,
            mode="w",
            encoding=settings.ENCODING_UTF_8,
        ) as tar:
            tar.add(name=tmp_filepath, arcname=os.path.basename(tmp_filepath))
        os.remove(tmp_filepath)

        try:
            yield filename
        finally:
            os.remove(bundle_filepath)

    def _load_bundle(self, bundle_name: str) -> int:
        with open(Path(self.files_dir, bundle_name), encoding=settings.ENCODING_UTF_8) as f:
            with transaction.atomic():
                response = self.client.post(
                    path=reverse("upload-bundle"),
                    data={"file": f},
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        with transaction.atomic():
            response = self.client.post(
                path=reverse("load-bundle"),
                data={"bundle_file": bundle_name},
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()["id"]

    def test_upload_duplicated_upgrade_script_names(self):
        same_upgrade_name = "Upgrade name"
        same_script_name = "Script name"
        same_version = "2.11"
        same_state_available = "any"
        same_state_on_success = "upgradable"
        same_from_edition = "\n        - community\n        - enterprise"
        kwargs = {
            "upg1_name": same_upgrade_name,
            "upg1_from_edition": same_from_edition,
            "upg1_min_version": same_version,
            "upg1_max_strict": same_version,
            "upg1_script1_name": same_script_name,
            "upg1_script2_name": same_script_name,
            "upg1_script3_name": same_script_name,
            "upg1_state_available": same_state_available,
            "upg1_state_on_success": same_state_on_success,
            "upg2_name": same_upgrade_name,
            "upg2_from_edition": same_from_edition,
            "upg2_min_version": same_version,
            "upg2_max_strict": same_version,
            "upg2_script1_name": same_script_name,
            "upg2_script2_name": same_script_name,
            "upg2_script3_name": same_script_name,
            "upg2_state_available": same_state_available,
            "upg2_state_on_success": same_state_on_success,
        }
        with self.make_bundle_from_str(
            bundle_content=self.bundle_config_template.format(**kwargs),
            filename="test_bundle.tar.gz",
        ) as bundle:
            try:
                bundle_id = self._load_bundle(bundle)
                Bundle.objects.get(pk=bundle_id).delete()
            except transaction.TransactionManagementError:  # == IntegrityError
                pass
            else:
                raise AssertionError("Same upgrades should not be allowed to uploaded")

        # if at least one of these values is different, it is considered to be a different upgrade
        different_values = [
            {"upg1_name": "New name"},
            {"upg1_from_edition": "\n        - community"},
            {"upg1_min_version": "0.1"},
            {"upg1_max_strict": "3.9"},
            {"upg1_state_available": "[running]"},
            {"upg1_state_on_success": "new shiny state on success"},
        ]
        for value in different_values:
            with self.make_bundle_from_str(
                bundle_content=self.bundle_config_template.format(**{**kwargs, **value}),
                filename="test_bundle.tar.gz",
            ) as bundle:
                bundle_id = self._load_bundle(bundle)
                Bundle.objects.get(pk=bundle_id).delete()

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

        self.assertIn(settings.ANSIBLE_VAULT_HEADER, secret_file_content)
        self.assertIn(settings.ANSIBLE_VAULT_HEADER, config_log.config["secretfile"])
        self.assertEqual(secret_file_bundle_content, ansible_decrypt(config_log.config["secretfile"]))

        new_content = "new content"
        config_log.config["secretfile"] = "new content"

        response: Response = self.client.post(
            path=reverse("config-log-list"),
            data={"obj_ref": cluster.pk, "config": json.dumps(config_log.config)},
        )

        self.assertEqual(response.status_code, HTTP_201_CREATED)

        new_config_log = ConfigLog.objects.filter(obj_ref=cluster.config).order_by("pk").last()

        self.assertIn(settings.ANSIBLE_VAULT_HEADER, new_config_log.config["secretfile"])
        self.assertEqual(new_content, ansible_decrypt(new_config_log.config["secretfile"]))

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
            data={"obj_ref": cluster.pk, "config": json.dumps(config_log.config)},
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
