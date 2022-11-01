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
# pylint: disable=line-too-long,too-many-statements

import hashlib
import json
import os
import re
import warnings
from copy import deepcopy
from typing import Any

import ruyaml
import yaml
import yspec.checker
from django.conf import settings
from django.db import IntegrityError
from rest_framework import status
from version_utils import rpm

import cm.checker
from cm.adcm_config import (
    check_config_type,
    proto_ref,
    read_bundle_file,
    type_is_complex,
)
from cm.errors import raise_adcm_ex as err
from cm.logger import logger
from cm.models import (
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
)

NAME_REGEX = r"[0-9a-zA-Z_\.-]+"


def save_definition(path, fname, conf, obj_list, bundle_hash, adcm_=False):
    if isinstance(conf, dict):
        save_object_definition(path, fname, conf, obj_list, bundle_hash, adcm_)
    else:
        for obj_def in conf:
            save_object_definition(path, fname, obj_def, obj_list, bundle_hash, adcm_)


def cook_obj_id(conf):
    return f"{conf['type']}.{conf['name']}.{conf['version']}"


def save_object_definition(path, fname, conf, obj_list, bundle_hash, adcm_=False):
    def_type = conf["type"]
    if def_type == "adcm" and not adcm_:
        msg = "Invalid type \"{}\" in object definition: {}"
        return err("INVALID_OBJECT_DEFINITION", msg.format(def_type, fname))
    check_object_definition(fname, conf, def_type, obj_list)
    obj = save_prototype(path, conf, def_type, bundle_hash)
    logger.info("Save definition of %s \"%s\" %s to stage", def_type, conf["name"], conf["version"])
    obj_list[cook_obj_id(conf)] = fname
    return obj


def check_object_definition(fname, conf, def_type, obj_list):
    ref = f"{def_type} \"{conf['name']}\" {conf['version']}"
    if cook_obj_id(conf) in obj_list:
        err("INVALID_OBJECT_DEFINITION", f"Duplicate definition of {ref} (file {fname})")


def get_config_files(path, bundle_hash):
    conf_list = []
    conf_types = [
        ("config.yaml", "yaml"),
        ("config.yml", "yaml"),
    ]
    if not os.path.isdir(path):
        err("STACK_LOAD_ERROR", f"no directory: {path}", status.HTTP_404_NOT_FOUND)
    for root, _, files in os.walk(path):
        for conf_file, conf_type in conf_types:
            if conf_file in files:
                dirs = root.split("/")
                start_index = dirs.index(bundle_hash) + 1
                path = os.path.join("", *dirs[start_index:])
                conf_list.append((path, root + "/" + conf_file, conf_type))
                break
    if not conf_list:
        err("STACK_LOAD_ERROR", f"no config files in stack directory \"{path}\"")
    return conf_list


def check_adcm_config(conf_file):
    warnings.simplefilter("error", ruyaml.error.ReusedAnchorWarning)
    schema_file = settings.CODE_DIR / "cm" / "adcm_schema.yaml"
    with open(schema_file, encoding=settings.ENCODING_UTF_8) as fd:
        rules = ruyaml.round_trip_load(fd)
    try:
        with open(conf_file, encoding=settings.ENCODING_UTF_8) as fd:
            data = cm.checker.round_trip_load(fd, version="1.1", allow_duplicate_keys=True)
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        err("STACK_LOAD_ERROR", f"YAML decode \"{conf_file}\" error: {e}")
    except ruyaml.error.ReusedAnchorWarning as e:
        err("STACK_LOAD_ERROR", f"YAML decode \"{conf_file}\" error: {e}")
    except ruyaml.constructor.DuplicateKeyError as e:
        msg = f"{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}"
        err("STACK_LOAD_ERROR", f"Duplicate Keys error: {msg}")
    except ruyaml.composer.ComposerError as e:
        err("STACK_LOAD_ERROR", f"YAML Composer error: {e}")
    try:
        cm.checker.check(data, rules)
        return data
    except cm.checker.FormatError as e:
        args = ""
        if e.errors:
            for ee in e.errors:
                if "Input data for" in ee.message:
                    continue
                args += f"line {ee.line}: {ee}\n"
        err("INVALID_OBJECT_DEFINITION", f"\"{conf_file}\" line {e.line} error: {e}", args)
        return {}


def read_definition(conf_file, conf_type):
    if os.path.isfile(conf_file):
        conf = check_adcm_config(conf_file)
        logger.info("Read config file: \"%s\"", conf_file)
        return conf
    logger.warning("Can not open config file: \"%s\"", conf_file)
    return {}


