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
from typing import Any, Optional, Tuple

import yspec.checker
from ansible.parsing.vault import VaultAES256, VaultSecret

from cm.config import (
    ANSIBLE_SECRET,
    ANSIBLE_VAULT_HEADER,
    BUNDLE_DIR,
    ENCODING,
    FILE_DIR,
)
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
)
from cm.variant import get_variant, process_variant

SECURE_PARAM_TYPES = ("password", "secrettext")


def proto_ref(proto):
    return f'{proto.type} "{proto.name}" {proto.version}'


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


def to_flat_dict(conf, spec):
    flat = {}
    for c1 in conf:
        if isinstance(conf[c1], dict):
            key = f"{c1}/"
            if key in spec and spec[key].type != "group":
                flat[f'{c1}/{""}'] = conf[c1]
            else:
                for c2 in conf[c1]:
                    flat[f"{c1}/{c2}"] = conf[c1][c2]
        else:
            flat[f'{c1}/{""}'] = conf[c1]

    return flat


def group_keys_to_flat(origin: dict, spec: dict):
    """
    Convert `group_keys` and `custom_group_keys` to flat structure as `<field>/`
     and `<group>/<field>`
    """
    result = {}
    for k, v in origin.items():
        if isinstance(v, Mapping):
            key = f"{k}/"
            if key in spec and spec[key].type != "group":
                result[key] = v
            else:
                if "fields" not in v or "value" not in origin[k]:
                    raise_adcm_ex("ATTRIBUTE_ERROR", "invalid format `group_keys` field")
                result[key] = v["value"]

                for _k, _v in origin[k]["fields"].items():
                    result[f"{k}/{_k}"] = _v
        else:
            result[f"{k}/"] = v

    return result


def get_default(c, proto=None):  # pylint: disable=too-many-branches
    value = c.default
    if c.default == "":
        value = None
    elif c.type == "string":
        value = c.default
    elif c.type == "text":
        value = c.default
    elif c.type in SECURE_PARAM_TYPES:
        if c.default:
            value = ansible_encrypt_and_format(c.default)
    elif type_is_complex(c.type):
        value = json.loads(c.default)
    elif c.type == "integer":
        value = int(c.default)
    elif c.type == "float":
        value = float(c.default)
    elif c.type == "boolean":
        if isinstance(c.default, bool):
            value = c.default
        else:
            value = bool(c.default.lower() in ("true", "yes"))
    elif c.type == "option":
        if c.default in c.limits["option"]:
            value = c.limits["option"][c.default]
    elif c.type == "file":
        if proto:
            if c.default:
                value = read_file_type(proto, c.default, proto.bundle.hash, c.name, c.subname)

    return value


def type_is_complex(conf_type):
    if conf_type in ("json", "structure", "list", "map"):
        return True

    return False


def read_file_type(proto, default, bundle_hash, name, subname):
    msg = f'config key "{name}/{subname}" default file'

    return read_bundle_file(proto, default, bundle_hash, msg)


def read_bundle_file(proto, fname, bundle_hash, pattern, ref=None):
    if not ref:
        ref = proto_ref(proto)

    if fname[0:2] == "./":
        path = Path(BUNDLE_DIR, bundle_hash, proto.path, fname)
    else:
        path = Path(BUNDLE_DIR, bundle_hash, fname)

    fd = None
    try:
        fd = open(path, "r", encoding="utf_8")
    except FileNotFoundError:
        msg = '{} "{}" is not found ({})'
        raise_adcm_ex("CONFIG_TYPE_ERROR", msg.format(pattern, path, ref))
    except PermissionError:
        msg = '{} "{}" can not be open ({})'
        raise_adcm_ex("CONFIG_TYPE_ERROR", msg.format(pattern, path, ref))

    if fd:
        body = fd.read()
        fd.close()

        return body

    return None


