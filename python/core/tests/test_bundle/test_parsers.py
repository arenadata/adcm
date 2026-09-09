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
from typing import Final, cast
from unittest import TestCase
from unittest.mock import Mock, patch

from pydantic import TypeAdapter, ValidationError
import yaml

from core.action import ComponentHostSource, HcAclRule, HostGroupParameter, ScriptType
from core.action.types import (
    AnsibleScript,
    AnsibleScriptParams,
    ExecutionStyle,
    HostGroupManageScript,
    HostManageScript,
    JobDetails,
    JobSpecV1,
    PythonScript,
    ScriptSpec,
    SimpleInternalScript,
)
from core.bundle._constants import ADCM_MM_ACTION_FORBIDDEN_PROPS_SET, ADCM_SERVICE_ACTION_NAMES_SET
from core.bundle._definitions import (
    ActionAvailability,
    ActionDefinition,
    ConfigParamPlainSpec,
    Definition,
    DefinitionsMap,
    UpgradeDefinition,
    UpgradeRestrictions,
    VersionBound,
)
from core.bundle._errors import BundleParsingError, BundleValidationError
from core.bundle._parsing import check_adcm_min_version, extract_parsing_meta, v_2_1
from core.bundle._parsing.shared.targets import ActionWizardStages
from core.bundle._parsing.types import BundleParser, RootEntry, VersionTag
from core.bundle._parsing.v_2_0.actions import ClusterObjectAction, ConfigApplyInternalScript
from core.bundle._parsing.v_2_0.upgrades import UpgradeWithScripts
from core.bundle._validate import check_config_definition, check_templates_are_correct
from core.spec.types import FullSpecKey
from core.templates._types import Template
from core.types import Names

BUNDLE_ROOT = Path(__file__).parent
NESTED_DIR_NAME = "nested"
FILE_IN_ROOT = BUNDLE_ROOT / "file.ext"
FILE_IN_NESTED = BUNDLE_ROOT / NESTED_DIR_NAME / "file.ext"

TEMPLATE_PATH = "something/to/do.yaml"

CASES_FROM_FILE_IN_NESTED = (
    ("relative-nested", f"./{TEMPLATE_PATH}", Path(NESTED_DIR_NAME, TEMPLATE_PATH)),
    ("full-nested", TEMPLATE_PATH, Path(TEMPLATE_PATH)),
)


# Latest contract version targeted by tests that need a concrete, up-to-date parser
# (as opposed to get_parsers(), which cross-checks behavior shared across all versions).
def build_script_spec(
    key: str,
    name: str,
    script: AnsibleScript | PythonScript | SimpleInternalScript,
    *,
    display_name: str = "",
    terminatable: bool = False,
) -> ScriptSpec:
    return ScriptSpec(
        key=FullSpecKey(key),
        names=Names(internal=name, display=display_name),
        script=script,
        details=JobDetails(terminatable=terminatable),
    )


def ansible_script(path: str, **params) -> AnsibleScript:
    return AnsibleScript(type=ScriptType.ANSIBLE, path=path, params=AnsibleScriptParams(**params))


def python_script(path: str) -> PythonScript:
    return PythonScript(type=ScriptType.PYTHON, path=path, params=None)


def simple_internal_script(name: str) -> SimpleInternalScript:
    return SimpleInternalScript(type=ScriptType.INTERNAL, path=name, params=None)


CONTRACT_VERSION: Final = "2.1"
MAIN_VENV: Final = "2.21"


def get_parsers() -> list[tuple[VersionTag, BundleParser]]:
    return [("2.1", v_2_1.Parser())]


# Common Implementations For various versions


class V2Implementation:
    @classmethod
    def build_cluster_entry(cls) -> dict:
        return {"type": "cluster", "venv": "2.16", "name": "aa", "version": "1", "contract_version": "2.1"}

    @classmethod
    def build_parser(cls) -> BundleParser:
        return v_2_1.Parser()


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

        def prepare_cluster_with_action(self, action_data: dict, include_scripts: bool = False) -> dict:
            if include_scripts:
                action_data["scripts"] = [*self.scripts_section]

            return {**self.cluster_entry, "actions": {"a": action_data}}

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

                    self.assertEqual(result.scripts["/0"].script.path, str(expected_path))

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


class TestPathResolutionV2(V2Implementation, _TestTemplate.ParserPathResolution):
    pass


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
        for version, parser in get_parsers():
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

        for version, parser in get_parsers():
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'service_manage'"):
                    parser.parse_scripts(scripts, template_path=Path(), action_allow_to_terminate=False, mode="upgrade")

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

        for version, parser in get_parsers():
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

        for version, parser in get_parsers():
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

        for version, parser in get_parsers():
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

        for version, parser in get_parsers():
            with self.subTest(version):
                result = parser.parse_scripts(
                    scripts, template_path=Path(), action_allow_to_terminate=False, mode="action"
                )
                script_spec = result.scripts["/0"]
                params = script_spec.script.params

                # extra params of an ansible script are kept as they are, no matter their names
                self.assertListEqual(params.operation, ["a", "b"])
                self.assertEqual(params.services, "very nice, awesome")