def get_license_hash(proto, conf, bundle_hash):
    if "license" not in conf:
        return None
    body = read_bundle_file(proto, conf["license"], bundle_hash, "license file")
    sha1 = hashlib.sha256()
    sha1.update(body.encode(settings.ENCODING_UTF_8))
    return sha1.hexdigest()


def process_config_group_customization(actual_config: dict, obj: StagePrototype):
    if not actual_config:
        return
    if "config_group_customization" not in actual_config:
        sp = None
        if obj.type == "service":
            try:
                sp = StagePrototype.objects.get(type="cluster")
            except StagePrototype.DoesNotExist:
                logger.debug("Can't find cluster for service %s", obj)
        if obj.type == "component":
            sp = obj.parent
        if sp:
            actual_config["config_group_customization"] = sp.config_group_customization


def save_prototype(path, conf, def_type, bundle_hash):
    # validate_name(type_name, '{} type name "{}"'.format(def_type, conf['name']))
    proto = StagePrototype(name=conf["name"], type=def_type, path=path, version=conf["version"])
    dict_to_obj(conf, "required", proto)
    dict_to_obj(conf, "shared", proto)
    dict_to_obj(conf, "monitoring", proto)
    dict_to_obj(conf, "display_name", proto)
    dict_to_obj(conf, "description", proto)
    dict_to_obj(conf, "adcm_min_version", proto)
    dict_to_obj(conf, "venv", proto)
    dict_to_obj(conf, "edition", proto)
    process_config_group_customization(conf, proto)
    dict_to_obj(conf, "config_group_customization", proto)
    dict_to_obj(conf, "allow_maintenance_mode", proto)
    fix_display_name(conf, proto)
    license_hash = get_license_hash(proto, conf, bundle_hash)
    if license_hash:
        proto.license_path = conf["license"]
        proto.license_hash = license_hash
    proto.save()
    save_actions(proto, conf, bundle_hash)
    save_upgrade(proto, conf, bundle_hash)
    save_components(proto, conf, bundle_hash)
    save_prototype_config(proto, conf, bundle_hash)
    save_export(proto, conf)
    save_import(proto, conf)
    return proto


def check_component_constraint(proto, name, conf):
    if not conf:
        return
    if "constraint" not in conf:
        return
    if len(conf["constraint"]) > 2:
        msg = "constraint of component \"{}\" in {} should have only 1 or 2 elements"
        err("INVALID_COMPONENT_DEFINITION", msg.format(name, proto_ref(proto)))


def save_components(proto, conf, bundle_hash):
    ref = proto_ref(proto)
    if not in_dict(conf, "components"):
        return
    for comp_name in conf["components"]:
        cc = conf["components"][comp_name]
        validate_name(comp_name, f"Component name \"{comp_name}\" of {ref}")
        component = StagePrototype(
            type="component",
            parent=proto,
            path=proto.path,
            name=comp_name,
            version=proto.version,
            adcm_min_version=proto.adcm_min_version,
        )
        dict_to_obj(cc, "description", component)
        dict_to_obj(cc, "display_name", component)
        dict_to_obj(cc, "monitoring", component)
        fix_display_name(cc, component)
        check_component_constraint(proto, comp_name, cc)
        dict_to_obj(cc, "params", component)
        dict_to_obj(cc, "constraint", component)
        dict_to_obj(cc, "requires", component)
        dict_to_obj(cc, "venv", component)
        dict_to_obj(cc, "bound_to", component)
        process_config_group_customization(cc, component)
        dict_to_obj(cc, "config_group_customization", component)
        component.save()
        save_actions(component, cc, bundle_hash)
        save_prototype_config(component, cc, bundle_hash)


def check_upgrade(proto, conf):
    label = f"upgrade \"{conf['name']}\""
    check_versions(proto, conf, label)
    check_upgrade_scripts(proto, conf, label)


def check_upgrade_scripts(proto, conf, label):
    ref = proto_ref(proto)
    count = 0
    if "scripts" in conf:
        for action in conf["scripts"]:
            if action["script_type"] == "internal":
                count += 1
                if count > 1:
                    msg = "Script with script_type \"internal\" must be unique in {} of {}"
                    err("INVALID_UPGRADE_DEFINITION", msg.format(label, ref))
                if action["script"] != "bundle_switch":
                    msg = "Script with script_type \"internal\" should be marked as \"bundle_switch\" in {} of {}"
                    err("INVALID_UPGRADE_DEFINITION", msg.format(label, ref))
        if count == 0:
            msg = "Scripts block in {} of {} must contain exact one block with script \"bundle_switch\""
            err("INVALID_UPGRADE_DEFINITION", msg.format(label, ref))
    else:
        if "masking" in conf or "on_success" in conf or "on_fail" in conf:
            msg = "{} of {} couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block"
            err("INVALID_UPGRADE_DEFINITION", msg.format(label, ref))


