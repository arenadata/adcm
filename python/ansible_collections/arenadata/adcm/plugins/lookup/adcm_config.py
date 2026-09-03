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
from collections.abc import Collection, Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, NamedTuple
import re
import sys
import json

sys.path.append("/adcm/python")

import adcm.init_django  # noqa: F401, isort:skip

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase
from ansible_plugin.utils import get_service_by_name
from cm.converters import CoreObject, orm_object_to_core_descriptor
from cm.errors import AdcmEx, raise_adcm_ex
from cm.legacy.checker import FormatError, SchemaError, process_rule
from cm.legacy.services.bundle import ADCMBundlePathResolver, BundlePathResolver, PathResolver, is_path_correct
from cm.legacy.services.config.patterns import Pattern
from cm.legacy.services.job.run import update_related_configs
from cm.legacy.status_api import send_config_creation_event
from cm.legacy.utils import deep_merge, obj_to_dict
from cm.legacy.variant import process_variant
from cm.logger import logger
from cm.models import (
    ADCM,
    Action,
    ADCMEntity,
    Cluster,
    Component,
    ConfigHostGroup,
    ConfigLog,
    Host,
    ObjectConfig,
    ProcessStep,
    Prototype,
    PrototypeConfig,
    Provider,
    Service,
    TaskLog,
)
from cm.transition.ansible import ansible_decrypt, ansible_encrypt_and_format
from django.conf import settings
from django.db.transaction import atomic
from rbac.roles import apply_policy_for_new_config
from rest_framework.status import HTTP_409_CONFLICT

DOCUMENTATION = """
    lookup: file
    author: Konstantin Voschanov <vka@arenadata.io>
    version_added: "0.1"
    short_description: set config key for host, cluster or service
    description:
        - This lookup set value of specified config key/subkey for host, cluster or service
    options:
      _terms:
        description: cluster|service|host, 'key/subkey', value
        required: True
    notes:
      - if you run service action, you don't need specify service name
"""

EXAMPLES = """
- debug: msg="set host config {{lookup('adcm_config', 'host', 'ssh-key', 'F25') }}"

- debug: msg="set cluster config {{lookup('adcm_config', 'cluster', 'adh.cfg/port', 80) }}"

- debug: msg="set service config {{lookup('adcm_config', 'service', 'adh.cfg/port', 80) }}"

- debug: msg="set service config {{lookup('adcm_config', 'service', 'adh.cfg/port', 80, service_name='ZOOKEEPER') }}"

"""

RETURN = """
  _raw:
    description:
      - new value of config
"""


class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        logger.debug("run %s %s", terms, kwargs)

        return [call_adcm_config_lookup(terms=terms, variables=variables, kwargs=kwargs).value]


class PluginResult(NamedTuple):
    value: dict | int | str
    changed: bool


def call_adcm_config_lookup(
    terms: Sequence[Any], variables: Mapping[str, Any], kwargs: Mapping[str, Any]
) -> PluginResult:
    """
    Ansible-independent part of `adcm_config` lookup call
    """
    job_id = variables["job"]["id"]

    if len(terms) < 3:
        msg = "not enough arguments to set config ({} of 3)"
        raise AnsibleError(msg.format(len(terms)))

    conf = {terms[1]: terms[2]}

    obj = detect_target(terms=terms, variables=variables, kwargs=kwargs)

    return update_config(obj=obj, conf=conf, job_id=job_id)


def detect_target(terms: Sequence[Any], variables: Mapping[str, Any], kwargs: Mapping[str, Any]) -> ADCM | CoreObject:
    """
    Detect object which config should be changed based on lookup arguments and ansible variables
    """
    if terms[0] == "service":
        if "cluster" not in variables:
            raise AnsibleError("there is no cluster in hostvars")
        cluster = variables["cluster"]
        if "service_name" in kwargs:
            return get_service_by_name(cluster["id"], kwargs["service_name"])
        if "job" in variables and "service_id" in variables["job"]:
            return Service.obj.get(
                id=variables["job"]["service_id"], cluster__id=cluster["id"], prototype__type="service"
            )

        msg = "no service_id in job or service_name and service_version in params"
        raise AnsibleError(msg)

    if terms[0] == "cluster":
        if "cluster" not in variables:
            raise AnsibleError("there is no cluster in hostvars")
        cluster = variables["cluster"]
        return Cluster.obj.get(id=cluster["id"])

    if terms[0] == "provider":
        if "provider" not in variables:
            raise AnsibleError("there is no host provider in hostvars")
        provider = variables["provider"]
        return Provider.obj.get(id=provider["id"])

    if terms[0] == "host":
        if "adcm_hostid" not in variables:
            raise AnsibleError("there is no adcm_hostid in hostvars")
        return Host.obj.get(id=variables["adcm_hostid"])

    raise AnsibleError(f"unknown object type: {terms[0]}")


