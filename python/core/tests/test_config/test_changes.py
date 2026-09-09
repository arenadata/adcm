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
from operator import attrgetter
from unittest import TestCase

from unittest_parametrize import ParametrizedTestCase, parametrize

from core.config._config import detect_changes
from core.config._spec.parameters import (
    Activation,
    BooleanParameter,
    ListParameter,
    MapParameter,
    ParameterGroup,
    Selection,
    StringParameter,
)
from core.config._spec.spec import FullSpec
from core.config._types import Attributes, Change, Configuration
from core.config._types import ChangeType as ChT
from core.tests.test_config.utils import name_id


class TestChangesDiff(ParametrizedTestCase, TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.parameters = (
            StringParameter(identifier=name_id("simple")),
            # selection group
            ParameterGroup(identifier=name_id("root_sel"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("root_sel", "one")),
            ListParameter(identifier=name_id("root_sel", "one", "l")),
            ParameterGroup(identifier=name_id("root_sel", "one", "ag"), activation=Activation()),
            ParameterGroup(identifier=name_id("root_sel", "one", "ag", "g")),
            StringParameter(identifier=name_id("root_sel", "one", "ag", "g", "s")),
            BooleanParameter(identifier=name_id("root_sel", "one", "ag", "b")),
            ParameterGroup(identifier=name_id("root_sel", "two")),
            MapParameter(identifier=name_id("root_sel", "two", "m")),
            # activatable group
            ParameterGroup(identifier=name_id("root_act"), activation=Activation()),
            MapParameter(identifier=name_id("root_act", "m")),
            BooleanParameter(identifier=name_id("root_act", "b")),
            # regular group
            ParameterGroup(identifier=name_id("root_group")),
            BooleanParameter(identifier=name_id("root_group", "b")),
        )
        cls.spec = FullSpec.from_parameters(*cls.parameters)

    def setUp(self) -> None:
        self.minimal_config = Configuration(
            values={
                "simple": "a",
                "root_sel": None,
                "root_act": {"m": {"k": "v"}, "b": False},
                "root_group": {"b": True},
            },
            attributes={"/root_act": Attributes(is_active=True)},
        )
        self.config_with_selected_one = Configuration(
            values=self.minimal_config.values
            | {"root_sel": {"one": {"l": ["3", "1", "2"], "ag": {"g": {"s": "w"}, "b": False}}}},
            attributes=self.minimal_config.attributes | {"/root_sel/one/ag": Attributes(is_active=False)},
        )

    def config_based_on(self, original: Configuration) -> Configuration:
        return deepcopy(original)

    def assert_changes(self, actual: list[Change], expected: list[Change]) -> None:
        by_name = attrgetter("parameter")
        sorted_actual = sorted(actual, key=by_name)
        sorted_expected = sorted(expected, key=by_name)
        self.assertListEqual(sorted_actual, sorted_expected)

    @parametrize(
        "var_name",
        ["minimal_config", "config_with_selected_one"],
        ids=["minimal_config", "config_with_selected_one"],
    )
    def test_no_changes(self, var_name: str):
        config = getattr(self, var_name)

        result = detect_changes(config, config, self.spec)

        self.assertListEqual(result, [])

    def test_value_in_root(self):
        expected = [Change(parameter="/simple", type=ChT.VALUE, old="a", new="b")]
        new_config = self.config_based_on(self.minimal_config)
        new_config.values["simple"] = "b"

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_value_in_group(self):
        expected = [Change(parameter="/root_group/b", type=ChT.VALUE, old=True, new=False)]
        new_config = self.config_based_on(self.minimal_config)
        new_config.values["root_group"]["b"] = False

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_activation_in_root(self):
        expected = [Change(parameter="/root_act", type=ChT.ACTIVATION, old=True, new=False)]
        new_config = self.config_based_on(self.minimal_config)
        new_config.attributes["/root_act"].is_active = False

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_activation_in_group(self):
        expected = [Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=True)]
        new_config = self.config_based_on(self.config_with_selected_one)
        new_config.attributes["/root_sel/one/ag"].is_active = True

        result = detect_changes(self.config_with_selected_one, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_sync_in_root(self):
        expected = [Change(parameter="/simple", type=ChT.SYNCHRONIZATION, old=True, new=False)]
        self.minimal_config.attributes["/simple"] = Attributes(is_synced=True)
        new_config = self.config_based_on(self.minimal_config)
        new_config.attributes["/simple"] = Attributes(is_synced=False)

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_sync_in_group(self):
        expected = [Change(parameter="/root_group/b", type=ChT.SYNCHRONIZATION, old=False, new=True)]
        self.minimal_config.attributes["/root_group/b"] = Attributes(is_synced=False)
        new_config = self.config_based_on(self.minimal_config)
        new_config.attributes["/root_group/b"] = Attributes(is_synced=True)

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_sync_and_activation_in_root(self):
        expected = [
            Change(parameter="/root_act", type=ChT.ACTIVATION, old=False, new=True),
            Change(parameter="/root_act", type=ChT.SYNCHRONIZATION, old=True, new=False),
        ]
        new_config = self.config_based_on(self.minimal_config)
        new_config.attributes["/root_act"] = Attributes(is_synced=False, is_active=True)
        self.minimal_config.attributes["/root_act"] = Attributes(is_synced=True, is_active=False)

        result = detect_changes(self.minimal_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_none_to_chosen(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old=None, new="one"),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=None, new=["3", "1", "2"]),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=None, new=False),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=None, new=False),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old=None, new="w"),
        ]

        result = detect_changes(self.minimal_config, self.config_with_selected_one, self.spec)

        self.assert_changes(result, expected)

    def test_selection_chosen_to_none(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new=None),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
        ]

        result = detect_changes(self.config_with_selected_one, self.minimal_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_change_chosen(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new="two"),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
            Change(parameter="/root_sel/two/m", type=ChT.VALUE, old=None, new={"k": "v"}),
        ]
        new_config = self.config_based_on(self.config_with_selected_one)
        new_config.values["root_sel"] = {"two": {"m": {"k": "v"}, "b": True}}
        new_config.attributes.pop("/root_sel/one/ag")

        result = detect_changes(self.config_with_selected_one, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_value_in_selection(self):
        expected = [Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=["4"])]
        new_config = self.config_based_on(self.config_with_selected_one)
        new_config.values["root_sel"]["one"]["l"] = ["4"]

        result = detect_changes(self.config_with_selected_one, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_activation_in_selection(self):
        expected = [Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=True)]
        new_config = self.config_based_on(self.config_with_selected_one)
        new_config.attributes["/root_sel/one/ag"].is_active = True

        result = detect_changes(self.config_with_selected_one, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_sync_in_selected_branch_without_selection_change(self):
        expected = [Change(parameter="/root_sel/one/l", type=ChT.SYNCHRONIZATION, old=True, new=False)]
        previous_config = self.config_based_on(self.config_with_selected_one)
        previous_config.attributes["/root_sel/one/l"] = Attributes(is_synced=True)
        new_config = self.config_based_on(previous_config)
        new_config.attributes["/root_sel/one/l"] = Attributes(is_synced=False)

        result = detect_changes(previous_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_change_with_desync_in_newly_selected_branch(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new="two"),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
            Change(parameter="/root_sel/two/m", type=ChT.VALUE, old=None, new={"k": "v"}),
            Change(parameter="/root_sel/two/m", type=ChT.SYNCHRONIZATION, old=None, new=False),
        ]
        previous_config = self.config_based_on(self.config_with_selected_one)
        new_config = self.config_based_on(self.config_with_selected_one)
        new_config.values["root_sel"] = {"two": {"m": {"k": "v"}}}
        new_config.attributes = {
            "/root_act": Attributes(is_active=True),
            "/root_sel/two/m": Attributes(is_synced=False),
        }

        result = detect_changes(previous_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_change_sync_in_outdated_branch(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new="two"),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
            Change(parameter="/root_sel/one/l", type=ChT.SYNCHRONIZATION, old=True, new=False),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
            Change(parameter="/root_sel/two/m", type=ChT.VALUE, old=None, new={"k": "v"}),
        ]
        previous_config = self.config_based_on(self.config_with_selected_one)
        previous_config.attributes["/root_sel/one/l"] = Attributes(is_synced=True)
        new_config = self.config_based_on(previous_config)
        new_config.values["root_sel"] = {"two": {"m": {"k": "v"}}}
        new_config.attributes["/root_sel/one/l"] = Attributes(is_synced=False)
        new_config.attributes.pop("/root_sel/one/ag")

        result = detect_changes(previous_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_to_none_sync_in_removed_branch(self):
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new=None),
            Change(parameter="/root_sel/one/l", type=ChT.VALUE, old=["3", "1", "2"], new=None),
            Change(parameter="/root_sel/one/l", type=ChT.SYNCHRONIZATION, old=True, new=None),
            Change(parameter="/root_sel/one/ag", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag/b", type=ChT.VALUE, old=False, new=None),
            Change(parameter="/root_sel/one/ag/g/s", type=ChT.VALUE, old="w", new=None),
        ]
        previous_config = self.config_based_on(self.config_with_selected_one)
        previous_config.attributes["/root_sel/one/l"] = Attributes(is_synced=True)
        new_config = self.config_based_on(previous_config)
        new_config.values["root_sel"] = None
        new_config.attributes.pop("/root_sel/one/l")
        new_config.attributes.pop("/root_sel/one/ag")

        result = detect_changes(previous_config, new_config, self.spec)

        self.assert_changes(result, expected)

    def test_selection_change_has_activation_gone_and_appeared(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("root_sel"), selection=Selection(is_required=False)),
            ParameterGroup(identifier=name_id("root_sel", "one")),
            ParameterGroup(identifier=name_id("root_sel", "one", "ag1"), activation=Activation()),
            BooleanParameter(identifier=name_id("root_sel", "one", "ag1", "b")),
            ParameterGroup(identifier=name_id("root_sel", "two")),
            ParameterGroup(identifier=name_id("root_sel", "two", "ag2"), activation=Activation()),
            BooleanParameter(identifier=name_id("root_sel", "two", "ag2", "b")),
        )
        previous_config = Configuration(
            values={"root_sel": {"one": {"ag1": {"b": True}}}},
            attributes={"/root_sel/one/ag1": Attributes(is_active=False)},
        )
        new_config = Configuration(
            values={"root_sel": {"two": {"ag2": {"b": False}}}},
            attributes={"/root_sel/two/ag2": Attributes(is_active=True)},
        )
        expected = [
            Change(parameter="/root_sel", type=ChT.SELECTION, old="one", new="two"),
            Change(parameter="/root_sel/one/ag1", type=ChT.ACTIVATION, old=False, new=None),
            Change(parameter="/root_sel/one/ag1/b", type=ChT.VALUE, old=True, new=None),
            Change(parameter="/root_sel/two/ag2", type=ChT.ACTIVATION, old=None, new=True),
            Change(parameter="/root_sel/two/ag2/b", type=ChT.VALUE, old=None, new=False),
        ]

        result = detect_changes(previous_config, new_config, spec)

        self.assert_changes(result, expected)
