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

"""
Cases of configuration adaptation to new specification (upgrade).

Cases are described in "configuration" terms rather than in specification ones:
each one is a plain dict of defaults (old and new), configuration before upgrade and expected result.
Specification is declared as a flat schema of full names, see `build_specification`.

All values are strings, so the only thing that matters about a value is where it came from:
`"old"` is a default of old bundle, `"new"` is a default of new one, `"custom"` is set by user.
"""

from typing import TypeAlias
from unittest import TestCase
import sys
import doctest

from unittest_parametrize import param, parametrize

from core.config._operations import adapt_configuration_for_new_specification
from core.config._spec import FullSpec
from core.config._spec.parameters import Activation, ParameterGroup, Selection, StringParameter
from core.config._types import Attributes, Configuration, Defaults, ParameterFullName
from core.tests.test_config.utils import ConfigTestCase, name_id

# Types

NestedValues: TypeAlias = dict
RawAttributes: TypeAlias = dict[ParameterFullName, dict]
Selections: TypeAlias = dict[ParameterFullName, str]
Schema: TypeAlias = dict[ParameterFullName, "str | tuple[str, dict]"]

# Schema node types

SELECTION = "selection"
GROUP = "group"
ACTIVATABLE = "activatable"
VALUE = "value"


def build_specification(schema: Schema) -> FullSpec:
    """
    Build specification from flat schema: full name of node to its type with extra arguments, if any.

    >>> spec = build_specification({"/storage": SELECTION, "/storage/hdfs": GROUP, "/storage/hdfs/path": VALUE})
    >>> sorted(spec.groups)
    ['/storage', '/storage/hdfs']
    >>> sorted(spec.parameters)
    ['/storage/hdfs/path']
    >>> spec.groups["/storage"].selection is not None
    True
    """
    parameters = []

    for full_name, node in schema.items():
        node_type, extra = node if isinstance(node, tuple) else (node, {})
        identifier = name_id(*full_name.strip("/").split("/"))

        match node_type:
            case "selection":
                parameters.append(ParameterGroup(identifier=identifier, selection=Selection(**extra)))
            case "group":
                parameters.append(ParameterGroup(identifier=identifier))
            case "activatable":
                parameters.append(ParameterGroup(identifier=identifier, activation=Activation(**extra)))
            case "value":
                parameters.append(StringParameter(identifier=identifier, **extra))
            case _:
                message = f"Unknown schema node type: {node_type}"
                raise ValueError(message)

    return FullSpec.from_parameters(*parameters)


def flatten_defaults(
    config: NestedValues,
    specification: FullSpec,
    selection: Selections | None = None,
    activation: dict[ParameterFullName, bool] | None = None,
) -> Defaults:
    """
    Convert "default configuration" dict to `Defaults`.

    Chosen option of a selection group is the only option present in `config`,
    give it in `selection` directly when defaults of more than one option are described.

    >>> schema = {"/storage": SELECTION, "/storage/hdfs": GROUP, "/storage/hdfs/path": VALUE}
    >>> spec = build_specification(schema)
    >>> defaults = flatten_defaults({"storage": {"hdfs": {"path": "old"}}}, specification=spec)
    >>> defaults.values
    {'/storage/hdfs/path': 'old'}
    >>> defaults.selection
    {'/storage': 'hdfs'}

    Value of a parameter may be `None`, while an absent key means there is no default at all:

    >>> flatten_defaults({"storage": {"hdfs": {"path": None}}}, specification=spec).values
    {'/storage/hdfs/path': None}
    >>> flatten_defaults({"storage": {"hdfs": {}}}, specification=spec).values
    {}

    Defaults of activatable groups are given directly, since configuration has no place for them:

    >>> flatten_defaults({}, specification=spec, activation={"/storage/hdfs": True}).activation
    {'/storage/hdfs': True}
    """
    given_selection = selection or {}

    values = {}
    detected_selection = {}

    def visit(node: NestedValues, prefix: ParameterFullName) -> None:
        group = specification.groups.get(prefix)
        if group is not None and group.selection:
            options = tuple(node.keys())

            if prefix in given_selection:
                detected_selection[prefix] = given_selection[prefix]
            elif len(options) == 1:
                detected_selection[prefix] = options[0]
            else:
                message = f"Can't detect chosen option of {prefix} out of {options}, specify it directly"
                raise ValueError(message)

        for key, value in node.items():
            full_name = f"{prefix}/{key}"

            if isinstance(value, dict):
                visit(node=value, prefix=full_name)
            else:
                values[full_name] = value

    visit(node=config, prefix="")

    return Defaults(values=values, selection=detected_selection, activation=activation or {})


def build_attributes(raw: RawAttributes) -> dict[ParameterFullName, Attributes]:
    """
    Convert `{full name: {"active": ..., "synced": ...}}` to configuration attributes.

    >>> build_attributes({"/storage/cache": {"active": True}})
    {'/storage/cache': Attributes(is_active=True, is_synced=None)}
    >>> build_attributes({"/storage/path": {"synced": False}})
    {'/storage/path': Attributes(is_active=None, is_synced=False)}
    """
    return {
        name: Attributes(is_active=attributes.get("active"), is_synced=attributes.get("synced"))
        for name, attributes in raw.items()
    }


