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

from core.bundle_alt.convertion import schema_entry_to_definition
from core.bundle_alt.errors import BundleValidationError
from core.bundle_alt.schema import ClusterSchema, HostSchema, ProviderSchema, ServiceSchema
from core.bundle_alt.types import (
    ActionAvailability,
    ActionDefinition,
    ConfigDefinition,
    ConfigParamPlainSpec,
    Definition,
    ImportDefinition,
    UpgradeDefinition,
    UpgradeRestrictions,
    VersionBound,
)
from core.bundle_alt.validation import (
    ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
    ADCM_HOST_TURN_ON_MM_ACTION_NAME,
    check_action_hc_acl_rules,
    check_bound_to,
    check_bundle_switch_amount_for_upgrade_action,
    check_exported_values_exists_in_config,
    check_import_defaults_exist_in_config,
    check_mm_host_action_is_allowed,
    check_requires,
)
from core.job.types import JobSpec, ScriptType

CLUSTER = "cluster"
SERVICE = "service"
COMPONENT = "component"

ERROR_CODE = "REQUIRES_ERROR"


def make_def(key, **kwargs):
    name = "dummy"
    if len(key) > 1:
        name = key[-1]

    defaults = {"type": key[0], "name": name, "version": "3.0"}

    if "config" in kwargs:
        kwargs["config"] = ConfigDefinition(parameters=kwargs["config"], default_values={}, default_attrs={})

    return Definition(**(defaults | kwargs))


def make_action(**kwargs):
    defaults = {"name": "aaa", "type": "job"}
    return ActionDefinition(**(defaults | kwargs))


def make_upgrade(**kwargs):
    defaults = {"name": "blahblah"}
    return UpgradeDefinition(**(defaults | kwargs))


def make_script(**kwargs):
    defaults = {
        "script": "aaa.yaml",
        "script_type": "ansible",
        "allow_to_terminate": False,
        "name": "aaa",
        "display_name": "aaa",
        "state_on_fail": "",
        "multi_state_on_fail_set": [],
        "multi_state_on_fail_unset": [],
        "params": {},
    }
    return JobSpec(**(defaults | kwargs))