def update_config(obj: ADCM | CoreObject, conf: dict, job_id: int) -> PluginResult:
    config_log = ConfigLog.objects.get(id=obj.config.current)

    new_config = deepcopy(config_log.config)
    new_attr = deepcopy(config_log.attr) if config_log.attr is not None else {}

    changed = False

    for keys, value in conf.items():
        keys_list = keys.split("/")
        key = keys_list[0]
        subkey = None
        if len(keys_list) > 1:
            subkey = keys_list[1]

        if subkey:
            try:
                prototype_conf = PrototypeConfig.objects.get(
                    name=key, subname=subkey, prototype=obj.prototype, action=None
                )
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}/{subkey}' does not exist") from error

            cast_value = cast_to_type(field_type=prototype_conf.type, value=value, limits=prototype_conf.limits)
            if new_config[key][subkey] != cast_value:
                new_config[key][subkey] = cast_value
                changed = True
        else:
            try:
                prototype_conf = PrototypeConfig.objects.get(name=key, subname="", prototype=obj.prototype, action=None)
            except PrototypeConfig.DoesNotExist as error:
                raise AnsibleError(f"Config parameter '{key}' does not exist") from error

            cast_value = cast_to_type(field_type=prototype_conf.type, value=value, limits=prototype_conf.limits)
            if new_config[key] != cast_value:
                new_config[key] = cast_value
                changed = True

    if not changed:
        return PluginResult(conf, False)

    # adcm_config lookup need refactor. For this use `apply_config_changes` function

    set_object_config_with_plugin(
        job_id=job_id, obj=obj, config=new_config, attr=new_attr, description="ansible update"
    )

    if len(conf) == 1:
        return PluginResult(next(iter(conf.values())), True)

    return PluginResult(conf, True)


def set_cluster_config(job_id: int, cluster_id: int, config: dict) -> PluginResult:
    obj = Cluster.obj.get(id=cluster_id)

    return update_config(obj=obj, conf=config, job_id=job_id)


def set_host_config(job_id: int, host_id: int, config: dict) -> PluginResult:
    obj = Host.obj.get(id=host_id)

    return update_config(obj=obj, conf=config, job_id=job_id)


def set_provider_config(job_id: int, provider_id: int, config: dict) -> PluginResult:
    obj = Provider.obj.get(id=provider_id)

    return update_config(obj=obj, conf=config, job_id=job_id)


def set_service_config_by_name(job_id: int, cluster_id: int, service_name: str, config: dict) -> PluginResult:
    obj = get_service_by_name(cluster_id, service_name)

    return update_config(obj=obj, conf=config, job_id=job_id)


def set_service_config(job_id: int, cluster_id: int, service_id: int, config: dict) -> PluginResult:
    obj = Service.obj.get(id=service_id, cluster__id=cluster_id, prototype__type="service")

    return update_config(obj=obj, conf=config, job_id=job_id)


# Everything below is reachable only from this legacy lookup plugin. It used to live in
# `cm.legacy.adcm_config.config` and `cm.legacy.api`, but nothing besides this plugin called it.


def proto_ref(prototype: Prototype) -> str:
    return f'{prototype.type} "{prototype.name}" {prototype.version}'


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
        for conf_key, conf_value in value.items():  # pyright: ignore [reportOptionalMemberAccess, reportAttributeAccessIssue]
            new_value[conf_key] = ansible_encrypt_and_format(msg=conf_value)

        value = new_value

    return value


