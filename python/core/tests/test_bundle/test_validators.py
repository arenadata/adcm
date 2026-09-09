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
from unittest.mock import Mock, patch

from unittest_parametrize import ParametrizedTestCase, param, parametrize

from core import config
from core.action import JobSpec
from core.bundle._definitions import (
    ActionDefinition,
    ConfigDefinition,
    ConfigParamPlainSpec,
    Definition,
    DefinitionsMap,
    ImportDefinition,
    UpgradeDefinition,
)
from core.bundle._errors import BundleValidationError
from core.bundle._validate import (
    check_action_hc_acl_rules,
    check_actions,
    check_bound_to,
    check_bundle_switch_amount_for_upgrade_action,
    check_config_defaults,
    check_display_names_are_unique,
    check_exported_values_exists_in_config,
    check_import_defaults_exist_in_config,
    check_mm_host_action_is_allowed,
    check_requires,
    check_templates_are_correct,
    check_upgrades,
)
from core.constants import ADCM_HOST_TURN_OFF_MM_ACTION_NAME, ADCM_HOST_TURN_ON_MM_ACTION_NAME
from core.templates._types import (
    Jinja2Engine,
    Jinja2Template,
    PythonEngine,
    PythonTemplate,
    RenderEngineType,
    TemplateFile,
    TemplateFileWithEntrypoint,
)
from core.tests.doubles.config import build_config_service_with_fakes
from core.tests.test_config.utils import name_id

CLUSTER = "cluster"
SERVICE = "service"
COMPONENT = "component"


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


class TestCheckDisplayNamesAreUnique(TestCase):
    def test_component_in_different_services_named_as_service(self):
        definitions: DefinitionsMap = {
            ("service", "main"): Definition(type="service", name="main", version="4", display_name="main"),
            ("component", "main", "main"): Definition(type="component", name="main", version="4", display_name="main"),
            ("service", "another"): Definition(type="service", name="another", version="4", display_name="another"),
            ("component", "another", "main"): Definition(
                type="component", name="main", version="4", display_name="main"
            ),
        }

        check_display_names_are_unique(definitions)

    def test_duplicated_display_names_within_one_service(self):
        definitions: DefinitionsMap = {
            ("service", "main"): Definition(type="service", name="main", version="4", display_name="main"),
            ("component", "main", "main"): Definition(type="component", name="main", version="4", display_name="cool"),
            ("component", "main", "another"): Definition(
                type="component", name="another", version="4", display_name="cool"
            ),
        }

        with self.assertRaises(BundleValidationError, msg="Incorrect definition of component 'another'"):
            check_display_names_are_unique(definitions)


