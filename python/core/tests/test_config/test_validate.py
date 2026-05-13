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


from core.config._spec import FullSpec
from core.config._spec.parameters import (
    Activation,
    ParameterGroup,
    Selection,
    StringParameter,
)
from core.config._types import Attributes, Configuration, ConfigValues
from core.config._validate import Violations, validate_configuration_is_consistent
from core.result import Fail, Success
from core.tests.test_config.utils import (
    ConfigTestCase,
    name_id,
)


class TestValidateConfigurationIsConsistent(ConfigTestCase):
    def prepare_spec_and_values_without_group(self, is_required: bool) -> tuple[FullSpec, ConfigValues]:
        spec = FullSpec.from_parameters(
            StringParameter(identifier=name_id("g1")),
            ParameterGroup(identifier=name_id("g"), selection=Selection(is_required=is_required)),
            ParameterGroup(identifier=name_id("g", "g1")),
            StringParameter(identifier=name_id("g", "g1", "a")),
            ParameterGroup(identifier=name_id("g", "g2")),
            StringParameter(identifier=name_id("g", "g2", "a")),
            ParameterGroup(identifier=name_id("g", "act")),
            ParameterGroup(identifier=name_id("g", "act", "a")),
            ParameterGroup(identifier=name_id("g", "act", "a", "b"), activation=Activation()),
            StringParameter(identifier=name_id("g", "act", "a", "b", "c")),
            StringParameter(identifier=name_id("a")),
        )
        values_without_group = {"g1": "1", "a": "4"}

        return spec, values_without_group

    def prepare_spec_and_config_selection_in_activatable(self) -> tuple[FullSpec, Configuration]:
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("a"), activation=Activation()),
            ParameterGroup(identifier=name_id("a", "g"), selection=Selection()),
            ParameterGroup(identifier=name_id("a", "g", "g1")),
            StringParameter(identifier=name_id("a", "g", "g1", "v")),
            ParameterGroup(identifier=name_id("a", "g", "g2")),
            ParameterGroup(identifier=name_id("a", "g", "g2", "s"), selection=Selection()),
            ParameterGroup(identifier=name_id("a", "g", "g2", "s", "s1")),
        )
        config = Configuration(values={"a": {"g": None}}, attributes={"/a": Attributes(is_active=False)})

        return spec, config

    def validate(self, configuration: Configuration, specification: FullSpec) -> Success[None] | Fail[Violations]:
        return validate_configuration_is_consistent(configuration=configuration, specification=specification)

    def test_none_value_for_non_required_success(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=False)
        config = Configuration(values=values | {"g": None})

        result = self.validate(config, spec)

        self.expect_success(result)

    def test_none_value_for_required_fail(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=True)
        config = Configuration(values=values | {"g": None})

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is=spec.groups["/g"], check_is="structure", reason_contains="incorrect group value type"
        )

    def test_default_value_for_required_success(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=True)
        config = Configuration(values=values | {"g": {"g1": {"a": "v"}}})

        result = self.validate(config, spec)

        self.expect_success(result)

    def test_plain_value_fail(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=False)
        config = Configuration(values=values | {"g": 1})

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is=spec.groups["/g"], check_is="structure", reason_contains=""
        )

    def test_different_groups_in_values_and_attributes_fail(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=True)
        synced_attributes = Attributes(is_synced=True)
        config = Configuration(
            values=values | {"g": {"g2": {"a": "v"}}},
            attributes={"/g/g1/a": synced_attributes} | {f"/{k}": synced_attributes for k in values},
        )

        result = self.validate(config, spec)

        violations = self.expect_fail(result).value
        self.assertEqual(len(violations), 2)
        violations_map = {v.parameter: v for v in violations}
        self.assertSetEqual(set(violations_map.keys()), {"/g/g1/a", "/g/g2/a"})
        self.assertEqual(violations_map["/g/g1/a"].check, "attribute")
        self.assertIn("unexpected", violations_map["/g/g1/a"].reason)
        self.assertIn("missing", violations_map["/g/g2/a"].reason)

    def test_no_selection_in_deactivated(self):
        spec, config = self.prepare_spec_and_config_selection_in_activatable()

        result = self.validate(config, spec)

        self.expect_success(result)

    def test_no_selection_in_activated(self):
        spec, config = self.prepare_spec_and_config_selection_in_activatable()
        config.attributes["/a"].is_active = True

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is="/a/g", check_is="structure", reason_contains="expected dict"
        )

    def test_incorrect_value_for_selection_in_deactivated(self):
        spec, config = self.prepare_spec_and_config_selection_in_activatable()
        config.values["a"]["g"] = 1

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is="/a/g", check_is="structure", reason_contains="expected dict"
        )

    def test_deactivated_group_empty(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=False)
        config = Configuration(
            values=values | {"g": {"act": {"a": {"b": {}}}}}, attributes={"/g/act/a/b": Attributes(is_active=False)}
        )

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is="/g/act/a/b/c", check_is="structure", reason_contains="is missing"
        )

    def test_deactivated_group_none(self):
        spec, values = self.prepare_spec_and_values_without_group(is_required=False)
        config = Configuration(
            values=values | {"g": {"act": {"a": {"b": None}}}}, attributes={"/g/act/a/b": Attributes(is_active=False)}
        )

        result = self.validate(config, spec)

        self.expect_exactly_one_violation_for(
            result, param_is="/g/act/a/b", check_is="structure", reason_contains="expected dict"
        )
