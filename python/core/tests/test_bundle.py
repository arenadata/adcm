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

from core.bundle_alt.validation import (
    ActionDefinition,
    ConfigDefinition,
    Definition,
    Script,
    UpgradeDefinition,
    check_action_hc_acl_rules,
    check_bound_to,
    check_bundle_switch_amount_for_upgrade_action,
    check_component_constraint_length,
    check_exported_values_exists_in_config,
    check_import_defaults_exist_in_config,
    check_requires,
)
from core.errors import BundleParsingError

CLUSTER = "cluster"
SERVICE = "service"
COMPONENT = "component"

ERROR_CODE = "REQUIRES_ERROR"


def make_def(key, **kwargs):
    name = "dummy"
    if len(key) > 1:
        name = key[-1]

    defaults = {
        "type": key[0],
        "name": name,
        "version": "3.0",
        "requires": [],
        "bound_to": {},
        "actions": {},
        "upgrades": {},
        "config": {},
        "import_": None,
        "export": None,
        "constraint": None,
        "path": Path(),
    }

    return Definition(**(defaults | kwargs))


def make_action(**kwargs):
    defaults = {
        "hostcomponentmap": [],
        "type": "job",
        "script": "run.yaml",
        "script_type": "ansible",
        "scripts": [],
        "jinja_scripts": None,
        "jinja_config": None,
    }
    return ActionDefinition(**(defaults | kwargs))


def make_upgrade(**kwargs):
    defaults = {"name": "blahblah", "hostcomponentmap": [], "scripts": []}
    return UpgradeDefinition(**(defaults | kwargs))


def make_script(**kwargs):
    defaults = {"script": "aaa.yaml", "script_type": "ansible"}
    return Script(**(defaults | kwargs))


def make_config(**kwargs):
    defaults = {"name": "some", "type": "integer"}
    return ConfigDefinition(**(defaults | kwargs))


