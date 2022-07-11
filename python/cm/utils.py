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


import ast
import json
from collections import OrderedDict


def eval_str(str_: str):
    if not isinstance(str_, str):
        return str_
    try:
        return json.loads(str_)
    except json.decoder.JSONDecodeError:
        return ast.literal_eval(str_)


#####
# Structure type field related stuff
#####


def dict_to_list_of_lists(dict_: dict) -> list:
    return [[k, v] for k, v in dict_.items()]


def flat_list_to_list_of_dicts(list_):
    if isinstance(list_, str):
        list_ = eval_str(list_)

    if not isinstance(list_, list):
        raise RuntimeError

    if all(isinstance(i, OrderedDict) for i in list_):
        return list_

    res = []
    if all(isinstance(i, list) for i in list_) and not all(
        isinstance(i, str) for sublist in list_ for i in sublist
    ):
        for item in list_:
            res.append(OrderedDict(item))
    elif all(isinstance(i, list) for i in list_) and all(
        isinstance(i, str) for sublist in list_ for i in sublist
    ):
        res = OrderedDict(list_)
    else:
        raise ValueError

    return res


def get_structure_repr(structure, fmt):
    from cm.logger import log

    log.critical(f'get_structure_repr structure\n{structure}\nfmt\n{fmt}')
    if not structure:
        return None

    if fmt not in ('list_of_lists', 'list_of_dicts') or not isinstance(structure, list):
        raise ValueError

    if all(isinstance(i, dict) for i in structure):
        inp_fmt = 'list_of_dicts'
    elif all(isinstance(i, list) for i in structure):
        inp_fmt = 'list_of_lists'
    else:
        raise ValueError
    log.critical(f'get_structure_repr inp_fmt\n{inp_fmt}')

    convert_func = lambda x: x

    if fmt == 'list_of_lists' and not all(isinstance(i, list) for i in structure):
        convert_func = dict_to_list_of_lists
    elif not all(isinstance(i, OrderedDict) for i in structure):
        convert_func = flat_list_to_list_of_dicts

    log.critical(f'get_structure_repr convert_func\n{convert_func}')
    return convert_func(structure)


#####
# End
#####
