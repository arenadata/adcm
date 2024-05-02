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

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Iterable, Protocol, TypeVar
import os

ANY = "any"
AVAILABLE = "available"
MASKING = "masking"
MULTI_STATE = "multi_state"
NAME_REGEX = r"[0-9a-zA-Z_\.-]+"
ON_FAIL = "on_fail"
ON_SUCCESS = "on_success"
SET = "set"
STATE = "state"
STATES = "states"
UNAVAILABLE = "unavailable"
UNSET = "unset"


class WithPK(Protocol):
    pk: int


ObjectWithPk = TypeVar("ObjectWithPk", bound=WithPK)


def build_id_object_mapping(objects: Iterable[ObjectWithPk]) -> dict[int, ObjectWithPk]:
    return {object_.pk: object_ for object_ in objects}


def get_env_with_venv_path(venv: str, existing_env: dict | None = None) -> dict:
    if existing_env is None:
        existing_env = os.environ.copy()

    if venv != "default":
        existing_env["PATH"] = f"/adcm/venv/{venv}/bin:{existing_env['PATH']}"

    return existing_env


def deep_merge(origin: dict, renovator: Mapping) -> dict:
    """
    Merge renovator into origin

    >>> o = {'a': 1, 'b': {'c': 1, 'd': 1}}
    >>> r = {'a': 1, 'b': {'c': 2 }}
    >>> deep_merge(o, r) == {'a': 1, 'b': {'c': 2, 'd': 1}}
    """

    for key, value in renovator.items():
        if isinstance(value, Mapping):
            node = origin.setdefault(key, {})
            deep_merge(node, value)
        else:
            origin[key] = value

    return origin


def obj_to_dict(obj: Any, keys: Iterable) -> dict:
    dictionary = {}
    for key in keys:
        if hasattr(obj, key):
            dictionary[key] = getattr(obj, key)

    return dictionary


def dict_to_obj(dictionary: dict, obj: Any, keys: Iterable) -> Any:
    for key in keys:
        setattr(obj, key, dictionary[key])

    return obj


def obj_ref(obj: type["ADCMEntity"]) -> str:  # noqa: F821
    if hasattr(obj, "name"):
        name = obj.name
    elif hasattr(obj, "fqdn"):
        name = obj.fqdn
    else:
        name = obj.prototype.name

    return f'{obj.prototype.type} #{obj.id} "{name}"'


def get_obj_type(obj_type: str) -> str:
    object_names_to_object_types = {
        "adcm": "adcm",
        "cluster": "cluster",
        "cluster object": "service",
        "service component": "component",
        "host provider": "provider",
        "host": "host",
    }
    return object_names_to_object_types[obj_type]


def str_remove_non_alnum(value: str) -> str:
    result = "".join(ch.lower().replace(" ", "-") for ch in value if (ch.isalnum() or ch == " "))
    while result.find("--") != -1:
        result = result.replace("--", "-")
    return result


def deep_get(deep_dict: dict, *nested_keys: str, default: Any) -> Any:
    """
    Safe dict.get() for deep-nested dictionaries
    dct[key1][key2][...] -> _deep_get(dct, key1, key2, ..., default_value)
    """

    val = deepcopy(deep_dict)
    for key in nested_keys:
        try:
            val = val[key]
        except (KeyError, TypeError):
            return default

    return val


def get_on_fail_states(config: dict) -> tuple[str, list[str], list[str]]:
    on_fail = config.get(ON_FAIL, "")

    if isinstance(on_fail, str):
        state_on_fail = on_fail
        multi_state_on_fail_set = []
        multi_state_on_fail_unset = []
    elif isinstance(on_fail, dict):
        state_on_fail = deep_get(on_fail, STATE, default="")
        multi_state_on_fail_set = deep_get(on_fail, MULTI_STATE, SET, default=[])
        multi_state_on_fail_unset = deep_get(on_fail, MULTI_STATE, UNSET, default=[])
    else:
        raise TypeError(f'Unsupported "{ON_FAIL}" type: "{type(on_fail)}"')

    return state_on_fail, multi_state_on_fail_set, multi_state_on_fail_unset