class TestTemplatesPath(ParametrizedTestCase, TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle_root = Path(__file__).parent / "files" / "scripts"

        cls.existing_jinja = Jinja2Template(
            engine=Jinja2Engine(type=RenderEngineType.JINJA2), file=TemplateFile(path=Path("exists.j2"))
        )
        cls.absent_jinja = Jinja2Template(
            engine=Jinja2Engine(type=RenderEngineType.JINJA2), file=TemplateFile(path=Path("notexist.j2"))
        )
        cls.existing_python = PythonTemplate(
            engine=PythonEngine(type=RenderEngineType.PYTHON),
            file=TemplateFileWithEntrypoint(path=Path("exists.py"), entrypoint="main"),
        )
        cls.absent_python = PythonTemplate(
            engine=PythonEngine(type=RenderEngineType.PYTHON),
            file=TemplateFileWithEntrypoint(path=Path("notexist.py"), entrypoint="main"),
        )
        cls.incorrect_entrypoint_python = PythonTemplate(
            engine=PythonEngine(type=RenderEngineType.PYTHON),
            file=TemplateFileWithEntrypoint(path=Path("notexist.py"), entrypoint="wrong"),
        )

    @parametrize(
        ("template_var_name", "template_field"),
        [
            param(template_var_name, template_field, id=f"{template_var_name}_{template_field}")
            for template_var_name in ("existing_jinja", "existing_python")
            for template_field in ("scripts_template", "wizard_template", "config_template")
        ],
    )
    def test_check_templates_are_correct(self, template_var_name: str, template_field: str):
        template = getattr(self, template_var_name)
        action = ActionDefinition(type="job", name="a", **{template_field: template})

        check_templates_are_correct(action=action, bundle_root=self.bundle_root)

    @parametrize(
        ("template_var_name", "template_field"),
        [
            param(template_var_name, template_field, id=f"{template_var_name}_{template_field}")
            for template_var_name in ("absent_jinja", "absent_python", "incorrect_entrypoint_python")
            for template_field in ("scripts_template", "wizard_template", "config_template")
        ],
    )
    def test_check_templates_are_incorrect(self, template_var_name: str, template_field: str):
        template = getattr(self, template_var_name)
        action = ActionDefinition(type="job", name="a", **{template_field: template})

        with self.assertRaises(BundleValidationError, msg="Incorrect template for *_template at"):
            check_templates_are_correct(action=action, bundle_root=self.bundle_root)

    @patch("core.bundle._validate.check_templates_are_correct")
    def test_adcm_7945_check_upgrades_calls_templates_check_on_action_with_scripts(
        self, check_jinja_templates_mock: Mock
    ):
        upgrade = UpgradeDefinition(
            name="correct_scripts_template",
            action=ActionDefinition(type="job", name="a", scripts_template=self.existing_jinja),
        )

        check_upgrades(upgrades=[upgrade], definitions={}, bundle_root=self.bundle_root)

        check_jinja_templates_mock.assert_called_once_with(action=upgrade.action, bundle_root=self.bundle_root)

    @patch("core.bundle._validate.check_templates_are_correct")
    def test_check_actions_calls_templates_check_on_action_with_scripts(self, check_jinja_templates_mock: Mock):
        action = ActionDefinition(type="job", name="a", scripts_template=self.existing_jinja)

        check_actions(actions=[action], bundle_root=self.bundle_root, definitions={}, definition_type="notimportant")

        check_jinja_templates_mock.assert_called_once_with(action=action, bundle_root=self.bundle_root)


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
        multiple_switch_err = 'with script_type "bundle_switch" must be unique'

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


class TestConfigErrorMessages(TestCase):
    def test_bundle_validate_error_message_with_full_display_name(self):
        expected_displ_name = "/Group/Test Int"
        min_value = 10
        tech_full_name = "/group/integer"

        group_param = config.spec.p.ParameterGroup(
            identifier=name_id("group"), extra=config.spec.p.ExtraProperties(display_name="Group")
        )
        param_with_wrong_default = config.spec.p.NumberParameter(
            identifier=name_id("group", "integer"),
            is_float=False,
            min=min_value,
            extra=config.spec.p.ExtraProperties(display_name="Test Int"),
        )
        specification = config.spec.FullSpec.from_parameters(group_param, param_with_wrong_default)

        wrong_default = config.Defaults(values={tech_full_name: 5})
        config_service, _ = build_config_service_with_fakes()

        with self.assertRaises(BundleValidationError) as err:
            check_config_defaults(specification=specification, defaults=wrong_default, config_service=config_service)

        self.assertEqual(
            f"object's defaults are invalid: - {expected_displ_name} [value]: should be greater than {min_value}",
            err.exception.message,
        )

    def test_validate_structure_schema_error_message_with_full_display_name(self):
        """
        Check messages from config._operations.validate_structure_parameters_schema.
        """

        expected_displ_name = "/Test Structure"
        param = config.spec.p.StructureParameter(
            identifier=name_id("structure"),
            yspec={},
            extra=config.spec.p.ExtraProperties(display_name="Test Structure"),
        )
        specification = config.spec.FullSpec.from_parameters(param)
        config_service, _ = build_config_service_with_fakes()
        config_service.yspec_schema = {
            "root": {"match": "dict", "required_items": ["root"]},
        }

        with self.assertRaises(BundleValidationError) as err:
            check_config_defaults(
                specification=specification, defaults=config.Defaults(), config_service=config_service
            )

        self.assertIn(
            f"object's defaults are invalid: - {expected_displ_name} [value]: yspec schema is incorrect:",
            err.exception.message,
        )
