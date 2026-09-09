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

from abc import abstractmethod
from pathlib import Path
from typing import cast
from unittest import TestCase

import yaml

from core.bundle._definitions import Definition, DefinitionsMap
from core.bundle._errors import BundleParsingError
from core.bundle._parsing import v_1_0, v_2_0, v_2_1
from core.bundle._parsing.types import BundleParser, RootEntry, VersionTag
from core.templates._types import Template

BUNDLE_ROOT = Path(__file__).parent
NESTED_DIR_NAME = "nested"
FILE_IN_ROOT = BUNDLE_ROOT / "file.ext"
FILE_IN_NESTED = BUNDLE_ROOT / NESTED_DIR_NAME / "file.ext"

TEMPLATE_PATH = "something/to/do.yaml"

CASES_FROM_FILE_IN_NESTED = (
    ("relative-nested", f"./{TEMPLATE_PATH}", Path(NESTED_DIR_NAME, TEMPLATE_PATH)),
    ("full-nested", TEMPLATE_PATH, Path(TEMPLATE_PATH)),
)


def get_parsers() -> list[tuple[VersionTag, BundleParser]]:
    return [("1.0", v_1_0.Parser()), ("2.0", v_2_0.Parser()), ("2.1", v_2_1.Parser())]


# Common Implementations For various versions


class V1Implementation:
    @classmethod
    def build_cluster_entry(cls) -> dict:
        return {"type": "cluster", "name": "aa", "version": "1"}

    @classmethod
    def build_parser(cls) -> BundleParser:
        return v_1_0.Parser()


class V2Implementation:
    @classmethod
    def build_cluster_entry(cls) -> dict:
        return {"type": "cluster", "venv": "2.16", "name": "aa", "version": "1", "contract_version": "2.0"}

    @classmethod
    def build_parser(cls) -> BundleParser:
        return v_2_0.Parser()


# Common Tests For Suites


