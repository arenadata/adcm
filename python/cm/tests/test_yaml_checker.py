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

from django.test import TestCase

from cm.checker import FormatError, process_rule

test_data = {
    "cluster": [
        {
            "cluster_name": "default_cluster",
            "shards": [
                {
                    "weight": 1,
                    "internal_replication": True,
                    "replicas": [
                        {
                            "host": "test-adqm01.ru-central1.internal",
                            "port": 9000,
                            "uuid": "123-4gdfwpr-2erett",
                            "user": "usr",
                            "password": "pswd",
                        }
                    ],
                }
            ],
        }
    ]
}

test_rules = {
    "root": {"match": "dict", "items": {"cluster": "cluster_list"}},
    "cluster_list": {"match": "list", "item": "cluster_item"},
    "cluster_item": {
        "match": "dict",
        "items": {"cluster_name": "string", "shards": "shard_list"},
        "required_items": ["cluster_name"],
    },
    "shard_list": {"match": "list", "item": "shard_item"},
    "shard_item": {
        "match": "dict",
        "items": {"weight": "integer", "internal_replication": "boolean", "replicas": "replica_list"},
        "required_items": ["weight", "internal_replication"],
    },
    "replica_list": {"match": "list", "item": "replica_item"},
    "replica_item": {
        "match": "dict",
        "items": {"host": "string", "port": "integer", "user": "string", "password": "string", "uuid": "string"},
        "required_items": ["host", "port"],
        "invisible_items": ["uuid"],
    },
    "string": {"match": "string"},
    "integer": {"match": "int"},
    "boolean": {"match": "bool"},
}


class TestYAMLChecker(TestCase):
    def test_initial_data_correct_success(self):
        process_rule(data=test_data, rules=test_rules, name="root")

    def test_invisible_field_not_in_data_success(self):
        rules = deepcopy(test_rules)
        rules["replica_item"]["invisible_items"].append("non_existent_field")
        process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_none_fail(self):
        rules = deepcopy(test_rules)
        rules["root"]["match"] = "none"
        rules["root"]["invisible_items"] = ["something"]
        with self.assertRaises(FormatError):
            process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_list_fail(self):
        rules = deepcopy(test_rules)
        rules["cluster_list"]["invisible_items"] = ["something"]
        with self.assertRaises(FormatError):
            process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_dict_key_selection_fail(self):
        rules = deepcopy(test_rules)
        rules["root"]["match"] = "dict_key_selection"
        rules["root"]["invisible_items"] = ["something"]
        with self.assertRaises(FormatError):
            process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_one_of_fail(self):
        rules = deepcopy(test_rules)
        rules["root"]["match"] = "one_of"
        rules["root"]["invisible_items"] = ["something"]
        with self.assertRaises(FormatError):
            process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_set_fail(self):
        rules = deepcopy(test_rules)
        rules["root"]["match"] = "set"
        rules["root"]["invisible_items"] = ["something"]
        with self.assertRaises(FormatError):
            process_rule(data=test_data, rules=rules, name="root")

    def test_invisible_items_in_match_simple_type_fail(self):
        for simple_type in ("string", "bool", "int", "float"):
            rules = deepcopy(test_rules)
            rules["root"]["match"] = simple_type
            rules["root"]["invisible_items"] = ["something"]
            with self.assertRaises(FormatError):
                process_rule(data=test_data, rules=rules, name="root")

    def test_pass_integer_and_float_in_match_float_success(self):
        schema = {
            "clusters": {"match": "list", "item": "fdict"},
            "fdict": {"match": "dict", "items": {"fval": "float_rule"}},
            "float_rule": {"match": "float"},
        }
        data = [{"fval": 4}, {"fval": 4.0}]
        process_rule(data=data, rules=schema, name="clusters")

    def test_pass_string_in_match_float_fail(self):
        schema = {
            "clusters": {"match": "list", "item": "fdict"},
            "fdict": {"match": "dict", "items": {"fval": "float_rule"}},
            "float_rule": {"match": "float"},
        }
        data = [{"fval": 4}, {"fval": 4.0}, {"fval": "also-string"}]
        with self.assertRaises(FormatError) as err:
            process_rule(data=data, rules=schema, name="clusters")

        self.assertIn("float", err.exception.message)
        self.assertIn("int", err.exception.message)