class TestConversionDoctests(TestCase):
    """`doctest.DocTestSuite` can't be used in here, since its cases aren't picklable for parallel test run"""

    def test_doctests_of_conversion_functions(self):
        results = doctest.testmod(sys.modules[__name__], verbose=False)

        self.assertEqual(results.failed, 0, msg=f"{results.failed} of {results.attempted} doctests failed")


class AdaptationTestCase(ConfigTestCase):
    """Base for adaptation suites, `adapt` is the function under test"""

    maxDiff = None

    adapt = staticmethod(adapt_configuration_for_new_specification)

    schema: Schema = {}
    new_schema: Schema | None = None
    include_synchronization: bool = False

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()

        cls.specification = build_specification(cls.schema)
        cls.new_specification = cls.specification if cls.new_schema is None else build_specification(cls.new_schema)

    def adapt_configuration(
        self,
        defaults: dict,
        config: dict,
        *,
        old_selection: Selections | None = None,
        new_selection: Selections | None = None,
        old_activation: dict[ParameterFullName, bool] | None = None,
        new_activation: dict[ParameterFullName, bool] | None = None,
    ) -> Configuration:
        configuration = Configuration(
            values=config.get("values", {}), attributes=build_attributes(config.get("attributes", {}))
        )

        result = self.adapt(
            configuration=configuration,
            specification=self.specification,
            defaults=flatten_defaults(
                config=defaults["old"],
                specification=self.specification,
                selection=old_selection,
                activation=old_activation,
            ),
            new_specification=self.new_specification,
            new_defaults=flatten_defaults(
                config=defaults["new"],
                specification=self.new_specification,
                selection=new_selection,
                activation=new_activation,
            ),
            include_synchronization=self.include_synchronization,
        )

        return self.expect_success(result).value

    def assert_values_adapted_to(self, defaults: dict, values: NestedValues, expected: NestedValues, **kwargs) -> None:
        adapted = self.adapt_configuration(defaults=defaults, config={"values": values}, **kwargs)

        self.assertDictEqual(adapted.values, expected)

    def assert_adapted_to(self, defaults: dict, config: dict, expected: dict, **kwargs) -> None:
        adapted = self.adapt_configuration(defaults=defaults, config=config, **kwargs)

        self.assertDictEqual(adapted.values, expected.get("values", {}))
        self.assertDictEqual(adapted.attributes, build_attributes(expected.get("attributes", {})))


# Schemas


# `storage` options differ in content: `hdfs` has only groups, `local` only values, `s3` both
STORAGE_SCHEMA: Schema = {
    "/storage": SELECTION,
    "/storage/hdfs": GROUP,
    "/storage/hdfs/tuning": GROUP,
    "/storage/hdfs/tuning/retention": VALUE,
    "/storage/hdfs/cache": SELECTION,
    "/storage/hdfs/cache/memory": GROUP,
    "/storage/hdfs/cache/memory/size": VALUE,
    "/storage/hdfs/cache/disk": GROUP,
    "/storage/hdfs/cache/disk/size": VALUE,
    "/storage/local": GROUP,
    "/storage/local/path": VALUE,
    "/storage/local/mode": VALUE,
    "/storage/s3": GROUP,
    "/storage/s3/bucket": VALUE,
    "/storage/s3/creds": GROUP,
    "/storage/s3/creds/token": VALUE,
}


def hdfs_defaults(retention: str, size: str) -> NestedValues:
    return {"hdfs": {"tuning": {"retention": retention}, "cache": {"memory": {"size": size}}}}


def local_defaults(path: str, mode: str) -> NestedValues:
    return {"local": {"path": path, "mode": mode}}


def s3_defaults(bucket: str, token: str) -> NestedValues:
    return {"s3": {"bucket": bucket, "creds": {"token": token}}}