def make_config(**kwargs):
    defaults = {"name": "some", "type": "integer"} | {
        "key": ("a",),
        "display_name": "A",
        "description": "aaaaa",
        "default": None,
        "limits": {},
        "ui_options": dict,
        "required": True,
        "group_customization": None,
    }

    result = defaults | kwargs
    result["key"] = tuple(result.pop("name").split("/"))
    return ConfigParamPlainSpec(**result)


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

    def test_check_mm_on_host_wrong_object_type_fail(self) -> None:
        for name in (ADCM_HOST_TURN_ON_MM_ACTION_NAME, ADCM_HOST_TURN_OFF_MM_ACTION_NAME):
            for type_ in ("service", "component", "provider", "host", "adcm"):
                with self.subTest(f"{name}-{type_}"):
                    action = ActionDefinition(type="job", name=name)
                    definition = Definition(type=type_, name="aaa", version="1")

                    with self.assertRaises(BundleValidationError) as err:
                        check_mm_host_action_is_allowed(action, definition)

                    self.assertEqual(
                        err.exception.message, f'Action named "{name}" should be defined in cluster context only'
                    )

    def test_check_mm_on_host_not_host_action_type_fail(self) -> None:
        for name in (ADCM_HOST_TURN_ON_MM_ACTION_NAME, ADCM_HOST_TURN_OFF_MM_ACTION_NAME):
            with self.subTest(name):
                action = ActionDefinition(type="task", name=name, is_host_action=False)
                definition = Definition(type="cluster", name="aaa", version="1")

                with self.assertRaises(BundleValidationError) as err:
                    check_mm_host_action_is_allowed(action, definition.type)

                self.assertEqual(err.exception.error, f'Action named "{name}" should be "host action"')

    def test_check_mm_on_host_not_host_action_type_success(self) -> None:
        for name in (ADCM_HOST_TURN_ON_MM_ACTION_NAME, ADCM_HOST_TURN_OFF_MM_ACTION_NAME):
            with self.subTest(name):
                action = ActionDefinition(type="task", name=name, is_host_action=True)
                definition = Definition(type="cluster", name="aaa", version="1")

                check_mm_host_action_is_allowed(action, definition.type)

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

                with self.assertRaises(BundleValidationError) as err:
                    check_requires(self.definitions | {key: with_requires})

                self.assertIn(message, err.exception.message)

    def test_requires_cyclic_fail(self) -> None:
        extra = {
            key: make_def(key, requires=requires)
            for key, requires in [
                ((SERVICE, "s1"), [{"service": "s2", "component": "c1"}]),
                ((SERVICE, "s2"), [{"service": "s1", "component": "c1"}]),
            ]
        }

        with self.assertRaises(BundleValidationError) as err:
            check_requires(self.definitions | extra)

        self.assertIn("should not be cyclic", err.exception.message)

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

        with self.assertRaises(BundleValidationError) as err:
            check_requires(self.definitions | {key: with_requires})
        self.assertIn(self.not_self_message, err.exception.message)

        key = (COMPONENT, "s2", "c3")
        requires = [{"service": "s2"}, {"service": "s1", "component": "c1"}, {"service": "notexist", "component": "c1"}]
        with_requires = make_def(key, requires=requires)

        with self.assertRaises(BundleValidationError) as err:
            check_requires(self.definitions | {key: with_requires})
        self.assertIn(self.missing_message, err.exception.message)

    def test_check_bound_to_success(self) -> None:
        key = (COMPONENT, "s2", "c3")
        with_bound_to = make_def(key, bound_to={"service": "s1", "component": "c1"})

        check_bound_to(owner_key=key, bound_to=with_bound_to.bound_to)

    def test_check_bound_to_fail(self) -> None:
        key = (COMPONENT, "s2", "c3")
        with_bound_to = make_def(key, bound_to={"service": "s2", "component": "c3"})

        with self.assertRaises(BundleValidationError) as err:
            check_bound_to(owner_key=key, bound_to=with_bound_to.bound_to)

        self.assertEqual(err.exception.message, 'Component can not require themself in "bound_to"')

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

                check_action_hc_acl_rules(action.hostcomponentmap, self.definitions | {key: with_action_with_hc})

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

                with self.assertRaises(BundleValidationError) as err:
                    check_action_hc_acl_rules(action.hostcomponentmap, self.definitions | {key: with_action_with_hc})

                self.assertIn("Unknown component", err.exception.message)

    def test_check_bundle_switch_amount_success(self) -> None:
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
                upgrade = make_upgrade(
                    action=make_action(scripts=[make_script(**script) for script in correct_scripts])
                )

                check_bundle_switch_amount_for_upgrade_action(upgrade)

    def test_check_bundle_switch_amount_fail(self) -> None:
        no_switch_err = 'must contain exact one block with script "bundle_switch"'
        multiple_switch_err = 'with script_type "internal" must be unique'

        bundle_switch = {"script": "bundle_switch", "script_type": "internal"}
        hc_apply = {"script": "hc_apply", "script_type": "internal"}
        bundle_revert = {"script": "bundle_revert", "script_type": "internal"}
        ansible = {"script_type": "ansible"}

        for case, err_message, correct_scripts in [
            ("no switch", no_switch_err, [ansible, hc_apply, bundle_revert]),
            ("multi_switch", multiple_switch_err, [ansible, bundle_switch, ansible, bundle_switch]),
        ]:
            with self.subTest(case):
                upgrade = make_upgrade(
                    action=make_action(scripts=[make_script(**script) for script in correct_scripts])
                )

                with self.assertRaises(BundleValidationError) as err:
                    check_bundle_switch_amount_for_upgrade_action(upgrade)

                self.assertIn(err_message, err.exception.message)

    def test_check_exported_values_exists_in_config_success(self) -> None:
        config = {("a",): ..., ("b",): ...}
        definition = make_def((CLUSTER,), config=config, exports=[])

        check_exported_values_exists_in_config(exports=definition.exports, config=definition.config)

        definition = make_def((CLUSTER,), config=config, exports=["a"])
        check_exported_values_exists_in_config(exports=definition.exports, config=definition.config)

    def test_check_exported_values_exists_in_config_fail(self) -> None:
        config = {("a",): ..., ("b",): ..., ("c", "k"): ...}
        definition = make_def((CLUSTER,), config=config, exports=["k"])

        with self.assertRaises(BundleValidationError) as err:
            check_exported_values_exists_in_config(exports=definition.exports, config=definition.config)

        self.assertIn("Group specified for export is missing in configuration: k", err.exception.message)

    def test_check_import_defaults_exist_in_config_success(self) -> None:
        config = {"/a": make_config(name="a", type="group"), "/b": make_config(name="b"), "/c/k": make_config(name="c")}

        with self.subTest("Import with no default"):
            definition = make_def((CLUSTER,), config=config, imports=[ImportDefinition(name="hoho")])

            check_import_defaults_exist_in_config(imports=definition.imports, config=definition.config)

        with self.subTest("Import with existing default"):
            definition = make_def((CLUSTER,), config=config, imports=[ImportDefinition(name="haha", default="a")])

            check_import_defaults_exist_in_config(imports=definition.imports, config=definition.config)

    def test_check_import_defaults_exist_in_config_fail(self) -> None:
        config = {"/a": make_config(name="a", type="group"), "/b": make_config(name="b"), "/c/k": make_config(name="c")}

        for case, imports in [
            ("Import default to not group", [{"name": "a", "default": "b"}]),
            ("Import default not existing field", [{"name": "a", "default": "p"}]),
        ]:
            with self.subTest(case):
                definition = make_def((CLUSTER,), config=config, imports=[ImportDefinition(**i) for i in imports])

                with self.assertRaises(BundleValidationError) as err:
                    check_import_defaults_exist_in_config(imports=definition.imports, config=definition.config)

                self.assertIn(
                    "Group specified as default for import a is missing in configuration: ", err.exception.message
                )


