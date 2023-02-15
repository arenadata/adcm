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

import cm.checker
import ruyaml
import yaml
import yspec.checker
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
from django.conf import settings
from django.db import IntegrityError
from rest_framework import status
from version_utils import rpm

ANY = "any"
AVAILABLE = "available"
MASKING = "masking"
MULTI_STATE = "multi_state"
NAME_REGEX = r"[0-9a-zA-Z_\.-]+"
ON_FAIL = "on_fail"
ON_SUCCESS = "on_success"
SET = "set"
STATE = "state"
STATES = "states"
UNAVAILABLE = "unavailable"
UNSET = "unset"


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
        return err("INVALID_OBJECT_DEFINITION", f'Invalid type "{def_type}" in object definition: {fname}')

    check_object_definition(fname, conf, def_type, obj_list)
    obj = save_prototype(path, conf, def_type, bundle_hash)
    logger.info('Save definition of %s "%s" %s to stage', def_type, conf["name"], conf["version"])
    obj_list[cook_obj_id(conf)] = fname

    return obj


def check_object_definition(fname, conf, def_type, obj_list):
    ref = f"{def_type} \"{conf['name']}\" {conf['version']}"
    if cook_obj_id(conf) in obj_list:
        err("INVALID_OBJECT_DEFINITION", f"Duplicate definition of {ref} (file {fname})")

    for action_name, action_data in conf.get("actions", {}).items():
        if action_name in {
            settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME,
            settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
        }:
            if def_type != "cluster":
                err("INVALID_OBJECT_DEFINITION", f'Action named "{action_name}" can be started only in cluster context')

            if not action_data.get("host_action"):
                err(
                    "INVALID_OBJECT_DEFINITION",
                    f'Action named "{action_name}" should have "host_action: true" property',
                )

        if action_name in settings.ADCM_SERVICE_ACTION_NAMES_SET and set(action_data).intersection(
            settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET
        ):
            err(
                "INVALID_OBJECT_DEFINITION",
                f'Maintenance mode actions shouldn\'t have "{settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )


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
        err("STACK_LOAD_ERROR", f'no config files in stack directory "{path}"')
    return conf_list


def check_adcm_config(conf_file):
    warnings.simplefilter("error", ruyaml.error.ReusedAnchorWarning)
    schema_file = settings.CODE_DIR / "cm" / "adcm_schema.yaml"
    with open(schema_file, encoding=settings.ENCODING_UTF_8) as f:
        rules = ruyaml.round_trip_load(f)

    try:
        with open(conf_file, encoding=settings.ENCODING_UTF_8) as f:
            data = cm.checker.round_trip_load(f, version="1.1", allow_duplicate_keys=True)
    except (ruyaml.parser.ParserError, ruyaml.scanner.ScannerError, NotImplementedError) as e:
        err("STACK_LOAD_ERROR", f'YAML decode "{conf_file}" error: {e}')
    except ruyaml.error.ReusedAnchorWarning as e:
        err("STACK_LOAD_ERROR", f'YAML decode "{conf_file}" error: {e}')
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
            for error in e.errors:
                if "Input data for" in error.message:
                    continue
                args += f"line {error.line}: {error}\n"

        err("INVALID_OBJECT_DEFINITION", f'"{conf_file}" line {e.line} error: {e}', args)

        return {}


def read_definition(conf_file, conf_type):  # pylint: disable=unused-argument
    if os.path.isfile(conf_file):
        conf = check_adcm_config(conf_file)
        logger.info('Read config file: "%s"', conf_file)

        return conf

    logger.warning('Can not open config file: "%s"', conf_file)

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
        stage_prototype = None
        if obj.type == "service":
            try:
                stage_prototype = StagePrototype.objects.get(type="cluster")
            except StagePrototype.DoesNotExist:
                logger.debug("Can't find cluster for service %s", obj)

        if obj.type == "component":
            stage_prototype = obj.parent

        if stage_prototype:
            actual_config["config_group_customization"] = stage_prototype.config_group_customization


def save_prototype(path: str, config: dict, type_prototype: str, bundle_hash: str) -> StagePrototype:
    prototype = StagePrototype(name=config["name"], type=type_prototype, path=path, version=config["version"])

    dict_to_obj(config, "required", prototype)
    dict_to_obj(config, "shared", prototype)
    dict_to_obj(config, "monitoring", prototype)
    dict_to_obj(config, "display_name", prototype)
    dict_to_obj(config, "description", prototype)
    dict_to_obj(config, "adcm_min_version", prototype)
    dict_to_obj(config, "venv", prototype)
    dict_to_obj(config, "edition", prototype)

    process_config_group_customization(config, prototype)

    dict_to_obj(config, "config_group_customization", prototype)
    dict_to_obj(config, "allow_maintenance_mode", prototype)

    fix_display_name(config, prototype)

    license_hash = get_license_hash(prototype, config, bundle_hash)

    if license_hash:
        if type_prototype not in ["cluster", "service", "provider"]:
            err(
                code="INVALID_OBJECT_DEFINITION",
                msg=f"Invalid license definition in {proto_ref(prototype)}. License can be placed in cluster, service or provider",
            )

        prototype.license_path = config["license"]
        prototype.license_hash = license_hash

    prototype.save()

    save_actions(prototype=prototype, config=config, bundle_hash=bundle_hash)
    save_upgrade(prototype=prototype, config=config, bundle_hash=bundle_hash)
    save_components(prototype, config, bundle_hash)
    save_prototype_config(prototype, config, bundle_hash)
    save_export(prototype, config)
    save_import(prototype, config)

    return prototype


def check_component_constraint(proto, name, conf):
    if not conf:
        return
    if "constraint" not in conf:
        return
    if len(conf["constraint"]) > 2:
        msg = 'constraint of component "{}" in {} should have only 1 or 2 elements'
        err("INVALID_COMPONENT_DEFINITION", msg.format(name, proto_ref(proto)))


def save_components(proto, conf, bundle_hash):
    ref = proto_ref(proto)

    if not in_dict(conf, "components"):
        return

    for comp_name in conf["components"]:
        component_conf = conf["components"][comp_name]
        validate_name(comp_name, f'Component name "{comp_name}" of {ref}')
        component = StagePrototype(
            type="component",
            parent=proto,
            path=proto.path,
            name=comp_name,
            version=proto.version,
            adcm_min_version=proto.adcm_min_version,
        )
        dict_to_obj(component_conf, "description", component)
        dict_to_obj(component_conf, "display_name", component)
        dict_to_obj(component_conf, "monitoring", component)

        fix_display_name(component_conf, component)
        check_component_constraint(proto, comp_name, component_conf)

        dict_to_obj(component_conf, "params", component)
        dict_to_obj(component_conf, "constraint", component)
        dict_to_obj(component_conf, "requires", component)
        dict_to_obj(component_conf, "venv", component)
        dict_to_obj(component_conf, "bound_to", component)

        process_config_group_customization(component_conf, component)

        dict_to_obj(component_conf, "config_group_customization", component)

        component.save()

        save_actions(prototype=component, config=component_conf, bundle_hash=bundle_hash)
        save_prototype_config(component, component_conf, bundle_hash)


def check_upgrade(prototype: StagePrototype, config: dict) -> None:
    label = f'upgrade "{config["name"]}"'
    check_versions(prototype=prototype, config=config, label=label)
    check_upgrade_scripts(prototype=prototype, config=config, label=label)


def check_upgrade_scripts(prototype: StagePrototype, config: dict, label: str) -> None:
    ref = proto_ref(prototype=prototype)
    count = 0

    if "scripts" in config:
        for action in config["scripts"]:
            if action["script_type"] == "internal":
                count += 1

                if count > 1:
                    err(
                        code="INVALID_UPGRADE_DEFINITION",
                        msg=f'Script with script_type "internal" must be unique in {label} of {ref}',
                    )

                if action["script"] not in {"bundle_switch", "bundle_revert"}:
                    err(
                        code="INVALID_UPGRADE_DEFINITION",
                        msg=f'Script with script_type "internal" should be marked as "bundle_switch" or "bundle_revert" in {label} of {ref}',
                    )

        if count == 0:
            err(
                code="INVALID_UPGRADE_DEFINITION",
                msg=f'Scripts block in {label} of {ref} must contain exact one block with script "bundle_switch"',
            )

    else:
        if "masking" in config or "on_success" in config or "on_fail" in config:
            err(
                code="INVALID_UPGRADE_DEFINITION",
                msg=f"{label} of {ref} couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
            )


def check_versions(prototype: StagePrototype, config: str, label: str) -> None:
    ref = proto_ref(prototype=prototype)

    if "min" in config["versions"] and "min_strict" in config["versions"]:
        err(
            code="INVALID_VERSION_DEFINITION",
            msg=f"min and min_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if "min" not in config["versions"] and "min_strict" not in config["versions"] and "import" not in label:
        err(
            code="INVALID_VERSION_DEFINITION", msg=f"min or min_strict should be present in versions of {label} ({ref})"
        )

    if "max" in config["versions"] and "max_strict" in config["versions"]:
        err(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if "max" not in config["versions"] and "max_strict" not in config["versions"] and "import" not in label:
        err(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict should be present in versions of {label} ({ref})",
        )

    for name in ("min", "min_strict", "max", "max_strict"):
        if name in config["versions"] and not config["versions"][name]:
            err(code="INVALID_VERSION_DEFINITION", msg=f"{name} versions of {label} should be not null ({ref})")


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


def save_upgrade(prototype: StagePrototype, config: dict, bundle_hash: str) -> None:
    if not in_dict(config, "upgrade"):
        return

    for item in config["upgrade"]:
        check_upgrade(prototype=prototype, config=item)
        upgrade = StageUpgrade(name=item["name"])
        set_version(upgrade, item)
        dict_to_obj(item, "description", upgrade)

        if "states" in item:
            dict_to_obj(item["states"], "available", upgrade)

            if "available" in item["states"]:
                upgrade.state_available = item["states"]["available"]

            if "on_success" in item["states"]:
                upgrade.state_on_success = item["states"]["on_success"]

        if in_dict(item, "from_edition"):
            upgrade.from_edition = item["from_edition"]

        if "scripts" in item:
            upgrade.action = save_upgrade_action(
                prototype=prototype, config=item, bundle_hash=bundle_hash, upgrade=upgrade
            )

        upgrade.save()


def save_export(proto, conf):
    ref = proto_ref(proto)
    if not in_dict(conf, "export"):
        return

    export = {}
    if isinstance(conf["export"], str):
        export = [conf["export"]]
    elif isinstance(conf["export"], list):
        export = conf["export"]

    for key in export:
        if not StagePrototypeConfig.objects.filter(prototype=proto, name=key):
            err("INVALID_OBJECT_DEFINITION", f'{ref} does not has "{key}" config group')

        stage_prototype_export = StagePrototypeExport(prototype=proto, name=key)
        stage_prototype_export.save()


def get_config_groups(proto, action=None):
    groups = {}
    for stage_prototype_config in StagePrototypeConfig.objects.filter(prototype=proto, action=action):
        if stage_prototype_config.subname != "":
            groups[stage_prototype_config.name] = stage_prototype_config.name

    return groups


def check_default_import(proto, conf):
    ref = proto_ref(proto)
    if "default" not in conf:
        return

    groups = get_config_groups(proto)
    for key in conf["default"]:
        if key not in groups:
            msg = 'No import default group "{}" in config ({})'
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
        stage_prototype_import = StagePrototypeImport(prototype=proto, name=key)
        if "versions" in conf["import"][key]:
            check_versions(proto, conf["import"][key], f'import "{key}"')
            set_version(stage_prototype_import, conf["import"][key])
            if stage_prototype_import.min_version and stage_prototype_import.max_version:
                if (
                    rpm.compare_versions(
                        str(stage_prototype_import.min_version), str(stage_prototype_import.max_version)
                    )
                    > 0
                ):
                    msg = "Min version should be less or equal max version"
                    err("INVALID_VERSION_DEFINITION", msg)

        dict_to_obj(conf["import"][key], "required", stage_prototype_import)
        dict_to_obj(conf["import"][key], "multibind", stage_prototype_import)
        dict_to_obj(conf["import"][key], "default", stage_prototype_import)

        stage_prototype_import.save()


def check_action_hc(proto, conf, name):  # pylint: disable=unused-argument
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
        dict_to_obj(sub, "allow_to_terminate", sub_action)
        on_fail = sub.get(ON_FAIL, "")
        if isinstance(on_fail, str):
            sub_action.state_on_fail = on_fail
            sub_action.multi_state_on_fail_set = []
            sub_action.multi_state_on_fail_unset = []
        elif isinstance(on_fail, dict):
            sub_action.state_on_fail = _deep_get(on_fail, STATE, default="")
            sub_action.multi_state_on_fail_set = _deep_get(on_fail, MULTI_STATE, SET, default=[])
            sub_action.multi_state_on_fail_unset = _deep_get(on_fail, MULTI_STATE, UNSET, default=[])
        sub_action.save()


def save_upgrade_action(
    prototype: StagePrototype, config: dict, bundle_hash: str, upgrade: StageUpgrade
) -> None | StageAction:
    if not in_dict(config, "versions"):
        return None

    config["type"] = "task"
    config["display_name"] = f"Upgrade: {config['name']}"

    if upgrade is not None:
        name = (
            f"{prototype.name}_{prototype.version}_{prototype.edition}_upgrade_{config['name']}_{upgrade.min_version}_strict_"
            f"{upgrade.min_strict}-{upgrade.max_version}_strict_{upgrade.min_strict}_editions-"
            f"{'_'.join(upgrade.from_edition)}_state_available-{'_'.join(upgrade.state_available)}_"
            f"state_on_success-{upgrade.state_on_success}"
        )
    else:
        name = f"{prototype.name}_{prototype.version}_{prototype.edition}_upgrade_{config['name']}"

    name = re.sub(r"\s+", "_", name).strip().lower()
    name = re.sub(r"[()]", "", name)

    return save_action(prototype=prototype, config=config, bundle_hash=bundle_hash, name=name)


def save_actions(prototype: StagePrototype, config: dict, bundle_hash: str) -> None:
    if not in_dict(config, "actions"):
        return

    for name in sorted(config["actions"]):
        save_action(prototype=prototype, config=config["actions"][name], bundle_hash=bundle_hash, name=name)


def save_action(prototype: StagePrototype, config: dict, bundle_hash: str, name: str) -> StageAction:
    validate_name(
        name=name, error_message=f'Action name "{name}" of {prototype.type} "{prototype.name}" {prototype.version}'
    )
    action = StageAction(prototype=prototype, name=name)
    action.type = config["type"]

    if config["type"] == "job":
        action.script = config["script"]
        action.script_type = config["script_type"]

    dict_to_obj(config, "display_name", action)
    dict_to_obj(config, "description", action)
    dict_to_obj(config, "allow_to_terminate", action)
    dict_to_obj(config, "partial_execution", action)
    dict_to_obj(config, "host_action", action)
    dict_to_obj(config, "ui_options", action)
    dict_to_obj(config, "params", action)
    dict_to_obj(config, "log_files", action)
    dict_to_obj(config, "venv", action)
    dict_to_obj(config, "allow_in_maintenance_mode", action)

    fix_display_name(config, action)

    check_action_hc(prototype, config, name)
    dict_to_obj(config, "hc_acl", action, "hostcomponentmap")

    if MASKING in config:
        if STATES in config:
            err(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {name} uses both mutual excluding states "states" and "masking"',
            )

        action.state_available = _deep_get(config, MASKING, STATE, AVAILABLE, default=ANY)
        action.state_unavailable = _deep_get(config, MASKING, STATE, UNAVAILABLE, default=[])
        action.state_on_success = _deep_get(config, ON_SUCCESS, STATE, default="")
        action.state_on_fail = _deep_get(config, ON_FAIL, STATE, default="")

        action.multi_state_available = _deep_get(config, MASKING, MULTI_STATE, AVAILABLE, default=ANY)
        action.multi_state_unavailable = _deep_get(config, MASKING, MULTI_STATE, UNAVAILABLE, default=[])
        action.multi_state_on_success_set = _deep_get(config, ON_SUCCESS, MULTI_STATE, SET, default=[])
        action.multi_state_on_success_unset = _deep_get(config, ON_SUCCESS, MULTI_STATE, UNSET, default=[])
        action.multi_state_on_fail_set = _deep_get(config, ON_FAIL, MULTI_STATE, SET, default=[])
        action.multi_state_on_fail_unset = _deep_get(config, ON_FAIL, MULTI_STATE, UNSET, default=[])
    else:
        if ON_SUCCESS in config or ON_FAIL in config:
            err(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {name} uses "on_success/on_fail" states without "masking"',
            )

        action.state_available = _deep_get(config, STATES, AVAILABLE, default=[])
        action.state_unavailable = []
        action.state_on_success = _deep_get(config, STATES, ON_SUCCESS, default="")
        action.state_on_fail = _deep_get(config, STATES, ON_FAIL, default="")

        action.multi_state_available = ANY
        action.multi_state_unavailable = []
        action.multi_state_on_success_set = []
        action.multi_state_on_success_unset = []
        action.multi_state_on_fail_set = []
        action.multi_state_on_fail_unset = []

    action.save()
    save_sub_actions(config, action)
    save_prototype_config(prototype, config, bundle_hash, action)

    return action


def is_group(conf):
    if conf["type"] == "group":
        return True

    return False


def get_yspec(proto, ref, bundle_hash, conf, name, subname):  # pylint: disable=unused-argument
    schema = None
    yspec_body = read_bundle_file(proto, conf["yspec"], bundle_hash, f'yspec file of config key "{name}/{subname}":')
    try:
        schema = yaml.safe_load(yspec_body)
    except (yaml.parser.ParserError, yaml.scanner.ScannerError) as e:
        err("CONFIG_TYPE_ERROR", f'yspec file of config key "{name}/{subname}" yaml decode error: {e}')

    success, error = yspec.checker.check_rule(schema)
    if not success:
        err("CONFIG_TYPE_ERROR", f'yspec file of config key "{name}/{subname}" error: {error}')

    return schema


def save_prototype_config(
    proto, proto_conf, bundle_hash, action=None
):  # pylint: disable=too-many-statements,too-many-locals
    if not in_dict(proto_conf, "config"):
        return

    conf_dict = proto_conf["config"]
    ref = proto_ref(proto)

    def check_variant(conf, name, subname):  # pylint: disable=unused-argument
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
            key_ref = f'(config key "{name}/{subname}" of {ref})'
            msg = 'can not have "read_only" and "writable" simultaneously {}'
            err("INVALID_CONFIG_DEFINITION", msg.format(key_ref))

        for label in ("read_only", "writable"):
            if label in conf:
                opt[label] = conf[label]

        return opt

    def cook_conf(obj, _conf, _name, _subname):
        stage_prototype_config = StagePrototypeConfig(prototype=obj, action=action, name=_name, type=_conf["type"])
        dict_to_obj(_conf, "description", stage_prototype_config)
        dict_to_obj(_conf, "display_name", stage_prototype_config)
        dict_to_obj(_conf, "required", stage_prototype_config)
        dict_to_obj(_conf, "ui_options", stage_prototype_config)
        dict_to_obj(_conf, "group_customization", stage_prototype_config)
        _conf["limits"] = process_limits(_conf, _name, _subname)
        dict_to_obj(_conf, "limits", stage_prototype_config)
        if "display_name" not in _conf:
            if _subname:
                stage_prototype_config.display_name = _subname
            else:
                stage_prototype_config.display_name = _name

        if "default" in _conf:
            check_config_type(proto, _name, _subname, _conf, _conf["default"], bundle_hash)

        if type_is_complex(_conf["type"]):
            dict_json_to_obj(_conf, "default", stage_prototype_config)
        else:
            dict_to_obj(_conf, "default", stage_prototype_config)

        if _subname:
            stage_prototype_config.subname = _subname

        try:
            stage_prototype_config.save()
        except IntegrityError:
            msg = "Duplicate config on {} {}, action {}, with name {} and subname {}"
            err("INVALID_CONFIG_DEFINITION", msg.format(obj.type, obj, action, _name, _subname))

    if isinstance(conf_dict, dict):
        for name, conf in conf_dict.items():
            if "type" in conf:
                validate_name(name, f'Config key "{name}" of {ref}')
                cook_conf(proto, conf, name, "")
            else:
                validate_name(name, f'Config group "{name}" of {ref}')
                group_conf = {"type": "group", "required": False}
                cook_conf(proto, group_conf, name, "")
                for subname, subconf in conf.items():
                    err_msg = f'Config key "{name}/{subname}" of {ref}'
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)
    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            name = conf["name"]
            validate_name(name, f'Config key "{name}" of {ref}')
            cook_conf(proto, conf, name, "")
            if is_group(conf):
                for subconf in conf["subs"]:
                    subname = subconf["name"]
                    err_msg = f'Config key "{name}/{subname}" of {ref}'
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(proto, subconf, name, subname)


def validate_name(name: str, error_message: str) -> None:
    if not isinstance(name, str):
        err(code="WRONG_NAME", msg=f"{error_message} should be string")

    regex = re.compile(pattern=NAME_REGEX)

    if regex.fullmatch(name) is None:
        err(
            code="WRONG_NAME",
            msg=f"{error_message} is incorrect. Only latin characters, digits, dots (.), dashes (-), and underscores (_) are allowed.",
        )


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
