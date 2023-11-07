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
from typing import Callable

import ruyaml

# pylint: disable=W0212


MATCH_DICT_RESERVED_DIRECTIVES = ("invisible_items",)


def _check_match_dict_reserved(data, rules, rule, path, parent=None):
    if any(directive in rules[rule] for directive in MATCH_DICT_RESERVED_DIRECTIVES):
        raise FormatError(
            path=path,
            message=f'{MATCH_DICT_RESERVED_DIRECTIVES} allowed only in "match: dict" sections',
            data=data,
            rule=rule,
            parent=parent,
        )


def round_trip_load(stream, version=None, preserve_quotes=None, allow_duplicate_keys=False):
    """
    Parse the first YAML document in a stream and produce the corresponding Python object.

    This is a replace for ruyaml.round_trip_load() function which can switch off
    duplicate YAML keys error
    """

    loader = ruyaml.RoundTripLoader(stream, version, preserve_quotes=preserve_quotes)
    loader._constructor.allow_duplicate_keys = allow_duplicate_keys
    try:
        return loader._constructor.get_single_data()
    finally:
        loader._parser.dispose()
        try:
            loader._reader.reset_reader()
        except AttributeError:
            pass
        try:
            loader._scanner.reset_scanner()
        except AttributeError:
            pass


class FormatError(Exception):
    def __init__(self, path, message, data=None, rule=None, parent=None, caused_by=None):
        self.path = path
        self.message = message
        self.data = data
        self.rule = rule
        self.errors = caused_by
        self.parent = parent
        self.line = None
        if isinstance(data, ruyaml.comments.CommentedBase):
            self.line = data.lc.line
        elif parent and isinstance(parent, ruyaml.comments.CommentedBase):
            self.line = parent.lc.line
        super().__init__(message)


class SchemaError(Exception):
    pass


class DataError(Exception):
    pass


def check_type(data, data_type, path, rule=None, parent=None):
    if not isinstance(data, data_type) or (isinstance(data, bool) and data_type is int):
        msg = f"Object should be a {str(data_type)}"
        if path:
            last = path[-1]
            msg = f'{last[0]} "{last[1]}" should be a {str(data_type)}'
        raise FormatError(path, msg, data, rule, parent)


def check_match_type(match, data, data_type, path, rule, parent=None):
    if not isinstance(data, data_type):
        msg = f'Input data for {match}, rule "{rule}" should be {str(data_type)}"'
        raise FormatError(path, msg, data, rule, parent)


def match_none(data, rules, rule, path, parent=None):
    _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)

    if data is not None:
        msg = "Object should be empty"
        if path:
            last = path[-1]
            msg = f'{last[0]} "{last[1]}" should be empty'
        raise FormatError(path, msg, data, rule, parent)


def match_any(data, rules, rule, path, parent=None):  # pylint: disable=unused-argument
    pass


def match_list(data, rules, rule, path, parent=None):
    _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)
    check_match_type("match_list", data, list, path, rule, parent)

    for i, item in enumerate(data):
        process_rule(item, rules, rules[rule]["item"], path + [("Value of list index", i)], parent)

    return True


def match_dict(data, rules, rule, path, parent=None):
    check_match_type("match_dict", data, dict, path, rule, parent)

    if "required_items" in rules[rule]:
        for i in rules[rule].get("required_items", []):
            if i not in data:
                raise FormatError(path, f'There is no required key "{i}" in map.', data, rule)

    for key in data:
        new_path = path + [("Value of map key", key)]

        if "items" in rules[rule] and key in rules[rule]["items"]:
            process_rule(data[key], rules, rules[rule]["items"][key], new_path, data)
        elif "default_item" in rules[rule]:
            process_rule(data[key], rules, rules[rule]["default_item"], new_path, data)
        else:
            msg = f'Map key "{key}" is not allowed here (rule "{rule}")'

            raise FormatError(path, msg, data, rule)


def match_dict_key_selection(data, rules, rule, path, parent=None):
    _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)
    check_match_type("dict_key_selection", data, dict, path, rule, parent)

    key = rules[rule]["selector"]
    if key not in data:
        msg = f'There is no key "{key}" in map.'
        raise FormatError(path, msg, data, rule, parent)
    value = data[key]
    if value in rules[rule]["variants"]:
        process_rule(data, rules, rules[rule]["variants"][value], path, parent)
    elif "default_variant" in rule:
        process_rule(data, rules, rules[rule]["default_variant"], path, parent)
    else:
        msg = f'Value "{value}" is not allowed for map key "{key}".'
        raise FormatError(path, msg, data, rule, parent)


def match_one_of(data, rules, rule, path, parent=None):
    _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)

    errors = []
    sub_errors = []
    for obj in rules[rule]["variants"]:
        try:
            process_rule(data, rules, obj, path, parent)
        except FormatError as e:
            if e.errors:
                sub_errors += e.errors
            errors.append(e)
    if len(errors) == len(rules[rule]["variants"]):
        errors += sub_errors
        msg = f'None of the variants for rule "{rule}" match'
        raise FormatError(path, msg, data, rule, parent, caused_by=errors)


def match_set(data, rules, rule, path, parent=None):
    _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)

    if data not in rules[rule]["variants"]:
        msg = f'Value "{data}" not in set {rules[rule]["variants"]}'
        raise FormatError(path, msg, data, rule, parent=parent)


def match_simple_type(obj_type: type | tuple[type, ...]) -> Callable:
    def match(data, rules, rule, path, parent=None):
        _check_match_dict_reserved(data=data, rules=rules, rule=rule, path=path, parent=parent)
        check_type(data, obj_type, path, rule, parent=parent)

    return match


MATCH = {
    "list": match_list,
    "dict": match_dict,
    "one_of": match_one_of,
    "dict_key_selection": match_dict_key_selection,
    "set": match_set,
    "string": match_simple_type(str),
    "bool": match_simple_type(bool),
    "int": match_simple_type(int),
    "float": match_simple_type((float, int)),
    "none": match_none,
    "any": match_any,
}


def check_rule(rules):
    if not isinstance(rules, dict):
        return False, "YSpec should be a map"
    if "root" not in rules:
        return False, 'YSpec should has "root" key'
    if "match" not in rules["root"]:
        return False, 'YSpec should has "match" subkey of "root" key'
    return True, ""


def process_rule(data, rules, name, path=None, parent=None):
    if path is None:
        path = []

    if name not in rules:
        raise SchemaError(f"There is no rule {name} in schema.")

    rule = rules[name]
    if "match" not in rule:
        raise SchemaError(f"There is no mandatory match attr in rule {rule} in schema.")

    match = rule["match"]
    if match not in MATCH:
        raise SchemaError(f"Unknown match {match} from schema. Impossible to handle that.")

    MATCH[match](data, rules, name, path=path, parent=parent)


def check(data, rules):
    if not isinstance(data, ruyaml.comments.CommentedBase):
        raise DataError("You should use ruyaml.round_trip_load() to parse data yaml")
    if not isinstance(rules, ruyaml.comments.CommentedBase):
        raise SchemaError("You should use ruyaml.round_trip_load() to parse schema yaml")
    process_rule(data, rules, "root")
