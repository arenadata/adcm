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

from adcm.tests.base import TestBase


class TestBundle(TestBase):
    files_dir = os.path.join(settings.BASE_DIR, "python", "cm", "tests", "files")
    bundle_config_template = """
- type: cluster
  name: Monitoring
  version: 666
  edition: community
  adcm_min_version: 2022.08.10.17
  description: Monitoring and Control Software

  upgrade:
    - name: {upg1_name}
      description: |
        The cluster will be prepared for upgrade. During the upgrade process,
        the cluster will be stopped and started after the installation
        is completed. To start the upgrade, run the Upgrade cluster action.
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
        tmp_filepath = os.path.join(self.files_dir, 'config.yaml')
        with open(tmp_filepath, 'wt', encoding='utf-8') as config:
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

    def test_duplicated_upgrade_script_names(self):
        kwargs = {
            'upg1_name': '666',
            'upg1_min_version': '2.11',
            'upg1_max_strict': '666',
            'upg1_script1_name': 'Pre upgrade check',
            'upg1_script2_name': 'Bundle upgrade',
            'upg1_script3_name': 'Post-upgrade actions',
            'upg1_state_available': 'any',
            'upg1_state_on_success': 'upgradable',
            'upg2_name': '666',
            'upg2_min_version': '2.10',
            'upg2_max_strict': '2.11',
            'upg2_script1_name': 'Pre upgrade check',
            'upg2_script2_name': 'Bundle upgrade',
            'upg2_script3_name': 'Post-upgrade actions',
            'upg2_state_available': 'any',
            'upg2_state_on_success': 'upgrade config',
        }
        with self.make_bundle_from_str(
            bundle_content=self.bundle_config_template.format(**kwargs),
            filename='test_bundle.tar.gz',
        ) as bundle:
            self.load_bundle(bundle)
