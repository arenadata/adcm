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
from pathlib import Path
from secrets import token_hex
from typing import Any

from django.conf import settings
from yaml import safe_load


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

    return adcm_token


def get_attr(config: dict) -> dict:
    attr = {}

    if all(
        (
            "activatable" in config["limits"],
            "active" in config["limits"],
            config["type"] == "group",
            config.get("name"),
        ),
    ):
        attr[config["name"]] = config["limits"]

    return attr


def _get_limits(config: dict, root_path: str) -> dict:  # noqa: C901
    # pylint: disable=too-many-branches
    limits = {}

    if "yspec" in config and config["type"] in settings.STACK_COMPLEX_FIELD_TYPES:
        with open(file=Path(root_path, config["yspec"]), encoding=settings.ENCODING_UTF_8) as f:
            data = f.read()

        limits.update(**safe_load(stream=data))

    if "option" in config and config["type"] == "option":
        limits["option"] = config["option"]

    if "source" in config and config["type"] == "variant":
        variant_type = config["source"]["type"]
        source = {"type": variant_type, "args": None}

        if "strict" in config["source"]:
            source["strict"] = config["source"]["strict"]
        else:
            source["strict"] = True

        if variant_type == "inline":
            source["value"] = config["source"]["value"]
        elif variant_type in ("config", "builtin"):
            source["name"] = config["source"]["name"]

        if variant_type == "builtin":
            if "args" in config["source"]:
                source["args"] = config["source"]["args"]

        limits["source"] = source

    if "activatable" in config and config["type"] == "group":
        limits.update(
            activatable=config["activatable"],
            active=False,
        )

        if "active" in config:
            limits.update(active=config["active"])

    if config["type"] in settings.STACK_NUMERIC_FIELD_TYPES:
        if "min" in config:
            limits["min"] = config["min"]

        if "max" in config:
            limits["max"] = config["max"]

    for label in ("read_only", "writable"):
        if label in config:
            limits[label] = config[label]

    return limits


def normalize_config(config: dict, root_path: str, name: str = "", subname: str = "") -> list[dict]:
    config_list = [config]

    name = name or config["name"]
    config["name"] = name
    if subname:
        config["subname"] = subname

    if config.get("display_name") is None:
        config["display_name"] = subname or name

    config["limits"] = _get_limits(config=config, root_path=root_path)

    if "subs" in config:
        for subconf in config["subs"]:
            config_list.extend(
                normalize_config(config=subconf, root_path=root_path, name=name, subname=subconf["name"]),
            )

    for field in settings.TEMPLATE_CONFIG_DELETE_FIELDS:
        if field in config:
            del config[field]

    return config_list