class TestDefaultsPropagation(AdaptationTestCase):
    """
    Value that isn't changed from old default takes new default, changed one is kept as is.

    Option of a selection group is "not changed" only when the option itself is the default one
    and all values in it are the default ones.
    """

    schema = STORAGE_SCHEMA

    @parametrize(
        ("defaults", "values", "expected"),
        [
            param(
                {"old": {"storage": hdfs_defaults("old", "old")}, "new": {"storage": hdfs_defaults("new", "new")}},
                {"storage": hdfs_defaults("custom", "old")},
                {"storage": hdfs_defaults("custom", "new")},
                id="changed_in_group_kept_and_untouched_inner_selection_takes_new_default",
            ),
            param(
                {"old": {"storage": hdfs_defaults("old", "old")}, "new": {"storage": hdfs_defaults("new", "new")}},
                {"storage": hdfs_defaults("old", "custom")},
                {"storage": hdfs_defaults("new", "custom")},
                id="changed_in_inner_selection_kept_and_untouched_group_takes_new_default",
            ),
            param(
                {"old": {"storage": hdfs_defaults("old", "old")}, "new": {"storage": hdfs_defaults("new", "new")}},
                {"storage": hdfs_defaults("old", "old")},
                {"storage": hdfs_defaults("new", "new")},
                id="nothing_changed_takes_all_new_defaults",
            ),
        ],
    )
    def test_values_of_chosen_option(self, defaults: dict, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(defaults=defaults, values=values, expected=expected)

    @parametrize(
        ("values", "expected", "new_selection"),
        [
            param(
                {"storage": hdfs_defaults("custom", "old")},
                {"storage": hdfs_defaults("custom", "old")},
                {"/storage": "s3"},
                id="changed_option_blocks_new_default_option",
            ),
            param(
                {"storage": hdfs_defaults("old", "old")},
                {"storage": s3_defaults("new", "new")},
                {"/storage": "s3"},
                id="untouched_option_takes_new_default_option",
            ),
        ],
    )
    def test_choice_of_selection_group(self, values: NestedValues, expected: NestedValues, new_selection: Selections):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": hdfs_defaults("old", "old") | s3_defaults("old", "old")},
                "new": {"storage": hdfs_defaults("old", "old") | s3_defaults("new", "new")},
            },
            values=values,
            expected=expected,
            old_selection={"/storage": "hdfs"},
            new_selection=new_selection,
        )

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"storage": local_defaults("custom", "old")},
                {"storage": local_defaults("custom", "old")},
                id="changed_value_in_chosen_non_default_option_is_kept",
            ),
            param(
                {"storage": local_defaults("old", "old")},
                {"storage": local_defaults("new", "old")},
                id="untouched_value_in_chosen_non_default_option_takes_new_default",
            ),
        ],
    )
    def test_values_of_chosen_non_default_option(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": hdfs_defaults("old", "old") | local_defaults("old", "old")},
                "new": {"storage": hdfs_defaults("new", "new") | local_defaults("new", "old")},
            },
            values=values,
            expected=expected,
            old_selection={"/storage": "hdfs"},
            new_selection={"/storage": "hdfs"},
        )


class TestContentOfChosenOption(AdaptationTestCase):
    """Same rules apply regardless of option having only groups, only values or both"""

    schema = STORAGE_SCHEMA

    @parametrize(
        ("old_defaults", "new_defaults", "values", "expected"),
        [
            param(
                hdfs_defaults("old", "old"),
                hdfs_defaults("new", "new"),
                hdfs_defaults("custom", "old"),
                hdfs_defaults("custom", "new"),
                id="option_with_groups_only",
            ),
            param(
                local_defaults("old", "old"),
                local_defaults("new", "new"),
                local_defaults("custom", "old"),
                local_defaults("custom", "new"),
                id="option_with_values_only",
            ),
            param(
                s3_defaults("old", "old"),
                s3_defaults("new", "new"),
                s3_defaults("custom", "old"),
                s3_defaults("custom", "new"),
                id="option_with_groups_and_values",
            ),
        ],
    )
    def test_changed_value_kept_and_untouched_one_takes_new_default(
        self,
        old_defaults: NestedValues,
        new_defaults: NestedValues,
        values: NestedValues,
        expected: NestedValues,
    ):
        self.assert_values_adapted_to(
            defaults={"old": {"storage": old_defaults}, "new": {"storage": new_defaults}},
            values={"storage": values},
            expected={"storage": expected},
        )


class TestNewDefaultIsNotSpecified(AdaptationTestCase):
    """New default is "specified" when its key is present in defaults and value isn't `None`"""

    schema = {"/settings": GROUP, "/settings/value": VALUE}

    @parametrize(
        ("defaults", "values", "expected"),
        [
            param(
                {"old": {"settings": {"value": "old"}}, "new": {"settings": {"value": None}}},
                {"settings": {"value": "old"}},
                {"settings": {"value": "old"}},
                id="untouched_value_keeps_old_default_when_new_one_is_none",
            ),
            param(
                {"old": {"settings": {"value": "old"}}, "new": {"settings": {}}},
                {"settings": {"value": "old"}},
                {"settings": {"value": None}},
                id="untouched_value_becomes_none_when_new_default_key_is_missing",
            ),
            param(
                {"old": {"settings": {"value": "old"}}, "new": {"settings": {"value": None}}},
                {"settings": {"value": "custom"}},
                {"settings": {"value": "custom"}},
                id="changed_value_is_kept_when_new_default_is_none",
            ),
            param(
                {"old": {"settings": {"value": None}}, "new": {"settings": {"value": "new"}}},
                {"settings": {"value": None}},
                {"settings": {"value": "new"}},
                id="untouched_none_value_takes_new_default",
            ),
            param(
                {"old": {"settings": {"value": None}}, "new": {"settings": {"value": "new"}}},
                {"settings": {"value": "custom"}},
                {"settings": {"value": "custom"}},
                id="changed_value_is_kept_when_old_default_is_none",
            ),
        ],
    )
    def test_new_default_is_not_specified(self, defaults: dict, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(defaults=defaults, values=values, expected=expected)


class TestSchemaChangeInsideOption(AdaptationTestCase):
    """Parameter `retention` of chosen option is replaced with `keep` in new specification"""

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/tuning": GROUP,
        "/storage/hdfs/tuning/size": VALUE,
        "/storage/hdfs/tuning/retention": VALUE,
    }
    new_schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/tuning": GROUP,
        "/storage/hdfs/tuning/size": VALUE,
        "/storage/hdfs/tuning/keep": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"storage": {"hdfs": {"tuning": {"size": "old", "retention": "old"}}}},
                {"storage": {"hdfs": {"tuning": {"size": "new", "keep": "new"}}}},
                id="nothing_changed",
            ),
            param(
                {"storage": {"hdfs": {"tuning": {"size": "old", "retention": "custom"}}}},
                {"storage": {"hdfs": {"tuning": {"size": "new", "keep": "new"}}}},
                id="removed_parameter_changed",
            ),
            param(
                {"storage": {"hdfs": {"tuning": {"size": "custom", "retention": "custom"}}}},
                {"storage": {"hdfs": {"tuning": {"size": "custom", "keep": "new"}}}},
                id="kept_and_removed_parameters_changed",
            ),
        ],
    )
    def test_removed_parameter_dropped_and_added_one_appears(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"tuning": {"size": "old", "retention": "old"}}}},
                "new": {"storage": {"hdfs": {"tuning": {"size": "new", "keep": "new"}}}},
            },
            values=values,
            expected=expected,
        )


