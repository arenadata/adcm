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
import os
from collections import OrderedDict
from itertools import product

import yaml

ENTITIES = [
    "cluster",
    "host",
    "provider",
    "service",
]

VERSION = "1.0"

IS_REQUIRED = [True, False]

TYPES = [
    "list",
    "map",
    "string",
    "password",
    "text",
    "file",
    "structure",
    "boolean",
    "integer",
    "float",
    "option",
    # 'variant'
]

IS_DEFAULTS = [True, False]

DEFAULTS = {
    "list": ["/dev/rdisk0s1", "/dev/rdisk0s2", "/dev/rdisk0s3"],
    "map": {"name": "Joe", "age": "24", "sex": "m"},
    "string": "string",
    "password": "password",
    "text": "text",
    "file": "{}_file",
    "structure": [
        {"country": "Greece", "code": 30},
        {"country": "France", "code": 33},
        {"country": "Spain", "code": 34},
    ],
    "boolean": True,
    "integer": 16,
    "float": 1.0,
    "option": "DAILY",
    "variant": ["a", "b", "c"],
}

SENT_VALUES_TYPE = [
    "correct_value",
    "null_value",
    "empty_value",
]

VARS = {
    "list": {"correct_value": ["a", "b", "c"], "null_value": None, "empty_value": []},
    "map": {
        "correct_value": {"name": "Joe", "age": "24", "sex": "m"},
        "null_value": None,
        "empty_value": {},
    },
    "string": {"correct_value": "string", "null_value": None, "empty_value": ""},
    "password": {"correct_value": "password", "null_value": None, "empty_value": ""},
    "text": {"correct_value": "text", "null_value": None, "empty_value": ""},
    "file": {"correct_value": "file content", "null_value": None, "empty_value": ""},
    "structure": {
        "correct_value": [
            {"country": "Greece", "code": 30},
            {"country": "France", "code": 33},
            {"country": "Spain", "code": 34},
        ],
        "null_value": None,
        "empty_value": [],
    },
    "boolean": {"correct_value": False, "null_value": None},
    "integer": {"correct_value": 16, "null_value": None},
    "float": {"correct_value": 1.0, "null_value": None},
    "option": {"correct_value": "DAILY", "null_value": None},
}


def represent_ordereddict(dumper, data):
    value = []

    for item_key, item_value in data.items():
        node_key = dumper.represent_data(item_key)
        node_value = dumper.represent_data(item_value)

        value.append((node_key, node_value))

    return yaml.nodes.MappingNode("tag:yaml.org,2002:map", value)


def represent_none(self, _):
    return self.represent_scalar("tag:yaml.org,2002:null", "")


yaml.add_representer(type(None), represent_none)
yaml.add_representer(OrderedDict, represent_ordereddict)


def write_yaml(path, data):
    with open(path, "w", encoding="utf_8") as f:
        yaml.dump(data, stream=f, explicit_start=True)


def config_generate(name, entity, config_type, is_required, is_default):
    config = []
    config_body = OrderedDict({"name": config_type, "type": config_type, "required": is_required})

    if config_type == "structure":
        config_body.update({"yspec": "./schema.yaml"})

    if config_type == "option":
        config_body.update({"option": {"DAILY": "DAILY", "WEEKLY": "WEEKLY"}})

    if is_default:
        if config_type == "file":
            config_body.update({"default": DEFAULTS[config_type].format(entity)})
        else:
            config_body.update({"default": DEFAULTS[config_type]})
    config.append(config_body)

    actions = OrderedDict(
        {
            "job": OrderedDict(
                {
                    "script": f"{entity}_action.yaml",
                    "script_type": "ansible",
                    "type": "job",
                    "states": OrderedDict({"available": ["created"]}),
                }
            )
        }
    )

    body = OrderedDict({"name": name, "type": entity, "version": "1.0", "config": config, "actions": actions})

    return body


def get_list_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_map_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_string_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    if sent_value_type == "empty_value":
        if is_required:
            if is_default:
                test_value = DEFAULTS[config_type]
            else:
                test_value = VARS[config_type]["null_value"]
        else:
            test_value = VARS[config_type]["empty_value"]

    return sent_value, test_value


def get_password_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    if sent_value_type == "empty_value":
        if is_required:
            if is_default:
                test_value = DEFAULTS[config_type]
            else:
                test_value = VARS[config_type]["null_value"]
        else:
            test_value = VARS[config_type]["empty_value"]

    return sent_value, test_value


def get_text_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    if sent_value_type == "empty_value":
        if is_required:
            if is_default:
                test_value = DEFAULTS[config_type]
            else:
                test_value = VARS[config_type]["null_value"]
        else:
            test_value = VARS[config_type]["empty_value"]

    return sent_value, test_value


