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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yspec.checker
from ansible.errors import AnsibleError
from ansible.parsing.vault import VaultAES256, VaultSecret
from cm.errors import raise_adcm_ex
from cm.logger import logger
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
from cm.variant import get_variant, process_variant
from django.conf import settings

SECURE_PARAM_TYPES = ("password", "secrettext")


def proto_ref(prototype: StagePrototype | Prototype) -> str:
    return f'{prototype.type} "{prototype.name}" {prototype.version}'


def obj_ref(obj):
    if hasattr(obj, "name"):
        name = obj.name
    elif hasattr(obj, "fqdn"):
        name = obj.fqdn
    else:
        name = obj.prototype.name

    return f'{obj.prototype.type} #{obj.id} "{name}"'


def obj_to_dict(obj, keys):
    dictionary = {}
    for key in keys:
        if hasattr(obj, key):
            dictionary[key] = getattr(obj, key)

    return dictionary


def dict_to_obj(dictionary, obj, keys):
    for key in keys:
        setattr(obj, key, dictionary[key])

    return obj


def to_flat_dict(config, spec):
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


def group_keys_to_flat(origin: dict, spec: dict):
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
    elif conf.type in SECURE_PARAM_TYPES:
        if conf.default:
            value = ansible_encrypt_and_format(conf.default)
    elif type_is_complex(conf.type):
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
                    pattern=proto.bundle.hash,
                    ref=f'config key "{conf.name}/{conf.subname}" default file',
                )
    elif conf.type == "secretfile":
        if proto:
            if conf.default:
                value = ansible_encrypt_and_format(
                    msg=read_bundle_file(
                        proto=proto,
                        fname=conf.default,
                        pattern=proto.bundle.hash,
                        ref=f'config key "{conf.name}/{conf.subname}" default file',
                    ),
                )

    if conf.type == "secretmap" and conf.default:
        new_value = {}
        for conf_key, conf_value in value.items():
            new_value[conf_key] = ansible_encrypt_and_format(conf_value)

        value = new_value

    return value


def type_is_complex(conf_type):
    if conf_type in settings.STACK_COMPLEX_FIELD_TYPES:
        return True

    return False


def read_bundle_file(proto: Prototype, fname: str, pattern: str, ref=None) -> str | None:
    if not ref:
        ref = proto_ref(proto)

    file_descriptor = None
    path = Path(settings.BUNDLE_DIR, proto.path, fname)
    try:
        file_descriptor = open(path, encoding=settings.ENCODING_UTF_8)  # pylint: disable=consider-using-with
    except FileNotFoundError:
        raise_adcm_ex(code="CONFIG_TYPE_ERROR", msg=f'{pattern} "{path}" is not found ({ref})')
    except PermissionError:
        raise_adcm_ex(code="CONFIG_TYPE_ERROR", msg=f'{pattern} "{path}" can not be open ({ref})')

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


def get_prototype_config(proto: Prototype, action: Action = None) -> tuple[dict, dict, dict, dict]:
    spec = {}
    flat_spec = OrderedDict()
    config = {}
    attr = {}
    flist = ("default", "required", "type", "limits")
    for conf in PrototypeConfig.objects.filter(prototype=proto, action=action, type="group").order_by("id"):
        spec[conf.name] = {}
        config[conf.name] = {}
        if "activatable" in conf.limits:
            attr[conf.name] = {"active": conf.limits["active"]}

    for conf in PrototypeConfig.objects.filter(prototype=proto, action=action).order_by("id"):
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


def cook_file_type_name(obj, key, sub_key):
    if hasattr(obj, "prototype"):
        filename = [obj.prototype.type, str(obj.id), key, sub_key]
    elif isinstance(obj, GroupConfig):
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


def ansible_encrypt(msg):
    vault = VaultAES256()
    secret = VaultSecret(bytes(settings.ANSIBLE_SECRET, settings.ENCODING_UTF_8))

    return vault.encrypt(bytes(msg, settings.ENCODING_UTF_8), secret)


def ansible_encrypt_and_format(msg):
    ciphertext = ansible_encrypt(msg)

    return f"{settings.ANSIBLE_VAULT_HEADER}\n{str(ciphertext, settings.ENCODING_UTF_8)}"