def init_object_config(proto: Prototype, obj: Any) -> Optional[ObjectConfig]:
    spec, _, conf, attr = get_prototype_config(proto)
    if not conf:
        return None

    obj_conf = ObjectConfig(current=0, previous=0)
    obj_conf.save()
    save_obj_config(obj_conf, conf, attr, "init")
    process_file_type(obj, spec, conf)

    return obj_conf


def get_prototype_config(proto: Prototype, action: Action = None) -> Tuple[dict, dict, dict, dict]:
    spec = {}
    flat_spec = OrderedDict()
    conf = {}
    attr = {}
    flist = ("default", "required", "type", "limits")
    for c in PrototypeConfig.objects.filter(prototype=proto, action=action, type="group").order_by(
        "id"
    ):
        spec[c.name] = {}
        conf[c.name] = {}
        if "activatable" in c.limits:
            attr[c.name] = {"active": c.limits["active"]}

    for c in PrototypeConfig.objects.filter(prototype=proto, action=action).order_by("id"):
        flat_spec[f"{c.name}/{c.subname}"] = c
        if c.subname == "":
            if c.type != "group":
                spec[c.name] = obj_to_dict(c, flist)
                conf[c.name] = get_default(c, proto)
        else:
            spec[c.name][c.subname] = obj_to_dict(c, flist)
            conf[c.name][c.subname] = get_default(c, proto)

    return spec, flat_spec, conf, attr


def make_object_config(obj: ADCMEntity, prototype: Prototype) -> None:
    if obj.config:
        return

    obj_conf = init_object_config(prototype, obj)
    if obj_conf:
        obj.config = obj_conf
        obj.save()


def switch_config(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    obj: ADCMEntity, new_proto: Prototype, old_proto: Prototype
) -> None:
    # process objects without config
    if not obj.config:
        make_object_config(obj, new_proto)
        return

    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    _, old_spec, _, _ = get_prototype_config(old_proto)
    new_unflat_spec, new_spec, _, _ = get_prototype_config(new_proto)
    old_conf = to_flat_dict(cl.config, old_spec)

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
                if group_name in cl.attr:
                    if cl.attr[group_name]["active"]:
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
        k1, k2 = key.split("/")
        if k2 == "":
            unflat_conf[k1] = value
        else:
            if k1 not in unflat_conf:
                unflat_conf[k1] = {}

            unflat_conf[k1][k2] = value

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
    cl = ConfigLog.obj.get(obj_ref=obj_conf, id=version)
    obj_conf.previous = obj_conf.current
    obj_conf.current = version
    obj_conf.save()

    if desc != "":
        cl.description = desc

    cl.save()

    return cl


def save_obj_config(obj_conf, conf, attr, desc=""):
    cl = ConfigLog(obj_ref=obj_conf, config=conf, attr=attr, description=desc)
    cl.save()
    obj_conf.previous = obj_conf.current
    obj_conf.current = cl.id
    obj_conf.save()

    return cl


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

    return Path(FILE_DIR, ".".join(filename))


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
    # TODO: That should be fixed some way in bundles or in openssh.
    if key == "ansible_ssh_private_key_file":
        if value != "":
            if value[-1] == "-":
                value += "\n"

    fd = open(filename, "w", encoding="utf_8")
    fd.write(value)
    fd.close()
    Path(filename).chmod(0o0600)

    return filename


def process_file_type(obj: Any, spec: dict, conf: dict):
    for key in conf:
        if "type" in spec[key]:
            if spec[key]["type"] == "file":
                save_file_type(obj, key, "", conf[key])
        elif conf[key]:
            for subkey in conf[key]:
                if spec[key][subkey]["type"] == "file":
                    save_file_type(obj, key, subkey, conf[key][subkey])


def ansible_encrypt(msg):
    vault = VaultAES256()
    secret = VaultSecret(bytes(ANSIBLE_SECRET, ENCODING))

    return vault.encrypt(bytes(msg, ENCODING), secret)


def ansible_encrypt_and_format(msg):
    ciphertext = ansible_encrypt(msg)

    return f"{ANSIBLE_VAULT_HEADER}\n{str(ciphertext, ENCODING)}"


