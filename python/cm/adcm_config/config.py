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

from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import re
import copy
import json

from ansible.errors import AnsibleError
from django.conf import settings
from django.db.models import QuerySet

from cm.adcm_config.ansible import ansible_decrypt, ansible_encrypt_and_format
from cm.adcm_config.checks import check_attr, check_config_type
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
from cm.errors import AdcmEx, raise_adcm_ex
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    ObjectConfig,
    Prototype,
    PrototypeConfig,
    Provider,
    Service,
    TaskLog,
)
from cm.services.bundle import ADCMBundlePathResolver, BundlePathResolver, PathResolver
from cm.services.config.jinja import get_jinja_config
from cm.utils import deep_merge, dict_to_obj, obj_to_dict
from cm.variant import get_variant, process_variant


@contextmanager
def reraise_file_errors_as_adcm_ex(filepath: Path | str, reference: str):
    try:
        yield
    except FileNotFoundError as err:
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=f'"{filepath}" is not found ({reference})') from err
    except PermissionError as err:
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=f'"{filepath}" can not be open ({reference})') from err


def init_object_config(proto: Prototype, obj: Any) -> ObjectConfig | None:
    spec, _, conf, attr = get_prototype_config(proto)
    if not conf:
        return None

    obj_conf = ObjectConfig(current=0, previous=0)
    obj_conf.save()
    save_object_config(obj_conf, conf, attr, "init")
    process_file_type(obj, spec, conf)

    return obj_conf


def get_prototype_config(
    prototype: Prototype, action: Action = None, obj: ADCMEntity = None
) -> tuple[dict, dict, dict, dict]:
    spec = {}
    flat_spec = OrderedDict()
    config = {}
    attr = {}
    flist = ("default", "required", "type", "limits")

    if action is not None and obj is not None and action.config_jinja:
        proto_conf, _ = get_jinja_config(action=action, cluster_relative_object=obj)
        proto_conf_group = [config for config in proto_conf if config.type == "group"]
    else:
        proto_conf = PrototypeConfig.objects.filter(prototype=prototype, action=action).order_by("id")
        proto_conf_group = PrototypeConfig.objects.filter(prototype=prototype, action=action, type="group").order_by(
            "id"
        )

    for conf in proto_conf_group:
        spec[conf.name] = {}
        config[conf.name] = {}
        if "activatable" in conf.limits:
            attr[conf.name] = {"active": conf.limits["active"]}

    path_resolver = (
        ADCMBundlePathResolver() if prototype.type == "adcm" else BundlePathResolver(bundle_hash=prototype.bundle.hash)
    )

    for conf in proto_conf:
        flat_spec[f"{conf.name}/{conf.subname}"] = conf
        if conf.subname == "":
            if conf.type != "group":
                spec[conf.name] = obj_to_dict(conf, flist)
                config[conf.name] = get_default(conf, path_resolver=path_resolver)
        else:
            spec[conf.name][conf.subname] = obj_to_dict(conf, flist)
            config[conf.name][conf.subname] = get_default(conf, path_resolver=path_resolver)

    return spec, flat_spec, config, attr


def make_object_config(obj: ADCMEntity, prototype: Prototype) -> None:
    if obj.config:
        return

    obj_conf = init_object_config(prototype, obj)
    if obj_conf:
        obj.config = obj_conf
        obj.save()


def switch_config(
    obj: ADCMEntity,
    new_prototype: Prototype,
    old_prototype: Prototype,
) -> None:
    # process objects without config
    if not obj.config:
        make_object_config(obj=obj, prototype=new_prototype)

        return

    config_log = ConfigLog.objects.get(obj_ref=obj.config, id=obj.config.current)

    _, old_spec, _, _ = get_prototype_config(prototype=old_prototype)
    new_unflat_spec, new_spec, _, _ = get_prototype_config(prototype=new_prototype)
    old_conf = to_flat_dict(config=config_log.config, spec=old_spec)

    old_path_resolver = (
        ADCMBundlePathResolver()
        if old_prototype.type == "adcm"
        else BundlePathResolver(bundle_hash=old_prototype.bundle.hash)
    )
    new_path_resolver = (
        ADCMBundlePathResolver()
        if old_prototype.type == "adcm"
        else BundlePathResolver(bundle_hash=new_prototype.bundle.hash)
    )

    def is_new_default(_key):
        if not new_spec[_key].default:
            return False

        if old_spec[_key].default:
            if _key in old_conf:
                return bool(get_default(conf=old_spec[_key], path_resolver=old_path_resolver) == old_conf[_key])
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
                new_conf[key] = get_default(conf=new_spec[key], path_resolver=new_path_resolver)
            else:
                new_conf[key] = old_conf.get(key, get_default(conf=new_spec[key], path_resolver=new_path_resolver))
        else:
            new_conf[key] = get_default(conf=new_spec[key], path_resolver=new_path_resolver)

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

    save_object_config(object_config=obj.config, config=unflat_conf, attr=attr, description="upgrade")
    process_file_type(obj=obj, spec=new_unflat_spec, conf=unflat_conf)