def check_versions(proto, conf, label):
    ref = proto_ref(proto)
    msg = "{} has no mandatory \"versions\" key ({})"
    if "min" in conf["versions"] and "min_strict" in conf["versions"]:
        msg = "min and min_strict can not be used simultaneously in versions of {} ({})"
        err("INVALID_VERSION_DEFINITION", msg.format(label, ref))
    if (
        "min" not in conf["versions"]
        and "min_strict" not in conf["versions"]
        and "import" not in label
    ):
        msg = "min or min_strict should be present in versions of {} ({})"
        err("INVALID_VERSION_DEFINITION", msg.format(label, ref))
    if "max" in conf["versions"] and "max_strict" in conf["versions"]:
        msg = "max and max_strict can not be used simultaneously in versions of {} ({})"
        err("INVALID_VERSION_DEFINITION", msg.format(label, ref))
    if (
        "max" not in conf["versions"]
        and "max_strict" not in conf["versions"]
        and "import" not in label
    ):
        msg = "max and max_strict should be present in versions of {} ({})"
        err("INVALID_VERSION_DEFINITION", msg.format(label, ref))
    for name in ("min", "min_strict", "max", "max_strict"):
        if name in conf["versions"] and not conf["versions"][name]:
            msg = "{} versions of {} should be not null ({})"
            err("INVALID_VERSION_DEFINITION", msg.format(name, label, ref))


def set_version(obj, conf):
    if "min" in conf["versions"]:
        obj.min_version = conf["versions"]["min"]
        obj.min_strict = False
    elif "min_strict" in conf["versions"]:
        obj.min_version = conf["versions"]["min_strict"]
        obj.min_strict = True

    if "max" in conf["versions"]:
        obj.max_version = conf["versions"]["max"]
        obj.max_strict = False
    elif "max_strict" in conf["versions"]:
        obj.max_version = conf["versions"]["max_strict"]
        obj.max_strict = True


def save_upgrade(proto, conf, bundle_hash):
    if not in_dict(conf, "upgrade"):
        return
    for item in conf["upgrade"]:
        check_upgrade(proto, item)
        upg = StageUpgrade(name=item["name"])
        set_version(upg, item)
        dict_to_obj(item, "description", upg)
        if "states" in item:
            dict_to_obj(item["states"], "available", upg)
            if "available" in item["states"]:
                upg.state_available = item["states"]["available"]
            if "on_success" in item["states"]:
                upg.state_on_success = item["states"]["on_success"]
        if in_dict(item, "from_edition"):
            upg.from_edition = item["from_edition"]
        if "scripts" in item:
            upg.action = save_actions(proto, item, bundle_hash, upg)
        upg.save()


def save_export(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, "export"):
        return
    if isinstance(conf["export"], str):
        export = [conf["export"]]
    elif isinstance(conf["export"], list):
        export = conf["export"]
    msg = "{} does not has \"{}\" config group"
    for key in export:
        if not StagePrototypeConfig.objects.filter(prototype=proto, name=key):
            err("INVALID_OBJECT_DEFINITION", msg.format(ref, key))
        se = StagePrototypeExport(prototype=proto, name=key)
        se.save()


def get_config_groups(proto, action=None):
    groups = {}
    for c in StagePrototypeConfig.objects.filter(prototype=proto, action=action):
        if c.subname != "":
            groups[c.name] = c.name
    return groups


def check_default_import(proto, conf):
    ref = proto_ref(proto)
    if "default" not in conf:
        return
    groups = get_config_groups(proto)
    for key in conf["default"]:
        if key not in groups:
            msg = "No import default group \"{}\" in config ({})"
            err("INVALID_OBJECT_DEFINITION", msg.format(key, ref))


