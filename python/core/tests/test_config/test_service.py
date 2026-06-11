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

from copy import deepcopy
from unittest import TestCase

from core.config import ConfigOperationError
from core.config._spec import FullSpec
from core.config._spec.parameters import (
    BooleanParameter,
    ExtraProperties,
    ListParameter,
    NumberParameter,
    ParameterGroup,
)
from core.config._types import ChangeRequest, Configuration, Defaults
from core.tests.doubles.config import build_config_service_with_fakes
from core.tests.test_config.utils import name_id
from core.types import ADCMCoreType, CoreObjectDescriptor


class TestValidationErrorMessages(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.config_service, _ = build_config_service_with_fakes()
        self.owner = CoreObjectDescriptor(id=1, type=ADCMCoreType.SERVICE)
        self.specification = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("group"), extra=ExtraProperties(display_name="Test Group")),
            NumberParameter(
                identifier=name_id("group", "integer"),
                is_float=False,
                min=10,
                extra=ExtraProperties(display_name="Test Integer"),
            ),
            BooleanParameter(
                identifier=name_id("group", "enabled"), extra=ExtraProperties(display_name="Test Enabled")
            ),
            ParameterGroup(
                identifier=name_id("group", "nested"),
                extra=ExtraProperties(display_name="Nested Group"),
            ),
            ListParameter(
                identifier=name_id("group", "nested", "items"),
                extra=ExtraProperties(display_name="Test Items"),
            ),
        )
        self.valid_configuration = Configuration(
            values={"group": {"integer": 10, "enabled": True, "nested": {"items": ["first"]}}}
        )
        self.expected_message_template = (
            "Configuration doesn't match specification. Following violations detected:\n{violation}"
        )

    def get_config_with_wrong_params(self, wrong_params: dict) -> Configuration:
        values = deepcopy(self.valid_configuration.values)
        values["group"] |= wrong_params

        return Configuration(values=values)

    def test_prepare_action_configuration_err_with_full_display_name(self):
        wrong_param = {"enabled": "yes"}
        invalid_configuration = self.get_config_with_wrong_params(wrong_params=wrong_param)
        expected_param_name = "/Test Group/Test Enabled"
        violation = f"- {expected_param_name} [value]: should be of type boolean"

        with self.assertRaises(ConfigOperationError) as err:
            self.config_service.prepare_action_configuration(
                configuration=invalid_configuration,
                specification=self.specification,
                owner=self.owner,
                owner_configuration=self.valid_configuration,
            )

        self.assertEqual(str(err.exception), self.expected_message_template.format(violation=violation))

    def test_prepare_new_configuration_from_changes_err_with_full_display_name(self):
        changes = [ChangeRequest.for_value(name="/group/nested/items", value="not-list")]
        expected_param_name = "/Test Group/Nested Group/Test Items"
        violation = f"- {expected_param_name} [value]: should be of type list"

        with self.assertRaises(ConfigOperationError) as err:
            self.config_service.prepare_new_configuration_from_changes(
                changes=changes,
                configuration=self.valid_configuration,
                specification=self.specification,
                defaults=Defaults(),
                owner=self.owner,
            )

        self.assertEqual(str(err.exception), self.expected_message_template.format(violation=violation))

    def test_prepare_new_configuration_err_with_full_display_name(self):
        wrong_param = {"integer": 5, "enabled": "yes"}
        invalid_configuration = self.get_config_with_wrong_params(wrong_params=wrong_param)
        expected_name_integer = "/Test Group/Test Integer"
        expected_name_bool = "/Test Group/Test Enabled"

        expected_message = self.expected_message_template.format(
            violation=(
                f"- {expected_name_integer} [value]: should be greater than 10\n"
                f"- {expected_name_bool} [value]: should be of type boolean"
            )
        )

        with self.assertRaises(ConfigOperationError) as err:
            self.config_service.prepare_new_configuration(
                new=invalid_configuration,
                previous=self.valid_configuration,
                specification=self.specification,
                owner=self.owner,
            )

        self.assertEqual(str(err.exception), expected_message)