def restore_cluster_config(obj_conf, version, desc=""):
    config_log = ConfigLog.obj.get(obj_ref=obj_conf, id=version)
    obj_conf.previous = obj_conf.current
    obj_conf.current = version
    obj_conf.save()

    if desc != "":
        config_log.description = desc

    config_log.save()

    return config_log


def _merge_config_field(origin_config_fields: dict, host_group_fields: dict, group_keys: dict, spec: dict) -> dict:
    for field_name, info in spec.items():
        if info["type"] == "group" and field_name in group_keys:
            _merge_config_field(
                origin_config_fields=origin_config_fields[field_name],
                host_group_fields=host_group_fields[field_name],
                group_keys=group_keys[field_name]["fields"],
                spec=spec[field_name]["fields"],
            )
        elif group_keys.get(field_name, False):
            origin_config_fields[field_name] = host_group_fields[field_name]

    return origin_config_fields


def _merge_attr_field(origin_attr_fields: dict, group_attr_fields: dict, group_keys: dict, spec: dict) -> dict:
    for field_name, info in spec.items():
        if info["type"] == "group" and group_keys.get(field_name, {}).get("value", False):
            origin_attr_fields[field_name] = group_attr_fields[field_name]

    return origin_attr_fields


def _clear_group_keys(group_keys: dict, spec: dict) -> dict:
    correct_group_keys = {}

    for field, info in spec.items():
        if info["type"] == "group":
            correct_group_keys[field] = {}
            correct_group_keys[field]["value"] = group_keys[field]["value"]
            correct_group_keys[field]["fields"] = {}

            for key in info["fields"]:
                correct_group_keys[field]["fields"][key] = group_keys[field]["fields"][key]
        else:
            correct_group_keys[field] = group_keys[field]

    return correct_group_keys


def merge_config_of_group_with_primary_config(
    group: ConfigHostGroup,
    primary_config: ConfigLog,
    current_config_of_group: ConfigLog,
    description: str,
) -> ConfigLog:
    spec = group.get_config_spec()
    current_group_keys = current_config_of_group.attr["group_keys"]

    config = _merge_config_field(
        origin_config_fields=copy.deepcopy(primary_config.config),
        host_group_fields=current_config_of_group.config,
        group_keys=current_group_keys,
        spec=spec,
    )
    attr = _merge_attr_field(
        origin_attr_fields=copy.deepcopy(primary_config.attr),
        group_attr_fields=current_config_of_group.attr,
        group_keys=current_group_keys,
        spec=spec,
    )

    group_keys, custom_group_keys = group.create_group_keys(config_spec=spec)

    attr["group_keys"] = _clear_group_keys(
        group_keys=deep_merge(origin=group_keys, renovator=current_group_keys), spec=spec
    )
    attr["custom_group_keys"] = custom_group_keys

    return ConfigLog.objects.create(obj_ref=group.config, config=config, attr=attr, description=description)


def update_host_groups_by_primary_object(object_: Cluster | Service | Component | Provider, config: ConfigLog) -> None:
    for host_group in object_.config_host_group.order_by("id"):
        current_config_of_host_group = ConfigLog.objects.get(id=host_group.config.current)

        config_log = merge_config_of_group_with_primary_config(
            group=host_group,
            primary_config=config,
            current_config_of_group=current_config_of_host_group,
            description=config.description,
        )

        config_log.save()

        host_group.config.previous = host_group.config.current
        host_group.config.current = config_log.id
        host_group.config.save(update_fields=["previous", "current"])

        host_group.prepare_files_for_config(config=config_log.config)


def update_host_group(host_group: ConfigHostGroup, config: ConfigLog) -> ConfigLog:
    primary_config = ConfigLog.objects.get(id=host_group.object.config.current)

    return merge_config_of_group_with_primary_config(
        group=host_group,
        primary_config=primary_config,
        current_config_of_group=config,
        description=config.description,
    )