class _TestTemplate:
    class ParserTestCase(TestCase):
        @classmethod
        def setUpClass(cls) -> None:
            super().setUpClass()
            cls.cluster_entry = cls.build_cluster_entry()
            cls.parser = cls.build_parser()

        @classmethod
        @abstractmethod
        def build_cluster_entry(cls) -> dict:
            ...

        @classmethod
        @abstractmethod
        def build_parser(cls) -> BundleParser:
            ...

        def prepare_list_with_entry(self, data: dict, path: Path) -> list[RootEntry]:
            return [RootEntry(data=data, full_path_to_file=path)]

        def expect_one_cluster_definition(self, result: DefinitionsMap) -> Definition:
            key = ("cluster",)
            self.assertIn(key, result)
            return result[key]

    class ParserPathResolution(ParserTestCase):
        @classmethod
        def setUpClass(cls) -> None:
            super().setUpClass()
            cls.scripts_section = [{"name": "a", "script": "o", "script_type": "ansible"}]

        def prepare_cluster_with_action(self, extra: dict, include_scripts: bool = False) -> dict:
            action = {"type": "task", **extra}
            if include_scripts:
                action["scripts"] = [*self.scripts_section]

            return {**self.cluster_entry, "actions": {"a": action}}

        def expect_template(self, template: Template | None) -> Template:
            self.assertIsNotNone(template)
            return cast(Template, template)

        # cases

        def test_parse_root_with_scripts_template(self):
            for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
                with self.subTest(case_name):
                    action_data = {"scripts_template": {"file": {"path": input_path}, "engine": {"type": "jinja2"}}}
                    data = self.prepare_cluster_with_action(action_data)
                    entries = self.prepare_list_with_entry(data, FILE_IN_NESTED)

                    result = self.parser.parse_root_entries(entries=entries, bundle_root=BUNDLE_ROOT)
                    definition = self.expect_one_cluster_definition(result)

                    template = self.expect_template(definition.actions[0].scripts_template)
                    self.assertEqual(template.file.path, expected_path)

        def test_parse_root_with_config_template(self):
            for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
                with self.subTest(case_name):
                    action_data = {"config_template": {"file": {"path": input_path}, "engine": {"type": "jinja2"}}}
                    data = self.prepare_cluster_with_action(action_data, include_scripts=True)
                    entries = self.prepare_list_with_entry(data, FILE_IN_NESTED)

                    result = self.parser.parse_root_entries(entries=entries, bundle_root=BUNDLE_ROOT)
                    definition = self.expect_one_cluster_definition(result)

                    template = self.expect_template(definition.actions[0].config_template)
                    self.assertEqual(template.file.path, expected_path)

        def test_parse_config(self):
            for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
                with self.subTest(case_name):
                    template_path = FILE_IN_NESTED.relative_to(BUNDLE_ROOT)
                    config_data = [
                        {"name": "ap", "type": "file", "default": input_path},
                        {"name": "as", "type": "secretfile", "default": input_path},
                    ]

                    result = self.parser.parse_config(
                        config=config_data, bundle_root=BUNDLE_ROOT, template_path=template_path
                    )

                    self.assertEqual(result.default_values[("ap",)], str(expected_path))
                    self.assertEqual(result.default_values[("as",)], str(expected_path))

        def test_parse_scripts(self):
            for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
                with self.subTest(case_name):
                    template_path = FILE_IN_NESTED.relative_to(BUNDLE_ROOT)
                    scripts_data = [{"name": "s1", "script_type": "ansible", "script": input_path}]

                    result = self.parser.parse_scripts(
                        scripts=scripts_data,
                        template_path=template_path,
                        mode="action",
                        action_allow_to_terminate=False,
                    )

                    self.assertEqual(result[0].script, str(expected_path))

    class ParserExtraFields(ParserTestCase):
        @abstractmethod
        def prepare_cluster_with_action(self, extra: dict) -> dict:
            ...

        def test_extra_field_in_config_of_root_object(self):
            data = {**self.cluster_entry, "config": [{"name": "a", "type": "string", "woo": "boo"}]}
            entry = RootEntry(data=data, full_path_to_file=FILE_IN_ROOT)

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_root_entries(entries=[entry], bundle_root=BUNDLE_ROOT)

            self.assertIn("woo", err.exception.error)
            self.assertIn("extra_forbidden", err.exception.error)

        def test_incorrect_type_field_in_config_of_root_object(self):
            data = {**self.cluster_entry, "config": [{"name": True, "type": "string"}]}
            entry = RootEntry(data=data, full_path_to_file=FILE_IN_ROOT)

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_root_entries(entries=[entry], bundle_root=BUNDLE_ROOT)

            self.assertIn("name", err.exception.error)
            self.assertIn("Input should be a valid string", err.exception.error)

        def test_extra_field_in_dynamic_config(self):
            data = [{"name": "a", "type": "string", "woo": "boo"}]

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_config(config=data, bundle_root=Path(), template_path=Path())

            self.assertIn("woo", err.exception.error)
            self.assertIn("extra_forbidden", err.exception.error)

        def test_incorrect_type_field_in_dynamic_config(self):
            data = [{"name": True, "type": "string"}]

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_config(config=data, bundle_root=Path(), template_path=Path())

            self.assertIn("name", err.exception.error)
            self.assertIn("Input should be a valid string", err.exception.error)

        def test_incorrect_type_field_in_action_of_root_object(self):
            data = self.prepare_cluster_with_action({"display_name": True})
            entry = RootEntry(data=data, full_path_to_file=FILE_IN_ROOT)

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_root_entries(entries=[entry], bundle_root=BUNDLE_ROOT)

            self.assertIn("display_name", err.exception.error)
            self.assertIn("Input should be a valid string", err.exception.error)

        def test_incorrect_type_field_in_dynamic_scripts(self):
            data = [{"name": True, "script": "string", "script_type": "ansible"}]

            with self.assertRaises(BundleParsingError) as err:
                self.parser.parse_scripts(
                    scripts=data, template_path=Path(), action_allow_to_terminate=False, mode="action"
                )

            self.assertIn("name", err.exception.error)
            self.assertIn("Input should be a valid string", err.exception.error)


# Test Suites


class TestPathResolutionV1(V1Implementation, _TestTemplate.ParserPathResolution):
    @classmethod
    def build_cluster_entry(cls) -> dict:
        return {"type": "cluster", "name": "aa", "version": "1"}

    @classmethod
    def build_parser(cls) -> BundleParser:
        return v_1_0.Parser()

    def test_parse_root_with_scripts_jinja_relative_nested(self):
        for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
            with self.subTest(case_name):
                action_data = {"scripts_jinja": input_path}
                data = self.prepare_cluster_with_action(action_data)
                entries = self.prepare_list_with_entry(data, FILE_IN_NESTED)

                result = self.parser.parse_root_entries(entries=entries, bundle_root=BUNDLE_ROOT)
                definition = self.expect_one_cluster_definition(result)

                actual_path = definition.actions[0].scripts_jinja
                self.assertEqual(actual_path, str(expected_path))

    def test_parse_root_with_config_jinja_relative_nested(self):
        for case_name, input_path, expected_path in CASES_FROM_FILE_IN_NESTED:
            with self.subTest(case_name):
                action_data = {"config_jinja": input_path}
                data = self.prepare_cluster_with_action(action_data, include_scripts=True)
                entries = self.prepare_list_with_entry(data, FILE_IN_NESTED)

                result = self.parser.parse_root_entries(entries=entries, bundle_root=BUNDLE_ROOT)
                definition = self.expect_one_cluster_definition(result)

                actual_path = definition.actions[0].config_jinja
                self.assertEqual(actual_path, str(expected_path))


