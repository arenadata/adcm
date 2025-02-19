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
Created for ADCM-6355.

Initial imports made from bundle_alt, because code was placed there waiting for removal to own `core.config` package.
"""

from typing import NamedTuple
from unittest import TestCase

from core.bundle_alt._config import check_default_values
from core.bundle_alt.types import ConfigParamPlainSpec
from core.errors import ConfigValueError


class _ObjectDesc(NamedTuple):
    type: str = "cluster"
    name: str = "Awesome Object"
    version: str = "1.2.3"


def make_spec(**kwargs) -> ConfigParamPlainSpec:
    defaults = {
        "type": "string",
        "key": ("a",),
        "display_name": "A",
        "description": "aaaaa",
        "default": None,
        "limits": {},
        "ui_options": dict,
        "required": True,
        "group_customization": None,
    }
    return ConfigParamPlainSpec(**(defaults | kwargs))


class TestCheckDefaultValues(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None

    def test_structure(self):
        desc = _ObjectDesc()
        key = ("wow", "how")
        param_yspec = {
            "root": {"match": "dict", "required_items": ["a"], "items": {"a": "integer"}},
            "integer": {"match": "int"},
        }

        with self.subTest("success"):
            params = {key: make_spec(type="structure", limits={"yspec": param_yspec})}
            values = {key: {"a": 12}}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("fail"):
            params = {key: make_spec(type="structure", limits={"yspec": param_yspec})}
            values = {key: {"b": "k"}}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("yspec error", err.exception.msg)

    def test_option(self):
        desc = _ObjectDesc()
        key = ("wow", "how")

        with self.subTest("success"):
            params = {key: make_spec(type="option", limits={"option": {"a": "b"}})}
            values = {key: "b"}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("fail"):
            params = {key: make_spec(type="option", limits={"option": {"a": "b"}})}
            values = {key: "a"}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("not in option list:", err.exception.msg)

    def test_variant_inline(self):
        desc = _ObjectDesc()
        key = ("wow", "how")

        with self.subTest("strict valid success"):
            params = {
                key: make_spec(type="variant", limits={"source": {"strict": True, "type": "inline", "value": [1, 2]}})
            }
            values = {key: 2}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("nonstrict invalid success"):
            params = {
                key: make_spec(type="variant", limits={"source": {"strict": False, "type": "inline", "value": [1, 2]}})
            }
            values = {key: "wrong"}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("strict invalid fail"):
            params = {
                key: make_spec(type="variant", limits={"source": {"strict": True, "type": "inline", "value": [1, 2]}})
            }
            values = {key: "ogogo"}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn('not in variant list: "[1, 2]"', err.exception.msg)
            self.assertIn("ogogo", err.exception.msg)

    def test_pattern(self):
        desc = _ObjectDesc()
        key = ("wow", "how")
        pattern = {"pattern": "[+].*"}
        ansible_header = "$ANSIBLE_VAULT;1.1;AES256"

        with self.subTest("string success"):
            params = {key: make_spec(type="string", limits=pattern)}
            values = {key: "+sldkj"}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("secrettext encrypted incorrect success"):
            params = {key: make_spec(type="secrettext", limits=pattern)}
            values = {key: f"{ansible_header}a"}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("text incorrect fail"):
            params = {key: make_spec(type="text", limits=pattern)}
            values = {key: "ooo"}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertEqual(
                err.exception.msg, f"The value of wow/how config parameter does not match pattern: {pattern['pattern']}"
            )

    def test_too_long_file_length(self):
        desc = _ObjectDesc()
        key = ("wow", "how")

        params = {key: make_spec(type="file")}
        values = {key: "a" * 2049}

        with self.assertRaises(ConfigValueError) as err:
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        self.assertIn("is too long", err.exception.msg)

    def test_min_max(self):
        desc = _ObjectDesc()
        key = ("wow",)

        with self.subTest("ignored for non-number"):
            params = {key: make_spec(type="string", limits={"min": 100, "max": 200})}
            values = {key: "sdlkfj"}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("integer min success"):
            params = {key: make_spec(type="integer", limits={"min": 100})}
            values = {key: 100}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("float max success"):
            params = {key: make_spec(type="float", limits={"max": 100})}
            values = {key: 99}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("integer min fail"):
            params = {key: make_spec(type="integer", limits={"min": 100})}
            values = {key: 99}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("should be more than 100", err.exception.msg)

        with self.subTest("float max fail"):
            params = {key: make_spec(type="float", limits={"max": 100})}
            values = {key: 101}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("should be less than 100", err.exception.msg)

    def test_children_are_strings(self):
        desc = _ObjectDesc()
        key = ("somecool", "final")

        with self.subTest("list all str success"):
            params = {key: make_spec(type="list")}
            values = {key: ["a", "b", "c", "d"]}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("dict all str success"):
            params = {key: make_spec(type="secretmap")}
            values = {key: {"a": "b", "c": "d"}}
            check_default_values(parameters=params, values=values, attributes={}, object_=desc)

        with self.subTest("list not all str fail"):
            params = {key: make_spec(type="list")}
            values = {key: ["a", "b", 1, "d"]}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("should be string", err.exception.msg)
            self.assertIn('of element "2" of config key', err.exception.msg)

        with self.subTest("dict not all str fail"):
            params = {key: make_spec(type="map")}
            values = {key: {"a": "b", "c": 2.3}}
            with self.assertRaises(ConfigValueError) as err:
                check_default_values(parameters=params, values=values, attributes={}, object_=desc)

            self.assertIn("should be string", err.exception.msg)
            self.assertIn('of element "c" of config key', err.exception.msg)

    def test_unset_value_required_inactive_group_success(self):
        desc = _ObjectDesc()
        key = ("somecool", "final")
        group_key = ("somecool",)

        params = {group_key: make_spec(type="group"), key: make_spec()}
        values = {key: None}
        attrs = {group_key: {"active": False}}

        check_default_values(parameters=params, values=values, attributes=attrs, object_=desc)

    def test_unset_value_required_raises_error(self):
        desc = _ObjectDesc()
        key = ("somecool",)
        key_repr = "somecool/"

        # type after normalization | type repr in error | default value
        cases = [
            ("string", None),
            ("string", ""),
            ("password", None),
            ("password", ""),
            ("text", None),
            ("text", ""),
            ("secrettext", None),
            ("secrettext", ""),
            ("file", None),
            ("secretfile", None),
            ("map", None),
            ("map", {}),
            ("secretmap", None),
            ("secretmap", {}),
            ("list", None),
            ("list", []),
            ("integer", None),
            ("float", None),
            ("boolean", None),
            ("json", None),
            ("structure", None),
            ("option", None),
            ("variant", None),
        ]

        for definition_type, value in cases:
            case_name = f"{definition_type}={value}"
            defaults = {key: value}
            params = {key: make_spec(type=definition_type, key=key, required=True)}

            with self.subTest(case_name):
                with self.assertRaises(ConfigValueError) as err:
                    check_default_values(parameters=params, values=defaults, attributes={}, object_=desc)

                err_msg = err.exception.msg

                self.assertTrue(err_msg.startswith("Default value"))
                self.assertIn(key_repr, err_msg)
                self.assertIn("is required", err_msg)

    def test_complex_value_for_plain_type_raises_error(self):
        desc = _ObjectDesc()
        key = ("somecool", "ingroup")
        key_repr = "somecool/ingroup"

        # type after normalization | type repr in error | default value
        cases = ["string", "password", "text", "secrettext", "file", "secrettext", "integer", "float", "boolean"]

        for type_ in cases:
            params = {key: make_spec(type=type_, key=key, required=True)}
            # only list and dict are considered "not flat"
            for value in ([], {}):
                defaults = {key: value}
                with self.subTest(f"{type_}={value}"):
                    with self.assertRaises(ConfigValueError) as err:
                        check_default_values(parameters=params, values=defaults, attributes={}, object_=desc)

                    err_msg = err.exception.msg

                    self.assertTrue(err_msg.startswith("Default value"))
                    self.assertIn(key_repr, err_msg)
                    self.assertIn("should be flat", err_msg)

    def test_incorrect_value_type_raises_error(self):
        desc = _ObjectDesc()
        key = ("somecool",)
        key_repr = "somecool/"

        # type after normalization | type repr in error | default value
        cases = [
            ("string", "string", 2),
            ("password", "string", object()),
            ("text", "string", False),
            ("secrettext", "string", 4.3),
            ("file", "string", True),
            ("secrettext", "string", object()),
            ("integer", "integer", 4.3),
            ("float", "float", "sdlkfj"),
            ("boolean", "boolean", 1),
            ("map", "map", []),
            ("secretmap", "map", "{}"),
            ("list", "array", {}),
            ("list", "array", "[]"),
        ]

        for definition_type, expected_type_name, value in cases:
            case_name = f"{definition_type} with value '{value}'"
            defaults = {key: value}
            params = {key: make_spec(type=definition_type, key=key, required=True)}

            with self.subTest(case_name):
                with self.assertRaises(ConfigValueError) as err:
                    check_default_values(parameters=params, values=defaults, attributes={}, object_=desc)

                err_msg = err.exception.msg

                self.assertTrue(err_msg.startswith("Default value"))
                self.assertIn(key_repr, err_msg)
                self.assertIn(f"should be an {expected_type_name}", err_msg)
