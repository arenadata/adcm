# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.


import ruyaml


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
    if not isinstance(data, data_type):
        msg = 'Object should be a {}'.format(str(data_type))
        if path:
            last = path[-1]
            msg = '{} "{}" should be a {}'.format(last[0], last[1], str(data_type))
        raise FormatError(path, msg, data, rule, parent)


def check_match_type(match, data, data_type, path, rule, parent=None):
    if not isinstance(data, data_type):
        msg = f'Input data for {match}, rule "{rule}" should be {str(data_type)}"'
        raise FormatError(path, msg, data, rule, parent)


def match_none(data, rules, rule, path, parent=None):
    if data is not None:
        msg = 'Object should be empty'
        if path:
            last = path[-1]
            msg = '{} "{}" should be empty'.format(last[0], last[1])
        raise FormatError(path, msg, data, rule, parent)


def match_any(data, rules, rule, path, parent=None):
    pass


def match_list(data, rules, rule, path, parent=None):
    check_match_type('match_list', data, list, path, rule, parent)
    for i, v in enumerate(data):
        process_rule(v, rules, rules[rule]['item'], path + [('Value of list index', i)], parent)
    return True


def match_dict(data, rules, rule, path, parent=None):
    check_match_type('match_dict', data, dict, path, rule, parent)
    if 'required_items' in rules[rule]:
        for i in rules[rule]['required_items']:
            if i not in data:
                raise FormatError(path, f'There is no required key "{i}" in map.', data, rule)
    for k in data:
        new_path = path + [('Value of map key', k)]
        if 'items' in rules[rule] and k in rules[rule]['items']:
            process_rule(data[k], rules, rules[rule]['items'][k], new_path, data)
        elif 'default_item' in rules[rule]:
            process_rule(data[k], rules, rules[rule]['default_item'], new_path, data)
        else:
            msg = f'Map key "{k}" is not allowed here (rule "{rule}")'
            raise FormatError(path, msg, data, rule)


def match_dict_key_selection(data, rules, rule, path, parent=None):
    check_match_type('dict_key_selection', data, dict, path, rule, parent)
    key = rules[rule]['selector']
    if key not in data:
        msg = f'There is no key "{key}" in map.'
        raise FormatError(path, msg, data, rule, parent)
    value = data[key]
    if value in rules[rule]['variants']:
        process_rule(data, rules, rules[rule]['variants'][value], path, parent)
    elif 'default_variant' in rule:
        process_rule(data, rules, rules[rule]['default_variant'], path, parent)
    else:
        msg = f'Value "{value}" is not allowed for map key "{key}".'
        raise FormatError(path, msg, data, rule, parent)


def match_one_of(data, rules, rule, path, parent=None):
    errors = []
    sub_errors = []
    for obj in rules[rule]['variants']:
        try:
            process_rule(data, rules, obj, path, parent)
        except FormatError as e:
            if e.errors:
                sub_errors += e.errors
            errors.append(e)
    if len(errors) == len(rules[rule]['variants']):
        errors += sub_errors
        msg = f'None of the variants for rule "{rule}" match'
        raise FormatError(path, msg, data, rule, parent, caused_by=errors)


def match_set(data, rules, rule, path, parent=None):
    if data not in rules[rule]['variants']:
        msg = f'Value "{data}" not in set {rules[rule]["variants"]}'
        raise FormatError(path, msg, data, rule, parent=parent)


def match_simple_type(obj_type):
    def match(data, rules, rule, path, parent=None):
        check_type(data, obj_type, path, rule, parent=parent)
    return match


MATCH = {
    'list': match_list,
    'dict': match_dict,
    'one_of': match_one_of,
    'dict_key_selection': match_dict_key_selection,
    'set': match_set,
    'string': match_simple_type(str),
    'bool': match_simple_type(bool),
    'int': match_simple_type(int),
    'float': match_simple_type(float),
    'none': match_none,
    'any': match_any,
}


def check_rule(rules):
    if not isinstance(rules, dict):
        return (False, 'YSpec should be a map')
    if 'root' not in rules:
        return (False, 'YSpec should has "root" key')
    if 'match' not in rules['root']:
        return (False, 'YSpec should has "match" subkey of "root" key')
    return (True, '')


def process_rule(data, rules, name, path=None, parent=None):
    if path is None:
        path = []
    if name not in rules:
        raise SchemaError(f"There is no rule {name} in schema.")
    rule = rules[name]
    if 'match' not in rule:
        raise SchemaError(f"There is no mandatory match attr in rule {rule} in schema.")
    match = rule['match']
    if match not in MATCH:
        raise SchemaError(f"Unknown match {match} from schema. Donno how to handle that.")

    # print(f'process_rule: {MATCH[match].__name__} "{name}" data: {data}')
    MATCH[match](data, rules, name, path=path, parent=parent)


def check(data, rules):
    if not isinstance(data, ruyaml.comments.CommentedBase):
        raise DataError("You should use ruyaml.round_trip_load() to parse data yaml")
    if not isinstance(rules, ruyaml.comments.CommentedBase):
        raise SchemaError("You should use ruyaml.round_trip_load() to parse schema yaml")
    process_rule(data, rules, 'root')