class TestSchemaChangeOfGroups(AdaptationTestCase):
    """Group `legacy` is replaced with group `fresh` in new specification"""

    schema = {
        "/main": GROUP,
        "/main/value": VALUE,
        "/legacy": GROUP,
        "/legacy/value": VALUE,
    }
    new_schema = {
        "/main": GROUP,
        "/main/value": VALUE,
        "/fresh": GROUP,
        "/fresh/value": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"main": {"value": "old"}, "legacy": {"value": "old"}},
                {"main": {"value": "new"}, "fresh": {"value": "new"}},
                id="nothing_changed",
            ),
            param(
                {"main": {"value": "old"}, "legacy": {"value": "custom"}},
                {"main": {"value": "new"}, "fresh": {"value": "new"}},
                id="value_in_removed_group_changed",
            ),
        ],
    )
    def test_removed_group_dropped_and_added_one_appears(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"main": {"value": "old"}, "legacy": {"value": "old"}},
                "new": {"main": {"value": "new"}, "fresh": {"value": "new"}},
            },
            values=values,
            expected=expected,
        )


class TestChosenOptionRemovedFromSpecification(AdaptationTestCase):
    """Option `hdfs` doesn't exist in new specification at all"""

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }
    new_schema = {
        "/storage": SELECTION,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"storage": {"hdfs": {"path": "old"}}},
                {"storage": {"local": {"path": "new"}}},
                id="values_are_defaults",
            ),
            param(
                {"storage": {"hdfs": {"path": "custom"}}},
                {"storage": {"local": {"path": "new"}}},
                id="value_in_chosen_option_changed",
            ),
        ],
    )
    def test_chosen_option_is_gone(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"path": "old"}, "local": {"path": "old"}}},
                "new": {"storage": {"local": {"path": "new"}}},
            },
            values=values,
            expected=expected,
            old_selection={"/storage": "hdfs"},
        )


class TestSecretsAreNotMigrated(AdaptationTestCase):
    """Secret values are never replaced with new defaults, see ADCM-7444"""

    schema = {
        "/settings": GROUP,
        "/settings/plain": VALUE,
        "/settings/secret": (VALUE, {"is_secret": True}),
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"settings": {"plain": "old", "secret": "old"}},
                {"settings": {"plain": "new", "secret": "old"}},
                id="untouched_secret_is_kept_while_plain_takes_new_default",
            ),
            param(
                {"settings": {"plain": "custom", "secret": "custom"}},
                {"settings": {"plain": "custom", "secret": "custom"}},
                id="changed_values_are_kept",
            ),
        ],
    )
    def test_secret_does_not_take_new_default(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"settings": {"plain": "old", "secret": "old"}},
                "new": {"settings": {"plain": "new", "secret": "new"}},
            },
            values=values,
            expected=expected,
        )


class TestActivationAttributes(AdaptationTestCase):
    """Activation set by user wins over new default, groups unknown to old configuration take new default"""

    schema = {
        "/optional": ACTIVATABLE,
        "/optional/value": VALUE,
    }
    new_schema = {
        "/optional": ACTIVATABLE,
        "/optional/value": VALUE,
        "/added": ACTIVATABLE,
        "/added/value": VALUE,
    }

    @parametrize(
        ("chosen_activation", "new_default_activation"),
        [
            param(True, False, id="activated_by_user"),
            param(False, True, id="deactivated_by_user"),
        ],
    )
    def test_activation_of_known_group_is_kept(self, chosen_activation: bool, new_default_activation: bool):
        self.assert_adapted_to(
            defaults={
                "old": {"optional": {"value": "old"}},
                "new": {"optional": {"value": "old"}, "added": {"value": "new"}},
            },
            config={
                "values": {"optional": {"value": "old"}},
                "attributes": {"/optional": {"active": chosen_activation}},
            },
            expected={
                "values": {"optional": {"value": "old"}, "added": {"value": "new"}},
                "attributes": {
                    "/optional": {"active": chosen_activation},
                    "/added": {"active": new_default_activation},
                },
            },
            old_activation={"/optional": not chosen_activation},
            new_activation={"/optional": not chosen_activation, "/added": new_default_activation},
        )