class TestScriptsConversion(TestCase):
    """Conversion of DSL spellings that mean the same thing into a single spec representation"""

    def parse(self, as_yaml: str) -> JobSpecV1:
        _, parser = get_parsers()[-1]
        return parser.parse_scripts(
            yaml.safe_load(as_yaml), template_path=Path(), action_allow_to_terminate=False, mode="action"
        )

    def test_unset_ansible_params_spellings_are_equal(self):
        # `params` of an ansible script is the only one the DSL lets spell "empty" in all three ways
        absent = """
        - name: s
          script: s.yaml
          script_type: ansible
        """
        explicit_null = """
        - name: s
          script: s.yaml
          script_type: ansible
          params:
        """
        empty_map = """
        - name: s
          script: s.yaml
          script_type: ansible
          params: {}
        """

        specs = [self.parse(case) for case in (absent, explicit_null, empty_map)]

        self.assertEqual(specs[0], specs[1])
        self.assertEqual(specs[0], specs[2])
        # they mean "no params of our own", which for ansible is its own defaults
        self.assertEqual(specs[0].scripts["/0"].script.params.ansible_tags, "")

    def test_scripts_without_params_get_none(self):
        # neither python nor simple internal scripts accept `params` in the DSL at all
        spec = self.parse(
            """
            - name: py
              script: s.py
              script_type: python
            - name: clean
              script: before_upgrade_clean
              script_type: internal
            """
        )

        self.assertIsNone(spec.scripts["/0"].script.params)
        self.assertIsNone(spec.scripts["/1"].script.params)

    def test_keys_follow_declaration_order(self):
        spec = self.parse(
            """
            - name: first
              script: a.yaml
              script_type: ansible
            - name: second
              script: b.yaml
              script_type: ansible
            """
        )

        self.assertEqual(list(spec.scripts), ["/0", "/1"])
        self.assertEqual([script.key for script in spec.scripts.values()], ["/0", "/1"])
        self.assertEqual(spec.hierarchy.fields, ["0", "1"])
        self.assertEqual(spec.hierarchy.rule, ExecutionStyle.SEQUENTIAL)

    def test_bundle_switch_in_rendered_action_fail(self):
        # the DSL union lets it through, so parsing rejects it the way `check_actions` does statically
        as_yaml = """
        - name: switch
          script: bundle_switch
          script_type: internal
        """

        with self.assertRaises(BundleValidationError) as err:
            self.parse(as_yaml)

        self.assertIn("bundle_switch is disallowed", str(err.exception))

    @patch("core.bundle._parsing.shared.parser.check_execution_hierarchy")
    def test_rendered_scripts_are_checked_for_hierarchy(self, check_mock: Mock):
        # rendered scripts never reach bundle validation, so parsing has to run the check itself
        spec = self.parse(
            """
            - name: s
              script: s.yaml
              script_type: ansible
            """
        )

        check_mock.assert_called_once_with(spec=spec)

    def test_terminatable_is_off_unless_stated(self):
        spec = self.parse(
            """
            - name: silent
              script: a.yaml
              script_type: ansible
            - name: loud
              script: b.yaml
              script_type: ansible
              allow_to_terminate: true
            """
        )

        self.assertFalse(spec.scripts["/0"].details.terminatable)
        self.assertTrue(spec.scripts["/1"].details.terminatable)

    def test_internal_scripts_are_never_terminatable(self):
        spec = self.parse(
            """
            - name: clean
              script: before_upgrade_clean
              script_type: internal
              allow_to_terminate: true
            """
        )

        self.assertFalse(spec.scripts["/0"].details.terminatable)

    def test_action_level_terminate_propagates_to_scripts(self):
        _, parser = get_parsers()[-1]
        as_yaml = """
        - name: ansible
          script: a.yaml
          script_type: ansible
        - name: switch
          script: bundle_switch
          script_type: internal
        """

        spec = parser.parse_scripts(
            yaml.safe_load(as_yaml), template_path=Path(), action_allow_to_terminate=True, mode="upgrade"
        )

        self.assertTrue(spec.scripts["/0"].details.terminatable)
        # ... except internal ones, which have no process to terminate
        self.assertFalse(spec.scripts["/1"].details.terminatable)

    def test_action_level_terminate_propagates_to_root_entry_scripts(self):
        entry = V2Implementation.build_cluster_entry() | {
            "actions": {
                "act": {
                    "allow_to_terminate": True,
                    "scripts": [
                        {"name": "inherits", "script": "a.yaml", "script_type": "ansible"},
                        {"name": "own", "script": "b.yaml", "script_type": "ansible", "allow_to_terminate": False},
                    ],
                }
            }
        }

        for version, parser in get_parsers():
            with self.subTest(version):
                definitions = parser.parse_root_entries(
                    [RootEntry(data=entry | {"contract_version": version}, full_path_to_file=FILE_IN_ROOT)],
                    bundle_root=BUNDLE_ROOT,
                )

                (action,) = definitions[("cluster",)].actions
                self.assertIsNotNone(action.scripts)
                self.assertTrue(action.scripts.scripts["/0"].details.terminatable)
                # explicit `false` is kept as is, only unset values are inherited
                self.assertFalse(action.scripts.scripts["/1"].details.terminatable)


class TestUpgradeScripts(TestCase):
    def test_bundle_switch_amount_in_dynamic_scripts_fail(self):
        ansible = {"name": "ansible", "script": "a.yaml", "script_type": "ansible"}
        switch = {"name": "switch", "script": "bundle_switch", "script_type": "internal"}

        cases = (
            (
                "no switch",
                [ansible],
                'Scripts block must contain exact one block with script "bundle_switch" in upgrade',
            ),
            (
                "multiple switches",
                [switch, ansible, switch],
                'Script with script_type "bundle_switch" must be unique in upgrade',
            ),
        )

        for version, parser in get_parsers():
            for case, scripts, message in cases:
                with self.subTest(f"{version}-{case}"):
                    # parsing error is what API reports as bundle definition error, it has to stay this way
                    with self.assertRaises(BundleParsingError) as err:
                        parser.parse_scripts(
                            scripts, template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode="upgrade"
                        )

                    self.assertIn(message, err.exception.message)

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

        for version, parser in get_parsers():
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

        for version, parser in get_parsers():
            with self.subTest(version):
                with self.assertRaises(BundleParsingError, msg="'bundle_revert'"):
                    parser.parse_scripts(
                        raw, template_path=FILE_IN_ROOT, action_allow_to_terminate=False, mode="upgrade"
                    )


class TestScriptsPresence(TestCase):
    """Scripts rendered from template are unknown until rendering, so only statically declared ones are converted"""

    def test_scripts_are_absent_for_scripts_template_success(self):
        scripts_template = {"file": {"path": "scripts.j2"}, "engine": {"type": "jinja2"}}
        upgrade = {"versions": {"min": "0", "max": "1"}, "states": {"available": "any"}}
        entry = V2Implementation.build_cluster_entry() | {
            "actions": {
                "with_scripts": {"scripts": [{"name": "run", "script": "a.yaml", "script_type": "ansible"}]},
                "with_scripts_template": {"scripts_template": scripts_template},
            },
            "upgrade": [
                upgrade
                | {
                    "name": "with_scripts",
                    "scripts": [{"name": "switch", "script": "bundle_switch", "script_type": "internal"}],
                },
                upgrade | {"name": "with_scripts_template", "scripts_template": scripts_template},
            ],
        }

        for version, parser in get_parsers():
            with self.subTest(version):
                definitions = parser.parse_root_entries(
                    [RootEntry(data=entry, full_path_to_file=FILE_IN_ROOT)], bundle_root=BUNDLE_ROOT
                )

                cluster = definitions[("cluster",)]
                converted = {
                    "actions": {action.name: action.scripts is not None for action in cluster.actions},
                    "upgrades": {
                        upgrade.name: upgrade.action.scripts is not None
                        for upgrade in cluster.upgrades
                        if upgrade.action is not None
                    },
                }
                self.assertDictEqual(
                    converted,
                    {
                        "actions": {"with_scripts": True, "with_scripts_template": False},
                        "upgrades": {"with_scripts": True, "with_scripts_template": False},
                    },
                )