class TestPathResolutionV2(V2Implementation, _TestTemplate.ParserPathResolution):
    def prepare_cluster_with_action(self, extra: dict, include_scripts: bool = False) -> dict:
        cluster_with_task = super().prepare_cluster_with_action(extra=extra, include_scripts=include_scripts)
        cluster_with_task["actions"]["a"].pop("type")
        return cluster_with_task


class TestIncorrectFieldsV1(V1Implementation, _TestTemplate.ParserExtraFields):
    def prepare_cluster_with_action(self, extra: dict) -> dict:
        scripts = [{"name": "aa", "script": "aa", "script_type": "ansible"}]
        action = {"type": "task", "scripts": scripts, **extra}
        return {**self.cluster_entry, "actions": {"a": action}}

    def test_extra_field_in_action_of_root_object(self):
        data = self.prepare_cluster_with_action({"woo": "a"})
        entry = RootEntry(data=data, full_path_to_file=FILE_IN_ROOT)

        with self.assertRaises(BundleParsingError) as err:
            self.parser.parse_root_entries(entries=[entry], bundle_root=BUNDLE_ROOT)

        self.assertIn("woo", err.exception.error)
        self.assertIn("extra_forbidden", err.exception.error)

    def test_extra_field_in_dynamic_scripts(self):
        data = [{"name": "a", "script": "string", "script_type": "ansible", "woo": "boo"}]

        with self.assertRaises(BundleParsingError) as err:
            self.parser.parse_scripts(
                scripts=data, template_path=Path(), action_allow_to_terminate=False, mode="action"
            )

        self.assertIn("woo", err.exception.error)
        self.assertIn("extra_forbidden", err.exception.error)


class TestIncorrectFieldsV2(V2Implementation, _TestTemplate.ParserExtraFields):
    def prepare_cluster_with_action(self, extra: dict) -> dict:
        scripts = [{"name": "aa", "script": "aa", "script_type": "ansible"}]
        action = {"scripts": scripts, **extra}
        return {**self.cluster_entry, "actions": {"a": action}}

    def test_extra_field_in_action_of_root_object(self):
        data = self.prepare_cluster_with_action({"woo": "a"})
        entry = RootEntry(data=data, full_path_to_file=FILE_IN_ROOT)

        with self.assertRaises(BundleParsingError) as err:
            self.parser.parse_root_entries(entries=[entry], bundle_root=BUNDLE_ROOT)

        self.assertIn("woo", err.exception.error)
        self.assertIn("unexpected_keyword_argument", err.exception.error)

    def test_extra_field_in_dynamic_scripts(self):
        data = [{"name": "a", "script": "string", "script_type": "ansible", "woo": "boo"}]

        with self.assertRaises(BundleParsingError) as err:
            self.parser.parse_scripts(
                scripts=data, template_path=Path(), action_allow_to_terminate=False, mode="action"
            )

        self.assertIn("woo", err.exception.error)
        self.assertIn("unexpected_keyword_argument", err.exception.error)


class TestApplyConfig(TestCase):
    def test_error_on_object_duplicate(self):
        as_yaml = """
        - name: apply duplicated object
          script: config_apply
          script_type: internal
          params:
            changes:
              - object: &service
                  type: service
                  service_name: "sa"
                parameters:
                  - key: "c"
                    value: "e"
              - object: *service
                parameters:
                  - key: "p"
                    value: "2"
        """
        scripts = yaml.safe_load(as_yaml)

        for version, parser in get_parsers():
            for mode in ("action", "wizard"):
                with self.subTest(version):
                    with self.assertRaises(BundleParsingError):
                        parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode=mode)

    def test_no_error_on_key_duplicate(self):
        as_yaml = """
        - name: apply correct
          script: config_apply
          script_type: internal
          params:
            changes:
              - object:
                  type: cluster
                parameters:
                  - key: "p"
                    value: "o"
              - object:
                  type: service
                  service_name: "sa"
                parameters:
                  - key: "p"
                    value: "1"
                  - key: "c"
                    value: "e"
              - object:
                  type: component
                  service_name: "sa"
                  component_name: "ca"
                parameters:
                  - key: "p"
                    value: "2"
                  - key: "c"
                    value: "e"
        """

        scripts = yaml.safe_load(as_yaml)

        results = []

        for version, parser in get_parsers():
            for mode in ("action", "wizard"):
                with self.subTest(version):
                    parsed = parser.parse_scripts(
                        scripts, template_path=Path(), action_allow_to_terminate=False, mode=mode
                    )
                    results.append((version, mode, parsed))

        for previous_idx, (cur_ver, cur_mode, cur_result) in enumerate(results[1:]):
            prev_ver, prev_mode, prev_result = results[previous_idx]
            name = f"{cur_ver}-{cur_mode}-same-as-{prev_ver}-{prev_mode}"
            with self.subTest(name):
                self.assertEqual(cur_result, prev_result)