def save_object_config(object_config: ObjectConfig, config: dict, attr: dict, description: str = "") -> ConfigLog:
    config_log = ConfigLog(obj_ref=object_config, config=config, attr=attr, description=description)
    obj = object_config.object

    if isinstance(obj, ConfigHostGroup):
        config_log = update_host_group(host_group=obj, config=config_log)
        config_log.save()
        obj.prepare_files_for_config(config=config_log.config)
    elif isinstance(obj, (Cluster, Service, Component, Provider)):
        config_log.save()
        update_host_groups_by_primary_object(object_=obj, config=config_log)
    else:
        config_log.save()

    object_config.previous = object_config.current
    object_config.current = config_log.id
    object_config.save(update_fields=["previous", "current"])

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

    if key == "ansible_ssh_private_key_file" and value != "" and value[-1] == "-":
        value += "\n"

    file_descriptor = open(filename, "w", encoding=settings.ENCODING_UTF_8)  # noqa: SIM115
    file_descriptor.write(value)
    file_descriptor.close()
    Path(filename).chmod(0o0600)

    return filename


def process_file_type(obj: Any, spec: dict, conf: dict):
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


def process_config(
    obj: ADCMEntity,
    spec: dict,
    old_conf: dict,
) -> dict:
    if not old_conf:
        return old_conf

    conf = copy.deepcopy(old_conf)
    for key in conf:
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


def ui_config(obj, config_log):
    conf = []
    _, spec, _, _ = get_prototype_config(obj.prototype)
    obj_conf = config_log.config
    obj_attr = config_log.attr
    flat_conf = to_flat_dict(obj_conf, spec)
    group_keys = obj_attr.get("group_keys", {})
    custom_group_keys = obj_attr.get("custom_group_keys", {})
    slist = ("name", "subname", "type", "description", "display_name", "required")

    path_resolver = (
        ADCMBundlePathResolver() if isinstance(obj, ADCM) else BundlePathResolver(bundle_hash=obj.prototype.bundle.hash)
    )

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

        item["default"] = get_default(spec[key], path_resolver=path_resolver)
        if key in flat_conf:
            item["value"] = flat_conf[key]
        else:
            item["value"] = get_default(spec[key], path_resolver=path_resolver)

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


def get_action_variant(obj: ADCMEntity, prototype_configs: QuerySet[PrototypeConfig] | list[PrototypeConfig]) -> None:
    if obj.config:
        config_log = ConfigLog.objects.filter(obj_ref=obj.config, id=obj.config.current).first()
        if config_log:
            for conf in prototype_configs:
                if conf.type != "variant":
                    continue

                conf.limits["source"]["value"] = get_variant(obj, config_log.config, conf.limits)


def restore_read_only(obj, spec, conf, old_conf):
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

    for key in spec:
        if "type" in spec[key]:
            if config_is_ro(obj, key, spec[key]["limits"]) and key not in conf and key in old_conf:
                conf[key] = old_conf[key]
        else:
            for subkey in spec[key]:
                if config_is_ro(obj=obj, key=f"{key}/{subkey}", limits=spec[key][subkey]["limits"]):
                    if key in conf and subkey not in conf and key in old_conf and subkey in old_conf[key]:
                        conf[key][subkey] = old_conf[key][subkey]
                    elif key in old_conf and subkey in old_conf[key]:
                        conf[key] = {subkey: old_conf[key][subkey]}

    return conf


def process_json_config(
    prototype: Prototype,
    obj: ADCMEntity | Action,
    new_config: dict,
    new_attr: dict | None = None,
    current_attr: dict | None = None,
) -> dict:
    spec, flat_spec, _, _ = get_prototype_config(prototype=prototype)
    check_attr(prototype, obj, new_attr, flat_spec, current_attr)
    group = None

    if isinstance(obj, ConfigHostGroup):
        group = obj
        obj = group.object

    process_variant(obj, spec, new_config)
    check_config_spec(proto=prototype, obj=obj, spec=spec, flat_spec=flat_spec, conf=new_config, attr=new_attr)
    return process_config_spec(obj=group or obj, spec=spec, new_config=new_config)