class TestScriptsRendering(TestCase):
    correct_config_apply_script = {
        "name": "state_2",
        "params": {
            "changes": [
                {"object": {"type": "cluster"}, "parameters": [{"key": "integer", "value": 99}]},
                {
                    "object": {"service_name": "service_two_components", "type": "service"},
                    "parameters": [{"key": "string", "value": "string"}],
                },
                {
                    "object": {
                        "component_name": "component_1",
                        "service_name": "service_two_components",
                        "type": "component",
                    },
                    "parameters": [{"key": "list", "value": [1, 2, 3]}],
                },
            ]
        },
        "script": "config_apply",
        "script_type": "internal",
    }
    wrong_config_apply_script_value_missing = {
        "name": "state_2",
        "params": {
            "changes": [
                {"object": {"type": "cluster"}, "parameters": [{"key": "integer", "value": 99}]},
                {
                    "object": {"service_name": "service_two_components", "type": "service"},
                    "parameters": [{"key": "string"}],
                },
                {
                    "object": {
                        "component_name": "component_1",
                        "service_name": "service_two_components",
                        "type": "component",
                    },
                    "parameters": [{"key": "list", "value": [1, 2, 3]}],
                },
            ]
        },
        "script": "config_apply",
        "script_type": "internal",
    }

    # error path is nested through the whole script definition down to the missing field,
    # entries of `scripts` are either scripts or groups, so there's a level telling which one it is
    missing_value_fragment = (
        "Errors found in definition of bundle entity:\n"
        " scripts\n"
        "  0\n"
        "   script\n"
        "    internal\n"
        "     config_apply\n"
        "      params\n"
        "       changes\n"
        "        1\n"
        "         parameters\n"
        "          0\n"
        "           value\n"
        "           | missing: Field required"
    )

    def test_parse_script_config_apply(self):
        for version, parser in get_parsers():
            with self.subTest(f"{version}-correct"):
                parser.parse_scripts(
                    [self.correct_config_apply_script],
                    template_path=FILE_IN_ROOT,
                    action_allow_to_terminate=True,
                    mode="action",
                )

            with self.subTest(f"{version}-missing-value"):
                with self.assertRaises(BundleParsingError) as err:
                    parser.parse_scripts(
                        [self.wrong_config_apply_script_value_missing],
                        template_path=FILE_IN_ROOT,
                        action_allow_to_terminate=True,
                        mode="action",
                    )

                self.assertIn(self.missing_value_fragment, err.exception.message)

    def test_parse_script_hc_apply(self):
        # allowed internal-script tags for wizard mode grow with contract version
        # (2.0+ add "before_upgrade_clean"/"service_manage"), so only assert the common part
        data = {"name": "hc_apply", "script": "hc_apply", "script_type": "internal"}

        for version, parser in get_parsers():
            with self.subTest(version):
                with self.assertRaises(BundleParsingError) as err:
                    parser.parse_scripts(
                        [data], template_path=FILE_IN_ROOT, action_allow_to_terminate=True, mode="wizard"
                    )

                message = err.exception.message
                self.assertIn("Input tag 'hc_apply'", message)
                for tag in ("'bundle_switch'", "'bundle_revert'", "'config_apply'"):
                    self.assertIn(tag, message)


