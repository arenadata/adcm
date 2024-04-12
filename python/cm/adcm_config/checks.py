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

from typing import Any

from django.conf import settings

from cm.adcm_config.utils import config_is_ro, group_keys_to_flat, proto_ref
from cm.checker import FormatError, SchemaError, process_rule
from cm.errors import AdcmEx
from cm.models import GroupConfig, Prototype, StagePrototype
from cm.services.bundle import is_path_correct


def check_agreement_group_attr(group_keys: dict, custom_group_keys: dict, spec: dict) -> None:
    flat_group_keys = group_keys_to_flat(origin=group_keys, spec=spec)
    flat_custom_group_keys = group_keys_to_flat(origin=custom_group_keys, spec=spec)
    for key, value in flat_custom_group_keys.items():
        if not value and flat_group_keys[key]:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"the `{key}` field cannot be included in the group")


def check_group_keys_attr(attr: dict, spec: dict, group_config: GroupConfig) -> None:
    if "group_keys" not in attr:
        raise AdcmEx(code="ATTRIBUTE_ERROR", msg='`attr` must contain "group_keys" key')

    group_keys = attr.get("group_keys")
    _, custom_group_keys = group_config.create_group_keys(config_spec=group_config.get_config_spec())
    check_structure_for_group_attr(group_keys=group_keys, spec=spec, key_name="group_keys")
    check_agreement_group_attr(group_keys=group_keys, custom_group_keys=custom_group_keys, spec=spec)


def check_attr(
    proto: Prototype,
    obj,
    attr: dict,
    spec: dict,
    current_attr: dict | None = None,
) -> None:
    is_group_config = False
    if isinstance(obj, GroupConfig):
        is_group_config = True

    ref = proto_ref(prototype=proto)
    allowed_key = ("active",)
    if not isinstance(attr, dict):
        raise AdcmEx(code="ATTRIBUTE_ERROR", msg="`attr` should be a map")

    for key in attr:
        if key in ["group_keys", "custom_group_keys"]:
            if not is_group_config:
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"not allowed key `{key}` for object ({ref})")
            continue

        if f"{key}/" not in spec:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key}` group in the config ({ref})")

        if spec[f"{key}/"].type != "group":
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"config key `{key}` is not a group ({ref})")

    for value in spec.values():
        key = value.name
        if value.type == "group" and "activatable" in value.limits:
            if key not in attr:
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key}` group in the `attr`")

            if not isinstance(attr[key], dict):
                raise AdcmEx(
                    code="ATTRIBUTE_ERROR",
                    msg=f"value of attribute `{key}` should be a map ({ref})",
                )

            for attr_key in attr[key]:
                if attr_key not in allowed_key:
                    raise AdcmEx(
                        code="ATTRIBUTE_ERROR",
                        msg=f"not allowed key `{attr_key}` of attribute `{key}` ({ref})",
                    )

                if not isinstance(attr[key]["active"], bool):
                    raise AdcmEx(
                        code="ATTRIBUTE_ERROR",
                        msg=f"value of key `active` of attribute `{key}` should be boolean ({ref})",
                    )

                if (
                    current_attr is not None
                    and (current_attr[key]["active"] != attr[key]["active"])
                    and config_is_ro(obj=obj, key=key, limits=value.limits)
                ):
                    raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=f"config key {key} of {ref} is read only")

    if is_group_config:
        check_group_keys_attr(attr=attr, spec=spec, group_config=obj)


def check_structure_for_group_attr(group_keys: dict, spec: dict, key_name: str) -> None:
    flat_group_attr = group_keys_to_flat(origin=group_keys, spec=spec)
    for key, value in flat_group_attr.items():
        if key not in spec:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid `{key}` field in `{key_name}`")

        if spec[key].type == "group":
            if not (
                isinstance(value, bool)
                and "activatable" in spec[key].limits
                or value is None
                and "activatable" not in spec[key].limits
            ):
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid type `value` field in `{key}`")
        else:
            if not isinstance(value, bool):
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid type `{key}` field in `{key_name}`")

    for key, value in spec.items():
        if value.type != "group" and key not in flat_group_attr:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"there is no `{key}` field in `{key_name}`")