class TestActivationAttributesOfRemovedGroups(AdaptationTestCase):
    """Attributes of groups that are gone or no longer activatable should be gone too"""

    schema = {
        "/stays": ACTIVATABLE,
        "/stays/value": VALUE,
        "/becomes_regular": ACTIVATABLE,
        "/becomes_regular/value": VALUE,
        "/removed": ACTIVATABLE,
        "/removed/value": VALUE,
    }
    new_schema = {
        "/stays": ACTIVATABLE,
        "/stays/value": VALUE,
        "/becomes_regular": GROUP,
        "/becomes_regular/value": VALUE,
    }

    def test_attributes_follow_specification(self):
        self.assert_adapted_to(
            defaults={
                "old": {"stays": {"value": "old"}, "becomes_regular": {"value": "old"}, "removed": {"value": "old"}},
                "new": {"stays": {"value": "old"}, "becomes_regular": {"value": "old"}},
            },
            config={
                "values": {
                    "stays": {"value": "old"},
                    "becomes_regular": {"value": "old"},
                    "removed": {"value": "old"},
                },
                "attributes": {
                    "/stays": {"active": True},
                    "/becomes_regular": {"active": True},
                    "/removed": {"active": True},
                },
            },
            expected={
                "values": {"stays": {"value": "old"}, "becomes_regular": {"value": "old"}},
                "attributes": {"/stays": {"active": True}},
            },
            old_activation={"/stays": False, "/becomes_regular": False, "/removed": False},
            new_activation={"/stays": False},
        )


class TestSynchronizationAttributes(AdaptationTestCase):
    """
    Synchronization of host group configuration: known flags are kept, unknown ones become synchronized.

    Activation and synchronization are independent, so all their combinations should survive adaptation.
    """

    include_synchronization = True

    schema = {
        "/optional": (ACTIVATABLE, {"is_desyncable": True}),
        "/optional/value": VALUE,
        "/plain": VALUE,
    }
    new_schema = {
        "/optional": (ACTIVATABLE, {"is_desyncable": True}),
        "/optional/value": VALUE,
        "/plain": VALUE,
        "/added": VALUE,
    }

    @parametrize(
        ("active", "synced"),
        [
            param(True, True, id="active_and_synced"),
            param(True, False, id="active_and_desynced"),
            param(False, True, id="inactive_and_synced"),
            param(False, False, id="inactive_and_desynced"),
        ],
    )
    def test_activation_and_synchronization_combination_is_kept(self, active: bool, synced: bool):
        self.assert_adapted_to(
            defaults={
                "old": {"optional": {"value": "old"}, "plain": "old"},
                "new": {"optional": {"value": "old"}, "plain": "old", "added": "new"},
            },
            config={
                "values": {"optional": {"value": "old"}, "plain": "old"},
                "attributes": {"/optional": {"active": active, "synced": synced}, "/plain": {"synced": synced}},
            },
            expected={
                "values": {"optional": {"value": "old"}, "plain": "old", "added": "new"},
                "attributes": {
                    "/optional": {"active": active, "synced": synced},
                    "/optional/value": {"synced": True},
                    "/plain": {"synced": synced},
                    # parameter is unknown to old configuration, so it is synchronized
                    "/added": {"synced": True},
                },
            },
            old_activation={"/optional": not active},
            new_activation={"/optional": not active},
        )


class TestSelectionGroupAppearsAndDisappears(AdaptationTestCase):
    """Selection group is added to / removed from specification as a whole"""

    schema = {
        "/main": GROUP,
        "/main/value": VALUE,
        "/gone": SELECTION,
        "/gone/first": GROUP,
        "/gone/first/value": VALUE,
        "/gone/second": GROUP,
        "/gone/second/value": VALUE,
    }
    new_schema = {
        "/main": GROUP,
        "/main/value": VALUE,
        "/added": SELECTION,
        "/added/first": GROUP,
        "/added/first/value": VALUE,
        "/added/second": GROUP,
        "/added/second/value": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"main": {"value": "old"}, "gone": {"first": {"value": "old"}}},
                {"main": {"value": "new"}, "added": {"first": {"value": "new"}}},
                id="nothing_changed",
            ),
            param(
                {"main": {"value": "old"}, "gone": {"second": {"value": "custom"}}},
                {"main": {"value": "new"}, "added": {"first": {"value": "new"}}},
                id="removed_selection_group_was_changed",
            ),
        ],
    )
    def test_removed_selection_group_dropped_and_added_one_appears(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"main": {"value": "old"}, "gone": {"first": {"value": "old"}}},
                "new": {"main": {"value": "new"}, "added": {"first": {"value": "new"}}},
            },
            values=values,
            expected=expected,
        )