class TestBundleProcessingErrors(TestCase):
    def parse(self, raw: str) -> DefinitionsMap:
        content = yaml.safe_load(raw)
        entries = [RootEntry(data=data, full_path_to_file=FILE_IN_ROOT) for data in content]

        # min-ADCM-version is checked from a lightweight pre-scan of the raw entries,
        # before the (potentially malformed) entries are actually parsed -
        # mirrors BundleService.parse_to_definitions's own ordering
        meta = extract_parsing_meta(entries)
        required_version = str(meta.adcm_min_version) if meta.adcm_min_version is not None else None
        check_adcm_min_version(current="30000.0.0", required=required_version)

        return v_2_1.Parser().parse_root_entries(entries, bundle_root=BUNDLE_ROOT)

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

    def test_missing_required_parent_definition(self):
        # a service needs a cluster sibling and a host needs a provider sibling;
        # _propagate_attributes used to let a raw KeyError escape for a bundle missing one
        cases = (
            (
                """
                - name: fff
                  type: service
                  version: 3
                """,
                "There isn't any cluster definition in bundle",
            ),
            (
                """
                - name: hhh
                  type: host
                  version: 3
                """,
                "There isn't any host provider definition in bundle",
            ),
        )
        for bundle, expected_message in cases:
            with self.subTest(expected_message):
                with self.assertRaises(BundleParsingError) as err:
                    self.parse(bundle)

                self.assertIn(expected_message, err.exception.message)

    def test_mm_actions_forbidden_properties(self):
        for name in ADCM_SERVICE_ACTION_NAMES_SET:
            for forbidden_prop in ADCM_MM_ACTION_FORBIDDEN_PROPS_SET:
                bundle = f"""
                - name: simple
                  type: cluster
                  contract_version: "{CONTRACT_VERSION}"
                  venv: "{MAIN_VENV}"
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

    def test_incorrect_wizard_template(self):
        bundle_template = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          actions:
            ugu:
              scripts:
                - name: dd
                  script: dd
                  script_type: ansible
              wizard_template:
                engine:
                  type: jinja2
                file:
                  path: {{}}
        """

        with self.subTest("non existing file jinja"):
            bundle = bundle_template.format("iexist.j2")
            action = self.parse(bundle)[("cluster",)].actions[0]

            with self.assertRaises(BundleValidationError) as err:
                check_templates_are_correct(action=action, bundle_root=BUNDLE_ROOT)

            self.assertIn("Incorrect template for *_template at iexist.j2", err.exception.message)

        with self.subTest("incorrect path format"):
            bundle = bundle_template.format("/iexist.j2")

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"wizard_template" has unsupported path format', err.exception.message)

    def test_incorrect_scripts_template(self):
        bundle_template = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          actions:
            ugu:
              scripts_template:
                engine:
                  type: python
                file:
                  path: {{}}
                  entrypoint: run
        """

        with self.subTest("non existing file python"):
            bundle = bundle_template.format("iexist.py")
            action = self.parse(bundle)[("cluster",)].actions[0]

            with self.assertRaises(BundleValidationError) as err:
                check_templates_are_correct(action=action, bundle_root=BUNDLE_ROOT)

            self.assertIn("Incorrect template for *_template at iexist.py", err.exception.message)

        with self.subTest("incorrect path format"):
            bundle = bundle_template.format("/iexist.j2")

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"scripts_template" has unsupported path format', err.exception.message)

    def test_incorrect_config_template(self):
        bundle_template = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          actions:
            ugu:
              scripts:
                - name: a
                  script_type: ansible
                  script: aa
              config_template:
                engine:
                  type: python
                file:
                  path: {{}}
                  entrypoint: run
        """

        with self.subTest("non existing file python"):
            bundle = bundle_template.format("iexist.py")
            action = self.parse(bundle)[("cluster",)].actions[0]

            with self.assertRaises(BundleValidationError) as err:
                check_templates_are_correct(action=action, bundle_root=BUNDLE_ROOT)

            self.assertIn("Incorrect template for *_template at iexist.py", err.exception.message)

        with self.subTest("incorrect path format"):
            bundle = bundle_template.format("/iexist.j2")

            with self.assertRaises(BundleParsingError) as err:
                self.parse(bundle)

            self.assertIn('"config_template" has unsupported path format', err.exception.message)

    def test_license_incorrect_path(self):
        for bad_path in ("/something", "../something"):
            with self.subTest(bad_path):
                bundle = f"""
                - name: aaa
                  type: cluster
                  contract_version: "{CONTRACT_VERSION}"
                  venv: "{MAIN_VENV}"
                  version: 2
                  license: {bad_path}
                """

                with self.assertRaises(BundleParsingError) as err:
                    self.parse(bundle)

                self.assertIn(f"Unsupported path format for license: {bad_path}", err.exception.message)

    def test_mutually_exclusive_host_action_and_action_host_group(self):
        bundle = f"""
        - name: parent
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 1
        - name: fff
          type: service
          version: 3
          actions:
            some:
              scripts:
                - name: some
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
        bundle = f"""
        - name: parent
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 1
        - name: fff
          type: service
          version: 3
          actions:
            some:
              scripts:
                - name: some
                  script: some.yaml
                  script_type: ansible
              masking: {{}}
              states: {{"available": "any"}}
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
                  contract_version: "{CONTRACT_VERSION}"
                  venv: "{MAIN_VENV}"
                  version: 3
                  actions:
                    some:
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
        bundle = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          actions:
            ogo:
              scripts:
                - name: ogo
                  script: /aa.yaml
                  script_type: ansible
        """

        with self.assertRaises(BundleParsingError) as err:
            self.parse(bundle)

        self.assertIn("has unsupported path format: /aa.yaml", err.exception.message)

    def test_incorrect_pattern(self):
        bundle = f"""
        - name: parent
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 1
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
        bundle = f"""
        - name: parent
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 1
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
            bundle = f"""
            - name: aaa
              type: cluster
              contract_version: "{CONTRACT_VERSION}"
              venv: "{MAIN_VENV}"
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
            bundle = f"""
            - name: aaa
              type: cluster
              contract_version: "{CONTRACT_VERSION}"
              venv: "{MAIN_VENV}"
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
            bundle = f"""
            - name: aaa
              type: cluster
              contract_version: "{CONTRACT_VERSION}"
              venv: "{MAIN_VENV}"
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
            bundle = f"""
            - name: aaa
              type: cluster
              contract_version: "{CONTRACT_VERSION}"
              venv: "{MAIN_VENV}"
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
        # In 1.0 this was one upgrade schema with a dedicated validator producing a single message.
        # In 2.x masking/on_success/on_fail only exist as fields on the scripts-bearing upgrade
        # variants (UpgradeWithScripts/UpgradeWithScriptsTemplate), so specifying one without
        # scripts/scripts_template no longer produces that message - it's rejected structurally
        # instead (as an unrecognized field on the no-scripts SimpleUpgrade variant, alongside
        # "scripts"/"scripts_template" being reported missing for the other variants). The behavior
        # (masking without scripts is rejected) is preserved; only the message text isn't.
        for section in ("masking", "on_fail", "on_success"):
            with self.subTest(section):
                bundle = f"""
                - name: aaa
                  type: cluster
                  contract_version: "{CONTRACT_VERSION}"
                  venv: "{MAIN_VENV}"
                  version: 2
                  upgrade:
                    - name: oo
                      versions:
                        min: 4
                        max: 5
                      {section}: {{}}
                """

                with self.assertRaises(BundleParsingError):
                    self.parse(bundle)

    def test_import_required_and_default(self):
        bundle = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
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
        bundle = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
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

    def test_group_customization_true_for_selection_group(self):
        bundle = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          config:
            - name: g
              type: selection_group
              group_customization: true
              subs:
                - name: g
                  type: group
                  subs:
                    - name: a
                      type: string
        """

        config = self.parse(bundle)[("cluster",)].config

        with self.assertRaises(BundleValidationError) as err:
            check_config_definition(definition=config, bundle_root=BUNDLE_ROOT)

        self.assertIn("isn't allowed to be desynchronized", err.exception.message)

    def test_group_customization_true_for_parent_of_selection_group(self):
        bundle = f"""
        - name: aaa
          type: cluster
          contract_version: "{CONTRACT_VERSION}"
          venv: "{MAIN_VENV}"
          version: 2
          config_group_customization: true
          config:
            - name: g
              type: selection_group
              subs:
                - name: g
                  type: group
                  subs:
                    - name: a
                      type: string
        """

        config = self.parse(bundle)[("cluster",)].config

        with self.assertRaises(BundleValidationError) as err:
            check_config_definition(definition=config, bundle_root=BUNDLE_ROOT)

        self.assertIn("isn't allowed to be desynchronized", err.exception.message)