def save_import(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, "import"):
        return
    for key in conf["import"]:
        if "default" in conf["import"][key] and "required" in conf["import"][key]:
            msg = "Import can't have default and be required in the same time ({})"
            err("INVALID_OBJECT_DEFINITION", msg.format(ref))
        check_default_import(proto, conf["import"][key])
        si = StagePrototypeImport(prototype=proto, name=key)
        if "versions" in conf["import"][key]:
            check_versions(proto, conf["import"][key], f"import \"{key}\"")
            set_version(si, conf["import"][key])
            if si.min_version and si.max_version:
                if rpm.compare_versions(str(si.min_version), str(si.max_version)) > 0:
                    msg = "Min version should be less or equal max version"
                    err("INVALID_VERSION_DEFINITION", msg)
        dict_to_obj(conf["import"][key], "required", si)
        dict_to_obj(conf["import"][key], "multibind", si)
        dict_to_obj(conf["import"][key], "default", si)
        si.save()


def check_action_hc(proto, conf, name):
    if "hc_acl" not in conf:
        return
    for idx, item in enumerate(conf["hc_acl"]):
        if "service" not in item:
            if proto.type == "service":
                item["service"] = proto.name
                conf["hc_acl"][idx]["service"] = proto.name


def save_sub_actions(conf, action):
    if action.type != "task":
        return
    for sub in conf["scripts"]:
        sub_action = StageSubAction(
            action=action, script=sub["script"], script_type=sub["script_type"], name=sub["name"]
        )
        sub_action.display_name = sub["name"]
        if "display_name" in sub:
            sub_action.display_name = sub["display_name"]
        dict_to_obj(sub, "params", sub_action)
        on_fail = sub.get(ON_FAIL, "")
        if isinstance(on_fail, str):
            sub_action.state_on_fail = on_fail
            sub_action.multi_state_on_fail_set = []
            sub_action.multi_state_on_fail_unset = []
        elif isinstance(on_fail, dict):
            sub_action.state_on_fail = _deep_get(on_fail, STATE, default="")
            sub_action.multi_state_on_fail_set = _deep_get(on_fail, MULTI_STATE, SET, default=[])
            sub_action.multi_state_on_fail_unset = _deep_get(
                on_fail, MULTI_STATE, UNSET, default=[]
            )
        sub_action.save()


MASKING = "masking"
STATES = "states"
STATE = "state"
MULTI_STATE = "multi_state"
AVAILABLE = "available"
UNAVAILABLE = "unavailable"
ON_SUCCESS = "on_success"
ON_FAIL = "on_fail"
ANY = "any"
SET = "set"
UNSET = "unset"


def save_actions(proto, conf, bundle_hash, upgrade: StageUpgrade | None = None):
    if in_dict(conf, "versions"):
        conf["type"] = "task"
        upgrade_name = conf["name"]
        conf["display_name"] = f"Upgrade: {upgrade_name}"
        if upgrade is not None:
            action_name = (
                f"{proto.name}_{proto.version}_{proto.edition}_upgrade_{upgrade_name}_{upgrade.min_version}_strict_"
                f"{upgrade.min_strict}-{upgrade.max_version}_strict_{upgrade.min_strict}_editions-"
                f"{'_'.join(upgrade.from_edition)}_state_available-{'_'.join(upgrade.state_available)}_"
                f"state_on_success-{upgrade.state_on_success}"
            )
        else:
            action_name = f"{proto.name}_{proto.version}_{proto.edition}_upgrade_{upgrade_name}"
        action_name = re.sub(r"\s+", "_", action_name).strip().lower()
        action_name = re.sub(r"\(|\)", "", action_name)
        upgrade_action = save_action(proto, conf, bundle_hash, action_name)
        return upgrade_action
    if not in_dict(conf, "actions"):
        return None
    for action_name in sorted(conf["actions"]):
        ac = conf["actions"][action_name]
        save_action(proto, ac, bundle_hash, action_name)
    return None