def get_option_value(value: str, limits: dict) -> str | int | float:
    if value in limits["option"].values():
        return value
    elif re.match(r"^\d+$", value):
        return int(value)
    elif re.match(r"^\d+\.\d+$", value):
        return float(value)

    return raise_adcm_ex("CONFIG_OPTION_ERROR")


@contextmanager
def reraise_file_errors_as_adcm_ex(filepath: Path | str, reference: str):
    try:
        yield
    except FileNotFoundError as err:
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=f'"{filepath}" is not found ({reference})') from err
    except PermissionError as err:
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=f'"{filepath}" can not be open ({reference})') from err


def __get_prototype_config(prototype: Prototype, action: Action | None = None) -> tuple[dict, dict, dict, dict]:
    prototype_configs = PrototypeConfig.objects.filter(prototype=prototype, action=action).order_by("id")

    return __get_spec_flat_spec_config_attr_from_prototype_configs(
        prototype=prototype, prototype_configs=prototype_configs
    )


def __get_spec_flat_spec_config_attr_from_prototype_configs(
    prototype: Prototype,
    prototype_configs: Collection[PrototypeConfig],
) -> tuple[dict, dict, dict, dict]:
    spec = {}
    flat_spec = OrderedDict()
    config = {}
    attr = {}
    flist = ("default", "required", "type", "limits")
    prototype_configs = tuple(prototype_configs)

    group_prototype_configs = (proto_conf for proto_conf in prototype_configs if proto_conf.type == "group")
    for conf in group_prototype_configs:
        spec[conf.name] = {}
        config[conf.name] = {}
        if "activatable" in conf.limits:
            attr[conf.name] = {"active": conf.limits["active"]}

    path_resolver = (
        ADCMBundlePathResolver() if prototype.type == "adcm" else BundlePathResolver(bundle_hash=prototype.bundle.hash)
    )

    for conf in prototype_configs:
        flat_spec[f"{conf.name}/{conf.subname}"] = conf
        if conf.subname == "":
            if conf.type != "group":
                spec[conf.name] = obj_to_dict(conf, flist)
                config[conf.name] = get_default(conf, path_resolver=path_resolver)
                spec[conf.name]["full_display_name"] = _build_full_display_name(flat_spec=flat_spec, key=conf.name)
        else:
            spec[conf.name][conf.subname] = obj_to_dict(conf, flist)
            config[conf.name][conf.subname] = get_default(conf, path_resolver=path_resolver)
            spec[conf.name][conf.subname]["full_display_name"] = _build_full_display_name(
                flat_spec=flat_spec, key=conf.name, subkey=conf.subname
            )

    return spec, flat_spec, config, attr


def get_full_display_name_from_spec(
    spec: dict, flat_spec: dict[str, PrototypeConfig], key: str, subkey: str = ""
) -> str:
    spec_param = spec[key][subkey] if subkey else spec[key]
    full_display_name = spec_param.get("full_display_name")
    if full_display_name is not None:
        return full_display_name

    if not subkey:
        key_name = f"{key}/"
        if flat_spec[key_name].type == "group":
            return _get_display_name_from_config(config=flat_spec.get(key_name), default_name=key)

    return _build_full_display_name(flat_spec=flat_spec, key=key, subkey=subkey)


def _get_display_name_from_config(config: PrototypeConfig | None, default_name: str) -> str:
    if config is None:
        return default_name

    return config.display_name or default_name


def _build_full_display_name(flat_spec: dict[str, PrototypeConfig], key: str, subkey: str = "") -> str:
    key_spec_name = f"{key}/"
    if not subkey:
        config = flat_spec.get(key_spec_name)
        return _get_display_name_from_config(config=config, default_name=key)

    subkey_spec_name = f"{key}/{subkey}"
    group_displ_name = _get_display_name_from_config(config=flat_spec.get(key_spec_name), default_name=key)
    field_displ_name = _get_display_name_from_config(config=flat_spec.get(subkey_spec_name), default_name=subkey)
    group_display_name_levels = tuple(group_displ_name.split("/"))
    field_display_name_levels = tuple(field_displ_name.split("/"))
    if field_display_name_levels[: len(group_display_name_levels)] == group_display_name_levels:
        return field_displ_name

    return f"{group_displ_name}/{field_displ_name}"


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