def check_config_spec(
    proto: Prototype,
    obj: ADCMEntity | Action,
    spec: dict,
    flat_spec: dict,
    conf: dict,
    attr: dict = None,
) -> None:
    if not isinstance(conf, dict):
        # AdcmEx is left here instead of TypeError, because of existing usages
        # and most likely existence of reliable code on exactly AdcmEx.
        # Replace during major refactoring.
        raise AdcmEx(code="JSON_ERROR", msg="config should be a mapping-like entity")

    ref = proto_ref(proto)

    unknown_keys = set(conf.keys()).difference(spec.keys())
    if unknown_keys:
        raise AdcmEx(
            code="CONFIG_KEY_ERROR",
            msg=f"There is unknown keys in input config ({ref}): {', '.join(sorted(unknown_keys))}",
        )

    for key in spec:
        # From discussion with colleagues: most likely type is absent for groups,
        # because spec for their children is in their value
        if spec[key].get("type", "group") != "group":
            if key not in conf:
                if key_is_required(obj=obj, key=key, subkey="", spec=spec):
                    raise AdcmEx(
                        code="CONFIG_KEY_ERROR", msg=f'There is no required key "{key}" in input config ({ref})'
                    )

                continue

            config_value = conf[key]
            if isinstance(config_value, dict) and spec[key]["type"] not in settings.STACK_COMPLEX_FIELD_TYPES:
                raise AdcmEx(
                    code="CONFIG_KEY_ERROR",
                    msg=f'Key "{key}" in input config should not have any subkeys ({ref})',
                )

            check_config_type(prototype=proto, key=key, subkey="", spec=spec[key], value=config_value)

            continue

        # Processing group
        if key not in conf:
            if sub_key_is_required(key=key, attr=attr, flat_spec=flat_spec, spec=spec, obj=obj):
                raise AdcmEx(code="CONFIG_KEY_ERROR", msg=f'There is no required key "{key}" in input config')

            continue

        config_value = conf[key]
        if not isinstance(config_value, dict):
            raise AdcmEx(code="CONFIG_KEY_ERROR", msg=f'There are not any subkeys for key "{key}" ({ref})')

        if not config_value:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR",
                msg=f'Key "{key}" should contain subkeys ({ref}): {list(spec[key].keys())}',
            )

        for subkey in config_value:
            if subkey not in spec[key]:
                raise AdcmEx(
                    code="CONFIG_KEY_ERROR",
                    msg=f'There is unknown subkey "{subkey}" for key "{key}" in input config ({ref})',
                )

        for subkey in spec[key]:
            if subkey not in config_value:
                if key_is_required(obj=obj, key=key, subkey=subkey, spec=spec):
                    raise AdcmEx(
                        code="CONFIG_KEY_ERROR",
                        msg=f'There is no required subkey "{subkey}" for key "{key}" ({ref})',
                    )

                continue

            check_config_type(
                prototype=proto,
                key=key,
                subkey=subkey,
                spec=spec[key][subkey],
                value=config_value[subkey],
                default=False,
                inactive=is_inactive(key, attr, flat_spec),
            )


def _process_secretfile(obj: ADCMEntity, key: str, subkey: str, value: Any) -> None:
    if value is not None and value.startswith(settings.ANSIBLE_VAULT_HEADER):
        try:
            value = ansible_decrypt(msg=value)
        except AnsibleError as e:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Can't decrypt value") from e

    save_file_type(obj=obj, key=key, subkey=subkey, value=value)


def _process_secret_param(conf: dict, key: str, subkey: str) -> None:
    value = conf[key]
    if subkey:
        value = conf[key][subkey]

    if not value:
        return

    if value.startswith(settings.ANSIBLE_VAULT_HEADER):
        try:
            ansible_decrypt(msg=value)
        except AnsibleError as e:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Can't decrypt value") from e

    else:
        value = ansible_encrypt_and_format(msg=value)

        if subkey:
            conf[key][subkey] = value
        else:
            conf[key] = value


def _process_secretmap(conf: dict, key: str, subkey: str) -> None:
    value = conf[key]
    if subkey:
        value = conf[key][subkey]

    if value is None:
        return

    for secretmap_key, secretmap_value in value.items():
        if secretmap_value.startswith(settings.ANSIBLE_VAULT_HEADER):
            try:
                ansible_decrypt(msg=secretmap_value)
            except AnsibleError as e:
                raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Can't decrypt value") from e

            if subkey:
                conf[key][subkey][secretmap_key] = secretmap_value
            else:
                conf[key][secretmap_key] = secretmap_value

        else:
            if subkey:
                conf[key][subkey][secretmap_key] = ansible_encrypt_and_format(msg=secretmap_value)
            else:
                conf[key][secretmap_key] = ansible_encrypt_and_format(msg=secretmap_value)


