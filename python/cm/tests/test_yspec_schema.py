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

from pathlib import Path

from adcm.tests.base import ParallelReadyTestCase
from django.test import TestCase

from cm.checker import FormatError
from cm.stack import check_yspec_schema


class TestYspecSchema(TestCase, ParallelReadyTestCase):
    def setUp(self):
        self.yspec_schemas_dir = Path(__file__).parent / "files" / "yspec_schemas"

    def test_wrong_schema_no_root(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_no_root.yaml")

        self.assertTrue(error.exception.message == 'There is no required key "root" in map.')

    def test_wrong_schema_no_match(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_no_match.yaml")

        self.assertTrue(error.exception.message == 'There is no key "match" in map.')

    def test_wrong_schema_not_supported_match(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_not_supported_match.yaml")

        self.assertTrue(error.exception.message == 'Value "not_supported_match" is not allowed for map key "match".')

    def test_wrong_schema_extra_field_in_simple_type(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_extra_field_in_simple_type.yaml")

        self.assertTrue(error.exception.message == 'Map key "extra" is not allowed here (rule "simple_type")')

    def test_good_schema_simple_type(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_simple_type.yaml")

    def test_wrong_schema_list_type_not_item_field(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_list_type_not_item_field.yaml")

        self.assertTrue(error.exception.message == 'There is no required key "item" in map.')

    def test_wrong_schema_extra_field_in_list_type(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_extra_field_in_list_type.yaml")

        self.assertTrue(error.exception.message == 'Map key "extra" is not allowed here (rule "list_type")')

    def test_good_schema_list_type(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_list_type.yaml")

    def test_wrong_schema_extra_field_in_dict_type(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_extra_field_in_dict_type.yaml")

        self.assertTrue(error.exception.message == 'Map key "extra" is not allowed here (rule "dict_type")')

    def test_good_schema_dict_type(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_dict_type.yaml")

    def test_good_schema_dict_type_with_default_item(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_dict_type_with_default_item.yaml")

    def test_wrong_schema_set_type_not_variants_field(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_set_type_not_variants_field.yaml")

        self.assertTrue(error.exception.message == 'There is no required key "variants" in map.')

    def test_wrong_schema_extra_field_in_set_type(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(conf_file=self.yspec_schemas_dir / "wrong_schema_extra_field_in_set_type.yaml")

        self.assertTrue(error.exception.message == 'Map key "extra" is not allowed here (rule "set_type")')

    def test_wrong_schema_set_type_wrong_variants_value_string(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(
                conf_file=self.yspec_schemas_dir / "wrong_schema_set_type_wrong_variants_value_string.yaml"
            )

        self.assertTrue(
            error.exception.message == 'Input data for match_list, rule "list_of_string" should be <class \'list\'>"'
        )

    def test_wrong_schema_set_type_wrong_variants_value_list_integer(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(
                conf_file=self.yspec_schemas_dir / "wrong_schema_set_type_wrong_variants_value_list_integer.yaml"
            )

        self.assertTrue(error.exception.message == "Value of list index \"0\" should be a <class 'str'>")

    def test_good_schema_set_type(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_set_type.yaml")

    def test_wrong_schema_dict_key_selection_not_variants_field(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(
                conf_file=self.yspec_schemas_dir / "wrong_schema_dict_key_selection_type_not_variants_field.yaml"
            )

        self.assertTrue(error.exception.message == 'There is no required key "variants" in map.')

    def test_wrong_schema_dict_value_selection_not_selector_field(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(
                conf_file=self.yspec_schemas_dir / "wrong_schema_dict_key_selection_type_not_selector_field.yaml"
            )

        self.assertTrue(error.exception.message == 'There is no required key "selector" in map.')

    def test_wrong_schema_extra_field_in_dict_value_selection_type(self):
        with self.assertRaises(FormatError) as error:
            check_yspec_schema(
                conf_file=self.yspec_schemas_dir / "wrong_schema_extra_field_in_dict_key_selection_type.yaml"
            )

        self.assertTrue(
            error.exception.message == 'Map key "extra" is not allowed here (rule "dict_key_selection_type")'
        )

    def test_good_schema_dict_key_selection_type(self):
        check_yspec_schema(conf_file=self.yspec_schemas_dir / "good_schema_dict_key_selection_type.yaml")