class TestOptionsOfSelectionGroupChanged(AdaptationTestCase):
    """Option `local` is replaced with option `s3`, while chosen `hdfs` stays"""

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }
    new_schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/s3": GROUP,
        "/storage/s3/path": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"storage": {"hdfs": {"path": "old"}}},
                {"storage": {"hdfs": {"path": "new"}}},
                id="nothing_changed",
            ),
            param(
                {"storage": {"hdfs": {"path": "custom"}}},
                {"storage": {"hdfs": {"path": "custom"}}},
                id="chosen_option_changed",
            ),
        ],
    )
    def test_changes_of_other_options_do_not_affect_chosen_one(self, values: NestedValues, expected: NestedValues):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"path": "old"}, "local": {"path": "old"}}},
                "new": {"storage": {"hdfs": {"path": "new"}, "s3": {"path": "new"}}},
            },
            values=values,
            expected=expected,
            old_selection={"/storage": "hdfs"},
            new_selection={"/storage": "hdfs"},
        )


class TestNestedSelectionGroupAdded(AdaptationTestCase):
    """Chosen option gets own selection group in new specification"""

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
    }
    new_schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/hdfs/cache": SELECTION,
        "/storage/hdfs/cache/memory": GROUP,
        "/storage/hdfs/cache/memory/size": VALUE,
        "/storage/hdfs/cache/disk": GROUP,
        "/storage/hdfs/cache/disk/size": VALUE,
    }

    @parametrize(
        ("values", "expected"),
        [
            param(
                {"storage": {"hdfs": {"path": "old"}}},
                {"storage": {"hdfs": {"path": "new", "cache": {"memory": {"size": "new"}}}}},
                id="nothing_changed",
            ),
            param(
                {"storage": {"hdfs": {"path": "custom"}}},
                {"storage": {"hdfs": {"path": "custom", "cache": {"memory": {"size": "new"}}}}},
                id="value_in_option_changed",
            ),
        ],
    )
    def test_added_nested_selection_group_appears_with_default_option(
        self, values: NestedValues, expected: NestedValues
    ):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"path": "old"}}},
                "new": {"storage": {"hdfs": {"path": "new", "cache": {"memory": {"size": "new"}}}}},
            },
            values=values,
            expected=expected,
        )


class TestGroupBecomesActivatable(AdaptationTestCase):
    """Regular group becomes activatable in new specification"""

    schema = {"/settings": GROUP, "/settings/value": VALUE}
    new_schema = {"/settings": ACTIVATABLE, "/settings/value": VALUE}

    @parametrize(
        ("new_default_activation",),
        [param(True, id="active_by_default"), param(False, id="inactive_by_default")],
    )
    def test_activation_attribute_appears_with_new_default(self, new_default_activation: bool):
        self.assert_adapted_to(
            defaults={"old": {"settings": {"value": "old"}}, "new": {"settings": {"value": "new"}}},
            config={"values": {"settings": {"value": "old"}}},
            expected={
                "values": {"settings": {"value": "new"}},
                "attributes": {"/settings": {"active": new_default_activation}},
            },
            new_activation={"/settings": new_default_activation},
        )


class TestActivationInsideSelectionOption(AdaptationTestCase):
    """
    Activatable group inside an option of a selection group, the shape of ADCM-8370.

    Attributes should follow the option that ends up being chosen.
    """

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/hdfs/cache": ACTIVATABLE,
        "/storage/hdfs/cache/size": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }

    HDFS_DEFAULTS = {"hdfs": {"path": "old", "cache": {"size": "old"}}, "local": {"path": "old"}}

    @parametrize(
        ("chosen_activation",),
        [param(True, id="activated_by_user"), param(False, id="deactivated_by_user")],
    )
    def test_activation_in_chosen_non_default_option_is_kept(self, chosen_activation: bool):
        self.assert_adapted_to(
            defaults={"old": {"storage": self.HDFS_DEFAULTS}, "new": {"storage": self.HDFS_DEFAULTS}},
            config={
                "values": {"storage": {"hdfs": {"path": "old", "cache": {"size": "old"}}}},
                "attributes": {"/storage/hdfs/cache": {"active": chosen_activation}},
            },
            expected={
                "values": {"storage": {"hdfs": {"path": "old", "cache": {"size": "old"}}}},
                "attributes": {"/storage/hdfs/cache": {"active": chosen_activation}},
            },
            old_selection={"/storage": "local"},
            new_selection={"/storage": "local"},
            old_activation={"/storage/hdfs/cache": not chosen_activation},
            new_activation={"/storage/hdfs/cache": not chosen_activation},
        )

    def test_activation_of_replaced_option_is_gone(self):
        self.assert_adapted_to(
            defaults={"old": {"storage": self.HDFS_DEFAULTS}, "new": {"storage": self.HDFS_DEFAULTS}},
            config={
                "values": {"storage": {"hdfs": {"path": "old", "cache": {"size": "old"}}}},
                "attributes": {"/storage/hdfs/cache": {"active": True}},
            },
            # nothing is changed, so new default option is taken and there is no activatable group in it
            expected={"values": {"storage": {"local": {"path": "old"}}}, "attributes": {}},
            old_selection={"/storage": "hdfs"},
            new_selection={"/storage": "local"},
            old_activation={"/storage/hdfs/cache": False},
            new_activation={"/storage/hdfs/cache": False},
        )


