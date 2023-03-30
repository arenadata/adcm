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

# pylint: disable=too-many-lines

import copy
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from ansible.errors import AnsibleError
from cm.adcm_config.ansible import ansible_decrypt, ansible_encrypt_and_format
from cm.adcm_config.checks import (
    check_attr,
    check_config_type,
    check_value_unselected_field,
)
from cm.adcm_config.utils import (
    config_is_ro,
    cook_file_type_name,
    group_is_activatable,
    is_inactive,
    key_is_required,
    proto_ref,
    sub_key_is_required,
    to_flat_dict,
)
from cm.errors import raise_adcm_ex
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    ConfigLog,
    GroupConfig,
    ObjectConfig,
    Prototype,
    PrototypeConfig,
    StagePrototype,
)
from cm.utils import dict_to_obj, obj_to_dict
from cm.variant import get_variant, process_variant
from django.conf import settings
from jinja_config import get_jinja_config


def read_bundle_file(proto: Prototype | StagePrototype, fname: str, bundle_hash: str, ref=None) -> str | None:
    if not ref:
        ref = proto_ref(proto)

    file_descriptor = None

    if fname[0:2] == "./":
        path = Path(settings.BUNDLE_DIR, bundle_hash, proto.path, fname)
    else:
        path = Path(settings.BUNDLE_DIR, bundle_hash, fname)

    try:
        file_descriptor = open(path, encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
    except FileNotFoundError:
        raise_adcm_ex(code="CONFIG_TYPE_ERROR", msg=f'{bundle_hash} "{path}" is not found ({ref})')
    except PermissionError:
        raise_adcm_ex(code="CONFIG_TYPE_ERROR", msg=f'{bundle_hash} "{path}" can not be open ({ref})')

    if file_descriptor:
        body = file_descriptor.read()
        file_descriptor.close()

        return body

    return None


def init_object_config(proto: Prototype, obj: Any) -> ObjectConfig | None:
    spec, _, conf, attr = get_prototype_config(proto)
    if not conf:
        return None

    obj_conf = ObjectConfig(current=0, previous=0)
    obj_conf.save()
    save_obj_config(obj_conf, conf, attr, "init")
    process_file_type(obj, spec, conf)

    return obj_conf


def get_prototype_config(
    proto: Prototype, action: Action = None, obj: type[ADCMEntity] = None
) -> tuple[dict, dict, dict, dict]:
    spec = {}
    flat_spec = OrderedDict()
    config = {}
    attr = {}
    flist = ("default", "required", "type", "limits")

    if action is not None and obj is not None and action.config_jinja:
        proto_conf, _ = get_jinja_config(action=action, obj=obj)
        proto_conf_group = [config for config in proto_conf if config.type == "group"]
    else:
        proto_conf = PrototypeConfig.objects.filter(prototype=proto, action=action).order_by("id")
        proto_conf_group = PrototypeConfig.objects.filter(prototype=proto, action=action, type="group").order_by("id")

    for conf in proto_conf_group:
        spec[conf.name] = {}
        config[conf.name] = {}
        if "activatable" in conf.limits:
            attr[conf.name] = {"active": conf.limits["active"]}

    for conf in proto_conf:
        flat_spec[f"{conf.name}/{conf.subname}"] = conf
        if conf.subname == "":
            if conf.type != "group":
                spec[conf.name] = obj_to_dict(conf, flist)
                config[conf.name] = get_default(conf, proto)
        else:
            spec[conf.name][conf.subname] = obj_to_dict(conf, flist)
            config[conf.name][conf.subname] = get_default(conf, proto)

    return spec, flat_spec, config, attr


def make_object_config(obj: ADCMEntity, prototype: Prototype) -> None:
    if obj.config:
        return

    obj_conf = init_object_config(prototype, obj)
    if obj_conf:
        obj.config = obj_conf
        obj.save()


def switch_config(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements # noqa: C901
    obj: ADCMEntity,
    new_proto: Prototype,
    old_proto: Prototype,
) -> None:
    # process objects without config
    if not obj.config:
        make_object_config(obj, new_proto)
        return

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    _, old_spec, _, _ = get_prototype_config(old_proto)
    new_unflat_spec, new_spec, _, _ = get_prototype_config(new_proto)
    old_conf = to_flat_dict(config_log.config, old_spec)

    def is_new_default(_key):
        if not new_spec[_key].default:
            return False

        if old_spec[_key].default:
            if _key in old_conf:
                return bool(get_default(old_spec[_key], old_proto) == old_conf[_key])
            else:
                return True

        if not old_spec[_key].default and new_spec[_key].default:
            return True

        return False

    # set new default config values and gather information about activatable groups
    new_conf = {}
    active_groups = {}
    inactive_groups = {}
    for key in new_spec:
        if new_spec[key].type == "group":
            limits = new_spec[key].limits
            if "activatable" in limits and "active" in limits:
                group_name = key.rstrip("/")
                # check group activity in old configuration
                if group_name in config_log.attr:
                    if config_log.attr[group_name]["active"]:
                        active_groups[group_name] = True
                    else:
                        inactive_groups[group_name] = True
                elif limits["active"]:
                    active_groups[group_name] = True
                else:
                    inactive_groups[group_name] = True

            continue

        if key in old_spec:
            if is_new_default(key):
                new_conf[key] = get_default(new_spec[key], new_proto)
            else:
                new_conf[key] = old_conf.get(key, get_default(new_spec[key], new_proto))
        else:
            new_conf[key] = get_default(new_spec[key], new_proto)

    # go from flat config to 2-level dictionary
    unflat_conf = {}
    for key, value in new_conf.items():
        key_1, key_2 = key.split("/")
        if key_2 == "":
            unflat_conf[key_1] = value
        else:
            if key_1 not in unflat_conf:
                unflat_conf[key_1] = {}

            unflat_conf[key_1][key_2] = value

    # set activatable groups attributes for new config
    attr = {}
    for key in unflat_conf:
        if key in active_groups:
            attr[key] = {"active": True}
        if key in inactive_groups:
            attr[key] = {"active": False}

    save_obj_config(obj.config, unflat_conf, attr, "upgrade")
    process_file_type(obj, new_unflat_spec, unflat_conf)


def restore_cluster_config(obj_conf, version, desc=""):
    config_log = ConfigLog.obj.get(obj_ref=obj_conf, id=version)
    obj_conf.previous = obj_conf.current
    obj_conf.current = version
    obj_conf.save()

    if desc != "":
        config_log.description = desc

    config_log.save()

    return config_log


def save_obj_config(obj_conf, conf, attr, desc=""):
    config_log = ConfigLog(obj_ref=obj_conf, config=conf, attr=attr, description=desc)
    config_log.save()
    obj_conf.previous = obj_conf.current
    obj_conf.current = config_log.id
    obj_conf.save()

    return config_log


def save_file_type(obj, key, subkey, value):
    filename = cook_file_type_name(obj, key, subkey)
    if value is None:
        _file = Path(filename)
        if _file.is_file():
            _file.unlink()

        return None

    # There is a trouble between openssh 7.9 and register function of Ansible.
    # Register function does rstrip of string, while openssh 7.9 not working
    # with private key files without \n at the end.
    # So when we create that key from playbook and save it in ADCM we get
    # "Load key : invalid format" on next connect to host.

    if key == "ansible_ssh_private_key_file":
        if value != "":
            if value[-1] == "-":
                value += "\n"

    file_descriptor = open(filename, "w", encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
    file_descriptor.write(value)
    file_descriptor.close()
    Path(filename).chmod(0o0600)

    return filename


def process_file_type(obj: Any, spec: dict, conf: dict):  # noqa: C901
    # pylint: disable=too-many-branches,disable=too-many-nested-blocks

    for key in conf:
        if "type" in spec[key]:
            if spec[key]["type"] == "file":
                save_file_type(obj, key, "", conf[key])
            elif spec[key]["type"] == "secretfile":
                if conf[key] is not None:
                    value = conf[key]
                    if conf[key].startswith(settings.ANSIBLE_VAULT_HEADER):
                        try:
                            value = ansible_decrypt(msg=value)
                        except AnsibleError:
                            raise_adcm_ex(
                                code="CONFIG_VALUE_ERROR",
                                msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                            )
                else:
                    value = None

                save_file_type(obj, key, "", value)
        elif conf[key]:
            for subkey in conf[key]:
                if spec[key][subkey]["type"] == "file":
                    save_file_type(obj, key, subkey, conf[key][subkey])
                elif spec[key][subkey]["type"] == "secretfile":
                    value = conf[key][subkey]
                    if conf[key][subkey] is not None:
                        if conf[key][subkey].startswith(settings.ANSIBLE_VAULT_HEADER):
                            try:
                                value = ansible_decrypt(msg=value)
                            except AnsibleError:
                                raise_adcm_ex(
                                    code="CONFIG_VALUE_ERROR",
                                    msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                                )
                    else:
                        value = None

                    save_file_type(obj, key, subkey, value)


def process_secret_params(spec, conf):  # noqa: C901
    for key in conf:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if spec[key]["type"] in {"password", "secrettext", "secretfile"} and conf[key]:
                if conf[key].startswith(settings.ANSIBLE_VAULT_HEADER):
                    try:
                        ansible_decrypt(msg=conf[key])
                    except AnsibleError:
                        raise_adcm_ex(
                            code="CONFIG_VALUE_ERROR",
                            msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                        )
                else:
                    conf[key] = ansible_encrypt_and_format(msg=conf[key])
        else:
            for subkey in conf[key]:
                if spec[key][subkey]["type"] in {"password", "secrettext", "secretfile"} and conf[key][subkey]:
                    if conf[key][subkey].startswith(settings.ANSIBLE_VAULT_HEADER):
                        try:
                            ansible_decrypt(msg=conf[key][subkey])
                        except AnsibleError:
                            raise_adcm_ex(
                                code="CONFIG_VALUE_ERROR",
                                msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                            )
                    else:
                        conf[key][subkey] = ansible_encrypt_and_format(msg=conf[key][subkey])

    return conf


def process_secretmap(spec: dict, conf: dict) -> dict:
    for key in conf:
        if "type" not in spec[key]:
            for _ in conf:
                process_secretmap(spec[key], conf[key])

        if spec[key].get("type") != "secretmap":
            continue

        if conf[key] is None:
            continue

        for conf_key, conf_value in conf[key].items():
            if conf_value.startswith(settings.ANSIBLE_VAULT_HEADER):
                try:
                    ansible_decrypt(msg=conf_value)
                except AnsibleError:
                    raise_adcm_ex(
                        code="CONFIG_VALUE_ERROR",
                        msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                    )

                conf[key][conf_key] = conf_value
            else:
                conf[key][conf_key] = ansible_encrypt_and_format(msg=conf_value)

    return conf


def process_config(  # pylint: disable=too-many-branches # noqa: C901
    obj: ADCMEntity,
    spec: dict,
    old_conf: dict,
) -> dict:
    if not old_conf:
        return old_conf

    conf = copy.deepcopy(old_conf)
    for key in conf:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if conf[key] is not None:
                if spec[key]["type"] in {"file", "secretfile"}:
                    conf[key] = cook_file_type_name(obj, key, "")

                elif spec[key]["type"] in {"password", "secrettext"}:
                    if settings.ANSIBLE_VAULT_HEADER in conf[key]:
                        conf[key] = {"__ansible_vault": conf[key]}

                elif spec[key]["type"] == "secretmap":
                    for map_key, map_value in conf[key].items():
                        if settings.ANSIBLE_VAULT_HEADER in map_value:
                            conf[key][map_key] = {"__ansible_vault": map_value}
        elif conf[key]:
            for subkey in conf[key]:
                if conf[key][subkey] is not None:
                    if spec[key][subkey]["type"] in {"file", "secretfile"}:
                        conf[key][subkey] = cook_file_type_name(obj, key, subkey)

                    elif spec[key][subkey]["type"] in {"password", "secrettext"}:
                        if settings.ANSIBLE_VAULT_HEADER in conf[key][subkey]:
                            conf[key][subkey] = {"__ansible_vault": conf[key][subkey]}

                    elif spec[key][subkey]["type"] == "secretmap":
                        for map_key, map_value in conf[key][subkey].items():
                            if settings.ANSIBLE_VAULT_HEADER in map_value:
                                conf[key][subkey][map_key] = {"__ansible_vault": map_value}

    return conf


def ui_config(obj, config_log):  # pylint: disable=too-many-locals
    conf = []
    _, spec, _, _ = get_prototype_config(obj.prototype)
    obj_conf = config_log.config
    obj_attr = config_log.attr
    flat_conf = to_flat_dict(obj_conf, spec)
    group_keys = obj_attr.get("group_keys", {})
    custom_group_keys = obj_attr.get("custom_group_keys", {})
    slist = ("name", "subname", "type", "description", "display_name", "required")

    for key in spec:
        item = obj_to_dict(spec[key], slist)
        limits = spec[key].limits
        item["limits"] = limits
        if spec[key].ui_options:
            item["ui_options"] = spec[key].ui_options
        else:
            item["ui_options"] = None

        item["read_only"] = bool(config_is_ro(obj, key, spec[key].limits))
        item["activatable"] = bool(group_is_activatable(spec[key]))
        if item["type"] == "variant":
            item["limits"]["source"]["value"] = get_variant(obj, obj_conf, limits)

        item["default"] = get_default(spec[key], obj.prototype)
        if key in flat_conf:
            item["value"] = flat_conf[key]
        else:
            item["value"] = get_default(spec[key], obj.prototype)

        if group_keys:
            if spec[key].type == "group":
                _key = key.split("/")[0]
                item["group"] = group_keys[_key]["value"]
                item["custom_group"] = custom_group_keys[_key]["value"]
            else:
                key_1, key_2 = key.split("/")
                if key_2:
                    item["group"] = group_keys[key_1]["fields"][key_2]
                    item["custom_group"] = custom_group_keys[key_1]["fields"][key_2]
                else:
                    item["group"] = group_keys[key_1]
                    item["custom_group"] = custom_group_keys[key_1]

        conf.append(item)

    return conf


def get_action_variant(obj, config):
    if obj.config:
        config_log = ConfigLog.objects.filter(obj_ref=obj.config, id=obj.config.current).first()
        if config_log:
            for conf in config:
                if conf.type != "variant":
                    continue

                conf.limits["source"]["value"] = get_variant(obj, config_log.config, conf.limits)


def restore_read_only(obj, spec, conf, old_conf):  # pylint: disable=too-many-branches # noqa: C901
    # Do not remove!
    # This patch fix old error when sometimes group config values can be lost
    # during bundle upgrade
    for key in spec:
        if "type" in spec[key]:
            continue
        if old_conf[key] is None:
            old_conf[key] = {}
            for subkey in spec[key]:
                old_conf[subkey] = get_default(
                    dict_to_obj(spec[key][subkey], PrototypeConfig(), ("type", "default", "limits")),
                )
    # end of patch

    for key in spec:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if config_is_ro(obj, key, spec[key]["limits"]) and key not in conf:
                if key in old_conf:
                    conf[key] = old_conf[key]
        else:
            for subkey in spec[key]:
                if config_is_ro(obj=obj, key=f"{key}/{subkey}", limits=spec[key][subkey]["limits"]):
                    if key in conf:
                        if subkey not in conf:
                            if key in old_conf and subkey in old_conf[key]:
                                conf[key][subkey] = old_conf[key][subkey]
                    elif key in old_conf and subkey in old_conf[key]:
                        conf[key] = {subkey: old_conf[key][subkey]}

    return conf


def process_json_config(
    proto: Prototype,
    obj: ADCMEntity | Action,
    new_config: dict,
    current_config: dict = None,
    new_attr=None,
    current_attr=None,
) -> dict:
    spec, flat_spec, _, _ = get_prototype_config(proto)
    check_attr(proto, obj, new_attr, flat_spec, current_attr)
    group = None

    if isinstance(obj, GroupConfig):
        config_spec = obj.get_config_spec()
        group_keys = new_attr.get("group_keys", {})
        check_value_unselected_field(
            current_config,
            new_config,
            current_attr,
            new_attr,
            group_keys,
            config_spec,
            obj.object,
        )
        group = obj
        obj = group.object

    process_variant(obj, spec, new_config)
    check_config_spec(proto=proto, obj=obj, spec=spec, flat_spec=flat_spec, conf=new_config, attr=new_attr)

    new_config = process_config_spec(obj=group or obj, spec=spec, new_config=new_config)

    return new_config


def check_config_spec(  # noqa: C901
    proto: Prototype,
    obj: ADCMEntity | Action,
    spec: dict,
    flat_spec: dict,
    conf: dict,
    attr: dict = None,
) -> None:
    # pylint: disable=too-many-branches,too-many-statements
    ref = proto_ref(proto)
    if isinstance(conf, (float, int)):
        raise_adcm_ex(code="JSON_ERROR", msg="config should not be just one int or float")

    if isinstance(conf, str):
        raise_adcm_ex(code="JSON_ERROR", msg="config should not be just one string")

    for key in conf:
        if key not in spec:
            raise_adcm_ex(code="CONFIG_KEY_ERROR", msg=f'There is unknown key "{key}" in input config ({ref})')

        if "type" in spec[key] and spec[key]["type"] != "group":
            if isinstance(conf[key], dict) and spec[key]["type"] not in settings.STACK_COMPLEX_FIELD_TYPES:
                raise_adcm_ex(
                    code="CONFIG_KEY_ERROR",
                    msg=f'Key "{key}" in input config should not have any subkeys ({ref})',
                )

    for key in spec:
        if "type" in spec[key] and spec[key]["type"] != "group":
            if key in conf:
                check_config_type(proto=proto, key=key, subkey="", spec=spec[key], value=conf[key])
            elif key_is_required(obj=obj, key=key, subkey="", spec=spec):
                raise_adcm_ex(code="CONFIG_KEY_ERROR", msg=f'There is no required key "{key}" in input config ({ref})')

        else:
            if key not in conf:
                if sub_key_is_required(key=key, attr=attr, flat_spec=flat_spec, spec=spec, obj=obj):
                    raise_adcm_ex(code="CONFIG_KEY_ERROR", msg=f'There are no required key "{key}" in input config')

            else:
                if not isinstance(conf[key], dict):
                    raise_adcm_ex(code="CONFIG_KEY_ERROR", msg=f'There are not any subkeys for key "{key}" ({ref})')

                if not conf[key]:
                    raise_adcm_ex(
                        code="CONFIG_KEY_ERROR",
                        msg=f'Key "{key}" should contains some subkeys ({ref}): {list(spec[key].keys())}',
                    )

                for subkey in conf[key]:
                    if subkey not in spec[key]:
                        raise_adcm_ex(
                            code="CONFIG_KEY_ERROR",
                            msg=f'There is unknown subkey "{subkey}" for key "{key}" in input config ({ref})',
                        )

                for subkey in spec[key]:
                    if subkey in conf[key]:
                        check_config_type(
                            proto=proto,
                            key=key,
                            subkey=subkey,
                            spec=spec[key][subkey],
                            value=conf[key][subkey],
                            default=False,
                            inactive=is_inactive(key, attr, flat_spec),
                        )
                    elif key_is_required(obj=obj, key=key, subkey=subkey, spec=spec):
                        raise_adcm_ex(
                            code="CONFIG_KEY_ERROR",
                            msg=f'There is no required subkey "{subkey}" for key "{key}" ({ref})',
                        )


def process_config_spec(obj: ADCMEntity, spec: dict, new_config: dict, current_config: dict = None) -> dict:
    if current_config:
        new_config = restore_read_only(obj=obj, spec=spec, conf=new_config, old_conf=current_config)

    process_file_type(obj=obj, spec=spec, conf=new_config)
    conf = process_secret_params(spec=spec, conf=new_config)
    conf = process_secretmap(spec=spec, conf=conf)

    return conf


def get_adcm_config(section=None):
    adcm_object = ADCM.objects.last()
    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if not section:
        return current_configlog.attr, current_configlog.config

    return current_configlog.attr.get(section, None), current_configlog.config.get(section, None)


def get_default(  # pylint: disable=too-many-branches  # noqa: C901
    conf: PrototypeConfig,
    proto: Prototype | None = None,
) -> Any:
    value = conf.default
    if conf.default == "":
        value = None
    elif conf.type == "string":
        value = conf.default
    elif conf.type == "text":
        value = conf.default
    elif conf.type in settings.SECURE_PARAM_TYPES:
        if conf.default:
            value = ansible_encrypt_and_format(msg=conf.default)
    elif conf.type in settings.STACK_COMPLEX_FIELD_TYPES:
        if isinstance(conf.default, str):
            conf.default = conf.default.replace("'", '"')
            value = json.loads(s=conf.default)
        else:
            value = conf.default
    elif conf.type == "integer":
        value = int(conf.default)
    elif conf.type == "float":
        value = float(conf.default)
    elif conf.type == "boolean":
        if isinstance(conf.default, bool):
            value = conf.default
        else:
            value = bool(conf.default.lower() in {"true", "yes"})
    elif conf.type == "option":
        if conf.default in conf.limits["option"]:
            value = conf.limits["option"][conf.default]

        for option in conf.limits["option"].values():
            if not isinstance(option, type(value)):
                if isinstance(option, bool):
                    value = bool(value)
                elif isinstance(option, int):
                    value = int(value)
                elif isinstance(option, float):
                    value = float(value)
                elif isinstance(option, str):
                    value = str(value)

    elif conf.type == "file":
        if proto:
            if conf.default:
                value = read_bundle_file(
                    proto=proto,
                    fname=conf.default,
                    bundle_hash=proto.bundle.hash,
                    ref=f'config key "{conf.name}/{conf.subname}" default file',
                )
    elif conf.type == "secretfile":
        if proto:
            if conf.default:
                value = ansible_encrypt_and_format(
                    msg=read_bundle_file(
                        proto=proto,
                        fname=conf.default,
                        bundle_hash=proto.bundle.hash,
                        ref=f'config key "{conf.name}/{conf.subname}" default file',
                    ),
                )

    if conf.type == "secretmap" and conf.default:
        new_value = {}
        for conf_key, conf_value in value.items():
            new_value[conf_key] = ansible_encrypt_and_format(msg=conf_value)

        value = new_value

    return value


def get_main_info(obj: ADCMEntity | None) -> str | None:
    """Return __main_info for object"""
    if obj.config is None:
        return None

    config_log = ConfigLog.objects.filter(id=obj.config.current).first()
    if config_log:
        _, spec, _, _ = get_prototype_config(obj.prototype)

        if "__main_info" in config_log.config:
            return config_log.config["__main_info"]
        elif "__main_info/" in spec:
            return get_default(spec["__main_info/"], obj.prototype)

    return None