def get_file_sent_test_value(*args):
    _, entity, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]

    test_value = f"/adcm/data/file/{entity}.{{{{ context.{entity}_id }}}}.file."

    if sent_value_type == "empty_value":
        if not is_default:
            test_value = VARS[config_type]["null_value"]

    if sent_value_type == "null_value":
        if is_required and not is_default:
            test_value = VARS[config_type]["null_value"]

        if not is_required:
            test_value = VARS[config_type]["null_value"]

    return sent_value, test_value


def get_structure_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if sent_value_type == "null_value":
        if is_required and is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_boolean_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if is_required and sent_value_type == "null_value":
        if is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_integer_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if is_required and sent_value_type == "null_value":
        if is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_float_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if is_required and sent_value_type == "null_value":
        if is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


def get_option_sent_test_value(*args):
    _, _, config_type, is_required, is_default, sent_value_type = args
    sent_value = VARS[config_type][sent_value_type]
    test_value = VARS[config_type][sent_value_type]

    if is_required and sent_value_type == "null_value":
        if is_default:
            test_value = DEFAULTS[config_type]

    return sent_value, test_value


SENT_TEST_VALUE = {
    "list": get_list_sent_test_value,
    "map": get_map_sent_test_value,
    "string": get_string_sent_test_value,
    "password": get_password_sent_test_value,
    "text": get_text_sent_test_value,
    "file": get_file_sent_test_value,
    "structure": get_structure_sent_test_value,
    "boolean": get_boolean_sent_test_value,
    "integer": get_integer_sent_test_value,
    "float": get_float_sent_test_value,
    "option": get_option_sent_test_value,
}


def action_generate(name, entity, config_type, is_required, is_default, sent_value_type):
    if entity == "service":
        that = [f"services.{entity}_{name}.config.{config_type} == test_value"]
    elif entity == "host":
        that = [f"{config_type} == test_value"]
    else:
        that = [f"{entity}.config.{config_type} == test_value"]

    tasks = [
        OrderedDict(
            {
                "name": "Ansible | List all known variables and facts",
                "debug": OrderedDict({"var": "hostvars[inventory_hostname]"}),
            }
        ),
        OrderedDict({"name": "Assert config", "assert": OrderedDict({"that": that})}),
    ]

    sent_value, test_value = SENT_TEST_VALUE[config_type](
        name, entity, config_type, is_required, is_default, sent_value_type
    )

    playbook_vars = {"sent_value": sent_value, "test_value": test_value}

    body = [
        OrderedDict(
            {
                "name": f"action_{entity}_{name}",
                "hosts": f"host_{name}",
                "gather_facts": False,
                "vars": playbook_vars,
                "tasks": tasks,
            }
        )
    ]

    return body


def run():  # pylint: disable=too-many-locals
    products = (IS_REQUIRED, IS_DEFAULTS, TYPES, SENT_VALUES_TYPE)
    for is_required, is_default, config_type, sent_value_type in product(*products):
        exclude_empty_value = ["boolean", "integer", "float", "option"]
        if config_type in exclude_empty_value and sent_value_type == "empty_value":
            continue
        if is_required:
            required_name = "required"
        else:
            required_name = "not_required"

        if is_default:
            default_name = "with_default"
        else:
            default_name = "without_default"

        name = f"{config_type}_{required_name}_{default_name}_sent_{sent_value_type}"

        for entity in ["cluster", "provider"]:
            path = f"{required_name}/{default_name}/sent_{sent_value_type}/{config_type}/{entity}/"
            os.makedirs(os.path.join(os.getcwd(), path), exist_ok=True)

            if entity == "cluster":
                additional_entity = "service"
            else:
                additional_entity = "host"

            entity_config = config_generate(f"{entity}_{name}", entity, config_type, is_required, is_default)
            additional_entity_config = config_generate(
                f"{additional_entity}_{name}",
                additional_entity,
                config_type,
                is_required,
                is_default,
            )

            config = [entity_config, additional_entity_config]
            write_yaml(f"{path}config.yaml", config)

            entity_action = action_generate(name, entity, config_type, is_required, is_default, sent_value_type)
            write_yaml(f"{path}{entity}_action.yaml", entity_action)

            additional_entity_action = action_generate(
                name, additional_entity, config_type, is_required, is_default, sent_value_type
            )
            write_yaml(f"{path}{additional_entity}_action.yaml", additional_entity_action)

            if config_type == "file":
                for file_name in [entity, additional_entity]:
                    with open(f"{path}{file_name}_file", "w", encoding="utf_8") as f:
                        f.write("file content\n")

            if config_type == "structure":
                schema = OrderedDict(
                    {
                        "root": OrderedDict({"match": "list", "item": "country_code"}),
                        "country_code": OrderedDict(
                            {
                                "match": "dict",
                                "items": OrderedDict({"country": "string", "code": "integer"}),
                            }
                        ),
                        "string": OrderedDict({"match": "string"}),
                        "integer": OrderedDict({"match": "int"}),
                    }
                )
                write_yaml(f"{path}schema.yaml", schema)


if __name__ == "__main__":
    run()