def __merge_config_of_group_with_primary_config(
    group: ConfigHostGroup,
    primary_config: ConfigLog,
    current_config_of_group: ConfigLog,
    description: str,
) -> ConfigLog:
    spec = group.get_config_spec()
    current_group_keys = current_config_of_group.attr["group_keys"]

    config = _merge_config_field(
        origin_config_fields=deepcopy(primary_config.config),
        host_group_fields=current_config_of_group.config,
        group_keys=current_group_keys,
        spec=spec,
    )
    attr = _merge_attr_field(
        origin_attr_fields=deepcopy(primary_config.attr),
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


def __update_host_groups_by_primary_object(
    object_: Cluster | Service | Component | Provider, config: ConfigLog
) -> None:
    for host_group in object_.config_host_group.order_by("id"):
        current_config_of_host_group = ConfigLog.objects.get(id=host_group.config.current)

        config_log = __merge_config_of_group_with_primary_config(
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


def save_object_config(object_config: ObjectConfig, config: dict, attr: dict, description: str = "") -> ConfigLog:
    config_log = ConfigLog(obj_ref=object_config, config=config, attr=attr, description=description)
    obj = object_config.object

    if isinstance(obj, ConfigHostGroup):
        raise TypeError("Unexpected call, this branch is set for removal")

    if isinstance(obj, Cluster | Service | Component | Provider):
        config_log.save()
        __update_host_groups_by_primary_object(object_=obj, config=config_log)
    else:
        config_log.save()

    object_config.previous = object_config.current
    object_config.current = config_log.id
    object_config.save(update_fields=["previous", "current"])

    return config_log


def __save_file_type(obj, key, subkey, value):
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


def process_json_config(
    prototype: Prototype,
    obj: ADCMEntity | Action,
    new_config: dict,
    new_attr: dict | None = None,
    current_attr: dict | None = None,
) -> dict:
    spec, flat_spec, _, _ = __get_prototype_config(prototype=prototype)
    check_attr(prototype, obj, new_attr, flat_spec, current_attr)
    group = None

    if isinstance(obj, ConfigHostGroup):
        group = obj
        obj = group.object

    process_variant(obj, spec, new_config)
    __check_config_spec(proto=prototype, obj=obj, spec=spec, flat_spec=flat_spec, conf=new_config, attr=new_attr)
    return __process_config_spec(obj=group or obj, spec=spec, new_config=new_config)


def __check_config_spec(
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
        key_display_name = get_full_display_name_from_spec(spec=spec, flat_spec=flat_spec, key=key)

        if spec[key].get("type", "group") != "group":
            if key not in conf:
                if key_is_required(obj=obj, key=key, subkey="", spec=spec):
                    raise AdcmEx(
                        code="CONFIG_KEY_ERROR",
                        msg=f'There is no required key "{key_display_name}" in input config ({ref})',
                    )

                continue

            config_value = conf[key]
            if isinstance(config_value, dict) and spec[key]["type"] not in settings.STACK_COMPLEX_FIELD_TYPES:
                raise AdcmEx(
                    code="CONFIG_KEY_ERROR",
                    msg=f'Key "{key_display_name}" in input config should not have any subkeys ({ref})',
                )

            check_config_type(prototype=proto, key=key, subkey="", spec=spec[key], value=config_value)

            continue

        # Processing group
        if key not in conf:
            if sub_key_is_required(key=key, attr=attr, flat_spec=flat_spec, spec=spec, obj=obj):
                raise AdcmEx(
                    code="CONFIG_KEY_ERROR", msg=f'There is no required key "{key_display_name}" in input config'
                )

            continue

        config_value = conf[key]
        if not isinstance(config_value, dict):
            raise AdcmEx(code="CONFIG_KEY_ERROR", msg=f'There are not any subkeys for key "{key_display_name}" ({ref})')

        if not config_value:
            raise AdcmEx(
                code="CONFIG_KEY_ERROR",
                msg=f'Key "{key_display_name}" should contain subkeys ({ref}): {list(spec[key].keys())}',
            )

        for subkey in config_value:
            if subkey not in spec[key]:
                raise AdcmEx(
                    code="CONFIG_KEY_ERROR",
                    msg=f'There is unknown subkey "{subkey}" for key "{key_display_name}" in input config ({ref})',
                )

        for subkey in spec[key]:
            if subkey not in config_value:
                if key_is_required(obj=obj, key=key, subkey=subkey, spec=spec):
                    subkey_name = _get_display_name_from_config(
                        config=flat_spec.get(f"{key}/{subkey}"), default_name=subkey
                    )
                    raise AdcmEx(
                        code="CONFIG_KEY_ERROR",
                        msg=f'There is no required subkey "{subkey_name}" for key "{key_display_name}" ({ref})',
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


def _process_secretfile(obj: ADCMEntity | ProcessStep, key: str, subkey: str, value: Any) -> None:
    if value is not None and value.startswith(settings.ANSIBLE_VAULT_HEADER):
        try:
            value = ansible_decrypt(msg=value)
        except AnsibleError as e:
            raise AdcmEx(code="CONFIG_VALUE_ERROR", msg="Can't decrypt value") from e

    __save_file_type(obj=obj, key=key, subkey=subkey, value=value)


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


def __process_config_spec(obj: ADCMEntity | TaskLog | ProcessStep, spec: dict, new_config: dict) -> dict:
    for cfg_key, cfg_value in new_config.items():
        spec_type = spec[cfg_key].get("type")

        if spec_type == "file":
            __save_file_type(obj=obj, key=cfg_key, subkey="", value=cfg_value)

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
                    __save_file_type(obj=obj, key=cfg_key, subkey=sub_cfg_key, value=sub_cfg_value)

                elif sub_spec_type == "secretfile":
                    _process_secretfile(obj=obj, key=cfg_key, subkey=sub_cfg_key, value=sub_cfg_value)
                    _process_secret_param(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

                elif sub_spec_type in {"password", "secrettext"}:
                    _process_secret_param(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

                elif sub_spec_type == "secretmap":
                    _process_secretmap(conf=new_config, key=cfg_key, subkey=sub_cfg_key)

    return new_config


def cast_to_type(field_type: str, value: Any, limits: dict) -> Any:
    match field_type:
        case "float":
            return float(value)
        case "integer":
            return int(value)
        case "option":
            return get_option_value(value=value, limits=limits)
        case _:
            return value


def set_object_config_with_plugin(
    job_id: int, obj: ADCM | CoreObject, config: dict, attr: dict, description: str
) -> None:
    old_config_log_id = obj.config.current
    new_conf = process_json_config(prototype=obj.prototype, obj=obj, new_config=config, new_attr=attr)

    with atomic():
        config_log = save_object_config(object_config=obj.config, config=new_conf, attr=attr, description=description)
        apply_policy_for_new_config(config_object=obj, config_log=config_log)

    core_object = orm_object_to_core_descriptor(object_=obj)
    update_related_configs(
        job_id=job_id,
        object_=core_object,
        object_prototype_id=obj.prototype_id,
        old_config_id=old_config_log_id,
        new_config_id=config_log.id,
    )
    send_config_creation_event(
        object_id=obj.id, object_type=obj.prototype.type, changes={"createdBy": config_log.created_by}
    )


# Moved from `cm.legacy.adcm_config.checks` and `cm.legacy.adcm_config.utils` for the same reason
# as the block above: nothing outside this legacy lookup plugin called any of it.


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


def cook_file_type_name(obj: ADCMEntity | ConfigHostGroup | ProcessStep, *keys: str) -> str:
    if isinstance(obj, ADCMEntity):
        filename = [obj.prototype.type, str(obj.id), *keys]
    elif isinstance(obj, ConfigHostGroup):
        filename = [obj.object.prototype.type, str(obj.object.id), "group", str(obj.id), *keys]
    elif isinstance(obj, ProcessStep):
        filename = ["process", str(obj.process_id), "step", str(obj.id), *keys]
    else:
        filename = ["task", str(obj.id), *keys]

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
