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

from typing import Any, Mapping

import yspec.checker
from cm.adcm_config.utils import config_is_ro, group_keys_to_flat, proto_ref
from cm.errors import raise_adcm_ex
from cm.logger import logger
from cm.models import Action, ADCMEntity, GroupConfig, Prototype
from django.conf import settings


def check_agreement_group_attr(group_keys: dict, custom_group_keys: dict, spec: dict) -> None:
    flat_group_keys = group_keys_to_flat(origin=group_keys, spec=spec)
    flat_custom_group_keys = group_keys_to_flat(origin=custom_group_keys, spec=spec)
    for key, value in flat_custom_group_keys.items():
        if not value and flat_group_keys[key]:
            raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"the `{key}` field cannot be included in the group")


def check_group_keys_attr(attr: dict, spec: dict, group_config: GroupConfig) -> None:
    if "group_keys" not in attr:
        raise_adcm_ex(code="ATTRIBUTE_ERROR", msg='`attr` must contain "group_keys" key')

    group_keys = attr.get("group_keys")
    _, custom_group_keys = group_config.create_group_keys(config_spec=group_config.get_config_spec())
    check_structure_for_group_attr(group_keys=group_keys, spec=spec, key_name="group_keys")
    check_agreement_group_attr(group_keys=group_keys, custom_group_keys=custom_group_keys, spec=spec)


