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
from unittest import TestCase, mock

from core.types import ADCMCoreType, CoreObjectDescriptor

from cm.services.config.spec import ConfigParamPlainSpec
from cm.services.job.inventory._config import update_configuration_for_inventory_inplace


class ConfigHostGroupTest(TestCase):
    def test_unsafe_in_update_configuration_for_inventory_inplace(self):
        func = update_configuration_for_inventory_inplace
        config = {"1": "val", "2": None, "g": {"1": "iv", "2": None}}
        default_param_spec = {
            "display_name": "x",
            "description": "x",
            "default": None,
            "limits": {},
            "ui_options": {},
            "required": True,
            "group_customization": None,
        }

        owner = CoreObjectDescriptor(id=1, type=ADCMCoreType.CLUSTER)

        for valid_type in ("string", "text"):
            for name, options, expected in (
                (
                    "unsafe-changed",
                    {"unsafe": True},
                    {"1": {"__ansible_unsafe": "val"}, "2": None, "g": {"1": {"__ansible_unsafe": "iv"}, "2": None}},
                ),
                (
                    "safe-unchanged",
                    {"unsafe": False},
                    config,
                ),
            ):
                spec = {
                    key: ConfigParamPlainSpec.from_dict(
                        {"type": valid_type, "ansible_options": options} | default_param_spec
                    )
                    for key in ("1/", "2/", "g/1", "g/2")
                }
                with self.subTest(f"{valid_type}-{name}"):
                    actual = func(configuration=deepcopy(config), attributes={}, specification=spec, config_owner=owner)
                    self.assertDictEqual(actual, expected)

        def patched_path_for_file(*, config_key, config_subkey="", **_):
            if config_subkey:
                return config[config_key][config_subkey]

            return config[config_key]

        with mock.patch("cm.services.job.inventory._config._build_string_path_for_file", new=patched_path_for_file):
            for invalid_type in ("password", "secrettext", "file", "secretfile"):
                with self.subTest(f"{invalid_type}-unchanged"):
                    # even if unsfae is True by some mistake, it shouldn't work
                    spec = {
                        key: ConfigParamPlainSpec.from_dict(
                            {"type": invalid_type, "ansible_options": {"unsafe": True}} | default_param_spec
                        )
                        for key in ("1/", "2/", "g/1", "g/2")
                    }
                    actual = func(configuration=deepcopy(config), attributes={}, specification=spec, config_owner=owner)
                    self.assertDictEqual(actual, config)
