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

from core.config._operations import prepare_initial_config_of_host_group
from core.config._spec.parameters import ParameterGroup, Selection, StringParameter
from core.config._spec.spec import FullSpec
from core.config._types import Attributes, Configuration
from core.tests.test_config.utils import ConfigTestCase, name_id


class TestPrepareInitialConfigOfHostGroup(ConfigTestCase):
    def test_no_attributes_from_disabled_selection_group_option(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "a")),
            StringParameter(identifier=name_id("s", "a", "v"), is_desyncable=True),
            ParameterGroup(identifier=name_id("s", "b")),
            StringParameter(identifier=name_id("s", "b", "v"), is_desyncable=False),
        )
        config = Configuration(values={"s": {"a": {"v": "p"}}})

        expected_attributes = {"/s/a/v": Attributes(is_synced=True)}

        result = prepare_initial_config_of_host_group(configuration=config, specification=spec)

        actual = self.expect_success(result).value
        self.assertDictEqual(actual.attributes, expected_attributes)

    def test_no_attributes_from_selection_group_eq_none(self):
        spec = FullSpec.from_parameters(
            ParameterGroup(identifier=name_id("s"), selection=Selection()),
            ParameterGroup(identifier=name_id("s", "a")),
            StringParameter(identifier=name_id("s", "a", "v"), is_desyncable=True),
            ParameterGroup(identifier=name_id("s", "b")),
            StringParameter(identifier=name_id("s", "b", "v"), is_desyncable=False),
        )
        config = Configuration(values={"s": None})

        expected_attributes = {}

        result = prepare_initial_config_of_host_group(configuration=config, specification=spec)

        actual = self.expect_success(result).value
        self.assertDictEqual(actual.attributes, expected_attributes)