def ansible_decrypt(msg):
    if ANSIBLE_VAULT_HEADER not in msg:
        return msg

    _, ciphertext = msg.split("\n")
    vault = VaultAES256()
    secret = VaultSecret(bytes(ANSIBLE_SECRET, ENCODING))

    return str(vault.decrypt(ciphertext, secret), ENCODING)


def is_ansible_encrypted(msg):
    if not isinstance(msg, str):
        msg = str(msg, ENCODING)
    if ANSIBLE_VAULT_HEADER in msg:
        return True

    return False


def process_password(spec, conf):
    def update_password(passwd):
        if "$ANSIBLE_VAULT;" in passwd:
            return passwd

        return ansible_encrypt_and_format(passwd)

    for key in conf:
        if "type" in spec[key]:
            if spec[key]["type"] in SECURE_PARAM_TYPES and conf[key]:
                conf[key] = update_password(conf[key])
        else:
            for subkey in conf[key]:
                if spec[key][subkey]["type"] in SECURE_PARAM_TYPES and conf[key][subkey]:
                    conf[key][subkey] = update_password(conf[key][subkey])

    return conf


def process_config(obj, spec, old_conf):  # pylint: disable=too-many-branches
    if not old_conf:
        return old_conf

    conf = copy.deepcopy(old_conf)
    for key in conf:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if conf[key] is not None:
                if spec[key]["type"] == "file":
                    conf[key] = cook_file_type_name(obj, key, "")
                elif spec[key]["type"] in SECURE_PARAM_TYPES:
                    if ANSIBLE_VAULT_HEADER in conf[key]:
                        conf[key] = {"__ansible_vault": conf[key]}
        elif conf[key]:
            for subkey in conf[key]:
                if conf[key][subkey] is not None:
                    if spec[key][subkey]["type"] == "file":
                        conf[key][subkey] = cook_file_type_name(obj, key, subkey)
                    elif spec[key][subkey]["type"] in SECURE_PARAM_TYPES:
                        if ANSIBLE_VAULT_HEADER in conf[key][subkey]:
                            conf[key][subkey] = {"__ansible_vault": conf[key][subkey]}

    return conf


def group_is_activatable(spec):
    if spec.type != "group":
        return False

    if "activatable" in spec.limits:
        return spec.limits["activatable"]

    return False


def ui_config(obj, cl):  # pylint: disable=too-many-locals
    conf = []
    _, spec, _, _ = get_prototype_config(obj.prototype)
    obj_conf = cl.config
    obj_attr = cl.attr
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
                k = key.split("/")[0]
                item["group"] = group_keys[k]["value"]
                item["custom_group"] = custom_group_keys[k]["value"]
            else:
                k1, k2 = key.split("/")
                if k2:
                    item["group"] = group_keys[k1]["fields"][k2]
                    item["custom_group"] = custom_group_keys[k1]["fields"][k2]
                else:
                    item["group"] = group_keys[k1]
                    item["custom_group"] = custom_group_keys[k1]

        conf.append(item)

    return conf


def get_action_variant(obj, conf):
    if obj.config:
        cl = ConfigLog.objects.filter(obj_ref=obj.config, id=obj.config.current).first()
        if cl:
            for c in conf:
                if c.type != "variant":
                    continue

                c.limits["source"]["value"] = get_variant(obj, cl.config, c.limits)


def config_is_ro(obj, key, limits):
    if not limits:
        return False

    if not hasattr(obj, "state"):
        return False

    ro = limits.get("read_only", [])
    wr = limits.get("writable", [])

    if ro and wr:
        msg = 'can not have "read_only" and "writable" simultaneously (config key "{}" of {})'
        raise_adcm_ex("INVALID_CONFIG_DEFINITION", msg.format(key, proto_ref(obj.prototype)))

    if ro == "any":
        return True

    if obj.state in ro:
        return True

    if wr == "any":
        return False

    if wr and obj.state not in wr:
        return True

    return False


