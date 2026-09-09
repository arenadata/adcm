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

from collections.abc import Callable
from copy import deepcopy

from unittest_parametrize import param, parametrize

from core.config._config import detect_active_groups
from core.config._operations import (
    ValidationResult,
    apply_changes,
    prepare_config_for_ansible,
    prepare_config_from_defaults,
    validate_new_changes_in_main_configuration,
)
from core.config._spec import FullSpec
from core.config._spec.operations import detect_deactivated_parameters
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
    Selection,
    SimpleParameter,
    StringParameter,
    StructureParameter,
    VariantParameter,
    WritableRule,
)
from core.config._types import (
    Attributes,
    ChangeRequest,
    Configuration,
    Defaults,
)
from core.config._validate import AlwaysPassValidator, Validators, Violations
from core.result import Fail, Success
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
                extra=ExtraProperties(
                    display_name="act",
                    edit_rule=ReadOnlyRule(read_only=[READ_ONLY_STATUS]),
                ),
                activation=Activation(is_desyncable=False),
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

        self.validators = Validators(variant=ConstantVariantResolver(()), pattern=ConstantPatternValidator(True))

    def validate_changes(
        self,
        new: Configuration,
        previous: Configuration | None = None,
        specification: FullSpec | None = None,
        validators: Validators | None = None,
    ):
        active_groups = detect_active_groups(attributes=new.attributes)
        deactivated_parameters = detect_deactivated_parameters(
            spec=specification or self.simple_spec, active_groups=active_groups
        )
        return validate_new_changes_in_main_configuration(
            new=new,
            previous=previous or self.simple_config_empty,
            specification=specification or self.simple_spec,
            deactivated_parameters=deactivated_parameters,
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

    def test_change_readonly_parameter_success(self):
        name = name_id("deeply", "nested", "group", "value")

        read_only_any = "read_only-any", ReadOnlyRule(read_only="any")
        read_only_at_state = "read_only-at-state", ReadOnlyRule(read_only=["created"])
        writable_at_state = "writable-at-state", WritableRule(writable=["notexist"])

        old_config = deepcopy(self.simple_config_valid)
        old_config.values["deeply"] = {"nested": {"group": {"value": "kuku"}}}
        new_config = deepcopy(old_config)
        new_config.values["deeply"]["nested"]["group"]["value"] = "changed"

        for case_name, rule in (read_only_any, read_only_at_state, writable_at_state):
            with self.subTest(case_name):
                ro_parameter = StringParameter(identifier=name, extra=ExtraProperties(edit_rule=rule))
                specification = FullSpec.from_parameters(*self.simple_parameters, ro_parameter)

                result = self.validate_changes(new=new_config, previous=old_config, specification=specification)

                self.expect_success(result)

    def test_values_required_in_root_is_empty_fail(self):
        cases = self.prepare_empty_cases("justval")

        for case_name, parameter, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(parameter)
                config = Configuration(values={parameter.identifier.name: value})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=parameter, check_is="value", reason_contains="should not be empty"
                )

    def test_values_required_in_group_is_empty_fail(self):
        group = ParameterGroup(identifier=name_id("g"))
        cases = self.prepare_empty_cases(group.identifier.name, "justval")

        for case_name, parameter, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(group, parameter)
                config = Configuration(values={group.identifier.name: {parameter.identifier.name: value}})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=parameter, check_is="value", reason_contains="should not be empty"
                )

    def test_values_requied_in_deactivated_group_success(self):
        group = ParameterGroup(identifier=name_id("g"), activation=Activation())
        cases = self.prepare_empty_cases(group.identifier.name, "justval")

        for case_name, parameter, value in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(group, parameter)
                config = Configuration(
                    values={group.identifier.name: {parameter.identifier.name: value}},
                    attributes={group.identifier.full: Attributes(is_active=False)},
                )

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_success(result)

    def test_values_incorrect_type_fail(self):
        cases = self.prepare_invalid_type_cases()

        for case_name, parameter, value, type_in_error in cases:
            with self.subTest(case_name):
                specification = FullSpec.from_parameters(parameter)
                config = Configuration(values={parameter.identifier.name: value})

                result = self.validate_changes(new=config, previous=config, specification=specification)

                self.expect_exactly_one_violation_for(
                    result, param_is=parameter, check_is="value", reason_contains=f"should be of type {type_in_error}"
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
        params: tuple[SimpleParameter | ParameterGroup, ...],
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
            StringParameter(identifier=name_id("file_root"), as_file=True, supports_multiline=True),
            StringParameter(
                identifier=name_id("group", "nested_file"), as_file=True, is_secret=True, supports_multiline=True
            ),
            StringParameter(
                identifier=name_id("after_file"),
                as_file=True,
                ansible=AnsibleOptions(unsafe=False),
                supports_multiline=True,
            ),
            StringParameter(identifier=name_id("none_file"), as_file=True, supports_multiline=True),
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
            StringParameter(identifier=name_id("f"), as_file=True, supports_multiline=True),
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

    def test_selection_group_none(self):
        params = (
            StringParameter(identifier=name_id("plain")),
            ParameterGroup(identifier=name_id("sel_group"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("sel_group", "nested")),
            StringParameter(identifier=name_id("sel_group", "nested", "a")),
            ParameterGroup(identifier=name_id("group")),
            StringParameter(identifier=name_id("group", "a")),
        )
        values = {"plain": "aa", "sel_group": None, "group": {"a": "vv"}}
        expected_values = values

        self.expect_correct_values(params=params, values=values, expected_values=expected_values)

    def test_selection_group_value(self):
        params = (
            StringParameter(identifier=name_id("plain")),
            ParameterGroup(identifier=name_id("sel_group"), selection=Selection()),
            ParameterGroup(identifier=name_id("sel_group", "nested")),
            StringParameter(identifier=name_id("sel_group", "nested", "a")),
            ParameterGroup(identifier=name_id("group")),
            StringParameter(identifier=name_id("group", "a")),
        )
        values = {"plain": "aa", "sel_group": {"nested": {"a": {"b"}}}, "group": {"a": "vv"}}
        expected_values = values | {
            "sel_group": {"nested": {"a": {"b"}}, "_selection": "nested"},
        }

        self.expect_correct_values(params=params, values=values, expected_values=expected_values)

    def test_prepare_nested_activatable_groups(self):
        params = (
            ParameterGroup(identifier=name_id("a1"), activation=Activation()),
            ParameterGroup(identifier=name_id("a1", "a2"), activation=Activation()),
            StringParameter(identifier=name_id("a1", "a2", "p")),
            StringParameter(identifier=name_id("a1", "p")),
        )
        config = Configuration(
            values={"a1": {"a2": {"p": "uu"}, "p": "oo"}},
            attributes={"/a1": Attributes(is_active=False), "/a2": Attributes(is_active=False)},
        )
        expected_values = {"a1": None}

        specification = FullSpec.from_parameters(*params)
        result = prepare_config_for_ansible(
            configuration=config,
            specification=specification,
            construct_parameter_path=lambda x: x,
        )

        self.expect_success(result)
        self.assertDictEqual(result.value.values, expected_values)


class TestPrepareConfigFromDefaults(ConfigTestCase):
    def prepare_spec_and_raw_defaults(self, as_default: str | None) -> tuple[FullSpec, Defaults]:
        spec = FullSpec.from_parameters(
            StringParameter(identifier=name_id("g1")),
            ParameterGroup(identifier=name_id("g"), selection=Selection()),
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
        defaults = Defaults(
            values={"/g1": "1", "/g/g1/a": "2", "/g/g2/a": "3", "/g/act/a/b/c": "2", "/a": "4"},
            selection={"/g": as_default},
        )

        return spec, defaults

    def test_selection_group_with_default(self):
        spec, raw_defaults = self.prepare_spec_and_raw_defaults(as_default="g1")
        expected_values = {"g1": "1", "g": {"g1": {"a": "2"}}, "a": "4"}

        configuration = prepare_config_from_defaults(defaults=raw_defaults, specification=spec)

        self.assertDictEqual(configuration.values, expected_values)
        self.assertDictEqual(configuration.attributes, {})

    def test_selection_group_with_activatable_groups(self):
        spec, raw_defaults = self.prepare_spec_and_raw_defaults(as_default="act")
        expected_values = {"g1": "1", "g": {"act": {"a": {"b": {"c": "2"}}}}, "a": "4"}
        expected_attributes = {"/g/act/a/b": Attributes(is_active=False)}

        configuration = prepare_config_from_defaults(defaults=raw_defaults, specification=spec)

        self.assertDictEqual(configuration.values, expected_values)
        self.assertDictEqual(configuration.attributes, expected_attributes)

    def test_selection_group_without_default(self):
        spec, raw_defaults = self.prepare_spec_and_raw_defaults(as_default=None)
        expected_values = {"g1": "1", "g": None, "a": "4"}

        configuration = prepare_config_from_defaults(defaults=raw_defaults, specification=spec)

        self.assertDictEqual(configuration.values, expected_values)
        self.assertDictEqual(configuration.attributes, {})

    def test_adcm_7418_nested_selection_group_without_default(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("a"), selection=Selection()),
            ParameterGroup(identifier=name_id("a", "b")),
            ParameterGroup(identifier=name_id("a", "b", "c"), selection=Selection()),
            ParameterGroup(identifier=name_id("a", "b", "c", "d")),
            ParameterGroup(identifier=name_id("a", "b", "c", "d", "e")),
            StringParameter(identifier=name_id("a", "b", "c", "d", "e", "f")),
        )

        # we rely on safe retrieval of defaults in here, add actual defaults if implementation changed
        configuration = prepare_config_from_defaults(defaults=Defaults(), specification=spec)

        self.assertDictEqual(configuration.values, {"a": None})
        self.assertDictEqual(configuration.attributes, {})


class TestSelectionGroupApplyAndValidate(ConfigTestCase):
    def apply_changes(
        self, changes: list[ChangeRequest], config: Configuration, defaults: Defaults
    ) -> Success[tuple[Configuration, bool]] | Fail[Violations]:
        return apply_changes(changes=changes, configuration=config, defaults=defaults)

    def validate(
        self, new: Configuration, previous: Configuration, spec: FullSpec
    ) -> Success[ValidationResult] | Fail[Violations]:
        validators = Validators(variant=AlwaysPassValidator(), pattern=AlwaysPassValidator())
        return validate_new_changes_in_main_configuration(
            new=new, previous=previous, specification=spec, deactivated_parameters=set(), validators=validators
        )

    def build_spec_and_defaults_simple(self) -> tuple[FullSpec, Defaults]:
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("s", "g1")),
            StringParameter(identifier=name_id("s", "g1", "a")),
            ParameterGroup(identifier=name_id("s", "g2")),
            StringParameter(identifier=name_id("s", "g2", "b")),
        )
        defaults = Defaults(values={"/s/g1/a": "1", "/s/g2/b": "2"})

        return spec, defaults

    def build_spec_and_defaults_with_activatable(self) -> tuple[FullSpec, Defaults]:
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("s", "g1")),
            StringParameter(identifier=name_id("s", "g1", "a")),
            ParameterGroup(identifier=name_id("s", "g1", "act1"), activation=Activation()),
            StringParameter(identifier=name_id("s", "g1", "act1", "v")),
            ParameterGroup(identifier=name_id("s", "g2")),
            StringParameter(identifier=name_id("s", "g2", "b")),
            ParameterGroup(identifier=name_id("s", "g2", "act2"), activation=Activation()),
            StringParameter(identifier=name_id("s", "g2", "act2", "v")),
        )
        defaults = Defaults(
            values={"/s/g1/a": "1", "/s/g1/act1/v": "1v", "/s/g2/b": "2", "/s/g2/act2/v": "2v"},
            activation={"/s/g1/act1": False, "/s/g2/act2": True},
        )

        return spec, defaults

    def assert_success_on_apply_and_validate(
        self,
        changes: list[ChangeRequest],
        config: Configuration,
        spec: FullSpec,
        defaults: Defaults,
        expected_config: Configuration,
    ) -> None:
        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        new_config, _ = self.expect_success(apply_result).value

        self.assertDictEqual(new_config.values, expected_config.values)
        self.assertDictEqual(new_config.attributes, expected_config.attributes)

        validate_result = self.validate(new=new_config, previous=config, spec=spec)

        self.expect_success(validate_result)

    def build_spec_and_defaults_with_nested_selection(self) -> tuple[FullSpec, Defaults]:
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("s", "g1")),
            ParameterGroup(identifier=name_id("s", "g1", "inner"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i1")),
            StringParameter(identifier=name_id("s", "g1", "inner", "i1", "v")),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i2")),
            StringParameter(identifier=name_id("s", "g1", "inner", "i2", "v")),
            ParameterGroup(identifier=name_id("s", "g2")),
            StringParameter(identifier=name_id("s", "g2", "b")),
        )
        defaults = Defaults(
            values={"/s/g1/inner/i1/v": "1", "/s/g1/inner/i2/v": "2", "/s/g2/b": "b"},
            selection={"/s": "g2", "/s/g1/inner": "i1"},
        )

        return spec, defaults

    def build_spec_and_defaults_with_activatable_in_nested_selection(self) -> tuple[FullSpec, Defaults]:
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("s", "g1")),
            ParameterGroup(identifier=name_id("s", "g1", "inner"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i1")),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i1", "act1"), activation=Activation()),
            StringParameter(identifier=name_id("s", "g1", "inner", "i1", "act1", "v")),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i2")),
            ParameterGroup(identifier=name_id("s", "g1", "inner", "i2", "act2"), activation=Activation()),
            StringParameter(identifier=name_id("s", "g1", "inner", "i2", "act2", "v")),
            ParameterGroup(identifier=name_id("s", "g2")),
            StringParameter(identifier=name_id("s", "g2", "b")),
        )
        defaults = Defaults(
            values={"/s/g1/inner/i1/act1/v": "1", "/s/g1/inner/i2/act2/v": "2", "/s/g2/b": "b"},
            selection={"/s": "g2", "/s/g1/inner": "i1"},
            activation={"/s/g1/inner/i1/act1": True, "/s/g1/inner/i2/act2": False},
        )

        return spec, defaults

    def test_switch_to_group_with_nested_selection_sets_attributes_of_default_option_only(self):
        spec, defaults = self.build_spec_and_defaults_with_activatable_in_nested_selection()
        config = Configuration(values={"s": {"g2": {"b": "b"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        # activatable group of non-default option of nested selection group isn't part of configuration,
        # so it should have no attributes
        expected_config = Configuration(
            values={"s": {"g1": {"inner": {"i1": {"act1": {"v": "1"}}}}}},
            attributes={"/s/g1/inner/i1/act1": Attributes(is_active=True)},
        )

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_switch_to_group_with_nested_selection_takes_its_default_option_only(self):
        spec, defaults = self.build_spec_and_defaults_with_nested_selection()
        config = Configuration(values={"s": {"g2": {"b": "b"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        # only default option of nested selection group should be there, not all of them
        expected_config = Configuration(values={"s": {"g1": {"inner": {"i1": {"v": "1"}}}}})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_switch_to_group_with_nested_selection_without_default_option(self):
        spec, defaults = self.build_spec_and_defaults_with_nested_selection()
        defaults.selection["/s/g1/inner"] = None
        config = Configuration(values={"s": {"g2": {"b": "b"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        expected_config = Configuration(values={"s": {"g1": {"inner": None}}})

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        new_config, _ = self.expect_success(apply_result).value
        self.assertDictEqual(new_config.values, expected_config.values)

    def test_from_none_to_valid_defaults(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": None})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g2")]

        expected_config = Configuration(values={"s": {"g2": {"b": "2"}}})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_from_another_group_to_valid_defaults(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g2")]

        expected_config = Configuration(values={"s": {"g2": {"b": "2"}}})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_from_same_group_no_changes(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        expected_config = config

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_to_none(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value=None)]

        expected_config = Configuration(values={"s": None})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_set_value_and_changing_group(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [
            ChangeRequest.for_value(name="/s/g2/b", value="40"),
            ChangeRequest.for_group_selection(name="/s", value="g2"),
        ]

        expected_config = Configuration(values={"s": {"g2": {"b": "40"}}})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_change_group_and_set_value_when_nones_in_defaults(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("s", "g1")),
            StringParameter(identifier=name_id("s", "g1", "a")),
            StringParameter(identifier=name_id("s", "g1", "c"), is_required=False),
            ParameterGroup(identifier=name_id("s", "g2")),
            StringParameter(identifier=name_id("s", "g2", "b")),
        )
        defaults = Defaults(values={"/s/g1/a": "1", "/s/g1/c": None, "/s/g2/b": "2"})
        config = Configuration(values={"s": {"g2": {"b": "4"}}})
        changes = [
            ChangeRequest.for_group_selection(name="/s", value="g1"),
            ChangeRequest.for_value(name="/s/g1/a", value="40"),
        ]

        expected_config = Configuration(values={"s": {"g1": {"a": "40", "c": None}}})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_non_existent_group_becomes_none_and_fails(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "g1")),
            StringParameter(identifier=name_id("s", "g1", "v")),
        )
        defaults = Defaults(values={"/s/g1/v": "a"})
        config = Configuration(values={"s": {"g1": {"v": "4"}}})
        changes = [
            ChangeRequest.for_group_selection(name="/s", value="notexist"),
        ]

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        new_config, _ = self.expect_success(apply_result).value
        self.assertEqual(new_config.values, {"s": {"notexist": {}}})

        validate_result = self.validate(new=new_config, previous=config, spec=spec)

        self.expect_exactly_one_violation_for(
            validate_result, param_is="/s/notexist", check_is="structure", reason_contains="value is unexpected"
        )

    def test_change_value_in_unpicked_group_fails(self):
        defaults = Defaults(values={"/s/sg1/sv": "a", "/s/sg2/sv": "b"})
        config = Configuration(values={"s": {"sg1": {"sv": "4"}}})
        changes = [
            ChangeRequest.for_value(name="/s/sg1/sv", value="else"),
            ChangeRequest.for_value(name="/s/sg2/sv", value="something"),
            ChangeRequest.for_group_selection(name="/s", value="sg2"),
        ]

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        self.expect_exactly_one_violation_for(
            apply_result, param_is="/s/sg1/sv", check_is="structure", reason_contains="no such key"
        )

    @parametrize(
        ("config", "switch_to", "expected_config"),
        [
            param(
                Configuration(
                    values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
                    attributes={"/s/g1/act1": Attributes(is_active=True)},
                ),
                "g2",
                Configuration(
                    values={"s": {"g2": {"b": "2", "act2": {"v": "2v"}}}},
                    attributes={"/s/g2/act2": Attributes(is_active=True)},
                ),
                id="from_another_group",
            ),
            param(
                Configuration(values={"s": None}),
                "g1",
                Configuration(
                    values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
                    attributes={"/s/g1/act1": Attributes(is_active=False)},
                ),
                id="from_none",
            ),
        ],
    )
    def test_switch_group_sets_attributes_of_new_group_from_defaults(
        self, config: Configuration, switch_to: str, expected_config: Configuration
    ):
        spec, defaults = self.build_spec_and_defaults_with_activatable()
        changes = [ChangeRequest.for_group_selection(name="/s", value=switch_to)]

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_switch_group_to_none_removes_attributes_of_previous_group(self):
        spec, defaults = self.build_spec_and_defaults_with_activatable()
        config = Configuration(
            values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
            attributes={"/s/g1/act1": Attributes(is_active=True)},
        )
        changes = [ChangeRequest.for_group_selection(name="/s", value=None)]

        expected_config = Configuration(values={"s": None}, attributes={})

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_switch_group_to_same_one_keeps_attributes(self):
        spec, defaults = self.build_spec_and_defaults_with_activatable()
        config = Configuration(
            values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
            attributes={"/s/g1/act1": Attributes(is_active=True)},
        )
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        expected_config = config

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )

    def test_set_same_value_is_not_a_change(self):
        spec, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [ChangeRequest.for_value(name="/s/g1/a", value="4")]

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        new_config, has_changed = self.expect_success(apply_result).value
        self.assertFalse(has_changed)
        self.assertDictEqual(new_config.values, config.values)

        self.expect_success(self.validate(new=new_config, previous=config, spec=spec))

    def test_non_string_selection_value_is_not_supported(self):
        _, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": {"g1": {"a": "4"}}})
        changes = [ChangeRequest.for_group_selection(name="/s", value=1)]

        with self.assertRaises(TypeError):
            self.apply_changes(changes=changes, config=config, defaults=defaults)

    def test_selection_change_of_non_group_value_is_not_supported(self):
        _, defaults = self.build_spec_and_defaults_simple()
        config = Configuration(values={"s": "not a group"})
        changes = [ChangeRequest.for_group_selection(name="/s", value="g1")]

        with self.assertRaises(TypeError):
            self.apply_changes(changes=changes, config=config, defaults=defaults)

    def test_change_activation_of_absent_group_fails(self):
        _, defaults = self.build_spec_and_defaults_with_activatable()
        config = Configuration(
            values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
            attributes={"/s/g1/act1": Attributes(is_active=True)},
        )
        changes = [ChangeRequest.for_activation_attribute(name="/s/g2/act2", value=True)]

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        self.expect_exactly_one_violation_for(
            apply_result, param_is="/s/g2/act2", check_is="structure", reason_contains="no such key"
        )

    def test_change_activation_to_same_value_is_not_a_change(self):
        _, defaults = self.build_spec_and_defaults_with_activatable()
        config = Configuration(
            values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
            attributes={"/s/g1/act1": Attributes(is_active=True)},
        )
        changes = [ChangeRequest.for_activation_attribute(name="/s/g1/act1", value=True)]

        apply_result = self.apply_changes(changes=changes, config=config, defaults=defaults)

        _, has_changed = self.expect_success(apply_result).value
        self.assertFalse(has_changed)

    def test_switch_group_and_change_activation_of_new_group(self):
        spec, defaults = self.build_spec_and_defaults_with_activatable()
        config = Configuration(
            values={"s": {"g1": {"a": "1", "act1": {"v": "1v"}}}},
            attributes={"/s/g1/act1": Attributes(is_active=True)},
        )
        changes = [
            ChangeRequest.for_group_selection(name="/s", value="g2"),
            ChangeRequest.for_activation_attribute(name="/s/g2/act2", value=False),
        ]

        expected_config = Configuration(
            values={"s": {"g2": {"b": "2", "act2": {"v": "2v"}}}},
            attributes={"/s/g2/act2": Attributes(is_active=False)},
        )

        self.assert_success_on_apply_and_validate(
            changes=changes, config=config, spec=spec, defaults=defaults, expected_config=expected_config
        )