def process_config_spec(obj: ADCMEntity | TaskLog, spec: dict, new_config: dict) -> dict:
    for cfg_key, cfg_value in new_config.items():
        spec_type = spec[cfg_key].get("type")

        if spec_type == "file":
            save_file_type(obj=obj, key=cfg_key, subkey="", value=cfg_value)

        elif spec_type == "secretfile":
            _process_secretfile(obj=obj, key=cfg_key, subkey="", value=cfg_value)
            _process_secret_param(conf=new_config, key=cfg_key, subkey="")

        elif spec_type in {"password", "secrettext"}:
            _process_secret_param(conf=new_config, key=cfg_key, subkey="")

        elif spec_type == "secretmap":
            _process_secretmap(conf=new_config, key=cfg_key, subkey="")

        elif spec_type is None and bool(cfg_value):
            for sub_cfg_key, sub_cfg_value in cfg_value.items():
                sub_spec_type = spec[cfg_key][sub_cfg_key]["type"]

                if sub_spec_type == "file":
                    save_file_type(obj=obj, key=cfg_key, subkey=sub_cfg_key, value=sub_cfg_value)

                elif sub_spec_type == "secretfile":
                    _process_secretfile(obj=obj, key=cfg_key, subkey=sub_cfg_key, value=sub_cfg_value)
                    _process_secret_param(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

                elif sub_spec_type in {"password", "secrettext"}:
                    _process_secret_param(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

                elif sub_spec_type == "secretmap":
                    _process_secretmap(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

    return new_config


def get_adcm_config(section=None):
    adcm_object = ADCM.objects.get()
    current_configlog = ConfigLog.objects.get(obj_ref=adcm_object.config, id=adcm_object.config.current)
    if not section:
        return current_configlog.attr, current_configlog.config

    return current_configlog.attr.get(section, None), current_configlog.config.get(section, None)


def get_option_value(value: str, limits: dict) -> str | int | float:
    if value in limits["option"].values():
        return value
    elif re.match(r"^\d+$", value):
        return int(value)
    elif re.match(r"^\d+\.\d+$", value):
        return float(value)

    return raise_adcm_ex("CONFIG_OPTION_ERROR")


def get_default(conf: PrototypeConfig, path_resolver: PathResolver | None = None) -> Any:
    value = conf.default
    if conf.default == "":
        value = None
    elif conf.type == "string" or conf.type == "text":
        value = conf.default
    elif conf.type in settings.SECURE_PARAM_TYPES and conf.default:
        value = ansible_encrypt_and_format(msg=conf.default)
    elif conf.type in settings.STACK_COMPLEX_FIELD_TYPES:
        value = json.loads(s=conf.default) if isinstance(conf.default, str) else conf.default
    elif conf.type == "integer":
        value = int(conf.default)
    elif conf.type == "float":
        value = float(conf.default)
    elif conf.type == "boolean":
        value = conf.default if isinstance(conf.default, bool) else bool(conf.default.lower() in {"true", "yes"})
    elif conf.type == "option":
        value = get_option_value(value=value, limits=conf.limits)
    elif conf.type == "file" and path_resolver and conf.default:
        with reraise_file_errors_as_adcm_ex(
            filepath=conf.default, reference=f'config key "{conf.name}/{conf.subname}" default file'
        ):
            value = path_resolver.resolve(conf.default).read_text(encoding="utf-8")
    elif conf.type == "secretfile" and path_resolver and conf.default:
        with reraise_file_errors_as_adcm_ex(
            filepath=conf.default, reference=f'config key "{conf.name}/{conf.subname}" default file'
        ):
            value = ansible_encrypt_and_format(msg=path_resolver.resolve(conf.default).read_text(encoding="utf-8"))

    if conf.type == "secretmap" and conf.default:
        new_value = {}
        for conf_key, conf_value in value.items():
            new_value[conf_key] = ansible_encrypt_and_format(msg=conf_value)

        value = new_value

    return value


def get_main_info(obj: ADCMEntity | None) -> str | None:
    if obj is None or obj.config is None:
        return None

    config_log = ConfigLog.objects.filter(id=obj.config.current).first()
    if not config_log:
        return None

    if "__main_info" in config_log.config:
        return config_log.config["__main_info"]

    main_info = PrototypeConfig.objects.filter(
        prototype=obj.prototype, action=None, name="__main_info", subname=""
    ).first()
    if not main_info:
        return None

    path_resolver = (
        ADCMBundlePathResolver() if isinstance(obj, ADCM) else BundlePathResolver(bundle_hash=obj.prototype.bundle.hash)
    )

    return get_default(main_info, path_resolver=path_resolver)