def check_read_only(obj, spec, conf, old_conf):
    flat_conf = to_flat_dict(conf, spec)
    flat_old_conf = to_flat_dict(old_conf, spec)

    for s in spec:
        if config_is_ro(obj, s, spec[s].limits) and s in flat_conf:

            # this block is an attempt to fix sending read-only fields of list and map types
            # Since this did not help, I had to completely turn off the validation
            # of read-only fields
            if spec[s].type == "list":
                if isinstance(flat_conf[s], list) and not flat_conf[s]:
                    continue

            if spec[s].type == "map":
                if isinstance(flat_conf[s], dict) and not flat_conf[s]:
                    continue

            if flat_conf[s] != flat_old_conf[s]:
                msg = "config key {} of {} is read only"
                raise_adcm_ex("CONFIG_VALUE_ERROR", msg.format(s, proto_ref(obj.prototype)))


def restore_read_only(obj, spec, conf, old_conf):  # # pylint: disable=too-many-branches
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
                    dict_to_obj(spec[key][subkey], PrototypeConfig(), ("type", "default", "limits"))
                )
    # end of patch

    for key in spec:  # pylint: disable=too-many-nested-blocks
        if "type" in spec[key]:
            if config_is_ro(obj, key, spec[key]["limits"]) and key not in conf:
                if key in old_conf:
                    conf[key] = old_conf[key]
        else:
            for subkey in spec[key]:
                if config_is_ro(obj, key + "/" + subkey, spec[key][subkey]["limits"]):
                    if key in conf:
                        if subkey not in conf:
                            if key in old_conf and subkey in old_conf[key]:
                                conf[key][subkey] = old_conf[key][subkey]
                    elif key in old_conf and subkey in old_conf[key]:
                        conf[key] = {subkey: old_conf[key][subkey]}

    return conf


def check_json_config(
    proto, obj, new_config, current_config=None, new_attr=None, current_attr=None
):
    spec, flat_spec, _, _ = get_prototype_config(proto)
    check_attr(proto, obj, new_attr, flat_spec, current_attr)

    if isinstance(obj, GroupConfig):
        config_spec = obj.get_config_spec()
        group_keys = new_attr.get("group_keys", {})
        check_value_unselected_field(
            current_config, new_config, current_attr, new_attr, group_keys, config_spec, obj.object
        )

    process_variant(obj, spec, new_config)

    return check_config_spec(proto, obj, spec, flat_spec, new_config, current_config, new_attr)


def check_structure_for_group_attr(group_keys, spec, key_name):
    """Check structure for `group_keys` and `custom_group_keys` field in attr"""
    flat_group_attr = group_keys_to_flat(group_keys, spec)
    for key, value in flat_group_attr.items():
        if key not in spec:
            raise_adcm_ex("ATTRIBUTE_ERROR", f"invalid `{key}` field in `{key_name}`")

        if spec[key].type == "group":
            if not (
                isinstance(value, bool)
                and "activatable" in spec[key].limits
                or value is None
                and "activatable" not in spec[key].limits
            ):
                raise_adcm_ex("ATTRIBUTE_ERROR", f"invalid type `value` field in `{key}`")
        else:
            if not isinstance(value, bool):
                raise_adcm_ex("ATTRIBUTE_ERROR", f"invalid type `{key}` field in `{key_name}`")

    for key, value in spec.items():
        if value.type != "group":
            if key not in flat_group_attr:
                raise_adcm_ex("ATTRIBUTE_ERROR", f"there is no `{key}` field in `{key_name}`")

    return flat_group_attr


def check_agreement_group_attr(group_keys, custom_group_keys, spec):
    """Check agreement group_keys and custom_group_keys"""
    flat_group_keys = group_keys_to_flat(group_keys, spec)
    flat_custom_group_keys = group_keys_to_flat(custom_group_keys, spec)
    for key, value in flat_custom_group_keys.items():
        if not value and flat_group_keys[key]:
            raise_adcm_ex("ATTRIBUTE_ERROR", f"the `{key}` field cannot be included in the group")