class TestDesyncableChangedBetweenBundles(AdaptationTestCase):
    """Synchronization flag isn't converted implicitly when group becomes (non-)desyncable, see ADCM-7429"""

    include_synchronization = True

    schema = {
        "/becomes_desyncable": ACTIVATABLE,
        "/becomes_desyncable/value": VALUE,
        "/becomes_regular": (ACTIVATABLE, {"is_desyncable": True}),
        "/becomes_regular/value": VALUE,
    }
    new_schema = {
        "/becomes_desyncable": (ACTIVATABLE, {"is_desyncable": True}),
        "/becomes_desyncable/value": VALUE,
        "/becomes_regular": ACTIVATABLE,
        "/becomes_regular/value": VALUE,
    }

    def test_synchronization_flags_are_kept_as_is(self):
        defaults = {"becomes_desyncable": {"value": "old"}, "becomes_regular": {"value": "old"}}
        activation = {"/becomes_desyncable": False, "/becomes_regular": False}

        self.assert_adapted_to(
            defaults={"old": defaults, "new": defaults},
            config={
                "values": {"becomes_desyncable": {"value": "old"}, "becomes_regular": {"value": "old"}},
                "attributes": {
                    "/becomes_desyncable": {"active": True, "synced": True},
                    "/becomes_regular": {"active": True, "synced": False},
                },
            },
            expected={
                "values": {"becomes_desyncable": {"value": "old"}, "becomes_regular": {"value": "old"}},
                "attributes": {
                    "/becomes_desyncable": {"active": True, "synced": True},
                    "/becomes_regular": {"active": True, "synced": False},
                    "/becomes_desyncable/value": {"synced": True},
                    "/becomes_regular/value": {"synced": True},
                },
            },
            old_activation=activation,
            new_activation=activation,
        )


class TestSynchronizationFollowsSpecification(AdaptationTestCase):
    """Synchronization attributes exist only for what is present in adapted configuration"""

    include_synchronization = True

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
        "/removed": VALUE,
    }
    new_schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }

    def test_no_attributes_for_removed_parameter_and_non_chosen_option(self):
        defaults = {"storage": {"hdfs": {"path": "old"}, "local": {"path": "old"}}, "removed": "old"}

        self.assert_adapted_to(
            defaults={"old": defaults, "new": {"storage": defaults["storage"]}},
            config={
                "values": {"storage": {"hdfs": {"path": "custom"}}, "removed": "old"},
                "attributes": {"/storage/hdfs/path": {"synced": False}, "/removed": {"synced": False}},
            },
            expected={
                "values": {"storage": {"hdfs": {"path": "custom"}}},
                # selection group itself is always synchronized, so it has no attributes,
                # same for parameters of options that aren't chosen and for removed parameter
                "attributes": {"/storage/hdfs/path": {"synced": False}},
            },
            old_selection={"/storage": "hdfs"},
            new_selection={"/storage": "hdfs"},
        )


class TestDefaultsInsideSelectionOption(AdaptationTestCase):
    """`None` defaults and secrets behave inside an option the same way as outside of it"""

    schema = {
        "/storage": SELECTION,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/plain": VALUE,
        "/storage/hdfs/secret": (VALUE, {"is_secret": True}),
    }

    def test_untouched_value_keeps_old_default_when_new_one_is_none(self):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"plain": "old", "secret": "old"}}},
                "new": {"storage": {"hdfs": {"plain": None, "secret": "old"}}},
            },
            values={"storage": {"hdfs": {"plain": "old", "secret": "old"}}},
            expected={"storage": {"hdfs": {"plain": "old", "secret": "old"}}},
        )

    def test_secret_does_not_take_new_default(self):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"plain": "old", "secret": "old"}}},
                "new": {"storage": {"hdfs": {"plain": "new", "secret": "new"}}},
            },
            values={"storage": {"hdfs": {"plain": "old", "secret": "old"}}},
            expected={"storage": {"hdfs": {"plain": "new", "secret": "old"}}},
        )


class TestOptionalSelectionGroup(AdaptationTestCase):
    """Selection group that allows no option to be chosen at all (`AT_MOST_ONE`)"""

    schema = {
        "/storage": (SELECTION, {"is_required": False}),
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }

    DEFAULTS = {"storage": {"hdfs": {"path": "old"}, "local": {"path": "old"}}}
    NEW_DEFAULTS = {"storage": {"hdfs": {"path": "new"}, "local": {"path": "new"}}}

    @parametrize(
        ("old_choice", "new_choice", "values", "expected"),
        [
            param(
                None,
                None,
                {"storage": None},
                {"storage": None},
                id="nothing_chosen_stays_nothing",
            ),
            param(
                None,
                "hdfs",
                {"storage": None},
                {"storage": {"hdfs": {"path": "new"}}},
                id="nothing_chosen_takes_new_default_option",
            ),
            param(
                None,
                None,
                {"storage": {"hdfs": {"path": "old"}}},
                # option is kept, because it is chosen by user, yet untouched value takes new default
                {"storage": {"hdfs": {"path": "new"}}},
                id="chosen_option_kept_when_there_is_no_new_default",
            ),
            param(
                "hdfs",
                "hdfs",
                {"storage": None},
                {"storage": None},
                id="deselected_by_user_stays_deselected",
            ),
        ],
    )
    def test_optional_selection_group(
        self, old_choice: str | None, new_choice: str | None, values: NestedValues, expected: NestedValues
    ):
        self.assert_values_adapted_to(
            defaults={"old": self.DEFAULTS, "new": self.NEW_DEFAULTS},
            values=values,
            expected=expected,
            old_selection={"/storage": old_choice},
            new_selection={"/storage": new_choice},
        )