class TestWizardSchema(TestCase):
    def test_correct_task_format_success(self):
        yaml_input = """
            stages:
              - name: hc_apply_stage
                display_name: "Host Component Apply"
                steps:
                  - name: mapping
                    display_name: Host Component Apply
                    hc_template:
                      file:
                        path: scripts/manage_hdfs_hc_step.j2
                      engine:
                        type: jinja2
              - name: manage_ssl_stage
                display_name: "Manage SSL"
                steps:
                  - name: configure_ssl
                    display_name: Configure SSL
                    config_template:
                      file:
                        path: scripts/manage_ssl.j2
                      engine:
                        type: jinja2
              - name: manage_kerberos_stage
                display_name: "Manage Kerberos"
                steps:
                  - name: configure_kerberos
                    display_name: "Kerberos configuration"
                    config_template:
                      file:
                        path: scripts/manage_ssl.j2
                      engine:
                        type: jinja2
                  - name: check_kerberos
                    display_name: "Check configuration"
                    ui_options:
                      button_name: Check
                    scripts_template:
                      file:
                        path: scripts/manage_ssl.j2
                      engine:
                        type: jinja2
              - name: save_stage
                display_name: "Save configuration"
                steps:
                  - name: save_configuration
                    display_name: "Check configuration"
                    ui_options:
                      button_name: Check
                    scripts_template:
                      file:
                        path: scripts/check.py
                        entrypoint: generate_scripts
                      engine:
                        type: python
                    """

        parsed_data = yaml.safe_load(yaml_input)
        validated_model = ActionWizardStages.model_validate(parsed_data["stages"])
        self.assertIsInstance(validated_model, ActionWizardStages)

    def test_prohibited_file_format_fail(self):
        yaml_input = """
            stages:
                - name: save_stage
                  display_name: "Save configuration"
                  steps:
                    - name: save_configuration
                      display_name: "Check configuration"
                      ui_options:
                        button_name: Check
                      scripts_template:
                        file:
                          path: ../../scripts_python/cluster/check.py
                          entrypoint: generate_scripts
                        engine:
                          type: python
        """
        with self.assertRaises(ValidationError) as err:
            parsed_data = yaml.safe_load(yaml_input)
            ActionWizardStages.model_validate(parsed_data["stages"])

        self.assertIn('"scripts_template" has unsupported path format', str(err.exception))

    def test_step_names_unique_fail(self):
        yaml_input = """
            stages:
              - name: manage_ssl_stage
                display_name: "Manage SSL"
                steps:
                  - name: configure_ssl
                    display_name: Configure SSL
                    config_template:
                      file:
                        path: scripts/manage_ssl.j2
                      engine:
                        type: jinja2
                  - name: configure_ssl
                    display_name: "Kerberos configuration"
                    config_template:
                      file:
                        path: scripts/manage_ssl.j2
                      engine:
                        type: jinja2
        """
        with self.assertRaises(ValidationError) as err:
            parsed_data = yaml.safe_load(yaml_input)
            ActionWizardStages.model_validate(parsed_data["stages"])

        self.assertIn("Duplicate step name: configure_ssl", str(err.exception))

    def test_entrypoint_specified_for_jinja_fail(self):
        yaml_input = """
            wizard_template:
              file:
                path: "./wizard_jinja/manage_install.j2"
                entrypoint: generate_scripts
              engine:
                type: jinja2
            states:
              available:
                - created
                - faulty_installed
        """
        with self.assertRaises(ValidationError) as err:
            parsed_data = yaml.safe_load(yaml_input)
            TypeAdapter(ClusterObjectAction).validate_python(parsed_data)

        # jinja2 templates have no "entrypoint" field at all now, so this is
        # rejected structurally rather than via a dedicated error message
        self.assertIn("Unexpected keyword argument", str(err.exception))

    def test_upgrade_action_with_wizard_fail(self):
        yaml_input = """
            name: upgrade_via_action_simple
            versions:
              min: '1.0'
              max: '2.0'
            states:
              available: any
            wizard_template:
              file:
                path: "./wizard_jinja/manage_install.j2"
              engine:
                type: jinja2
            scripts:
              - name: pre
                script: ./playbook.yaml
                script_type: ansible
              - name: switch
                script: bundle_switch
                script_type: internal
              - name: post
                script: ./playbook.yaml
                script_type: ansible
        """
        with self.assertRaises(ValidationError) as err:
            parsed_data = yaml.safe_load(yaml_input)
            UpgradeWithScripts.model_validate(parsed_data)

        # upgrade actions have no "wizard_template" field at all now, so this is
        # rejected structurally rather than via a dedicated error message
        self.assertIn("Extra inputs are not permitted", str(err.exception))

    def test_config_apply_pass(self):
        yaml_input = """
            name: state_2
            display_name: "State 2"
            script_type: internal
            script: config_apply
            params:
              changes:
                - object:
                    type: cluster
                  parameters:
                    - key: "{{ ssl_key }}"
                      value: "{{ action.process.manage_ssl_stage.configure_ssl.config.ssl_config }}"
                - object:
                    type: service
                    service_name: "{{ roles_generic_args.service_name }}"
                  parameters:
                    - key: "{{ ssl_key }}"
                      value: true
                - object:
                    type: component
                    service_name: "{{ roles_generic_args.service_name }}"
                    component_name: "{{ roles_generic_args.component_name }}"
                  parameters:
                    - key: "{{ ssl_key }}"
                      value: "{{ action.process.manage_ssl_stage.configure_ssl.config.ssl_config }}"
        """
        parsed_data = yaml.safe_load(yaml_input)
        TypeAdapter(ConfigApplyInternalScript).validate_python(parsed_data)


