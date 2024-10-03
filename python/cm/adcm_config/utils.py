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

from pathlib import Path
from typing import Mapping, Union

from django.conf import settings

from cm.errors import raise_adcm_ex
from cm.models import (
    Action,
    ADCMEntity,
    ConfigHostGroup,
    Prototype,
    PrototypeConfig,
    StagePrototype,
)


def group_keys_to_flat(origin: dict, spec: dict) -> dict:
    """
    Convert `group_keys` and `custom_group_keys` to flat structure as `<field>/`
     and `<group>/<field>`
    """

    result = {}
    for group_key, group_value in origin.items():
        if isinstance(group_value, Mapping):
            key = f"{group_key}/"
            if key in spec and spec[key].type != "group":
                result[key] = group_value
            else:
                if "fields" not in group_value or "value" not in origin[group_key]:
                    raise_adcm_ex(code="ATTRIBUTE_ERROR", msg="invalid format `group_keys` field")
                result[key] = group_value["value"]

                for _k, _v in origin[group_key]["fields"].items():
                    result[f"{group_key}/{_k}"] = _v
        else:
            result[f"{group_key}/"] = group_value

    return result


def proto_ref(prototype: StagePrototype | Prototype) -> str:
    return f'{prototype.type} "{prototype.name}" {prototype.version}'


def group_is_activatable(spec: PrototypeConfig) -> bool:
    if spec.type != "group":
        return False

    if "activatable" in spec.limits:
        return spec.limits["activatable"]

    return False


def to_flat_dict(config: dict, spec: dict) -> dict:
    flat = {}
    for conf_1 in config:
        if isinstance(config[conf_1], dict):
            key = f"{conf_1}/"
            if key in spec and spec[key].type != "group":
                flat[f'{conf_1}/{""}'] = config[conf_1]
            else:
                for conf_2 in config[conf_1]:
                    flat[f"{conf_1}/{conf_2}"] = config[conf_1][conf_2]
        else:
            flat[f'{conf_1}/{""}'] = config[conf_1]

    return flat


def cook_file_type_name(obj: Union["ADCMEntity", "ConfigHostGroup"], key: str, sub_key: str) -> str:
    if isinstance(obj, ADCMEntity):
        filename = [obj.prototype.type, str(obj.id), key, sub_key]
    elif isinstance(obj, ConfigHostGroup):
        filename = [
            obj.object.prototype.type,
            str(obj.object.id),
            "group",
            str(obj.id),
            key,
            sub_key,
        ]
    else:
        filename = ["task", str(obj.id), key, sub_key]

    return str(Path(settings.FILE_DIR, ".".join(filename)))


def config_is_ro(obj: ADCMEntity | Action, key: str, limits: dict) -> bool:
    if not limits:
        return False

    if not hasattr(obj, "state"):
        return False

    readonly = limits.get("read_only", [])
    writeable = limits.get("writable", [])

    if readonly and writeable:
        raise_adcm_ex(
            code="INVALID_CONFIG_DEFINITION",
            msg=(
                'can not have "read_only" and "writable"'
                f' simultaneously (config key "{key}" of {proto_ref(obj.prototype)})'
            ),
        )

    if readonly == "any":
        return True

    if obj.state in readonly:
        return True

    if writeable == "any":
        return False

    if writeable and obj.state not in writeable:
        return True

    return False


def key_is_required(obj: ADCMEntity | Action, key: str, subkey: str, spec: dict) -> bool:
    if config_is_ro(obj=obj, key=f"{key}/{subkey}", limits=spec.get("limits", "")):
        return False

    if subkey:
        return spec[key][subkey]["required"]

    return spec[key]["required"]


def is_inactive(key: str, attr: dict, flat_spec: dict) -> bool:
    if attr and flat_spec[f"{key}/"].type == "group" and key in attr and "active" in attr[key]:
        return not bool(attr[key]["active"])

    return False


def sub_key_is_required(key: str, attr: dict, flat_spec: dict, spec: dict, obj: ADCMEntity) -> bool:
    if is_inactive(key=key, attr=attr, flat_spec=flat_spec):
        return False

    return any(key_is_required(obj=obj, key=key, subkey=subkey, spec=spec) for subkey in spec[key])