def check_attr(  # pylint: disable=too-many-branches
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
        raise_adcm_ex(code="ATTRIBUTE_ERROR", msg="`attr` should be a map")

    for key, value in attr.items():
        if key in ["group_keys", "custom_group_keys"]:
            if not is_group_config:
                raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"not allowed key `{key}` for object ({ref})")
            continue

        if f"{key}/" not in spec:
            raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key}` group in the config ({ref})")

        if spec[f"{key}/"].type != "group":
            raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"config key `{key}` is not a group ({ref})")

    for value in spec.values():
        key = value.name
        if value.type == "group" and "activatable" in value.limits:
            if key not in attr:
                raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"there isn't `{key}` group in the `attr`")

            if not isinstance(attr[key], dict):
                raise_adcm_ex(
                    code="ATTRIBUTE_ERROR",
                    msg=f"value of attribute `{key}` should be a map ({ref})",
                )

            for attr_key in attr[key]:
                if attr_key not in allowed_key:
                    raise_adcm_ex(
                        code="ATTRIBUTE_ERROR",
                        msg=f"not allowed key `{attr_key}` of attribute `{key}` ({ref})",
                    )

                if not isinstance(attr[key]["active"], bool):
                    raise_adcm_ex(
                        code="ATTRIBUTE_ERROR",
                        msg=f"value of key `active` of attribute `{key}` should be boolean ({ref})",
                    )

                if (
                    current_attr is not None
                    and (current_attr[key]["active"] != attr[key]["active"])
                    and config_is_ro(obj=obj, key=key, limits=value.limits)
                ):
                    raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=f"config key {key} of {ref} is read only")

    if is_group_config:
        check_group_keys_attr(attr=attr, spec=spec, group_config=obj)


def check_structure_for_group_attr(group_keys: dict, spec: dict, key_name: str) -> None:
    flat_group_attr = group_keys_to_flat(origin=group_keys, spec=spec)
    for key, value in flat_group_attr.items():
        if key not in spec:
            raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"invalid `{key}` field in `{key_name}`")

        if spec[key].type == "group":
            if not (
                isinstance(value, bool)
                and "activatable" in spec[key].limits
                or value is None
                and "activatable" not in spec[key].limits
            ):
                raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"invalid type `value` field in `{key}`")
        else:
            if not isinstance(value, bool):
                raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"invalid type `{key}` field in `{key_name}`")

    for key, value in spec.items():
        if value.type != "group":
            if key not in flat_group_attr:
                raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"there is no `{key}` field in `{key_name}`")


def _check_empty_values(key: str, current: dict, new: dict) -> bool:
    key_in_config = key in current and key in new
    if key_in_config and (
        (bool(current[key]) is False and new[key] is None) or (current[key] is None and bool(new[key]) is False)
    ):
        return True

    return False


def check_value_unselected_field(
    current_config: dict,
    new_config: dict,
    current_attr: dict,
    new_attr: dict,
    group_keys: dict,
    spec: dict,
    obj: type[ADCMEntity] | Action,
) -> None:
    """
    Check value unselected field
    :param current_config: Current config
    :param new_config: New config
    :param current_attr: Current attr
    :param new_attr: New attr
    :param group_keys: group_keys from attr
    :param spec: Config specification
    :param obj: Parent object (Cluster, Service, Component Provider or Host)
    """
    # pylint: disable=too-many-boolean-expressions

    for group_key, group_value in group_keys.items():
        if isinstance(group_value, Mapping):
            if (
                "activatable" in spec[group_key]["limits"]
                and not group_value["value"]
                and current_attr[group_key]["active"] != new_attr[group_key]["active"]
            ):
                msg = (
                    f"Value of `{group_key}` activatable group is different in current and new attr."
                    f' Current: ({current_attr[group_key]["active"]}), New: ({new_attr[group_key]["active"]})'
                )
                logger.info(msg)
                raise_adcm_ex(code="GROUP_CONFIG_CHANGE_UNSELECTED_FIELD", msg=msg)

            check_value_unselected_field(
                current_config=current_config[group_key],
                new_config=new_config[group_key],
                current_attr=current_attr,
                new_attr=new_attr,
                group_keys=group_keys[group_key]["fields"],
                spec=spec[group_key]["fields"],
                obj=obj,
            )
        else:
            if spec[group_key]["type"] in {"list", "map", "secretmap", "string", "structure"}:
                if config_is_ro(obj=obj, key=group_key, limits=spec[group_key]["limits"]) or _check_empty_values(
                    key=group_key,
                    current=current_config,
                    new=new_config,
                ):
                    continue

            if (
                not group_value
                and group_key in current_config
                and group_key in new_config
                and current_config[group_key] != new_config[group_key]
            ):
                msg = (
                    f"Value of `{group_key}` field is different in current and new config."
                    f" Current: ({current_config[group_key]}), New: ({new_config[group_key]})"
                )
                logger.info(msg)
                raise_adcm_ex(code="GROUP_CONFIG_CHANGE_UNSELECTED_FIELD", msg=msg)


def _check_str(value: Any, idx: Any, key: str, subkey: str, ref: str, label: str):
    if not isinstance(value, str):
        raise_adcm_ex(
            code="CONFIG_VALUE_ERROR",
            msg=f'{label} ("{value}") of element "{idx}" of config key "{key}/{subkey}"' f" should be string ({ref})",
        )


def check_config_type(  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    proto: Prototype,
    key: str,
    subkey: str,
    spec: dict,
    value: Any,
    default: bool = False,
    inactive: bool = False,
) -> None:
    ref = proto_ref(prototype=proto)
    if default:
        label = "Default value"
    else:
        label = "Value"

    tmpl1 = f'{label} of config key "{key}/{subkey}" {{}} ({ref})'
    tmpl2 = f'{label} ("{value}") of config key "{key}/{subkey}" {{}} ({ref})'
    should_not_be_empty = "should be not empty"

    if (
        value is None  # pylint: disable=too-many-boolean-expressions
        or (spec["type"] == "map" and value == {})
        or (spec["type"] == "secretmap" and value == {})
        or (spec["type"] == "list" and value == [])
    ):
        if inactive:
            return

        if "required" in spec and spec["required"]:
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("is required"))
        else:
            return

    if isinstance(value, (list, dict)) and spec["type"] not in settings.STACK_COMPLEX_FIELD_TYPES:
        if spec["type"] != "group":
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be flat"))

    if spec["type"] == "list":
        if not isinstance(value, list):
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be an array"))

        if "required" in spec and spec["required"] and value == []:
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        for i, _value in enumerate(value):
            _check_str(value=_value, idx=i, key=key, subkey=subkey, ref=ref, label=label)

    if spec["type"] in {"map", "secretmap"}:
        if not isinstance(value, dict):
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("should be a map"))

        if "required" in spec and spec["required"] and value == {}:
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        for value_key, value_value in value.items():
            _check_str(value=value_value, idx=value_key, key=key, subkey=subkey, ref=ref, label=label)

    if spec["type"] in ("string", "password", "text", "secrettext"):
        if not isinstance(value, str):
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be string"))

        if "required" in spec and spec["required"] and value == "":
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

    if spec["type"] in {"file", "secretfile"}:
        if not isinstance(value, str):
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be string"))

        if value == "":
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format(should_not_be_empty))

        if default:
            if len(value) > 2048:
                raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl1.format("is too long"))

    if spec["type"] == "structure":
        schema = spec["limits"]["yspec"]
        try:
            yspec.checker.process_rule(data=value, rules=schema, name="root")
        except yspec.checker.FormatError as e:
            msg = tmpl1.format(f"yspec error: {str(e)} at block {e.data}")
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=msg)
        except yspec.checker.SchemaError as e:
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=f"yspec error: {str(e)}")

    if spec["type"] == "boolean" and not isinstance(value, bool):
        raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be boolean"))

    if spec["type"] == "integer" and not isinstance(value, int):
        raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be integer"))

    if spec["type"] == "float" and not isinstance(value, (int, float)):
        raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format("should be float"))

    if spec["type"] == "integer" or spec["type"] == "float":
        limits = spec["limits"]
        if "min" in limits and value < limits["min"]:
            msg = f'should be more than {limits["min"]}'
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

        if "max" in limits and value > limits["max"]:
            msg = f'should be less than {limits["max"]}'
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

    if spec["type"] == "option":
        option = spec["limits"]["option"]
        check = False

        for _value in option.values():
            if _value == value:
                check = True

                break

        if not check:
            msg = f'not in option list: "{option}"'
            raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

    if spec["type"] == "variant":
        source = spec["limits"]["source"]
        if source["strict"]:
            if source["type"] == "inline" and value not in source["value"]:
                msg = f'not in variant list: "{source["value"]}"'
                raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))

            if not default:
                if source["type"] in ("config", "builtin") and value not in source["value"]:
                    msg = f'not in variant list: "{source["value"]}"'
                    raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=tmpl2.format(msg))