def check_value_unselected_field(
    current_config, new_config, current_attr, new_attr, group_keys, spec, obj
):
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
            (bool(current[key]) is False and new[key] is None)
            or (current[key] is None and bool(new[key]) is False)
        ):
            return True

        return False

    for k, v in group_keys.items():
        if isinstance(v, Mapping):
            if (
                "activatable" in spec[k]["limits"]
                and not v["value"]
                and current_attr[k]["active"] != new_attr[k]["active"]
            ):
                msg = (
                    f"Value of `{k}` activatable group is different in current and new attr."
                    f' Current: ({current_attr[k]["active"]}), New: ({new_attr[k]["active"]})'
                )
                logger.info(msg)
                raise_adcm_ex("GROUP_CONFIG_CHANGE_UNSELECTED_FIELD", msg)

            check_value_unselected_field(
                current_config[k],
                new_config[k],
                current_attr,
                new_attr,
                group_keys[k]["fields"],
                spec[k]["fields"],
                obj,
            )
        else:
            if spec[k]["type"] in ["list", "map", "string", "structure"]:
                if config_is_ro(obj, k, spec[k]["limits"]) or check_empty_values(
                    k, current_config, new_config
                ):
                    continue

            if (
                not v
                and k in current_config
                and k in new_config
                and current_config[k] != new_config[k]
            ):
                msg = (
                    f"Value of `{k}` field is different in current and new config."
                    f" Current: ({current_config[k]}), New: ({new_config[k]})"
                )
                logger.info(msg)
                raise_adcm_ex("GROUP_CONFIG_CHANGE_UNSELECTED_FIELD", msg)


def check_group_keys_attr(attr, spec, group_config):
    """Check attr for group config"""
    if "group_keys" not in attr:
        raise_adcm_ex("ATTRIBUTE_ERROR", '`attr` must contain "group_keys" key')

    group_keys = attr.get("group_keys")
    _, custom_group_keys = group_config.create_group_keys(group_config.get_config_spec())
    check_structure_for_group_attr(group_keys, spec, "group_keys")
    check_agreement_group_attr(group_keys, custom_group_keys, spec)


def check_attr(
    proto: Prototype, obj, attr: dict, spec: dict, current_attr: dict | None = None
):  # pylint: disable=too-many-branches
    is_group_config = False
    if isinstance(obj, GroupConfig):
        is_group_config = True

    ref = proto_ref(proto)
    allowed_key = ("active",)
    if not isinstance(attr, dict):
        raise_adcm_ex("ATTRIBUTE_ERROR", "`attr` should be a map")

    for key, value in attr.items():
        if key in ["group_keys", "custom_group_keys"]:
            if not is_group_config:
                raise_adcm_ex("ATTRIBUTE_ERROR", f"not allowed key `{key}` for object ({ref})")
            continue

        if key + "/" not in spec:
            raise_adcm_ex("ATTRIBUTE_ERROR", f"there isn't `{key}` group in the config ({ref})")
        if spec[key + "/"].type != "group":
            raise_adcm_ex("ATTRIBUTE_ERROR", f"config key `{key}` is not a group ({ref})")

    for value in spec.values():
        key = value.name
        if value.type == "group" and "activatable" in value.limits:
            if key not in attr:
                raise_adcm_ex("ATTRIBUTE_ERROR", f"there isn't `{key}` group in the `attr`")

            if not isinstance(attr[key], dict):
                raise_adcm_ex(
                    "ATTRIBUTE_ERROR",
                    f"value of attribute `{key}` should be a map ({ref})",
                )

            for attr_key in attr[key]:
                if attr_key not in allowed_key:
                    raise_adcm_ex(
                        "ATTRIBUTE_ERROR",
                        f"not allowed key `{attr_key}` of attribute `{key}` ({ref})",
                    )

                if not isinstance(attr[key]["active"], bool):
                    raise_adcm_ex(
                        "ATTRIBUTE_ERROR",
                        f"value of key `active` of attribute `{key}` should be boolean ({ref})",
                    )

                if (current_attr[key]["active"] != attr[key]["active"]) and config_is_ro(
                    obj, key, value.limits
                ):
                    msg = "config key {} of {} is read only"
                    raise_adcm_ex("CONFIG_VALUE_ERROR", msg.format(key, ref))

    if is_group_config:
        check_group_keys_attr(attr, spec, obj)