def process_file_type(obj: Any, spec: dict, conf: dict):  # noqa: C901
    # pylint: disable=too-many-branches,disable=too-many-nested-blocks

    for key in conf:
        if "type" in spec[key]:
            if spec[key]["type"] == "file":
                save_file_type(obj, key, "", conf[key])
            elif spec[key]["type"] == "secretfile":
                if conf[key] is not None:
                    if conf[key].startswith(settings.ANSIBLE_VAULT_HEADER):
                        try:
                            ansible_decrypt(msg=conf[key])
                        except AnsibleError:
                            raise_adcm_ex(
                                code="CONFIG_VALUE_ERROR",
                                msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                            )

                        value = conf[key]
                    else:
                        value = ansible_encrypt_and_format(msg=conf[key])
                else:
                    value = None

                save_file_type(obj, key, "", value)
                conf[key] = value
        elif conf[key]:
            for subkey in conf[key]:
                if spec[key][subkey]["type"] == "file":
                    save_file_type(obj, key, subkey, conf[key][subkey])
                elif spec[key][subkey]["type"] == "secretfile":
                    if conf[key][subkey] is not None:
                        if conf[key][subkey].startswith(settings.ANSIBLE_VAULT_HEADER):
                            try:
                                ansible_decrypt(msg=conf[key])
                            except AnsibleError:
                                raise_adcm_ex(
                                    code="CONFIG_VALUE_ERROR",
                                    msg=f"Secret value must not starts with {settings.ANSIBLE_VAULT_HEADER}",
                                )

                            value = conf[key][subkey]
                        else:
                            value = ansible_encrypt_and_format(msg=conf[key][subkey])
                    else:
                        value = None

                    save_file_type(obj, key, subkey, value)
                    conf[key][subkey] = value


def ansible_decrypt(msg):
    if settings.ANSIBLE_VAULT_HEADER not in msg:
        return msg

    _, ciphertext = msg.split("\n")
    vault = VaultAES256()
    secret = VaultSecret(bytes(settings.ANSIBLE_SECRET, settings.ENCODING_UTF_8))

    return str(vault.decrypt(ciphertext, secret), settings.ENCODING_UTF_8)


def is_ansible_encrypted(msg):
    if not isinstance(msg, str):
        msg = str(msg, settings.ENCODING_UTF_8)
    if settings.ANSIBLE_VAULT_HEADER in msg:
        return True

    return False


def process_secret_params(spec, conf):  # noqa: C901
    for key in conf:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if spec[key]["type"] in SECURE_PARAM_TYPES and conf[key]:
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
                if spec[key][subkey]["type"] in SECURE_PARAM_TYPES and conf[key][subkey]:
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

                elif spec[key]["type"] in SECURE_PARAM_TYPES:
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

                    elif spec[key][subkey]["type"] in SECURE_PARAM_TYPES:
                        if settings.ANSIBLE_VAULT_HEADER in conf[key][subkey]:
                            conf[key][subkey] = {"__ansible_vault": conf[key][subkey]}

                    elif spec[key][subkey]["type"] == "secretmap":
                        for map_key, map_value in conf[key][subkey].items():
                            if settings.ANSIBLE_VAULT_HEADER in map_value:
                                conf[key][subkey][map_key] = {"__ansible_vault": map_value}

    return conf


def group_is_activatable(spec):
    if spec.type != "group":
        return False

    if "activatable" in spec.limits:
        return spec.limits["activatable"]

    return False


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


def config_is_ro(obj: ADCMEntity | Action, key: str, limits: dict) -> bool:
    # pylint: disable=too-many-return-statements
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


def check_read_only(obj, specs, conf, old_conf):
    flat_conf = to_flat_dict(conf, specs)
    flat_old_conf = to_flat_dict(old_conf, specs)

    for spec in specs:
        if config_is_ro(obj, spec, specs[spec].limits) and spec in flat_conf:
            # this block is an attempt to fix sending read-only fields of list and map types
            # Since this did not help, I had to completely turn off the validation
            # of read-only fields
            if specs[spec].type == "list":
                if isinstance(flat_conf[spec], list) and not flat_conf[spec]:
                    continue

            if specs[spec].type in {"map", "secretmap"}:
                if isinstance(flat_conf[spec], dict) and not flat_conf[spec]:
                    continue

            if flat_conf[spec] != flat_old_conf[spec]:
                raise_adcm_ex(
                    code="CONFIG_VALUE_ERROR",
                    msg=f"config key {spec} of {proto_ref(obj.prototype)} is read only",
                )


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