class TestBundleDefinitionConversion(TestCase):
    maxDiff = None

    def parse(self, entries: list[dict], path: str = ".") -> DefinitionsMap:
        file_path = BUNDLE_ROOT / path / "entry.yaml"
        root_entries = [RootEntry(data=entry, full_path_to_file=file_path) for entry in entries]
        return v_2_1.Parser().parse_root_entries(root_entries, bundle_root=BUNDLE_ROOT)

    def test_simple_definition(self):
        with self.subTest("cluster"):
            raw = {
                "type": "cluster",
                "contract_version": CONTRACT_VERSION,
                "venv": MAIN_VENV,
                "name": "AAA",
                "version": 2.3,
            }
            result = self.parse([raw], path=".")

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[("cluster",)],
                Definition(type="cluster", name="AAA", display_name="AAA", version="2.3", venv=MAIN_VENV),
            )

        with self.subTest("provider"):
            raw = {
                "type": "provider",
                "contract_version": CONTRACT_VERSION,
                "venv": MAIN_VENV,
                "name": "AAA",
                "version": 2.3,
            }
            result = self.parse([raw], path=".")

            self.assertEqual(len(result), 1)
            self.assertEqual(
                result[("provider",)],
                Definition(type="provider", name="AAA", display_name="AAA", version="2.3", venv=MAIN_VENV),
            )

        with self.subTest("host"):
            # a host always ships alongside a provider in a real bundle; the parser now enforces that
            raw = {"type": "host", "name": "AAA", "version": 2.3}
            provider = {
                "type": "provider",
                "contract_version": CONTRACT_VERSION,
                "venv": MAIN_VENV,
                "name": "PPP",
                "version": "1",
            }
            result = self.parse([raw, provider], path=".")

            self.assertEqual(
                result[("host",)],
                Definition(type="host", name="AAA", display_name="AAA", version="2.3", venv=MAIN_VENV),
            )

    def test_simple_service_no_components(self):
        raw = {"type": "service", "name": "strange", "display_name": "is Different", "version": 4}
        cluster = {
            "type": "cluster",
            "contract_version": CONTRACT_VERSION,
            "venv": MAIN_VENV,
            "name": "parent",
            "version": "1",
        }

        result = self.parse([raw, cluster], path="inner")

        expected = Definition(
            type="service", name="strange", display_name="is Different", version="4", path="inner", venv=MAIN_VENV
        )
        self.assertEqual(result[("service", "strange")], expected)

    def test_simple_service_components(self):
        raw = {
            "type": "service",
            "name": "strange",
            "version": 4,
            "components": {"a": None, "b": {"display_name": "ho ho"}},
        }
        cluster = {
            "type": "cluster",
            "contract_version": CONTRACT_VERSION,
            "venv": MAIN_VENV,
            "name": "parent",
            "version": "1",
        }

        result = self.parse([raw, cluster], path="inner")

        expected_service = Definition(
            type="service", name="strange", display_name="strange", version="4", path="inner", venv=MAIN_VENV
        )
        expected_component_a = Definition(
            type="component", name="a", display_name="a", version="4", path="inner", venv=MAIN_VENV
        )
        expected_component_b = Definition(
            type="component", name="b", display_name="ho ho", version="4", path="inner", venv=MAIN_VENV
        )

        self.assertEqual(result[("service", "strange")], expected_service)
        self.assertEqual(result[("component", "strange", "a")], expected_component_a)
        self.assertEqual(result[("component", "strange", "b")], expected_component_b)

    def test_actions(self):
        # 2.x has no job/task distinction: every action always carries a `scripts` list.
        raw = {
            "type": "service",
            "name": "strange",
            "version": "aa.fb",
            "actions": {
                "simple_job": {"scripts": [{"name": "simple_job", "script": "wow.yaml", "script_type": "ansible"}]},
                "simple_task": {
                    "display_name": "Awesome ma I",
                    "scripts": [
                        {"name": "first", "script": "./root.yaml", "script_type": "ansible"},
                        {
                            "name": "second",
                            "display_name": "Special",
                            "script": "another.yaml",
                            "script_type": "ansible",
                        },
                    ],
                },
                "not_full_states": {
                    "scripts": [{"name": "not_full_states", "script": "x.py", "script_type": "python"}],
                    "states": {"available": "any"},
                },
                "not_full_masking": {
                    "scripts": [{"name": "not_full_masking", "script": "x.py", "script_type": "python"}],
                    "masking": {"state": {"unavailable": ["o"]}},
                },
            },
        }
        cluster = {
            "type": "cluster",
            "contract_version": CONTRACT_VERSION,
            "venv": MAIN_VENV,
            "name": "parent",
            "version": "1",
        }
        actions = [
            ActionDefinition(
                name="simple_job",
                display_name="simple_job",
                venv=MAIN_VENV,
                scripts=JobSpecV1.from_entries(
                    build_script_spec("/0", "simple_job", ansible_script("wow.yaml")),
                ),
                available_at=ActionAvailability(states=[], multi_states="any"),
            ),
            ActionDefinition(
                name="simple_task",
                display_name="Awesome ma I",
                venv=MAIN_VENV,
                scripts=JobSpecV1.from_entries(
                    build_script_spec("/0", "first", ansible_script("inner/root.yaml")),
                    build_script_spec("/1", "second", ansible_script("another.yaml"), display_name="Special"),
                ),
                available_at=ActionAvailability(states=[], multi_states="any"),
            ),
            ActionDefinition(
                name="not_full_states",
                display_name="not_full_states",
                venv=MAIN_VENV,
                scripts=JobSpecV1.from_entries(
                    build_script_spec("/0", "not_full_states", python_script("x.py")),
                ),
                available_at=ActionAvailability(states="any", multi_states="any"),
            ),
            ActionDefinition(
                name="not_full_masking",
                display_name="not_full_masking",
                venv=MAIN_VENV,
                scripts=JobSpecV1.from_entries(
                    build_script_spec("/0", "not_full_masking", python_script("x.py")),
                ),
                unavailable_at=ActionAvailability(states=["o"], multi_states=[]),
            ),
        ]

        result = self.parse([raw, cluster], path="inner")

        self.assertEqual(result[("service", "strange")].actions, actions)

    def test_config(self):
        raw = {
            "type": "cluster",
            "contract_version": CONTRACT_VERSION,
            "venv": MAIN_VENV,
            "name": "strange",
            "version": "aa.fb",
            "config_group_customization": True,
            "config": [
                {"name": "a", "display_name": "Wow", "type": "string"},
                {
                    "name": "g1",
                    "type": "group",
                    "subs": [
                        {"name": "a", "type": "string"},
                        {"name": "b", "type": "text", "pattern": "oo", "default": "haha"},
                    ],
                },
                {
                    "name": "g2",
                    "display_name": "Very Active",
                    "type": "group",
                    "activatable": True,
                    "active": True,
                    "subs": [
                        {"name": "a", "type": "list", "default": ["u"]},
                        {"name": "b", "type": "map", "default": {"k": "v"}},
                        {"name": "whatshere", "type": "file", "default": "./special.txt"},
                    ],
                },
                {"name": "b", "type": "integer", "default": 43, "group_customization": False},
            ],
        }

        s = ConfigParamPlainSpec
        cfg_val = {"group_customization": True}

        expected_parameters = {
            spec.key: spec
            for spec in [
                s(key=("a",), display_name="Wow", type="string", **cfg_val),
                s(key=("g1",), display_name="g1", type="group", **cfg_val),
                s(key=("g1", "a"), display_name="a", type="string", **cfg_val),
                s(
                    key=("g1", "b"),
                    display_name="b",
                    type="text",
                    limits={"pattern": "oo"},
                    default="haha",
                    **cfg_val,
                ),
                s(
                    key=("g2",),
                    display_name="Very Active",
                    type="group",
                    limits={"activatable": True, "active": True},
                    **cfg_val,
                ),
                s(key=("g2", "a"), display_name="a", type="list", default=["u"], **cfg_val),
                s(key=("g2", "b"), display_name="b", type="map", default={"k": "v"}, **cfg_val),
                s(
                    key=("g2", "whatshere"),
                    display_name="whatshere",
                    type="file",
                    default="details/special.txt",
                    **cfg_val,
                ),
                s(key=("b",), display_name="b", type="integer", default=43, group_customization=False),
            ]
        }
        expected_default_values = {
            ("g1", "b"): "haha",
            ("g2", "a"): ["u"],
            ("g2", "b"): {"k": "v"},
            ("g2", "whatshere"): "details/special.txt",
            ("b",): 43,
        }
        expected_default_attrs = {("g2",): {"active": True}}

        result = self.parse([raw], path="details")
        config = result[("cluster",)].config

        self.assertDictEqual(config.default_attrs, expected_default_attrs)
        self.assertDictEqual(config.default_values, expected_default_values)
        self.assertDictEqual(config.parameters, expected_parameters)

    def test_upgrades(self):
        raw = {
            "type": "cluster",
            "contract_version": CONTRACT_VERSION,
            "venv": MAIN_VENV,
            "name": "strange",
            "version": "aa.fb",
            "upgrade": [
                {
                    "name": "full",
                    "description": "this is desc",
                    "display_name": "own Value",
                    "states": {"available": ["o", "no"], "on_success": "upgr"},
                    "from_edition": ["enterprise"],
                    "versions": {"min": 0, "max": 43.3},
                },
                {"name": "simple", "versions": {"max_strict": 2, "min_strict": 0}},
                {
                    "name": "action-like",
                    "states": {"available": "any"},
                    "from_edition": ["yet", "custom"],
                    "versions": {"min_strict": "12.2.eee", "max": 43.3},
                    "scripts": [
                        {"name": "first", "script": "./root.yaml", "script_type": "ansible"},
                        {
                            "name": "second",
                            "display_name": "Special",
                            "script": "bundle_switch",
                            "script_type": "internal",
                        },
                    ],
                },
            ],
        }

        upgrade_action_name = (
            "strange_aa.fb_community_upgrade_action-like_12.2.eee_strict_true-43.3_strict_true_"
            "editions-yet_custom_state_available-a_n_y_state_on_success-"
        )

        upgrades = [
            UpgradeDefinition(
                name="full",
                description="this is desc",
                display_name="own Value",
                state_available=["o", "no"],
                state_on_success="upgr",
                restrictions=UpgradeRestrictions(
                    min_version=VersionBound(value="0", is_strict=False),
                    max_version=VersionBound(value="43.3", is_strict=False),
                    from_editions=["enterprise"],
                ),
            ),
            UpgradeDefinition(
                name="simple",
                display_name="simple",
                restrictions=UpgradeRestrictions(
                    min_version=VersionBound(value="0", is_strict=True),
                    max_version=VersionBound(value="2", is_strict=True),
                ),
            ),
            UpgradeDefinition(
                name="action-like",
                display_name="action-like",
                state_available="any",
                restrictions=UpgradeRestrictions(
                    min_version=VersionBound(value="12.2.eee", is_strict=True),
                    max_version=VersionBound(value="43.3", is_strict=False),
                    from_editions=["yet", "custom"],
                ),
                action=ActionDefinition(
                    name=upgrade_action_name,
                    display_name="Upgrade: action-like",
                    venv=MAIN_VENV,
                    available_at=ActionAvailability(states="any", multi_states="any"),
                    scripts=JobSpecV1.from_entries(
                        build_script_spec("/0", "first", ansible_script("root.yaml")),
                        build_script_spec(
                            "/1", "second", simple_internal_script("bundle_switch"), display_name="Special"
                        ),
                    ),
                ),
            ),
        ]

        result = self.parse([raw], path=".")

        self.assertEqual(result[("cluster",)].upgrades, upgrades)


