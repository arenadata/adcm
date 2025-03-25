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

from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import yaml

from core.bundle_alt.errors import BundleParsingError
from core.bundle_alt.process import retrieve_bundle_definitions
from core.bundle_alt.schema import ADCM_MM_ACTION_FORBIDDEN_PROPS_SET, ADCM_SERVICE_ACTION_NAMES_SET


def fake_get_config_files(*_):
    return [(Path(), Path())]


class TestBundleProcessingErrors(TestCase):
    def parse(self, raw: str):
        with patch("core.bundle_alt.process.get_config_files", new=fake_get_config_files), patch(
            "core.bundle_alt.process._read_config_file", new=lambda _: yaml.safe_load(raw)
        ):
            return retrieve_bundle_definitions(Path(), adcm_version="30000.0.0", yspec_schema={})

    # test_yaml_errors (?) see `read_definition` from `bundle`

    def test_min_version_checked_before_parsing(self):
        bundle = """
        - name: service
          type: service
          field_not_exist: 4
        - name: cluster
          type: cluster
          adcm_min_version: 40000
          field_not_exist: {}
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("This bundle required ADCM version equal to 40000 or newer.", err.exception.message)

    def test_duplicated_definition(self):
        bundle = """
        - name: simple
          type: service
          version: 4.0
        - name: simple
          type: service
          version: 2.3
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("Duplicate definition", err.exception.message)

    def test_mm_actions_forbidden_properties(self):
        for name in ADCM_SERVICE_ACTION_NAMES_SET:
            for forbidden_prop in ADCM_MM_ACTION_FORBIDDEN_PROPS_SET:
                bundle = f"""
                - name: simple
                  type: cluster
                  version: 4.0
                - name: simple
                  type: service
                  version: 2.3

                  actions:
                    {name}:
                      {forbidden_prop}: x
                """

                with self.assertRaises(BundleParsingError) as err:
                    self.parse(bundle)

                self.assertIn("Maintenance mode actions shouldn't have ", err.exception.message)

    def test_scripts_jinja(self):
        with self.subTest("mutualy exclusive with scripts"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              actions:
                ogo:
                  type: task
                  scripts_jinja: iexist.j2
                  scripts:
                    - name: sub
                      script: woho
                      script_type: ansible
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"scripts" and "scripts_jinja" are mutually exclusive', err.exception.message)

        with self.subTest("incorrect path format"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              actions:
                ogo:
                  type: task
                  scripts_jinja: /iexist.j2
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"scripts_jinja" has unsupported path format', err.exception.message)

        # todo add incorrect template test

    def test_config_jinja(self):
        with self.subTest("mutualy exclusive with config"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              actions:
                ogo:
                  type: job
                  script: aa
                  script_type: ansible
                  config_jinja: iexist.j2
                  config: []
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"config" and "config_jinja" are mutually exclusive', err.exception.message)

        with self.subTest("incorrect path format"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              actions:
                ogo:
                  type: job
                  script: aa
                  script_type: ansible
                  config_jinja: /iexist.j2
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"config_jinja" has unsupported path format', err.exception.message)

        # todo add incorrect template test

    def test_license_incorrect_object(self):
        with self.subTest("host"):
            bundle = """
            - name: ohno
              type: host
              version: 1
              license: x
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("License can be placed in cluster, service or provider", err.exception.message)

        with self.subTest("component"):
            bundle = """
            - name: hhshs
              type: service
              version: 1
              components:
                a:
                  license: x
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("License can be placed in cluster, service or provider", err.exception.message)

    def test_license_incorrect_path(self):
        bundle = """
        - name: fff
          type: service
          version: 3
          license: /path.txt
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("Unsupported path format for license: /path.txt", err.exception.message)

    def test_mutually_exclusive_host_action_and_action_host_group(self):
        bundle = """
        - name: fff
          type: service
          version: 3
          actions:
            some:
              type: job
              script: some.yaml
              script_type: ansible
              host_action: yes
              allow_for_action_host_group: true
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn(
            "The allow_for_action_host_group and host_action attributes are mutually exclusive.", err.exception.message
        )

    def test_mutually_exclusive_masking_states(self):
        bundle = """
        - name: fff
          type: service
          version: 3
          actions:
            some:
              type: job
              script: some.yaml
              script_type: ansible
              masking: {}
              states: {"available": "any"}
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn('uses both mutual excluding states "states" and "masking"', err.exception.message)

    def test_mutually_exclusive_states_on_success_on_fail(self):
        for key in ("on_success", "on_fail"):
            with self.subTest(key):
                bundle = f"""
                - name: fff
                  type: cluster
                  version: 3
                  actions:
                    some:
                      type: task
                      scripts:
                        - name: first
                          script: some.yaml
                          script_type: ansible
                      states:
                        available: any
                      {key}: {{}}
                """

                with self.assertRaises(BundleParsingError) as err:
                    self.parse(bundle)

                self.assertIn('uses "on_success/on_fail" states without "masking"', err.exception.message)

    def test_script_path_correctness(self):
        bundle = """
        - name: aaa
          type: cluster
          version: 2
          actions:
            ogo:
              type: job
              script: /aa.yaml
              script_type: ansible
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("has unsupported path format: /aa.yaml", err.exception.message)

    def test_incorrect_pattern(self):
        bundle = """
        - name: aaa
          type: service
          version: 2
          config:
            - name: x
              type: string
              pattern: "[["
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("is not valid regular expression", err.exception.message)

    def test_mutually_exclusive_read_only_and_writable(self):
        bundle = """
        - name: aaa
          type: service
          version: 2
          config:
            - name: x
              type: string
              read_only: any
              writable: any
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn('can not have "read_only" and "writable" simultaneously', err.exception.message)

    def test_upgrade_versions(self):
        with self.subTest("mutualy exclusive mins"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              upgrade:
                - name: oo
                  versions:
                    min: 4
                    min_strict: 4.0
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("min and min_strict can not be used simultaneously in versions", err.exception.message)

        with self.subTest("either of mins should be present"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              upgrade:
                - name: oo
                  versions:
                    max: 4
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("min or min_strict should be present in versions", err.exception.message)

        with self.subTest("mutualy exclusive maxs"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              upgrade:
                - name: oo
                  versions:
                    max: 4
                    max_strict: 4.0
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("max and max_strict can not be used simultaneously in versions", err.exception.message)

        with self.subTest("either of maxs should be present"):
            bundle = """
            - name: aaa
              type: cluster
              version: 2
              upgrade:
                - name: oo
                  versions:
                    min: 4
            """

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn("max or max_strict should be present in versions", err.exception.message)

    def test_masking_without_scripts(self):
        for section in ("masking", "on_fail", "on_success"):
            with self.subTest(section):
                bundle = f"""
                - name: aaa
                  type: cluster
                  version: 2
                  upgrade:
                    - name: oo
                      versions:
                        min: 4
                        max: 5
                      {section}: {{}}
                """

                with self.assertRaises(BundleParsingError) as err:
                    self.parse(bundle)

                self.assertIn(
                    "couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
                    err.exception.message,
                )

    def test_import_required_and_default(self):
        bundle = """
        - name: aaa
          type: cluster
          version: 2
          import:
            something:
              required: true
              default: [aaa]
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("Import can't have default and be required in the same time", err.exception.message)

    def test_import_max_less_min(self):
        bundle = """
        - name: aaa
          type: cluster
          version: 2
          import:
            something:
              versions:
                min: 5
                max: 3
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("Min version should be less or equal max version", err.exception.message)