class TestBundleValidation(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

        self.definitions = {
            key: make_def(key)
            for key in (
                (CLUSTER,),
                (SERVICE, "s1"),
                (COMPONENT, "s1", "c1"),
                (SERVICE, "s2"),
                (COMPONENT, "s2", "c1"),
                (COMPONENT, "s2", "c2"),
            )
        }
        self.missing_message = "No required"
        self.not_self_message = "can not require themself"

    def test_check_requires_success(self) -> None:
        for case_name, key, requires in [
            ["service require service", (SERVICE, "s3"), [{"service": "s1"}]],
            ["service require component", (SERVICE, "s3"), [{"service": "s1", "component": "c1"}]],
            ["component require service", (COMPONENT, "s2", "c1"), [{"service": "s1"}]],
            ["component require component", (COMPONENT, "s2", "c1"), [{"service": "s1", "component": "c1"}]],
        ]:
            with self.subTest(case_name):
                with_requires = make_def(key, requires=requires)
                # expect no error
                check_requires(self.definitions | {key: with_requires})

    def test_check_requires_fail(self) -> None:
        for case_name, key, requires, message in [
            ["service require itself", (SERVICE, "s3"), [{"service": "s3"}], self.not_self_message],
            ["service require non-existing service", (SERVICE, "s3"), [{"service": "notexist"}], self.missing_message],
            [
                "service require non-existing component",
                (SERVICE, "s3"),
                [{"service": "notexist", "component": "c1"}],
                self.missing_message,
            ],
            [
                "component require itself",
                (COMPONENT, "s1", "c1"),
                [{"service": "s1", "component": "c1"}],
                self.not_self_message,
            ],
            [
                "component require non-existing service",
                (COMPONENT, "s1", "c1"),
                [{"service": "notexist"}],
                self.missing_message,
            ],
            [
                "component require non-existing component",
                (COMPONENT, "s1", "c1"),
                [{"service": "s2", "component": "notexist"}],
                self.missing_message,
            ],
        ]:
            with self.subTest(case_name):
                with_requires = make_def(key, requires=requires)

                with self.assertRaises(BundleParsingError) as err:
                    check_requires(self.definitions | {key: with_requires})

                self.assertEqual(err.exception.code, ERROR_CODE)
                self.assertIn(message, err.exception.msg)

    def test_requires_cyclic_fail(self) -> None:
        extra = {
            key: make_def(key, requires=requires)
            for key, requires in [
                ((SERVICE, "s1"), [{"service": "s2", "component": "c1"}]),
                ((SERVICE, "s2"), [{"service": "s1", "component": "c1"}]),
            ]
        }

        with self.assertRaises(BundleParsingError) as err:
            check_requires(self.definitions | extra)

        self.assertEqual(err.exception.code, ERROR_CODE)
        self.assertIn("should not be cyclic", err.exception.msg)

    def test_multiple_requires_success(self) -> None:
        key = (SERVICE, "s4")
        requires = [{"service": "s2"}, {"service": "s1", "component": "c1"}]
        with_requires = make_def(key, requires=requires)

        check_requires(self.definitions | {key: with_requires})

        key = (COMPONENT, "s2", "c3")
        requires = [{"service": "s2"}, {"service": "s1", "component": "c1"}]
        with_requires = make_def(key, requires=requires)

        check_requires(self.definitions | {key: with_requires})

    def test_multiple_requires_fail(self) -> None:
        key = (SERVICE, "s4")
        requires = [{"service": "s2"}, {"service": "s1", "component": "c1"}, {"service": "s4"}]
        with_requires = make_def(key, requires=requires)

        with self.assertRaises(BundleParsingError) as err:
            check_requires(self.definitions | {key: with_requires})
        self.assertEqual(err.exception.code, ERROR_CODE)
        self.assertIn(self.not_self_message, err.exception.msg)

        key = (COMPONENT, "s2", "c3")
        requires = [{"service": "s2"}, {"service": "s1", "component": "c1"}, {"service": "notexist", "component": "c1"}]
        with_requires = make_def(key, requires=requires)

        with self.assertRaises(BundleParsingError) as err:
            check_requires(self.definitions | {key: with_requires})
        self.assertEqual(err.exception.code, ERROR_CODE)
        self.assertIn(self.missing_message, err.exception.msg)

    def test_check_bound_to_success(self) -> None:
        key = (COMPONENT, "s2", "c3")
        with_bound_to = make_def(key, bound_to={"service": "s1", "component": "c1"})

        check_bound_to(key, with_bound_to, self.definitions | {key: with_bound_to})

    def test_check_bound_to_fail(self) -> None:
        key = (COMPONENT, "s2", "c3")
        with_bound_to = make_def(key, bound_to={"service": "s2", "component": "c3"})

        with self.assertRaises(BundleParsingError) as err:
            check_bound_to(key, with_bound_to, self.definitions | {key: with_bound_to})

        self.assertEqual(err.exception.code, "COMPONENT_CONSTRAINT_ERROR")

    def test_check_action_hostcomponentmap_success(self) -> None:
        action = make_action(
            hostcomponentmap=[
                {"service": "s1", "component": "c1"},
                # duplication for add-remove case
                {"service": "s1", "component": "c1"},
                {"service": "s2", "component": "c2"},
            ]
        )

        for key in [
            (CLUSTER,),
            (SERVICE, "s3"),
            (COMPONENT, "s2", "c3"),
        ]:
            with self.subTest(key[0]):
                with_action_with_hc = make_def(key, actions=[action])

                check_action_hc_acl_rules(
                    action.hostcomponentmap, with_action_with_hc, self.definitions | {key: with_action_with_hc}
                )

    def test_check_action_hostcomponentmap_fail(self) -> None:
        action = make_action(
            hostcomponentmap=[
                {"service": "s1", "component": "c1"},
                {"service": "s4", "component": "c1"},
                {"service": "s2", "component": "c2"},
            ]
        )

        for key in [
            (CLUSTER,),
            (SERVICE, "s3"),
            (COMPONENT, "s2", "c3"),
        ]:
            with self.subTest(key[0]):
                with_action_with_hc = make_def(key, actions=[action])

                with self.assertRaises(BundleParsingError) as err:
                    check_action_hc_acl_rules(
                        action.hostcomponentmap, with_action_with_hc, self.definitions | {key: with_action_with_hc}
                    )

                self.assertEqual(err.exception.code, "INVALID_ACTION_DEFINITION")

    def test_check_bundle_switch_amount_success(self) -> None:
        definition = make_def((CLUSTER,))

        bundle_switch = {"script": "bundle_switch", "script_type": "internal"}
        hc_apply = {"script": "hc_apply", "script_type": "internal"}
        bundle_revert = {"script": "bundle_revert", "script_type": "internal"}
        ansible = {"script_type": "ansible"}

        for case, correct_scripts in [
            ("single switch", [bundle_switch]),
            ("switch and ansible", [ansible, bundle_switch, ansible]),
            (
                "ansible, switch and other internal",
                [hc_apply, bundle_revert, bundle_switch, bundle_revert, hc_apply, ansible],
            ),
        ]:
            with self.subTest(case):
                upgrade = make_upgrade(scripts=[make_script(**script) for script in correct_scripts])

                check_bundle_switch_amount_for_upgrade_action(definition, upgrade)

    def test_check_bundle_switch_amount_fail(self) -> None:
        no_switch_err = 'must contain exact one block with script "bundle_switch"'
        multiple_switch_err = 'with script_type "internal" must be unique'

        definition = make_def((CLUSTER,))

        bundle_switch = {"script": "bundle_switch", "script_type": "internal"}
        hc_apply = {"script": "hc_apply", "script_type": "internal"}
        bundle_revert = {"script": "bundle_revert", "script_type": "internal"}
        ansible = {"script_type": "ansible"}

        for case, err_msg, correct_scripts in [
            ("no switch", no_switch_err, [ansible, hc_apply, bundle_revert]),
            ("multi_switch", multiple_switch_err, [ansible, bundle_switch, ansible, bundle_switch]),
        ]:
            with self.subTest(case):
                upgrade = make_upgrade(scripts=[make_script(**script) for script in correct_scripts])

                with self.assertRaises(BundleParsingError) as err:
                    check_bundle_switch_amount_for_upgrade_action(definition, upgrade)

                self.assertEqual(err.exception.code, "INVALID_UPGRADE_DEFINITION")
                self.assertIn(err_msg, err.exception.msg)

    def check_component_constraint_length_success(self):
        service_def = make_def((SERVICE, "s1"))

        for case, constraint in [
            ("1 item int", [1]),
            ("1 item str", ["+"]),
            ("2 item int int", [1, 4]),
            ("2 item str int", ["odd", 4]),
        ]:
            with self.subTest(case):
                component_def = make_def((COMPONENT, "s1", "c1"), constraint=constraint)
                check_component_constraint_length(component_def, service_def)

    def test_check_component_constraint_length_fail(self):
        zero_err = "should not be empty"
        too_many_err = "should have only 1 or 2 elements"

        service_def = make_def((SERVICE, "s1"))

        for case, err_msg, constraint in [
            ("0 items", zero_err, []),
            ("3 items", too_many_err, [1, 2, 3]),
        ]:
            with self.subTest(case):
                component_def = make_def((COMPONENT, "s1", "c1"), constraint=constraint)

                with self.assertRaises(BundleParsingError) as err:
                    check_component_constraint_length(component_def, service_def)

                self.assertEqual(err.exception.code, "INVALID_COMPONENT_DEFINITION")
                self.assertIn(err_msg, err.exception.msg)

    def test_check_exported_values_exists_in_config_success(self) -> None:
        config = {"/a": ..., "/b": ...}
        definition = make_def((CLUSTER,), config=config, export=[])

        check_exported_values_exists_in_config(definition)

        definition = make_def((CLUSTER,), config=config, export=["a"])
        check_exported_values_exists_in_config(definition)

    def test_check_exported_values_exists_in_config_fail(self) -> None:
        config = {"/a": ..., "/b": ..., "/c/k": ...}
        definition = make_def((CLUSTER,), config=config, export=["k"])

        with self.assertRaises(BundleParsingError) as err:
            check_exported_values_exists_in_config(definition)

        self.assertEqual(err.exception.code, "INVALID_OBJECT_DEFINITION")
        self.assertIn('does not has "k" config group', err.exception.msg)

    def test_check_import_defaults_exist_in_config_success(self) -> None:
        config = {"/a": make_config(name="a", type="group"), "/b": make_config(name="b"), "/c/k": make_config(name="c")}

        with self.subTest("Import with no default"):
            definition = make_def((CLUSTER,), config=config, import_=[{}])

            check_import_defaults_exist_in_config(definition)

        with self.subTest("Import with existing default"):
            definition = make_def((CLUSTER,), config=config, import_=[{"default": "a"}])

            check_import_defaults_exist_in_config(definition)

    def test_check_import_defaults_exist_in_config_fail(self) -> None:
        config = {"/a": make_config(name="a", type="group"), "/b": make_config(name="b"), "/c/k": make_config(name="c")}

        for case, imports in [
            ("Import default to not group", [{"default": "b"}]),
            ("Import default not existing field", [{"default": "p"}]),
        ]:
            with self.subTest(case):
                definition = make_def((CLUSTER,), config=config, import_=imports)

                with self.assertRaises(BundleParsingError) as err:
                    check_import_defaults_exist_in_config(definition)

                self.assertEqual(err.exception.code, "INVALID_OBJECT_DEFINITION")
                self.assertIn("No import default group", err.exception.msg)
