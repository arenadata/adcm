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

from unittest_parametrize import param, parametrize

from core.config._operations import prepare_initial_config_of_host_group, update_config_of_host_group
from core.config._spec.parameters import Activation, ParameterGroup, Selection, StringParameter
from core.config._spec.spec import FullSpec
from core.config._types import Attributes, Configuration
from core.tests.test_config.utils import ConfigTestCase, name_id


def spec_with_selection() -> FullSpec:
    return FullSpec.from_parameters(
        ParameterGroup(identifier=name_id("s"), selection=Selection()),
        ParameterGroup(identifier=name_id("s", "a")),
        StringParameter(identifier=name_id("s", "a", "v"), is_desyncable=True),
        ParameterGroup(identifier=name_id("s", "b")),
        StringParameter(identifier=name_id("s", "b", "v"), is_desyncable=False),
    )


class TestPrepareInitialConfigOfHostGroup(ConfigTestCase):
    def test_no_attributes_from_disabled_selection_group_option(self):
        spec = spec_with_selection()
        config = Configuration(values={"s": {"a": {"v": "p"}}})
        expected_attributes = {"/s/a/v": Attributes(is_synced=True)}

        result = prepare_initial_config_of_host_group(configuration=config, specification=spec)

        actual = self.expect_success(result).value
        self.assertDictEqual(actual.attributes, expected_attributes)

    def test_no_attributes_from_selection_group_eq_none(self):
        spec = spec_with_selection()
        config = Configuration(values={"s": None})
        expected_attributes = {}

        result = prepare_initial_config_of_host_group(configuration=config, specification=spec)

        actual = self.expect_success(result).value
        self.assertDictEqual(actual.attributes, expected_attributes)


class TestUpdateConfigOfHostGroup(ConfigTestCase):
    @parametrize(
        ("is_synced", "expected_value"),
        [
            param(False, "host", id="desynced_copies_host_value"),
            param(True, "main", id="synced_keeps_main_value"),
        ],
    )
    def test_sync_flag_behavior_for_regular_parameter(self, is_synced: bool, expected_value: str):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("g")),
            StringParameter(identifier=name_id("g", "p"), is_desyncable=True),
        )
        main_config = Configuration(values={"g": {"p": "main"}})
        host_group_config = Configuration(
            values={"g": {"p": "host"}},
            attributes={"/g/p": Attributes(is_synced=is_synced)},
        )
        expected_attributes = {"/g/p": Attributes(is_synced=is_synced)}

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, {"g": {"p": expected_value}})
        self.assertDictEqual(result_config.attributes, expected_attributes)

    def test_adcm_7948_unsynced_in_outdated_selected(self):
        spec = spec_with_selection()
        main_config = Configuration(values={"s": {"b": "v"}})
        # group is changed in main config, when host group still have info about "old" attributes
        host_group_config = Configuration(values={"s": {"a": "v"}}, attributes={"/s/a/v": Attributes(is_synced=False)})
        expected_config = deepcopy(main_config)

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, expected_config.values)
        self.assertDictEqual(result_config.attributes, expected_config.attributes)

    def test_activatable_desynced(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("a"), activation=Activation(is_desyncable=True)),
            StringParameter(identifier=name_id("a", "s")),
        )
        # values aren't important in this case
        main_config = Configuration(values={}, attributes={"/a": Attributes(is_active=False)})
        host_group_config = Configuration(values={}, attributes={"/a": Attributes(is_active=True, is_synced=False)})

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, {})
        self.assertDictEqual(result_config.attributes, {"/a": Attributes(is_active=True, is_synced=False)})

    def test_activatable_attr_with_unset_sync_is_normalized(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("a"), activation=Activation()),
            StringParameter(identifier=name_id("a", "s")),
        )
        main_config = Configuration(
            values={"a": {"s": "x"}}, attributes={"/a": Attributes(is_active=True, is_synced=None)}
        )
        host_group_config = Configuration(values={"a": {"s": "x"}})

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, {"a": {"s": "x"}})
        self.assertDictEqual(
            result_config.attributes,
            {
                "/a": Attributes(is_active=True, is_synced=True),
                "/a/s": Attributes(is_synced=True),
            },
        )

    def test_rebuild_preserves_previous_sync_and_defaults_missing(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("g")),
            StringParameter(identifier=name_id("g", "p1"), is_desyncable=True),
            StringParameter(identifier=name_id("g", "p2"), is_desyncable=True),
        )
        main_config = Configuration(values={"g": {"p1": "m1", "p2": "m2"}})
        host_group_config = Configuration(
            values={"g": {"p1": "h1", "p2": "h2"}},
            attributes={"/g/p1": Attributes(is_synced=False)},
        )

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, {"g": {"p1": "h1", "p2": "m2"}})
        self.assertDictEqual(
            result_config.attributes,
            {
                "/g/p1": Attributes(is_synced=False),
                "/g/p2": Attributes(is_synced=True),
            },
        )

    def test_mixed_present_synced_desynced_and_stale(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "a")),
            StringParameter(identifier=name_id("s", "a", "v"), is_desyncable=True),
            ParameterGroup(identifier=name_id("s", "b")),
            StringParameter(identifier=name_id("s", "b", "v"), is_desyncable=True),
            ParameterGroup(identifier=name_id("s", "c")),
            StringParameter(identifier=name_id("s", "c", "v"), is_desyncable=True),
        )
        main_config = Configuration(values={"s": {"b": {"v": "main_b"}, "c": {"v": "main_c"}}})
        host_group_config = Configuration(
            values={"s": {"a": {"v": "host_a"}, "b": {"v": "host_b"}, "c": {"v": "host_c"}}},
            attributes={
                "/s/a/v": Attributes(is_synced=False),
                "/s/b/v": Attributes(is_synced=False),
                "/s/c/v": Attributes(is_synced=True),
            },
        )

        result = update_config_of_host_group(main=main_config, host_group=host_group_config, specification=spec)

        result_config = self.expect_success(result).value
        self.assertDictEqual(result_config.values, {"s": {"b": {"v": "host_b"}, "c": {"v": "main_c"}}})
        self.assertDictEqual(
            result_config.attributes,
            {
                "/s/b/v": Attributes(is_synced=False),
                "/s/c/v": Attributes(is_synced=True),
            },
        )