def save_action(proto, ac, bundle_hash, action_name):
    check_action(proto, action_name)
    action = StageAction(prototype=proto, name=action_name)
    action.type = ac["type"]
    if ac["type"] == "job":
        action.script = ac["script"]
        action.script_type = ac["script_type"]
    dict_to_obj(ac, "button", action)
    dict_to_obj(ac, "display_name", action)
    dict_to_obj(ac, "description", action)
    dict_to_obj(ac, "allow_to_terminate", action)
    dict_to_obj(ac, "partial_execution", action)
    dict_to_obj(ac, "host_action", action)
    dict_to_obj(ac, "ui_options", action)
    dict_to_obj(ac, "params", action)
    dict_to_obj(ac, "log_files", action)
    dict_to_obj(ac, "venv", action)
    dict_to_obj(ac, "allow_in_maintenance_mode", action)
    fix_display_name(ac, action)
    check_action_hc(proto, ac, action_name)
    dict_to_obj(ac, "hc_acl", action, "hostcomponentmap")
    if MASKING in ac:
        if STATES in ac:
            err(
                "INVALID_OBJECT_DEFINITION",
                f"Action {action_name} uses both mutual excluding states \"states\" and \"masking\"",
            )

        action.state_available = _deep_get(ac, MASKING, STATE, AVAILABLE, default=ANY)
        action.state_unavailable = _deep_get(ac, MASKING, STATE, UNAVAILABLE, default=[])
        action.state_on_success = _deep_get(ac, ON_SUCCESS, STATE, default="")
        action.state_on_fail = _deep_get(ac, ON_FAIL, STATE, default="")

        action.multi_state_available = _deep_get(ac, MASKING, MULTI_STATE, AVAILABLE, default=ANY)
        action.multi_state_unavailable = _deep_get(
            ac, MASKING, MULTI_STATE, UNAVAILABLE, default=[]
        )
        action.multi_state_on_success_set = _deep_get(ac, ON_SUCCESS, MULTI_STATE, SET, default=[])
        action.multi_state_on_success_unset = _deep_get(
            ac, ON_SUCCESS, MULTI_STATE, UNSET, default=[]
        )
        action.multi_state_on_fail_set = _deep_get(ac, ON_FAIL, MULTI_STATE, SET, default=[])
        action.multi_state_on_fail_unset = _deep_get(ac, ON_FAIL, MULTI_STATE, UNSET, default=[])
    else:
        if ON_SUCCESS in ac or ON_FAIL in ac:
            err(
                "INVALID_OBJECT_DEFINITION",
                f"Action {action_name} uses \"on_success/on_fail\" states without \"masking\"",
            )

        action.state_available = _deep_get(ac, STATES, AVAILABLE, default=[])
        action.state_unavailable = []
        action.state_on_success = _deep_get(ac, STATES, ON_SUCCESS, default="")
        action.state_on_fail = _deep_get(ac, STATES, ON_FAIL, default="")

        action.multi_state_available = ANY
        action.multi_state_unavailable = []
        action.multi_state_on_success_set = []
        action.multi_state_on_success_unset = []
        action.multi_state_on_fail_set = []
        action.multi_state_on_fail_unset = []
    action.save()
    save_sub_actions(ac, action)
    save_prototype_config(proto, ac, bundle_hash, action)
    return action


def check_action(proto, action):
    err_msg = f"Action name \"{action}\" of {proto.type} \"{proto.name}\" {proto.version}"
    validate_name(action, err_msg)


def is_group(conf):
    if conf["type"] == "group":
        return True
    return False


def get_yspec(proto, ref, bundle_hash, conf, name, subname):
    msg = f"yspec file of config key \"{name}/{subname}\":"
    yspec_body = read_bundle_file(proto, conf["yspec"], bundle_hash, msg)
    try:
        schema = yaml.safe_load(yspec_body)
    except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
        msg = "yspec file of config key \"{}/{}\" yaml decode error: {}"
        err("CONFIG_TYPE_ERROR", msg.format(name, subname, e))
    ok, error = yspec.checker.check_rule(schema)
    if not ok:
        msg = "yspec file of config key \"{}/{}\" error: {}"
        err("CONFIG_TYPE_ERROR", msg.format(name, subname, error))
    return schema


