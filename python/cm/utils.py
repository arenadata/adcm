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


def dict_to_list_of_lists(dict_: dict) -> list:
    return [[k, v] for k, v in dict_.items()]


def flat_list_to_list_of_dicts(list_):
    if isinstance(list_, str):
        list_ = eval_str(list_)

    if not isinstance(list_, list):
        raise RuntimeError
    elif all(isinstance(i, dict) for i in list_):
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