def check_and_process_json_config(
    proto: Prototype,
    obj: ADCMEntity | Action,
    new_config: dict,
    current_config: dict = None,
    new_attr=None,
    current_attr=None,
):
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


def check_structure_for_group_attr(group_keys, spec, key_name):
    """Check structure for `group_keys` and `custom_group_keys` field in attr"""
    flat_group_attr = group_keys_to_flat(group_keys, spec)
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

    return flat_group_attr


def check_agreement_group_attr(group_keys, custom_group_keys, spec):
    """Check agreement group_keys and custom_group_keys"""
    flat_group_keys = group_keys_to_flat(group_keys, spec)
    flat_custom_group_keys = group_keys_to_flat(custom_group_keys, spec)
    for key, value in flat_custom_group_keys.items():
        if not value and flat_group_keys[key]:
            raise_adcm_ex(code="ATTRIBUTE_ERROR", msg=f"the `{key}` field cannot be included in the group")


def check_value_unselected_field(current_config, new_config, current_attr, new_attr, group_keys, spec, obj):
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

    def check_empty_values(key, current, new):
        key_in_config = key in current and key in new
        if key_in_config and (
            (bool(current[key]) is False and new[key] is None) or (current[key] is None and bool(new[key]) is False)
        ):
            return True

        return False

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
                current_config[group_key],
                new_config[group_key],
                current_attr,
                new_attr,
                group_keys[group_key]["fields"],
                spec[group_key]["fields"],
                obj,
            )
        else:
            if spec[group_key]["type"] in {"list", "map", "secretmap", "string", "structure"}:
                if config_is_ro(obj, group_key, spec[group_key]["limits"]) or check_empty_values(
                    group_key,
                    current_config,
                    new_config,
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


def check_group_keys_attr(attr, spec, group_config):
    """Check attr for group config"""
    if "group_keys" not in attr:
        raise_adcm_ex(code="ATTRIBUTE_ERROR", msg='`attr` must contain "group_keys" key')

    group_keys = attr.get("group_keys")
    _, custom_group_keys = group_config.create_group_keys(group_config.get_config_spec())
    check_structure_for_group_attr(group_keys, spec, "group_keys")
    check_agreement_group_attr(group_keys, custom_group_keys, spec)


def check_attr(  # noqa: C901
    proto: Prototype,
    obj,
    attr: dict,
    spec: dict,
    current_attr: dict | None = None,
):  # pylint: disable=too-many-branches
    is_group_config = False
    if isinstance(obj, GroupConfig):
        is_group_config = True

    ref = proto_ref(proto)
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
                    and config_is_ro(obj, key, value.limits)
                ):
                    raise_adcm_ex(code="CONFIG_VALUE_ERROR", msg=f"config key {key} of {ref} is read only")

    if is_group_config:
        check_group_keys_attr(attr, spec, obj)


def key_is_required(obj: ADCMEntity | Action, key: str, subkey: str, spec: dict) -> bool:
    if config_is_ro(obj, f"{key}/{subkey}", spec.get("limits", "")):
        return False

    if subkey:
        return spec[key][subkey]["required"]

    return spec[key]["required"]


def is_inactive(key: str, attr: dict, flat_spec: dict) -> bool:
    if attr and flat_spec[f"{key}/"].type == "group":
        if key in attr and "active" in attr[key]:
            return not bool(attr[key]["active"])

    return False


def sub_key_is_required(key: str, attr: dict, flat_spec: dict, spec: dict, obj: ADCMEntity) -> bool:
    if is_inactive(key=key, attr=attr, flat_spec=flat_spec):
        return False

    for subkey in spec[key]:
        if key_is_required(obj=obj, key=key, subkey=subkey, spec=spec):
            return True

    return False


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
            if isinstance(conf[key], dict) and not type_is_complex(spec[key]["type"]):
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