class TestBundleDefinitionConvertion(TestCase):
    maxDiff = None

    def convert(self, source, path="."):
        if isinstance(source, ServiceSchema):
            entries: dict = {("service", source.name): source}
            for name, component in (source.components or {}).items():
                entries[("component", source.name, name)] = component
        else:
            entries = {(source.type,): source}

        return tuple(
            (key, schema_entry_to_definition(key, entry, entries, path, Path())) for key, entry in entries.items()
        )

    def test_simple_definition(self):
        for type_, model in (("cluster", ClusterSchema), ("provider", ProviderSchema), ("host", HostSchema)):
            with self.subTest(type_):
                raw = {"type": type_, "name": "AAA", "version": 2.3}
                schema = model.model_validate(raw)

                expected = Definition(type=type_, name="AAA", display_name="AAA", version="2.3")

                result = self.convert(schema, path=".")

                self.assertEqual(len(result), 1)

                key, definition = result[0]

                self.assertEqual(key, (type_,))
                self.assertEqual(definition, expected)

    def test_simple_service_no_components(self):
        raw = {"type": "service", "name": "strange", "display_name": "is Different", "version": 4}
        schema = ServiceSchema.model_validate(raw)

        expected = Definition(type="service", name="strange", display_name="is Different", version="4", path="inner")

        result = self.convert(schema, path="inner")

        self.assertEqual(len(result), 1)

        key, definition = result[0]

        self.assertEqual(key, ("service", "strange"))
        self.assertEqual(definition, expected)

    def test_simple_service_components(self):
        raw = {
            "type": "service",
            "name": "strange",
            "version": 4,
            "components": {"a": None, "b": {"display_name": "ho ho"}},
        }
        schema = ServiceSchema.model_validate(raw)

        expected_service = Definition(type="service", name="strange", display_name="strange", version="4", path="inner")
        expected_component_a = Definition(type="component", name="a", display_name="a", version="4", path="inner")
        expected_component_b = Definition(type="component", name="b", display_name="ho ho", version="4", path="inner")

        result = self.convert(schema, path="inner")

        self.assertEqual(len(result), 3)

        key, definition = result[0]

        self.assertEqual(key, ("service", "strange"))
        self.assertEqual(definition, expected_service)

        key, definition = result[1]

        self.assertEqual(key, ("component", "strange", "a"))
        self.assertEqual(definition, expected_component_a)

        key, definition = result[2]

        self.assertEqual(key, ("component", "strange", "b"))
        self.assertEqual(definition, expected_component_b)

    def test_actions(self):
        raw = {
            "type": "service",
            "name": "strange",
            "version": "aa.fb",
            "actions": {
                "simple_job": {"script": "wow.yaml", "type": "job", "script_type": "ansible"},
                "simple_task": {
                    "type": "task",
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
                "jinja_config_job": {
                    "script": "haha.yaml",
                    "type": "job",
                    "script_type": "python",
                    "config_jinja": "./path/to/file.j2",
                },
                "jinja_scripts_task": {"type": "task", "scripts_jinja": "./path/to/file.j2"},
                "not_full_states": {
                    "script": "x.py",
                    "type": "job",
                    "script_type": "python",
                    "states": {"available": "any"},
                },
                "not_full_masking": {
                    "script": "x.py",
                    "type": "job",
                    "script_type": "python",
                    "masking": {"state": {"unavailable": ["o"]}},
                },
            },
        }
        schema = ServiceSchema.model_validate(raw)
        script_defaults = {
            "params": {},
            "allow_to_terminate": False,
            "state_on_fail": "",
            "multi_state_on_fail_set": [],
            "multi_state_on_fail_unset": [],
        }

        actions = [
            ActionDefinition(
                type="job",
                name="simple_job",
                display_name="simple_job",
                scripts=[
                    JobSpec(
                        name="simple_job",
                        display_name="simple_job",
                        script="wow.yaml",
                        script_type=ScriptType.ANSIBLE,
                        **script_defaults,
                    )
                ],
                available_at=ActionAvailability(states=[], multi_states="any"),
            ),
            ActionDefinition(
                type="task",
                name="simple_task",
                display_name="Awesome ma I",
                scripts=[
                    JobSpec(
                        name="first",
                        display_name="first",
                        script="inner/root.yaml",
                        script_type=ScriptType.ANSIBLE,
                        **script_defaults,
                    ),
                    JobSpec(
                        name="second",
                        display_name="Special",
                        script="another.yaml",
                        script_type=ScriptType.ANSIBLE,
                        **script_defaults,
                    ),
                ],
                available_at=ActionAvailability(states=[], multi_states="any"),
            ),
            ActionDefinition(
                type="job",
                name="jinja_config_job",
                display_name="jinja_config_job",
                scripts=[
                    JobSpec(
                        name="jinja_config_job",
                        display_name="jinja_config_job",
                        script="haha.yaml",
                        script_type=ScriptType.PYTHON,
                        **script_defaults,
                    )
                ],
                available_at=ActionAvailability(states=[], multi_states="any"),
                config_jinja="inner/path/to/file.j2",
            ),
            ActionDefinition(
                type="task",
                name="jinja_scripts_task",
                display_name="jinja_scripts_task",
                scripts=[],
                scripts_jinja="inner/path/to/file.j2",
                available_at=ActionAvailability(states=[], multi_states="any"),
            ),
            ActionDefinition(
                type="job",
                name="not_full_states",
                display_name="not_full_states",
                scripts=[
                    JobSpec(
                        name="not_full_states",
                        display_name="not_full_states",
                        script="x.py",
                        script_type=ScriptType.PYTHON,
                        **script_defaults,
                    )
                ],
                available_at=ActionAvailability(states="any", multi_states="any"),
            ),
            ActionDefinition(
                type="job",
                name="not_full_masking",
                display_name="not_full_masking",
                scripts=[
                    JobSpec(
                        name="not_full_masking",
                        display_name="not_full_masking",
                        script="x.py",
                        script_type=ScriptType.PYTHON,
                        **script_defaults,
                    )
                ],
                unavailable_at=ActionAvailability(states=["o"], multi_states=[]),
            ),
        ]

        (_, definition), *_ = self.convert(schema, path="inner")

        self.assertEqual(definition.actions, actions)

    def test_config(self):
        raw = {
            "type": "cluster",
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
        schema = ClusterSchema.model_validate(raw)

        s = ConfigParamPlainSpec
        cfg_val = {"group_customization": True}

        expected = ConfigDefinition(
            parameters={
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
            },
            default_values={
                ("g1", "b"): "haha",
                ("g2", "a"): ["u"],
                ("g2", "b"): {"k": "v"},
                ("g2", "whatshere"): "details/special.txt",
                ("b",): 43,
            },
            default_attrs={("g2",): {"active": True}},
        )

        (_, definition), *_ = self.convert(schema, "details")

        self.assertDictEqual(definition.config.default_attrs, expected.default_attrs)
        self.assertDictEqual(definition.config.default_values, expected.default_values)
        self.assertDictEqual(definition.config.parameters, expected.parameters)

    def test_upgrades(self):
        raw = {
            "type": "cluster",
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
        schema = ClusterSchema.model_validate(raw)

        upgrade_action_name = (
            "strange_aa.fb_community_upgrade_action-like_12.2.eee_strict_true-43.3_strict_true_"
            "editions-yet_custom_state_available-a_n_y_state_on_success-"
        )

        script_defaults = {
            "params": {},
            "allow_to_terminate": False,
            "state_on_fail": "",
            "multi_state_on_fail_set": [],
            "multi_state_on_fail_unset": [],
        }

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
                    type="task",
                    available_at=ActionAvailability(states="any", multi_states="any"),
                    scripts=[
                        JobSpec(
                            name="first",
                            display_name="first",
                            script="root.yaml",
                            script_type=ScriptType.ANSIBLE,
                            **script_defaults,
                        ),
                        JobSpec(
                            name="second",
                            display_name="Special",
                            script="bundle_switch",
                            script_type=ScriptType.INTERNAL,
                            **script_defaults,
                        ),
                    ],
                ),
            ),
        ]

        (_, definition), *_ = self.convert(schema, ".")

        self.assertEqual(definition.upgrades, upgrades)
