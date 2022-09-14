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

# Since this module is beyond QA responsibility we will not fix docstrings here
# pylint: disable=missing-function-docstring, missing-class-docstring

import os
from contextlib import contextmanager
from tarfile import TarFile

from django.conf import settings
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse
from rest_framework import status

from cm.models import Bundle
from init_db import init as init_adcm
from rbac.upgrade.role import init_roles


# TODO: refactor this after merging 1524 (audit) in develop
class TestBase(TestCase):
    files_dir = None

    def setUp(self) -> None:
        init_adcm()
        init_roles()

        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        response = self.client.post(
            path=reverse("rbac:token"),
            data={"username": "admin", "password": "admin"},
            content_type="application/json",
        )
        self.client.defaults["Authorization"] = f"Token {response.data['token']}"

        self.client_unauthorized = Client(HTTP_USER_AGENT="Mozilla/5.0")

    def load_bundle(self, bundle_name: str) -> int:
        with open(os.path.join(self.files_dir, bundle_name), encoding="utf-8") as f:
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


class TestBundle(TestBase):
    files_dir = os.path.join(settings.BASE_DIR, "python", "cm", "tests", "files")
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
        with open(tmp_filepath, "wt", encoding="utf-8") as config:
            config.write(bundle_content)

        bundle_filepath = os.path.join(self.files_dir, filename)
        with TarFile.open(
            name=bundle_filepath,
            mode="w",
            encoding="utf-8",
        ) as tar:
            tar.add(name=tmp_filepath, arcname=os.path.basename(tmp_filepath))
        os.remove(tmp_filepath)

        try:
            yield filename
        finally:
            os.remove(bundle_filepath)

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
                bundle_id = self.load_bundle(bundle)
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
                bundle_id = self.load_bundle(bundle)
                Bundle.objects.get(pk=bundle_id).delete()