def check_config_type(  # noqa: C901
    proto,
    key,
    subkey,
    spec,
    value,
    default=False,
    inactive=False,
):  # pylint: disable=too-many-branches,too-many-statements,too-many-locals
    ref = proto_ref(proto)
    if default:
        label = "Default value"
    else:
        label = "Value"

    tmpl1 = f'{label} of config key "{key}/{subkey}" {{}} ({ref})'
    tmpl2 = f'{label} ("{value}") of config key "{key}/{subkey}" {{}} ({ref})'
    should_not_be_empty = "should be not empty"

    def check_str(_idx, _v):
        if not isinstance(_v, str):
            _msg = f'{label} ("{_v}") of element "{_idx}" of config key "{key}/{subkey}"' f" should be string ({ref})"
            raise_adcm_ex("CONFIG_VALUE_ERROR", _msg)

    if (
        value is None  # pylint: disable=too-many-boolean-expressions
        or (spec["type"] == "map" and value == {})
        or (spec["type"] == "secretmap" and value == {})
        or (spec["type"] == "list" and value == [])
    ):
        if inactive:
            return

        if "required" in spec and spec["required"]:
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("is required"))
        else:
            return

    if isinstance(value, (list, dict)) and not type_is_complex(spec["type"]):
        if spec["type"] != "group":
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("should be flat"))

    if spec["type"] == "list":
        if not isinstance(value, list):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("should be an array"))

        if "required" in spec and spec["required"] and value == []:
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

        for i, _value in enumerate(value):
            check_str(i, _value)

    if spec["type"] in {"map", "secretmap"}:
        if not isinstance(value, dict):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("should be a map"))

        if "required" in spec and spec["required"] and value == {}:
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

        for value_key, value_value in value.items():
            check_str(value_key, value_value)

    if spec["type"] in ("string", "password", "text", "secrettext"):
        if not isinstance(value, str):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be string"))

        if "required" in spec and spec["required"] and value == "":
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

    if spec["type"] in {"file", "secretfile"}:
        if not isinstance(value, str):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be string"))

        if value == "":
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

        if default:
            if len(value) > 2048:
                raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("is too long"))

    if spec["type"] == "structure":
        schema = spec["limits"]["yspec"]
        try:
            yspec.checker.process_rule(value, schema, "root")
        except yspec.checker.FormatError as e:
            msg = tmpl1.format(f"yspec error: {str(e)} at block {e.data}")
            raise_adcm_ex("CONFIG_VALUE_ERROR", msg)
        except yspec.checker.SchemaError as e:
            raise_adcm_ex("CONFIG_VALUE_ERROR", f"yspec error: {str(e)}")

    if spec["type"] == "boolean" and not isinstance(value, bool):
        raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be boolean"))

    if spec["type"] == "integer" and not isinstance(value, int):
        raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be integer"))

    if spec["type"] == "float" and not isinstance(value, (int, float)):
        raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be float"))

    if spec["type"] == "integer" or spec["type"] == "float":
        limits = spec["limits"]
        if "min" in limits and value < limits["min"]:
            msg = f'should be more than {limits["min"]}'
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format(msg))

        if "max" in limits and value > limits["max"]:
            msg = f'should be less than {limits["max"]}'
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format(msg))

    if spec["type"] == "option":
        option = spec["limits"]["option"]
        check = False

        for _value in option.values():
            if _value == value:
                check = True

                break

        if not check:
            msg = f'not in option list: "{option}"'
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format(msg))

    if spec["type"] == "variant":
        source = spec["limits"]["source"]
        if source["strict"]:
            if source["type"] == "inline" and value not in source["value"]:
                msg = f'not in variant list: "{source["value"]}"'
                raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format(msg))

            if not default:
                if source["type"] in ("config", "builtin") and value not in source["value"]:
                    msg = f'not in variant list: "{source["value"]}"'
                    raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format(msg))


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


def get_adcm_config(section=None):
    adcm_object = ADCM.objects.last()
    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if not section:
        return current_configlog.attr, current_configlog.config

    return current_configlog.attr.get(section, None), current_configlog.config.get(section, None)