class TestServiceManage(TestCase):
    script_yaml = """
    - name: manage services
      script: service_manage
      script_type: internal
      params:
        operation: add
        services:
          - name: service_1
          - name: service_2
            config_changes:
              - key: "/some_param"
                value: "some_value"
            hc_changes:
              - component: component_1
                hosts: ["host-1", "host-2"]
    """

    def test_parse_in_action_and_wizard_modes_success(self):
        scripts = yaml.safe_load(self.script_yaml)

        results = []
        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            for mode in ("action", "wizard"):
                with self.subTest(f"{version}-{mode}"):
                    parsed = parser.parse_scripts(
                        scripts, template_path=Path(), action_allow_to_terminate=False, mode=mode
                    )
                    results.append((version, mode, parsed))

        for previous_idx, (cur_ver, cur_mode, cur_result) in enumerate(results[1:]):
            prev_ver, prev_mode, prev_result = results[previous_idx]
            with self.subTest(f"{cur_ver}-{cur_mode}-same-as-{prev_ver}-{prev_mode}"):
                self.assertEqual(cur_result, prev_result)

    def test_rejected_in_upgrade_mode_fail(self):
        scripts = yaml.safe_load(self.script_yaml)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'service_manage'"):
                    parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="upgrade")

    def test_not_supported_for_1_0_fail(self):
        scripts = yaml.safe_load(self.script_yaml)

        for _, parser in filter(lambda x: x[0] == "1.0", get_parsers()):
            with self.assertRaises(BundleParsingError, msg="'service_manage'"):
                parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="action")

    def test_duplicate_services_fail(self):
        as_yaml = """
        - name: manage services
          script: service_manage
          script_type: internal
          params:
            operation: add
            services:
              - name: service_1
              - name: service_1
        """
        scripts = yaml.safe_load(as_yaml)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="Duplicate service"):
                    parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="action")

    def test_unsupported_operation_fail(self):
        as_yaml = """
        - name: manage services
          script: service_manage
          script_type: internal
          params:
            operation: remove
            services:
              - name: service_1
        """
        scripts = yaml.safe_load(as_yaml)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'add'"):
                    parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="action")

    def test_empty_services_fail(self):
        as_yaml = """
        - name: manage services
          script: service_manage
          script_type: internal
          params:
            operation: add
            services: []
        """
        scripts = yaml.safe_load(as_yaml)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError):
                    parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="action")

    def test_adcm_8330_no_field_conflict(self):
        as_yaml = """
        - name: lookalike_ansible
          script: something
          script_type: ansible
          params:
            operation: ["a", "b"]
            services: "very nice, awesome"
        """

        scripts = yaml.safe_load(as_yaml)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                result = parser.parse_scripts(
                    scripts, template_path=Path(), action_allow_to_terminate=False, mode="action"
                )
                script, *_ = result

                self.assertListEqual(script.params["operation"], ["a", "b"])
                self.assertEqual(script.params["services"], "very nice, awesome")


class TestUpgradeScripts(TestCase):
    def test_adcm_7953_internal_revert_in_scripts_fail(self):
        yaml_schema = """
        - type: cluster
          name: some_cluster
          version: 3
          upgrade:
            - name: some_upgrade
              versions:
                  min: 1
                  max: 2
              states:
                available: any
                on_success: upgraded
                on_fail: failed
              scripts:
                - name: internal
                  script: bundle_revert
                  script_type: internal
        """
        raw = yaml.safe_load(yaml_schema)
        root = RootEntry(data=raw[0], full_path_to_file=FILE_IN_ROOT)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'bundle_revert'"):
                    parser.parse_root_entries([root], bundle_root=BUNDLE_ROOT)

    def test_adcm_7953_internal_revert_in_dynamic_scripts_fail(self):
        yaml_schema = """
        - name: internal
          script: bundle_revert
          script_type: internal
        """
        raw = yaml.safe_load(yaml_schema)

        for version, parser in filter(lambda x: x[0] != "1.0", get_parsers()):
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'bundle_revert'"):
                    parser.parse_scripts(
                        raw, template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode="upgrade"
                    )