def check_config_spec(
    proto, obj, spec, flat_spec, conf, old_conf=None, attr=None
):  # pylint: disable=too-many-branches,too-many-statements
    group = None
    if isinstance(obj, GroupConfig):
        group = obj
        obj = group.object

    ref = proto_ref(proto)
    if isinstance(conf, (float, int)):
        raise_adcm_ex("JSON_ERROR", "config should not be just one int or float")

    if isinstance(conf, str):
        raise_adcm_ex("JSON_ERROR", "config should not be just one string")

    def key_is_required(_key, subkey, _spec):
        if config_is_ro(obj, f"{_key}/{subkey}", spec.get("limits", "")):
            return False

        if _spec["required"]:
            return True

        return False

    def is_inactive(_key):
        if attr and flat_spec[f"{_key}/"].type == "group":
            if _key in attr and "active" in attr[_key]:
                return not bool(attr[_key]["active"])

        return False

    def check_sub(_key):
        if not isinstance(conf[_key], dict):
            _msg = 'There are not any subkeys for key "{}" ({})'
            raise_adcm_ex("CONFIG_KEY_ERROR", _msg.format(_key, ref))

        if not conf[_key]:
            _msg = 'Key "{}" should contains some subkeys ({})'
            raise_adcm_ex("CONFIG_KEY_ERROR", _msg.format(_key, ref), list(spec[_key].keys()))

        for subkey in conf[_key]:
            if subkey not in spec[_key]:
                _msg = 'There is unknown subkey "{}" for key "{}" in input config ({})'
                raise_adcm_ex("CONFIG_KEY_ERROR", _msg.format(subkey, _key, ref))

        for subkey in spec[_key]:
            if subkey in conf[_key]:
                check_config_type(
                    proto,
                    _key,
                    subkey,
                    spec[_key][subkey],
                    conf[_key][subkey],
                    False,
                    is_inactive(_key),
                )
            elif key_is_required(_key, subkey, spec[_key][subkey]):
                _msg = 'There is no required subkey "{}" for key "{}" ({})'
                raise_adcm_ex("CONFIG_KEY_ERROR", _msg.format(subkey, _key, ref))

    def sub_key_is_required(_key):
        if is_inactive(_key):
            return False

        for subkey in spec[_key]:
            if key_is_required(_key, subkey, spec[_key][subkey]):
                return True

        return False

    for key in conf:
        if key not in spec:
            msg = 'There is unknown key "{}" in input config ({})'
            raise_adcm_ex("CONFIG_KEY_ERROR", msg.format(key, ref))

        if "type" in spec[key] and spec[key]["type"] != "group":
            if isinstance(conf[key], dict) and not type_is_complex(spec[key]["type"]):
                msg = 'Key "{}" in input config should not have any subkeys ({})'
                raise_adcm_ex("CONFIG_KEY_ERROR", msg.format(key, ref))

    for key in spec:
        if "type" in spec[key] and spec[key]["type"] != "group":
            if key in conf:
                check_config_type(proto, key, "", spec[key], conf[key])
            elif key_is_required(key, "", spec[key]):
                msg = 'There is no required key "{}" in input config ({})'
                raise_adcm_ex("CONFIG_KEY_ERROR", msg.format(key, ref))
        else:
            if key not in conf:
                if sub_key_is_required(key):
                    msg = 'There are no required key "{}" in input config'
                    raise_adcm_ex("CONFIG_KEY_ERROR", msg.format(key))
            else:
                check_sub(key)

    if old_conf:
        # TODO: it is necessary to investigate the problem
        # check_read_only(obj, flat_spec, conf, old_conf)
        restore_read_only(obj, spec, conf, old_conf)

    # for process_file_type() function not need `if old_conf:`
    process_file_type(group or obj, spec, conf)
    process_password(spec, conf)

    return conf