class TestDeeplyNestedSelectionGroups(AdaptationTestCase):
    """Three levels of selection groups nested one into another"""

    schema = {
        "/first": SELECTION,
        "/first/a": GROUP,
        "/first/a/second": SELECTION,
        "/first/a/second/b": GROUP,
        "/first/a/second/b/third": SELECTION,
        "/first/a/second/b/third/c": GROUP,
        "/first/a/second/b/third/c/value": VALUE,
        "/first/a/second/b/third/d": GROUP,
        "/first/a/second/b/third/d/value": VALUE,
    }

    def defaults(self, value: str) -> NestedValues:
        return {"first": {"a": {"second": {"b": {"third": {"c": {"value": value}}}}}}}

    def test_untouched_deepest_value_takes_new_default(self):
        self.assert_values_adapted_to(
            defaults={"old": self.defaults("old"), "new": self.defaults("new")},
            values=self.defaults("old"),
            expected=self.defaults("new"),
        )

    def test_changed_deepest_value_is_kept(self):
        self.assert_values_adapted_to(
            defaults={"old": self.defaults("old"), "new": self.defaults("new")},
            values=self.defaults("custom"),
            expected=self.defaults("custom"),
        )

    def test_changed_deepest_choice_is_kept(self):
        self.assert_values_adapted_to(
            defaults={
                "old": {"first": {"a": {"second": {"b": {"third": {"c": {"value": "old"}, "d": {"value": "old"}}}}}}},
                "new": {"first": {"a": {"second": {"b": {"third": {"c": {"value": "new"}, "d": {"value": "new"}}}}}}},
            },
            values={"first": {"a": {"second": {"b": {"third": {"d": {"value": "old"}}}}}}},
            expected={"first": {"a": {"second": {"b": {"third": {"d": {"value": "new"}}}}}}},
            old_selection={"/first/a/second/b/third": "c"},
            new_selection={"/first/a/second/b/third": "c"},
        )


class TestIndependentSelectionGroups(AdaptationTestCase):
    """Two selection groups next to each other are adapted independently"""

    schema = {
        "/left": SELECTION,
        "/left/one": GROUP,
        "/left/one/value": VALUE,
        "/left/two": GROUP,
        "/left/two/value": VALUE,
        "/right": SELECTION,
        "/right/one": GROUP,
        "/right/one/value": VALUE,
        "/right/two": GROUP,
        "/right/two/value": VALUE,
    }

    DEFAULTS = {
        "left": {"one": {"value": "old"}, "two": {"value": "old"}},
        "right": {"one": {"value": "old"}, "two": {"value": "old"}},
    }
    NEW_DEFAULTS = {
        "left": {"one": {"value": "new"}, "two": {"value": "new"}},
        "right": {"one": {"value": "new"}, "two": {"value": "new"}},
    }

    def test_changed_one_does_not_block_new_default_of_another(self):
        self.assert_values_adapted_to(
            defaults={"old": self.DEFAULTS, "new": self.NEW_DEFAULTS},
            values={"left": {"one": {"value": "custom"}}, "right": {"one": {"value": "old"}}},
            expected={"left": {"one": {"value": "custom"}}, "right": {"two": {"value": "new"}}},
            old_selection={"/left": "one", "/right": "one"},
            new_selection={"/left": "one", "/right": "two"},
        )


class TestMalformedPreviousConfiguration(AdaptationTestCase):
    """Configuration that doesn't match its own specification shouldn't break adaptation"""

    schema = {"/settings": GROUP, "/settings/value": VALUE}

    def test_regular_group_with_none_value_falls_back_to_new_defaults(self):
        self.assert_values_adapted_to(
            defaults={"old": {"settings": {"value": "old"}}, "new": {"settings": {"value": "new"}}},
            # regular group isn't expected to hold `None`, yet it shouldn't break adaptation
            values={"settings": None},
            expected={"settings": {"value": "new"}},
        )


class TestSelectionGroupBecomesRegular(AdaptationTestCase):
    """
    Selection group without default option becomes a regular one.

    Type change of a node is an undefined behavior, this case only pins that it doesn't break adaptation.
    """

    schema = {
        "/storage": (SELECTION, {"is_required": False}),
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }
    new_schema = {
        "/storage": GROUP,
        "/storage/hdfs": GROUP,
        "/storage/hdfs/path": VALUE,
        "/storage/local": GROUP,
        "/storage/local/path": VALUE,
    }

    def test_all_options_become_regular_groups(self):
        self.assert_values_adapted_to(
            defaults={
                "old": {"storage": {"hdfs": {"path": "old"}, "local": {"path": "old"}}},
                "new": {"storage": {"hdfs": {"path": "new"}, "local": {"path": "new"}}},
            },
            values={"storage": {"hdfs": {"path": "custom"}}},
            expected={"storage": {"hdfs": {"path": "custom"}, "local": {"path": "new"}}},
            old_selection={"/storage": None},
        )
