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
from typing import Callable

from core.config._operations import prepare_config_for_ansible, validate_new_changes_in_main_configuration
from core.config._spec import FullSpec
from core.config._spec.parameters import (
    Activation,
    AnsibleOptions,
    BooleanParameter,
    ExtraProperties,
    JSONParameter,
    ListParameter,
    MapParameter,
    NumberParameter,
    OptionParameter,
    ParameterGroup,
    ReadOnlyRule,
    SimpleParameter,
    StringParameter,
    StructureParameter,
    VariantParameter,
    WritableRule,
)
from core.config._types import Attributes, ConfigOwnerObjectInfo, Configuration
from core.config._validate import Validators
from core.tests.test_config.utils import (
    READ_ONLY_STATUS,
    ConfigTestCase,
    ConstantPatternValidator,
    ConstantVariantResolver,
    name_id,
)

# todo add cases for sync checks, have a feeling there'll be more logic for changes that exists at the moment


class TestValidateNewChangesInMainConfiguration(ConfigTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.simple_parameters = (
            StringParameter(identifier=name_id("plain")),
            ParameterGroup(
                identifier=name_id("group"),
                extra=ExtraProperties(display_name="group"),
                activation=None,
            ),
            ListParameter(identifier=name_id("group", "nested")),
            StringParameter(identifier=name_id("group", "another"), pattern=r"eq-\d{4}"),
            ParameterGroup(
                identifier=name_id("act"),
                extra=ExtraProperties(display_name="act"),
                activation=Activation(
                    edit_rule=ReadOnlyRule(read_only=[READ_ONLY_STATUS]),
                    is_desyncable=False,
                    is_active_by_default=True,
                ),
            ),
            MapParameter(identifier=name_id("act", "secrets"), is_secret=True),
            StringParameter(identifier=name_id("act", "file"), as_file=True, supports_multiline=True),
            NumberParameter(identifier=name_id("after"), is_float=True),
        )

        self.simple_spec = FullSpec.from_parameters(*self.simple_parameters)
        self.simple_config_empty = Configuration(
            values={
                "plain": None,
                "group": {"nested": None, "another": None},
                "act": {"secrets": None, "file": None},
                "after": None,
            },
            attributes={"act": Attributes(is_active=True)},
        )

        self.simple_config_valid = Configuration(
            values={
                "plain": "stuff",
                "group": {"nested": ["a", "b"], "another": "eq-4315"},
                "act": {
                    "secrets": {"k": "v"},
                    "file": "some\nmultiline\ncontent",
                },
                "after": 43.23,
            },
            attributes={
                "/act": Attributes(is_active=True),
            },
        )

        self.created_owner_info = ConfigOwnerObjectInfo(state="created")
        self.validators = Validators(variant=ConstantVariantResolver(()), pattern=ConstantPatternValidator(True))

    def validate_changes(
        self,
        new: Configuration,
        previous: Configuration | None = None,
        specification: FullSpec | None = None,
        validators: Validators | None = None,
    ):
        return validate_new_changes_in_main_configuration(
            new=new,
            previous=previous or self.simple_config_empty,
            specification=specification or self.simple_spec,
            owner_info=self.created_owner_info,
            validators=validators or self.validators,
        )

    def prepare_empty_cases(self, *names):
        root_identifier = name_id(*names)
        string_param = StringParameter(identifier=root_identifier)
        map_param = MapParameter(identifier=root_identifier)
        secretmap_param = MapParameter(identifier=root_identifier, is_secret=True)
        list_param = ListParameter(identifier=root_identifier)
        return (
            ("string-none", string_param, None),
            ("string-empty", string_param, ""),
            ("map-none", map_param, None),
            ("map-empty", map_param, {}),
            ("map-secret-none", secretmap_param, None),
            ("map-secret-empty", secretmap_param, {}),
            ("list-none", list_param, None),
            ("list-empty", list_param, []),
        )

    def prepare_invalid_type_cases(self):
        name = name_id("whoop")
        return (
            ("string", StringParameter(identifier=name), 2, "string"),
            ("number-int", NumberParameter(identifier=name, is_float=False), 4.3, "integer"),
            ("number-float", NumberParameter(identifier=name, is_float=True), "sdlkfj", "float"),
            ("map", MapParameter(identifier=name), [], "map"),
            ("list", ListParameter(identifier=name), {}, "list"),
            ("bool", BooleanParameter(identifier=name), 1, "boolean"),
        )

    def test_valid_config_success(self):
        result = self.validate_changes(new=self.simple_config_valid)

        self.expect_success(result)

    def test_missing_field_fail(self):
        name, full_name = self.get_name_and_full_name("after")

        changed_config = self.simple_config_valid
        changed_config.values.pop(name)

        result = self.validate_changes(new=changed_config)

        fail = self.expect_fail(result)
        self.assertEqual(len(fail.value), 1)
        violation = fail.value[0]
        self.assertEqual(violation.parameter, full_name)
        self.assertEqual(violation.check, "structure")
        self.assertIn("missing", violation.reason)

    def test_extra_field_fail(self):
        name, full_name = self.get_name_and_full_name("group", "notexist")

        changed_config = self.simple_config_valid
        changed_config.values["group"][name] = "something"

        result = self.validate_changes(new=changed_config)

        fail = self.expect_fail(result)
        self.assertEqual(len(fail.value), 1)
        violation = fail.value[0]
        self.assertEqual(violation.parameter, full_name)
        self.assertEqual(violation.check, "structure")
        self.assertIn("unexpected", violation.reason)

    def test_missing_attribute_fail(self):
        _, full_name = self.get_name_and_full_name("act")

        changed_config = self.simple_config_valid
        changed_config.attributes.pop(full_name)

        result = self.validate_changes(new=changed_config)

        fail = self.expect_fail(result)
        self.assertEqual(len(fail.value), 1)
        violation = fail.value[0]
        self.assertEqual(violation.parameter, full_name)
        self.assertEqual(violation.check, "attribute")
        self.assertIn("missing", violation.reason)

    def test_extra_attribute_fail(self):
        _, full_name = self.get_name_and_full_name("/notexist")

        changed_config = self.simple_config_valid
        changed_config.attributes[full_name] = Attributes(is_active=False)

        result = self.validate_changes(new=changed_config)

        fail = self.expect_fail(result)
        self.assertEqual(len(fail.value), 1)
        violation = fail.value[0]
        self.assertEqual(violation.parameter, full_name)
        self.assertEqual(violation.check, "attribute")
        self.assertIn("unexpected", violation.reason)

    def test_change_readonly_parameter_fail(self):
        name = name_id("deeply", "nested", "group", "value")

        read_only_any = "read_only-any", ReadOnlyRule(read_only="any")
        read_only_at_state = "read_only-at-state", ReadOnlyRule(read_only=[self.created_owner_info.state])
        writable_at_state = "writable-at-state", WritableRule(writable=["notexist"])

        old_config = deepcopy(self.simple_config_valid)
        old_config.values["deeply"] = {"nested": {"group": {"value": "kuku"}}}
        new_config = deepcopy(old_config)
        new_config.values["deeply"]["nested"]["group"]["value"] = "changed"

        for case_name, rule in (read_only_any, read_only_at_state, writable_at_state):
            with self.subTest(case_name):
                ro_parameter = StringParameter(identifier=name, edit_rule=rule)
                specification = FullSpec.from_parameters(*self.simple_parameters, ro_parameter)

                result = self.validate_changes(new=new_config, previous=old_config, specification=specification)

                violation = self.expect_exactly_one_violation(result)
                self.assertEqual(violation.parameter, ro_parameter.identifier.full)
                self.assertEqual(violation.check, "change")
                self.assertIn("is read-only", violation.reason)

    def test_values_required_in_root_is_empty_fail(self):
        cases = self.prepare_empty_cases("justval")

        for case_name, param, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(param)
                config = Configuration(values={param.identifier.name: value})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=param, check_is="value", reason_contains="should not be empty"
                )

    def test_values_required_in_group_is_empty_fail(self):
        group = ParameterGroup(identifier=name_id("g"))
        cases = self.prepare_empty_cases(group.identifier.name, "justval")

        for case_name, param, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(group, param)
                config = Configuration(values={group.identifier.name: {param.identifier.name: value}})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=param, check_is="value", reason_contains="should not be empty"
                )

    def test_values_requied_in_deactivated_group_success(self):
        group = ParameterGroup(identifier=name_id("g"), activation=Activation())
        cases = self.prepare_empty_cases(group.identifier.name, "justval")

        for case_name, param, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(group, param)
                config = Configuration(
                    values={group.identifier.name: {param.identifier.name: value}},
                    attributes={group.identifier.full: Attributes(is_active=False)},
                )

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_success(result)

    def test_values_incorrect_type_fail(self):
        cases = self.prepare_invalid_type_cases()

        for case_name, param, value, type_in_error in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(param)
                config = Configuration(values={param.identifier.name: value})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=param, check_is="value", reason_contains=f"should be of type {type_in_error}"
                )

    def test_string_pattern_mismatch_fail(self):
        pattern = r"\d+"
        param = StringParameter(identifier=name_id("plain"), pattern=pattern)
        validators = Validators(variant=ConstantVariantResolver(()), pattern=ConstantPatternValidator(False))
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: "anything"})

        result = self.validate_changes(new=config, previous=config, specification=specification, validators=validators)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains=f'does not match pattern: "{pattern}"'
        )

    def test_number_max_violation_fail(self):
        param = NumberParameter(is_float=False, identifier=name_id("inside", "plain"), max=4)
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={"inside": {param.identifier.name: 5}})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="should be lesser than"
        )

    def test_number_min_violation_fail(self):
        param = NumberParameter(is_float=True, identifier=name_id("inside", "plain"), min=2.3)
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={"inside": {param.identifier.name: 2.29}})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="should be greater than"
        )

    def test_map_non_str_keys_fail(self):
        param = MapParameter(identifier=name_id("plain"))
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: {1: "a"}})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="all keys and values must be strings"
        )

    def test_map_non_str_values_fail(self):
        param = MapParameter(identifier=name_id("inside", "plain"), is_secret=True)
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={"inside": {param.identifier.name: {"a": 1}}})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="all keys and values must be strings"
        )

    def test_list_non_str_entries_fail(self):
        param = ListParameter(identifier=name_id("plain"))
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: [43, "sdf"]})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="all entries must be strings"
        )

    def test_option_wrong_value_fail(self):
        param = OptionParameter(identifier=name_id("plain"), options={"1": 43})
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: "23"})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="not in option list"
        )

    def test_structure_mismatch_fail(self):
        schema = {
            "root": {"match": "dict", "default_item": "string"},
            "string": {"match": "string"},
        }
        param = StructureParameter(identifier=name_id("plain"), yspec=schema)
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: {"ao": 1}})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(result, param_is=param, check_is="value", reason_contains="yspec error")

    def test_variant_wrong_value_fail(self):
        param = VariantParameter(identifier=name_id("plain"), is_strict=True, source="inline", payload={})
        specification = FullSpec.from_parameters(param)
        config = Configuration(values={param.identifier.name: "23"})

        result = self.validate_changes(new=config, previous=config, specification=specification)

        self.expect_exactly_one_violation_for(
            result, param_is=param, check_is="value", reason_contains="not in variant list"
        )

    def test_deactivated_field_changed_success(self):
        new_config = self.simple_config_valid
        new_config.values["act"]["secrets"] = {"another": "one"}
        new_config.attributes["/act"].is_active = False

        result = self.validate_changes(new=new_config)

        self.expect_success(result)


