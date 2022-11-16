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
Dummy data generators
"""

from random import choice, randint

import allure
from genson import SchemaBuilder
from rstr.xeger import Xeger
from tests.api.utils.tools import random_string


def gen_int(prop=None):
    """
    Generate int value
    :param prop: dict
    Example: {'minimum': 10, 'maximum': 154}
    """
    if not prop:
        prop = {}
    min_value = prop.get("minimum", 0)
    max_value = prop.get("maximum", (2**63) - 1.0)
    return randint(a=min_value, b=max_value)


def gen_string(prop=None):
    """
    Generate String value
    :param prop: dict
    Examples: {'minLength': 10, 'maxLength': 154}
              {'pattern': '^\\d+\\w*$'}
    """
    if not prop:
        prop = {}
    min_length = prop.get("minLength", 1)
    max_length = prop.get("maxLength", 1024)
    pattern = prop.get("pattern", None)
    if pattern:
        if min_length or max_length:
            # TODO implement pattern with min/max length
            raise NotImplementedError
        return Xeger().xeger(pattern)
    return random_string(strlen=randint(min_length, max_length))


# pylint: disable=unused-argument
def gen_bool(prop=None):
    """
    Generate Boolean value
    :param prop: for capability only
    """
    return bool(randint(0, 1))


def gen_enum(prop):
    """
    Generate Enum value
    :param prop: dict
    Example: {'enum': ['test', 'example', 'random']}
    """
    enum = prop["enum"]
    return choice(enum)


def _gen_anything():
    return choice([gen_int(), gen_string(), gen_bool(), None])


def _should_include(key, required_list):
    if key in required_list:
        return True
    return bool(randint(0, 1))


def gen_array(prop):
    """
    Generate Array value
    :param prop: dict
    Example: {'minItems': 1, 'maxItems': 1, 'items': {'type': 'string'} }
    """
    if not prop:
        prop = {}
    min_items = prop.get("minItems", 0)
    max_items = prop.get("maxItems", 10)
    if prop.get("items", {}).get("type", False) is not False:
        generator = _get_generator(prop.get("items"))
    else:
        generator = _gen_anything
    return [generator() for _ in range(min_items, max_items)]


def _gen_any_obj():
    return {random_string(): _gen_anything() for _ in range(randint(1, 10))}


def gen_object(prop=None):
    """
    Generate Object value
    :param prop: dict
    Example: object description from jsonSchema
    {
        "type": "object",
        "properties": {
            "DB Name": {
                "type": "string"
            },
            "Segment": {
                "type": "integer"
            },
            "Full backup": {
                "type": "boolean"
            }
        },
        "additionalProperties": false,
        "required": [
            "DB Name",
            "Segment"
        ]
    }
    """
    if not prop:
        prop = {}
    required = prop.get("required", [])
    output = {}
    prop_key = "properties"
    if prop.get("properties", None) is None:
        if prop.get("additionalProperties") is True or prop.get("additionalProperties") == {}:
            return _gen_any_obj()
        return {key: gen_string() for key in prop.get("additionalProperties", {})}

    for k in prop[prop_key].keys():
        json_prop = prop[prop_key][k]

        if _should_include(k, required):
            output[k] = _get_generator(json_prop)

        if k == "duration":
            msg = "Set 'duration' property to 2 sec in fake generated data by JSON schema"
            with allure.step(msg):
                output[k] = 2

    return output


def _gen_one_of(prop):
    possible_values = []
    for value in prop["oneOf"]:
        possible_values.append(_get_generator(value))

    return choice(possible_values)


def _get_generator(prop):
    disp = {
        "string": gen_string,
        "integer": gen_int,
        "number": gen_int,
        "boolean": gen_bool,
        "object": gen_object,
        "array": gen_array,
        "null": lambda x: None,
    }

    enum = prop.get("enum", None)
    if enum is not None:
        return gen_enum(prop)

    one_of = prop.get("oneOf", None)
    if one_of is not None:
        return _gen_one_of(prop)

    json_type = prop.get("type", None)
    if json_type is None:
        raise JsonTypeError(f"Could not find type in prop {prop}")

    if isinstance(json_type, list):
        if "null" in json_type:
            json_type.remove("null")
        json_type = choice(json_type)

    return disp[json_type](prop)


def generate_json_from_schema(json_schema):
    """
    Generate Json Object value from schema
    """
    if not json_schema:
        return _gen_any_obj()
    return _get_generator(json_schema)


def build_schema_by_json(json):
    """
    Build Json Schema by json value
    """
    sch_builder = SchemaBuilder()
    sch_builder.add_object(json)
    return sch_builder.to_schema()


class JsonTypeError(Exception):
    """Raised when there is no type in Json schema entry"""