def _check_empty_values(key: str, current: dict, new: dict) -> bool:
    key_in_config = key in current and key in new
    if key_in_config and (
        (bool(current[key]) is False and new[key] is None) or (current[key] is None and bool(new[key]) is False)
    ):
        return True

    return False


def _check_str(value: Any, idx: Any, key: str, subkey: str, ref: str, label: str):
    if not isinstance(value, str):
        raise AdcmEx(
            code="CONFIG_VALUE_ERROR",
            msg=f'{label} ("{value}") of element "{idx}" of config key "{key}/{subkey}"' f" should be string ({ref})",
        )


def check_config_type(
    prototype: StagePrototype | Prototype,
    key: str,
    subkey: str,
    spec: dict,
    value: Any,
    default: bool = False,
    inactive: bool = False,
) -> None:
    ref = proto_ref(prototype=prototype)
    label = "Default value" if default else "Value"

    tmpl1 = f'{label} of config key "{key}/{subkey}" {{}} ({ref})'
    tmpl2 = f'{label} ("{value}") of config key "{key}/{subkey}" {{}} ({ref})'
    should_not_be_empty = "should be not empty"

    if (
        value is None
        or (spec["type"] == "map" and value == {})
        or (spec["type"] == "secretmap" and value == {})
        or (spec["type"] == "list" and value == [])
    ):
        if inactive:
            return

        if "required" in spec and spec["required"]:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("is required"))

        return

    if (
        isinstance(value, (list, dict))
        and spec["type"] not in settings.STACK_COMPLEX_FIELD_TYPES
        and spec["type"] != "group"
    ):
        raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be flat"))

    if spec["type"] == "list":
        if not isinstance(value, list):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be an array"))

        if "required" in spec and spec["required"] and value == []:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        for i, _value in enumerate(value):
            _check_str(value=_value, idx=i, key=key, subkey=subkey, ref=ref, label=label)

    if spec["type"] in {"map", "secretmap"}:
        if not isinstance(value, dict):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be a map"))

        if "required" in spec and spec["required"] and value == {}:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        for value_key, value_value in value.items():
            _check_str(value=value_value, idx=value_key, key=key, subkey=subkey, ref=ref, label=label)

    if spec["type"] in ("string", "password", "text", "secrettext"):
        if not isinstance(value, str):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be string"))

        if "required" in spec and spec["required"] and value == "":
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

    if spec["type"] in {"file", "secretfile"}:
        if not isinstance(value, str):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be string"))

        if value == "":
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        if default:
            if len(value) > 2048:
                raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("is too long"))

            if not is_path_correct(value):
                # todo looks like it's only applicable to bundle parsing, not for any other stage
                raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("has unsupported path format"))

    if spec["type"] == "structure":
        schema = spec["limits"]["yspec"]
        try:
            process_rule(data=value, rules=schema, name="root")
        except FormatError as e:
            msg = tmpl1.format(f"yspec error: {str(e)} at block {e.data}")
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=msg) from e
        except SchemaError as e:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=f"yspec error: {str(e)}") from e

    if spec["type"] == "boolean" and not isinstance(value, bool):
        raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be boolean"))

    if spec["type"] == "integer" and not isinstance(value, int):
        raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be integer"))

    if spec["type"] == "float" and not isinstance(value, (int, float)):
        raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be float"))

    if spec["type"] == "integer" or spec["type"] == "float":
        limits = spec["limits"]
        if "min" in limits and value < limits["min"]:
            msg = f'should be more than {limits["min"]}'
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

        if "max" in limits and value > limits["max"]:
            msg = f'should be less than {limits["max"]}'
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

    if spec["type"] == "option":
        option = spec["limits"]["option"]

        if value not in option.values():
            msg = f'not in option list: "{option.values()}"'
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

    if spec["type"] == "variant":
        source = spec["limits"]["source"]
        if source["strict"]:
            if source["type"] == "inline" and value not in source["value"]:
                msg = f'not in variant list: "{source["value"]}"'
                raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

            if not default and source["type"] in ("config", "builtin") and value not in source["value"]:
                msg = f'not in variant list: "{source["value"]}"'
                raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))
