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

import json
import os
from collections.abc import Mapping
from pathlib import Path
from secrets import token_hex
from typing import Any, Iterable

from django.conf import settings


def dict_json_get_or_create(path: str | Path, field: str, value: Any = None) -> Any:
    with open(path, encoding=settings.ENCODING_UTF_8) as f:
        data = json.load(f)

    if field not in data:
        data[field] = value
        with open(path, "w", encoding=settings.ENCODING_UTF_8) as f:
            json.dump(data, f)

    return data[field]


def get_adcm_token() -> str:
    if not settings.ADCM_TOKEN_FILE.is_file():
        settings.ADCM_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(file=settings.ADCM_TOKEN_FILE, mode="w", encoding=settings.ENCODING_UTF_8) as f:
            f.write(token_hex(20))

    with open(file=settings.ADCM_TOKEN_FILE, encoding=settings.ENCODING_UTF_8) as f:
        adcm_token = f.read().strip()
        adcm_token.encode(encoding="idna").decode(encoding=settings.ENCODING_UTF_8)

    return adcm_token


def get_env_with_venv_path(venv: str, existing_env: dict | None = None) -> dict:
    if existing_env is None:
        existing_env = os.environ.copy()

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


def obj_ref(obj: type["ADCMEntity"]) -> str:
    if hasattr(obj, "name"):
        name = obj.name
    elif hasattr(obj, "fqdn"):
        name = obj.fqdn
    else:
        name = obj.prototype.name

    return f'{obj.prototype.type} #{obj.id} "{name}"'