def save_prototype_config(
    proto, proto_conf, bundle_hash, action=None
):  # pylint: disable=too-many-statements,too-many-locals
    if not in_dict(proto_conf, "config"):
        return
    conf_dict = proto_conf["config"]
    ref = proto_ref(proto)

    def check_variant(conf, name, subname):
        vtype = conf["source"]["type"]
        source = {"type": vtype, "args": None}
        if "strict" in conf["source"]:
            source["strict"] = conf["source"]["strict"]
        else:
            source["strict"] = True
        if vtype == "inline":
            source["value"] = conf["source"]["value"]
        elif vtype in ("config", "builtin"):
            source["name"] = conf["source"]["name"]
        if vtype == "builtin":
            if "args" in conf["source"]:
                source["args"] = conf["source"]["args"]
        return source

    def process_limits(conf, name, subname):
        opt = {}
        if conf["type"] == "option":
            opt = {"option": conf["option"]}
        elif conf["type"] == "variant":
            opt["source"] = check_variant(conf, name, subname)
        elif conf["type"] == "integer" or conf["type"] == "float":
            if "min" in conf:
                opt["min"] = conf["min"]
            if "max" in conf:
                opt["max"] = conf["max"]
        elif conf["type"] == "structure":
            opt["yspec"] = get_yspec(proto, ref, bundle_hash, conf, name, subname)
        elif is_group(conf):
            if "activatable" in conf:
                opt["activatable"] = conf["activatable"]
                opt["active"] = False
                if "active" in conf:
                    opt["active"] = conf["active"]

        if "read_only" in conf and "writable" in conf:
            key_ref = f"(config key \"{name}/{subname}\" of {ref})"
            msg = "can not have \"read_only\" and \"writable\" simultaneously {}"
            err("INVALID_CONFIG_DEFINITION", msg.format(key_ref))

        for label in ("read_only", "writable"):
            if label in conf:
                opt[label] = conf[label]

        return opt

    def cook_conf(obj, conf, name, subname):
        sc = StagePrototypeConfig(prototype=obj, action=action, name=name, type=conf["type"])
        dict_to_obj(conf, "description", sc)
        dict_to_obj(conf, "display_name", sc)
        dict_to_obj(conf, "required", sc)
        dict_to_obj(conf, "ui_options", sc)
        dict_to_obj(conf, "group_customization", sc)
        conf["limits"] = process_limits(conf, name, subname)
        dict_to_obj(conf, "limits", sc)
        if "display_name" not in conf:
            if subname:
                sc.display_name = subname
            else:
                sc.display_name = name
        if "default" in conf:
            check_config_type(proto, name, subname, conf, conf["default"], bundle_hash)
        if type_is_complex(conf["type"]):
            dict_json_to_obj(conf, "default", sc)
        else:
            dict_to_obj(conf, "default", sc)
        if subname:
            sc.subname = subname
        try:
            sc.save()
        except IntegrityError:
            msg = "Duplicate config on {} {}, action {}, with name {} and subname {}"
            err("INVALID_CONFIG_DEFINITION", msg.format(obj.type, obj, action, name, subname))

    if isinstance(conf_dict, dict):
        for (name, conf) in conf_dict.items():
            if "type" in conf:
                validate_name(name, f"Config key \"{name}\" of {ref}")
                cook_conf(proto, conf, name, "")
            else:
                validate_name(name, f"Config group \"{name}\" of {ref}")
                group_conf = {"type": "group", "required": False}
                cook_conf(proto, group_conf, name, "")
                for (subname, subconf) in conf.items():
                    err_msg = f"Config key \"{name}/{subname}\" of {ref}"
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)
    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            name = conf["name"]
            validate_name(name, f"Config key \"{name}\" of {ref}")
            cook_conf(proto, conf, name, "")
            if is_group(conf):
                for subconf in conf["subs"]:
                    subname = subconf["name"]
                    err_msg = f"Config key \"{name}/{subname}\" of {ref}"
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)


def validate_name(value, err_msg):
    if not isinstance(value, str):
        err("WRONG_NAME", f"{err_msg} should be string")
    p = re.compile(NAME_REGEX)
    msg1 = (
        "{} is incorrect. Only latin characters, digits,"
        " dots (.), dashes (-), and underscores (_) are allowed."
    )
    if p.fullmatch(value) is None:
        err("WRONG_NAME", msg1.format(err_msg))
    return value


def fix_display_name(conf, obj):
    if isinstance(conf, dict) and "display_name" in conf:
        return
    obj.display_name = obj.name


def in_dict(dictionary, key):
    if not isinstance(dictionary, dict):
        return False
    if key in dictionary:
        if dictionary[key] is None:
            return False
        else:
            return True
    else:
        return False


def dict_to_obj(dictionary, key, obj, obj_key=None):
    if not obj_key:
        obj_key = key
    if not isinstance(dictionary, dict):
        return
    if key in dictionary:
        if dictionary[key] is not None:
            setattr(obj, obj_key, dictionary[key])


def dict_json_to_obj(dictionary, key, obj, obj_key=""):
    if obj_key == "":
        obj_key = key
    if isinstance(dictionary, dict):
        if key in dictionary:
            setattr(obj, obj_key, json.dumps(dictionary[key]))


def _deep_get(deep_dict: dict, *nested_keys: str, default: Any) -> Any:
    """
    Safe dict.get() for deep-nested dictionaries
    dct[key1][key2][...] -> _deep_get(dct, key1, key2, ..., default_value)
    """
    val = deepcopy(deep_dict)
    for key in nested_keys:
        try:
            val = val[key]
        except (KeyError, TypeError):
            return default
    return val