class TestPrepareConfigForAnsible(ConfigTestCase):
    def expect_correct_values(
        self,
        params: tuple[SimpleParameter, ...],
        values: dict,
        expected_values: dict,
        path_constructor: Callable | None = None,
    ):
        specification = FullSpec.from_parameters(*params)
        result = prepare_config_for_ansible(
            configuration=Configuration(values=values),
            specification=specification,
            construct_parameter_path=path_constructor or (lambda x: x),
        )

        self.expect_success(result)
        self.assertDictEqual(result.value.values, expected_values)

    def test_files_as_paths(self):
        prefix = "cluster.1"
        params = (
            StringParameter(identifier=name_id("plain"), as_file=False),
            StringParameter(identifier=name_id("file_root"), as_file=True),
            StringParameter(identifier=name_id("group", "nested_file"), as_file=True, is_secret=True),
            StringParameter(identifier=name_id("after_file"), as_file=True, ansible=AnsibleOptions(unsafe=True)),
            StringParameter(identifier=name_id("none_file"), as_file=True),
        )
        values = {
            "plain": "a",
            "file_root": "fr",
            "group": {"nested_file": "gnf"},
            "after_file": "af",
            "none_file": None,
        }
        expected_values = {
            "plain": "a",
            "file_root": f"{prefix}.file_root.",
            "group": {"nested_file": f"{prefix}.group.nested_file"},
            "after_file": f"{prefix}.after_file.",
            "none_file": None,
        }

        self.expect_correct_values(
            params=params, values=values, expected_values=expected_values, path_constructor=lambda x: f"{prefix}.{x}"
        )

    def test_secrets_in_ansible_vault_dict(self):
        ansible_vault = "__ansible_vault"
        params = (
            StringParameter(identifier=name_id("plain-s"), is_secret=False),
            StringParameter(identifier=name_id("secret-s"), is_secret=True),
            StringParameter(identifier=name_id("group", "plain-s"), is_secret=False),
            StringParameter(identifier=name_id("group", "secret-s"), is_secret=True),
            StringParameter(identifier=name_id("group", "secret-none"), is_secret=True),
            MapParameter(identifier=name_id("group", "nested", "plain-d"), is_secret=False),
            MapParameter(identifier=name_id("group", "nested", "secret-d"), is_secret=True),
            MapParameter(identifier=name_id("group", "nested", "secret-none"), is_secret=True),
            MapParameter(identifier=name_id("plain-d"), is_secret=False),
            MapParameter(identifier=name_id("secret-d"), is_secret=True),
        )
        values = {
            "plain-s": "ps",
            "secret-s": "ss",
            "group": {
                "plain-s": "gps",
                "secret-s": "gss",
                "secret-none": None,
                "nested": {
                    "plain-d": {"k": "gnpd"},
                    "secret-d": {"k": "gnsd"},
                    "secret-none": None,
                },
            },
            "plain-d": {"k": "pd"},
            "secret-d": {"k": "sd"},
        }
        expected_values = {
            "plain-s": "ps",
            "secret-s": {ansible_vault: "ss"},
            "group": {
                "plain-s": "gps",
                "secret-s": {ansible_vault: "gss"},
                "secret-none": None,
                "nested": {
                    "plain-d": {"k": "gnpd"},
                    "secret-d": {"k": {ansible_vault: "gnsd"}},
                    "secret-none": None,
                },
            },
            "plain-d": {"k": "pd"},
            "secret-d": {"k": {ansible_vault: "sd"}},
        }

        self.expect_correct_values(params=params, values=values, expected_values=expected_values)

    def test_default_for_none_map_list(self):
        params = (
            StringParameter(identifier=name_id("s")),
            NumberParameter(identifier=name_id("n"), is_float=False),
            JSONParameter(identifier=name_id("j")),
            MapParameter(identifier=name_id("m")),
            MapParameter(identifier=name_id("sm"), is_secret=True),
            ListParameter(identifier=name_id("l")),
            StringParameter(identifier=name_id("f"), as_file=True),
            VariantParameter(identifier=name_id("v"), is_strict=True, payload={}, source="builtin"),
            OptionParameter(identifier=name_id("o"), options={}),
        )

        values = {"s": None, "n": None, "j": None, "m": None, "sm": None, "l": None, "f": None, "v": None, "o": None}
        expected_values = values | {"m": {}, "l": []}

        self.expect_correct_values(params=params, values=values, expected_values=expected_values)

    def test_ansible_unsafe_str(self):
        ansible_unsafe = "__ansible_unsafe"
        params = (
            StringParameter(identifier=name_id("plain"), ansible=AnsibleOptions(unsafe=False)),
            StringParameter(identifier=name_id("group", "nested", "uns"), ansible=AnsibleOptions(unsafe=True)),
            StringParameter(identifier=name_id("group", "uns-none"), ansible=AnsibleOptions(unsafe=True)),
        )
        values = {
            "plain": "aa",
            "group": {"nested": {"uns": "f"}, "uns-none": None},
        }
        expected_values = {
            "plain": "aa",
            "group": {"nested": {"uns": {ansible_unsafe: "f"}}, "uns-none": None},
        }

        self.expect_correct_values(params=params, values=values, expected_values=expected_values)
