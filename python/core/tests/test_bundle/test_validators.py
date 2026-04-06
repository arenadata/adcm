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

from parameterized import parameterized

from core.bundle._definitions import ActionDefinition, Definition, DefinitionsMap, UpgradeDefinition
from core.bundle._errors import BundleValidationError
from core.bundle._validate import (
    check_actions,
    check_display_names_are_unique,
    check_templates_are_correct,
    check_upgrades,
)
from core.templates._types import (
    Jinja2Engine,
    Jinja2Template,
    PythonEngine,
    PythonTemplate,
    RenderEngineType,
    TemplateFile,
    TemplateFileWithEntrypoint,
)


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


class TestTemplatesPath(TestCase):
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

    @parameterized.expand(
        (f"{template_var_name}-{template_field}", template_var_name, template_field)
        for template_var_name in ("existing_jinja", "existing_python")
        for template_field in ("scripts_template", "wizard_template", "config_template")
    )
    def test_check_templates_are_correct(self, _, template_var_name: str, template_field: str):
        template = getattr(self, template_var_name)
        action = ActionDefinition(type="job", name="a", **{template_field: template})

        check_templates_are_correct(action=action, bundle_root=self.bundle_root)

    @parameterized.expand(
        (f"{template_var_name}-{template_field}", template_var_name, template_field)
        for template_var_name in ("absent_jinja", "absent_python", "incorrect_entrypoint_python")
        for template_field in ("scripts_template", "wizard_template", "config_template")
    )
    def test_check_templates_are_incorrect(self, _, template_var_name: str, template_field: str):
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