class TestHostManage(TestCase):
    """The `host_manage` and `host_group_manage` internal scripts"""

    scripts_yaml = """
    - name: share hosts
      script: host_manage
      script_type: internal
      params:
        operation: add_duplicates
        source:
          - type: component
            cluster_name: adb-one
            service_name: adb
            component_name: segment
          - type: cluster
            cluster_name: adb-two
        mapping_rules:
          - {service: adb_clusters, component: adcc_agent, action: add}
    - name: fill groups
      script: host_manage
      script_type: internal
      params:
        operation: add_to_groups
        source:
          - type: cluster
            cluster_name: adb-one
        groups:
          - name: adb-one
            type: config_host_group
            object: {type: service, service_name: adb_clusters}
    - name: release hosts
      script: host_manage
      script_type: internal
      params:
        operation: remove_duplicates
        source:
          - type: config_host_group
            name: adb-one
            object: {type: service, service_name: adb_clusters}
    - name: prepare groups
      script: host_group_manage
      script_type: internal
      params:
        operation: add
        groups:
          - name: adb-one
            type: config_host_group
            object: {type: service, service_name: adb_clusters}
            description: "per-cluster settings"
            parameters:
              - key: adcc_agent/ram
                value: 4
          - name: adb-one
            type: action_host_group
            object: {type: component, service_name: adb_clusters, component_name: adcc_agent}
    - name: drop groups
      script: host_group_manage
      script_type: internal
      params:
        operation: remove
        groups:
          - name: adb-one
            type: config_host_group
            object: {type: service, service_name: adb_clusters}
    """

    def parse(self, as_yaml: str, mode: str = "action", version: str = "2.1"):
        parser = dict(get_parsers())[version]
        return parser.parse_scripts(
            yaml.safe_load(as_yaml), template_path=Path(), action_allow_to_terminate=False, mode=mode
        )

    def test_parse_in_action_mode_success(self):
        for version, parser in get_parsers():
            with self.subTest(version):
                parsed = parser.parse_scripts(
                    yaml.safe_load(self.scripts_yaml),
                    template_path=Path(),
                    action_allow_to_terminate=False,
                    mode="action",
                )

                scripts = [spec.script for spec in parsed.scripts.values()]
                self.assertEqual(
                    [type(script) for script in scripts],
                    [HostManageScript] * 3 + [HostGroupManageScript] * 2,
                )
                self.assertEqual(scripts[0].params.operation, "add_duplicates")
                self.assertEqual(
                    scripts[0].params.source[0],
                    ComponentHostSource(
                        type="component", cluster_name="adb-one", service_name="adb", component_name="segment"
                    ),
                )
                self.assertEqual(
                    scripts[0].params.mapping_rules,
                    [HcAclRule(service="adb_clusters", component="adcc_agent", action="add")],
                )
                self.assertEqual(scripts[1].params.groups[0].name, "adb-one")
                self.assertEqual(scripts[3].params.groups[0].description, "per-cluster settings")
                self.assertEqual(
                    scripts[3].params.groups[0].parameters, [HostGroupParameter(key="adcc_agent/ram", value=4)]
                )

    def test_rejected_in_upgrade_and_wizard_modes_fail(self):
        for version, parser in get_parsers():
            for mode in ("upgrade", "wizard"):
                with self.subTest(f"{version}-{mode}"):
                    with self.assertRaises(BundleParsingError, msg="'host_manage'"):
                        parser.parse_scripts(
                            yaml.safe_load(self.scripts_yaml),
                            template_path=Path(),
                            action_allow_to_terminate=False,
                            mode=mode,
                        )

    def test_empty_hosts_survives_the_dump_success(self):
        """`hosts: []` means "empty the group" and must not collapse into "leave it alone"."""

        parsed = self.parse(
            """
            - name: empty group
              script: host_group_manage
              script_type: internal
              params:
                operation: add
                groups:
                  - name: adb-one
                    type: config_host_group
                    object: {type: cluster}
                    hosts: []
            """
        )

        self.assertEqual(parsed.scripts["/0"].script.params.groups[0].hosts, [])
        # the plan is stored as JSON and read back before the job runs
        stored = JobSpecV1.model_validate(parsed.model_dump(mode="json"))
        self.assertEqual(stored.scripts["/0"].script.params.groups[0].hosts, [])

    def test_omitted_hosts_is_none_in_the_plan_success(self):
        parsed = self.parse(
            """
            - name: create group
              script: host_group_manage
              script_type: internal
              params:
                operation: add
                groups:
                  - name: adb-one
                    type: config_host_group
                    object: {type: cluster}
            """
        )

        self.assertIsNone(parsed.scripts["/0"].script.params.groups[0].hosts)
        stored = JobSpecV1.model_validate(parsed.model_dump(mode="json"))
        self.assertIsNone(stored.scripts["/0"].script.params.groups[0].hosts)

    def test_unknown_operation_fail(self):
        with self.assertRaises(BundleParsingError, msg="operation"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add
                    source: [{type: cluster}]
                """
            )

    def test_empty_source_fail(self):
        with self.assertRaises(BundleParsingError, msg="source"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_duplicates
                    source: []
                """
            )

    def test_source_is_required_fail(self):
        with self.assertRaises(BundleParsingError, msg="source"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_duplicates
                """
            )

    def test_duplicate_source_entries_fail(self):
        with self.assertRaises(BundleParsingError, msg="Duplicate `source` entry"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_duplicates
                    source:
                      - {type: cluster, cluster_name: adb-one}
                      - {type: cluster, cluster_name: adb-one}
                """
            )

    def test_cluster_name_on_host_entry_fail(self):
        """A host is named by an fqdn, which identifies it without a cluster."""

        with self.assertRaises(BundleParsingError, msg="cluster_name"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_duplicates
                    source:
                      - {type: host, host_name: h1, cluster_name: adb-one}
                """
            )

    def test_cluster_name_on_group_entry_fail(self):
        with self.assertRaises(BundleParsingError, msg="cluster_name"):
            self.parse(
                """
                - name: release hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: remove_duplicates
                    source:
                      - type: config_host_group
                        name: adb-one
                        cluster_name: adb-one
                        object: {type: cluster}
                """
            )

    def test_empty_name_fail(self):
        """`{{ task.config.typo }}` renders to an empty string rather than failing."""

        with self.assertRaises(BundleParsingError, msg="cluster_name"):
            self.parse(
                """
                - name: share hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_duplicates
                    source: [{type: cluster, cluster_name: ""}]
                """
            )

    def test_target_on_remove_duplicates_fail(self):
        with self.assertRaises(BundleParsingError, msg="target"):
            self.parse(
                """
                - name: release hosts
                  script: host_manage
                  script_type: internal
                  params:
                    operation: remove_duplicates
                    source: [{type: cluster, cluster_name: adb-one}]
                    target: [{cluster_name: adb-two}]
                """
            )

    def test_mapping_rules_on_add_to_groups_fail(self):
        with self.assertRaises(BundleParsingError, msg="mapping_rules"):
            self.parse(
                """
                - name: fill groups
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_to_groups
                    source: [{type: cluster}]
                    groups: [{name: g, type: config_host_group}]
                    mapping_rules: [{service: s, component: c, action: add}]
                """
            )

    def test_add_to_groups_without_groups_fail(self):
        with self.assertRaises(BundleParsingError, msg="groups"):
            self.parse(
                """
                - name: fill groups
                  script: host_manage
                  script_type: internal
                  params:
                    operation: add_to_groups
                    source: [{type: cluster}]
                """
            )

    def test_hosts_on_group_removal_fail(self):
        with self.assertRaises(BundleParsingError, msg="hosts"):
            self.parse(
                """
                - name: drop groups
                  script: host_group_manage
                  script_type: internal
                  params:
                    operation: remove
                    groups:
                      - name: adb-one
                        type: config_host_group
                        object: {type: cluster}
                        hosts: [h1]
                """
            )

    def test_parameters_on_action_host_group_fail(self):
        with self.assertRaises(BundleParsingError, msg="parameters"):
            self.parse(
                """
                - name: prepare groups
                  script: host_group_manage
                  script_type: internal
                  params:
                    operation: add
                    groups:
                      - name: adb-one
                        type: action_host_group
                        object: {type: cluster}
                        parameters: [{key: a, value: 1}]
                """
            )

    def test_provider_owned_action_host_group_fail(self):
        with self.assertRaises(BundleParsingError, msg="provider"):
            self.parse(
                """
                - name: prepare groups
                  script: host_group_manage
                  script_type: internal
                  params:
                    operation: add
                    groups:
                      - name: adb-one
                        type: action_host_group
                        object: {type: provider}
                """
            )

    def test_duplicate_group_entries_fail(self):
        with self.assertRaises(BundleParsingError, msg="Duplicate"):
            self.parse(
                """
                - name: prepare groups
                  script: host_group_manage
                  script_type: internal
                  params:
                    operation: add
                    groups:
                      - {name: adb-one, type: config_host_group, object: {type: cluster}}
                      - {name: adb-one, type: config_host_group, object: {type: cluster}}
                """
            )