def check_config_type(
    proto, key, subkey, spec, value, default=False, inactive=False
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
            _msg = (
                f'{label} ("{_v}") of element "{_idx}" of config key "{key}/{subkey}"'
                f" should be string ({ref})"
            )
            raise_adcm_ex("CONFIG_VALUE_ERROR", _msg)

    if (
        value is None
        or (spec["type"] == "map" and value == {})
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

        for idx, v in enumerate(value):
            check_str(idx, v)

    if spec["type"] == "map":
        if not isinstance(value, dict):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("should be a map"))

        if "required" in spec and spec["required"] and value == {}:
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

        for k, v in value.items():
            check_str(k, v)

    if spec["type"] in ("string", "password", "text", "secrettext"):
        if not isinstance(value, str):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be string"))

        if "required" in spec and spec["required"] and value == "":
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

    if spec["type"] == "file":
        if not isinstance(value, str):
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl2.format("should be string"))

        if value == "":
            raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format(should_not_be_empty))

        if default:
            if len(value) > 2048:
                raise_adcm_ex("CONFIG_VALUE_ERROR", tmpl1.format("is too long"))

            read_file_type(proto, value, default, key, subkey)

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
        for _, v in option.items():
            if v == value:
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


def replace_object_config(obj, key, subkey, value, proto_conf):
    cl = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)
    conf = cl.config

    if proto_conf.type in SECURE_PARAM_TYPES and not is_ansible_encrypted(value):
        value = ansible_encrypt_and_format(value)

    if subkey:
        conf[key][subkey] = value
    else:
        conf[key] = value

    save_obj_config(obj.config, conf, cl.attr, "ansible update")


def set_object_config(obj, keys, value):
    proto = obj.prototype
    spl = keys.split("/")
    key = spl[0]
    if len(spl) == 1:
        subkey = ""
    else:
        subkey = spl[1]

    pconf = PrototypeConfig.obj.get(prototype=proto, action=None, name=key, subname=subkey)
    if pconf.type == "group":
        msg = 'You can not update config group "{}" for {}'
        raise_adcm_ex("CONFIG_VALUE_ERROR", msg.format(key, obj_ref(obj)))

    check_config_type(proto, key, subkey, obj_to_dict(pconf, ("type", "limits", "option")), value)
    replace_object_config(obj, key, subkey, value, pconf)
    if pconf.type == "file":
        save_file_type(obj, key, subkey, value)

    log_value = value
    if pconf.type in SECURE_PARAM_TYPES:
        log_value = "****"

    logger.info('update %s config %s/%s to "%s"', obj_ref(obj), key, subkey, log_value)

    return value


def get_main_info(obj: Optional[ADCMEntity]) -> Optional[str]:
    """Return __main_info for object"""
    if obj.config is None:
        return None

    cl = ConfigLog.objects.filter(id=obj.config.current).first()
    if cl:
        _, spec, _, _ = get_prototype_config(obj.prototype)

        if "__main_info" in cl.config:
            return cl.config["__main_info"]
        elif "__main_info/" in spec:
            return get_default(spec["__main_info/"], obj.prototype)

    return None


def get_adcm_config(section=None):
    adcm_object = ADCM.objects.last()
    current_configlog = ConfigLog.objects.get(
        obj_ref=adcm_object.config, id=adcm_object.config.current
    )
    if not section:
        return current_configlog.attr, current_configlog.config

    return current_configlog.attr.get(section, None), current_configlog.config.get(section, None)
