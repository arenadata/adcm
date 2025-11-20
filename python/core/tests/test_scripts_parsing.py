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

from core.bundle_alt.errors import BundleParsingError
from core.bundle_alt.process import ScriptsConversionContext, parse_scripts
from core.bundle_alt.schema import DynamicScriptsSchema, WizardScriptsSchema

data = {
    "correct_script": {
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
    },
    "wrong_script_value_missing": {
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
    },
}


class TestScriptsRendering(TestCase):
    def test_parse_script_config_apply(self):
        expected_fragment = (
            "Errors found in definition of bundle entity:\n"
            " scripts\n"
            "  0\n"
            "   internal\n"
            "    config_apply\n"
            "     params\n"
            "      changes\n"
            "       1\n"
            "        parameters\n"
            "         0\n"
            "          value\n"
            "          | missing: Field required"
        )

        for case, case_data in data.items():
            with self.subTest(case):
                if case == "correct_script":
                    parse_scripts(
                        [data["correct_script"]],
                        context=ScriptsConversionContext(source_dir=Path(), action_allow_to_terminate=True),
                        schema=DynamicScriptsSchema,
                    )
                else:
                    with self.assertRaises(BundleParsingError) as cm:
                        parse_scripts(
                            [case_data],
                            context=ScriptsConversionContext(source_dir=Path(), action_allow_to_terminate=True),
                            schema=DynamicScriptsSchema,
                        )

                    err_msg = str(cm.exception)

                    self.assertIn(expected_fragment, err_msg)

    def test_parse_script_hc_apply(self):
        data = {"name": "hc_apply", "script": "hc_apply", "script_type": "internal"}

        with self.assertRaises(BundleParsingError) as error:
            parse_scripts(
                [data],
                context=ScriptsConversionContext(source_dir=Path(), action_allow_to_terminate=True),
                schema=WizardScriptsSchema,
            )

        expected_msg = (
            "Input tag 'hc_apply' found using 'script' does not match any of the expected tags:"
            " 'bundle_switch', 'bundle_revert', 'config_apply'"
        )
        self.assertIn(expected_msg, error.exception.message)
