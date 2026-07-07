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
from rest_framework.status import HTTP_409_CONFLICT

from cm.errors import AdcmEx
from cm.legacy.adcm_config.utils import config_is_ro, group_keys_to_flat, proto_ref
from cm.legacy.checker import FormatError, SchemaError, process_rule
from cm.legacy.services.bundle import is_path_correct
from cm.legacy.services.config.patterns import Pattern
from cm.models import ConfigHostGroup, Prototype, PrototypeConfig


def check_agreement_group_attr(group_keys: dict, custom_group_keys: dict, spec: dict) -> None:
    flat_group_keys = group_keys_to_flat(origin=group_keys, spec=spec)
    flat_custom_group_keys = group_keys_to_flat(origin=custom_group_keys, spec=spec)
    for key, value in flat_custom_group_keys.items():
        if not value and flat_group_keys[key]:
            key_display_name = _get_full_display_name_from_flat_spec(config=spec[key], spec=spec)
            raise AdcmEx(
                code="ATTRIBUTE_ERROR",
                msg=f"the `{key_display_name}` field cannot be included in the group",
            )


def check_group_keys_attr(attr: dict, spec: dict, config_host_group: ConfigHostGroup) -> None:
    if "group_keys" not in attr:
        raise AdcmEx(code="ATTRIBUTE_ERROR", msg='`attr` must contain "group_keys" key')

    group_keys = attr.get("group_keys")
    _, custom_group_keys = config_host_group.create_group_keys(config_spec=config_host_group.get_config_spec())
    check_structure_for_group_attr(group_keys=group_keys, spec=spec, key_name="group_keys")
    check_agreement_group_attr(group_keys=group_keys, custom_group_keys=custom_group_keys, spec=spec)


def check_attr(
    proto: Prototype,
    obj,
    attr: dict,
    spec: dict,
    current_attr: dict | None = None,
) -> None:
    is_host_group = False
    if isinstance(obj, ConfigHostGroup):
        is_host_group = True

    ref = proto_ref(prototype=proto)
    allowed_key = ("active",)
    if not isinstance(attr, dict):
        raise AdcmEx(code="ATTRIBUTE_ERROR", msg="`attr` should be a map")

    for key in attr:
        if key in ["group_keys", "custom_group_keys"]:
            if not is_host_group:
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"not allowed key `{key}` for object ({ref})")
            continue

        spec_key = f"{key}/"
        if spec_key not in spec:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key}` group in the config ({ref})")

        key_display_name = _get_key_display_name(spec=spec[spec_key], key=key)
        if spec[spec_key].type != "group":
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"config key `{key_display_name}` is not a group ({ref})")

    for value in spec.values():
        key = value.name
        if value.type == "group" and "activatable" in value.limits:
            key_display_name = _get_key_display_name(spec=value, key=key)
            if key not in attr:
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key_display_name}` group in the `attr`")

            if not isinstance(attr[key], dict):
                raise AdcmEx(
                    code="ATTRIBUTE_ERROR",
                    msg=f"value of attribute `{key_display_name}` should be a map ({ref})",
                )

            for attr_key in attr[key]:
                if attr_key not in allowed_key:
                    raise AdcmEx(
                        code="ATTRIBUTE_ERROR",
                        msg=f"not allowed key `{attr_key}` of attribute `{key_display_name}` ({ref})",
                    )

                if not isinstance(attr[key]["active"], bool):
                    raise AdcmEx(
                        code="ATTRIBUTE_ERROR",
                        msg=f"value of key `active` of attribute `{key_display_name}` should be boolean ({ref})",
                    )

                if (
                    current_attr is not None
                    and (current_attr[key]["active"] != attr[key]["active"])
                    and config_is_ro(obj=obj, key=key, limits=value.limits)
                ):
                    raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=f"config key {key_display_name} of {ref} is read only")

    if is_host_group:
        check_group_keys_attr(attr=attr, spec=spec, config_host_group=obj)


def check_structure_for_group_attr(group_keys: dict, spec: dict, key_name: str) -> None:
    flat_group_attr = group_keys_to_flat(origin=group_keys, spec=spec)
    for key, value in flat_group_attr.items():
        if key not in spec:
            raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid `{key}` field in `{key_name}`")

        config = spec[key]
        key_display_name = _get_full_display_name_from_flat_spec(config=config, spec=spec)
        if config.type == "group":
            if not (
                isinstance(value, bool)
                and "activatable" in config.limits
                or value is None
                and "activatable" not in config.limits
            ):
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid type `value` field in `{key_display_name}`")
        else:
            if not isinstance(value, bool):
                raise AdcmEx(code="ATTRIBUTE_ERROR", msg=f"invalid type `{key_display_name}` field in `{key_name}`")

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


def _get_full_display_name_from_flat_spec(config: PrototypeConfig, spec: dict[str, PrototypeConfig]) -> str:
    if not config.subname:
        return config.display_name or config.name

    group_config = spec.get(f"{config.name}/")
    group_display_name = group_config.display_name if group_config and group_config.display_name else config.name
    sub_display_name = config.display_name or config.subname
    return f"{group_display_name}/{sub_display_name}"


def _get_key_display_name(spec: dict | PrototypeConfig, key: str, subkey: str = "") -> str:
    default_name = f"{key}/{subkey}" if subkey else f"{key}/"
    if isinstance(spec, PrototypeConfig):
        return spec.display_name or default_name

    return spec.get("full_display_name", default_name)


def _check_str(value: Any, idx: Any, key_name: str, ref: str, label: str):
    if not isinstance(value, str):
        raise AdcmEx(
            code="CONFIG_VALUE_ERROR",
            msg=f'{label} ("{value}") of element "{idx}" of config key "{key_name}" should be string ({ref})',
        )


def check_config_type(
    prototype: Prototype,
    key: str,
    subkey: str,
    spec: dict,
    value: Any,
    default: bool = False,
    inactive: bool = False,
) -> None:
    ref = proto_ref(prototype=prototype)
    label = "Default value" if default else "Value"
    key_display_name = _get_key_display_name(spec=spec, key=key, subkey=subkey)

    tmpl1 = f'{label} of config key "{key_display_name}" {{}} ({ref})'
    tmpl2 = f'{label} ("{value}") of config key "{key_display_name}" {{}} ({ref})'
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
        isinstance(value, list | dict)
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
            _check_str(value=_value, idx=i, key_name=key_display_name, ref=ref, label=label)

    if spec["type"] in {"map", "secretmap"}:
        if not isinstance(value, dict):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be a map"))

        if "required" in spec and spec["required"] and value == {}:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        for value_key, value_value in value.items():
            _check_str(value=value_value, idx=value_key, key_name=key_display_name, ref=ref, label=label)

    if spec["type"] in ("string", "password", "text", "secrettext"):
        if not isinstance(value, str):
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be string"))

        if "required" in spec and spec["required"] and value == "":
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        if (
            (saved_pattern := spec["limits"].get("pattern"))
            and not value.startswith(settings.ANSIBLE_VAULT_HEADER)
            and not Pattern(saved_pattern).matches(value)
        ):
            message = f"The value of {key_display_name} config parameter does not match pattern: {saved_pattern}"
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg=message, http_code=HTTP_409_CONFLICT)

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

    if spec["type"] == "float" and not isinstance(value, int | float):
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
