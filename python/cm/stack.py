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

from copy import copy, deepcopy
from pathlib import Path
from typing import Any, List, Literal
import os
import re
import json
import hashlib
import warnings

from adcm_version import compare_prototype_versions
from django.conf import settings
from django.db import IntegrityError
from jinja2 import Template
from jinja2.exceptions import TemplateError
from rest_framework import status
from rest_framework.exceptions import NotFound
from ruyaml.composer import ComposerError
from ruyaml.constructor import DuplicateKeyError
from ruyaml.error import ReusedAnchorWarning
from ruyaml.parser import ParserError as RuYamlParserError
from ruyaml.scanner import ScannerError as RuYamlScannerError
from yaml.parser import ParserError as YamlParserError
from yaml.scanner import ScannerError as YamlScannerError
import yaml
import ruyaml

from cm.adcm_config.checks import check_config_type
from cm.adcm_config.config import read_bundle_file
from cm.adcm_config.utils import proto_ref
from cm.checker import FormatError, check, check_rule, round_trip_load
from cm.errors import AdcmEx, raise_adcm_ex
from cm.logger import logger
from cm.models import (
    Host,
    Prototype,
    ServiceComponent,
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
)

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


def save_definition(
    path: Path,
    fname: Path,
    conf: dict | list,
    obj_list: dict,
    bundle_hash: str,
    adcm_: bool = False,
) -> tuple[list[StagePrototype], list[StageUpgrade]]:
    prototypes = []
    stage_upgrades = []

    if isinstance(conf, dict):
        prototype, upgrades = save_object_definition(
            path=path, fname=fname, conf=conf, obj_list=obj_list, bundle_hash=bundle_hash, adcm_=adcm_
        )
        prototypes.append(prototype)
        stage_upgrades.extend(upgrades)
    else:
        for obj_def in conf:
            prototype, upgrades = save_object_definition(
                path=path, fname=fname, conf=obj_def, obj_list=obj_list, bundle_hash=bundle_hash, adcm_=adcm_
            )
            prototypes.append(prototype)
            stage_upgrades.extend(upgrades)

    return prototypes, stage_upgrades


def cook_obj_id(conf):
    return f"{conf['type']}.{conf['name']}.{conf['version']}"


def save_object_definition(
    path: Path,
    fname: Path,
    conf: dict,
    obj_list: dict,
    bundle_hash: str,
    adcm_: bool = False,
) -> tuple[StagePrototype, list[StageUpgrade]]:
    def_type = conf["type"]
    if def_type == "adcm" and not adcm_:
        raise AdcmEx(
            code="INVALID_OBJECT_DEFINITION",
            msg=f'Invalid type "{def_type}" in object definition: {fname}',
        )

    check_object_definition(fname=fname, conf=conf, def_type=def_type, obj_list=obj_list, bundle_hash=bundle_hash)
    prototype, upgrades = save_prototype(path=path, conf=conf, def_type=def_type, bundle_hash=bundle_hash)
    logger.info('Save definition of %s "%s" %s to stage', def_type, conf["name"], conf["version"])
    obj_list[cook_obj_id(conf)] = fname

    return prototype, upgrades


def check_actions_definition(def_type: str, actions: dict, bundle_hash: str) -> None:
    for action_name, action_data in actions.items():
        if action_name in {
            settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME,
            settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
        }:
            if def_type != "cluster":
                raise_adcm_ex(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'Action named "{action_name}" can be started only in cluster context',
                )

            if not action_data.get("host_action"):
                raise_adcm_ex(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'Action named "{action_name}" should have "host_action: true" property',
                )
        if action_name in settings.ADCM_SERVICE_ACTION_NAMES_SET and set(action_data).intersection(
            settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET,
        ):
            raise_adcm_ex(
                code="INVALID_OBJECT_DEFINITION",
                msg=f"Maintenance mode actions shouldn't have "
                f'"{settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )

        if action_data.get("config_jinja") and action_data.get("config"):
            raise_adcm_ex(
                code="INVALID_OBJECT_DEFINITION",
                msg='"config" and "config_jinja" are mutually exclusive action options',
            )

        elif action_data.get("config_jinja") and action_data.get("config") is None:
            jinja_conf_file = Path(settings.BUNDLE_DIR, bundle_hash, action_data["config_jinja"])
            try:
                Template(source=jinja_conf_file.read_text(encoding=settings.ENCODING_UTF_8))
            except (FileNotFoundError, TemplateError) as e:
                raise_adcm_ex(code="INVALID_OBJECT_DEFINITION", msg=str(e))


def check_object_definition(fname: Path, conf: dict, def_type: str, obj_list, bundle_hash: str | None = None) -> None:
    ref = f"{def_type} \"{conf['name']}\" {conf['version']}"
    if cook_obj_id(conf) in obj_list:
        raise_adcm_ex(code="INVALID_OBJECT_DEFINITION", msg=f"Duplicate definition of {ref} (file {fname})")

    actions = conf.get("actions")
    if actions:
        check_actions_definition(def_type=def_type, actions=actions, bundle_hash=bundle_hash)


def get_config_files(path: Path) -> list[tuple[Path, Path]]:
    conf_list = []
    if not path.is_dir():
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f"no directory: {path}", args=status.HTTP_404_NOT_FOUND)

    for item in path.rglob("*"):
        if item.is_file() and item.name in {"config.yaml", "config.yml"}:
            conf_list.append((item.relative_to(path).parent, item))

    if not conf_list:
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f'no config files in stack directory "{path}"')

    return conf_list


def check_adcm_config(conf_file: Path) -> Any:
    warnings.simplefilter(action="error", category=ReusedAnchorWarning)
    schema_file = Path(settings.CODE_DIR, "cm", "adcm_schema.yaml")

    with Path(schema_file).open(encoding=settings.ENCODING_UTF_8) as f:
        rules = ruyaml.round_trip_load(f)
    try:
        with Path(conf_file).open(encoding=settings.ENCODING_UTF_8) as f:
            data = round_trip_load(f, version="1.1", allow_duplicate_keys=True)
    except (RuYamlParserError, RuYamlScannerError, NotImplementedError) as e:
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f'YAML decode "{conf_file}" error: {e}')
    except ruyaml.error.ReusedAnchorWarning as e:
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f'YAML decode "{conf_file}" error: {e}')
    except DuplicateKeyError as e:
        msg = f"{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}"
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f"Duplicate Keys error: {msg}")
    except ComposerError as e:
        raise_adcm_ex(code="STACK_LOAD_ERROR", msg=f"YAML Composer error: {e}")
    try:
        check(data, rules)
        return data  # noqa: TRY300
    except FormatError as e:
        error_msgs = []
        if e.errors:
            for error in e.errors:
                if "Input data for" in error.message:
                    continue

                error_msgs.append(f"line {error.line}: {error}")

        msg = f"'{conf_file}' line {e.line} error: {e}\n{os.linesep.join(error_msgs)}"
        logger.error(msg=msg)
        raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=msg) from e


def read_definition(conf_file: Path) -> dict:
    conf = check_adcm_config(conf_file=conf_file)
    logger.info('Read config file: "%s"', conf_file)

    return conf


def get_license_hash(proto, conf, bundle_hash):
    if "license" not in conf:
        return None

    body = read_bundle_file(proto=proto, fname=conf["license"], bundle_hash=bundle_hash, ref="license file")
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


def save_prototype(
    path: Path, conf: dict, def_type: str, bundle_hash: str
) -> tuple[StagePrototype, list[StageUpgrade]]:
    prototype = StagePrototype(name=conf["name"], type=def_type, path=path, version=conf["version"])

    dict_to_obj(dictionary=conf, key="required", obj=prototype)
    dict_to_obj(dictionary=conf, key="requires", obj=prototype)
    dict_to_obj(dictionary=conf, key="shared", obj=prototype)
    dict_to_obj(dictionary=conf, key="monitoring", obj=prototype)
    dict_to_obj(dictionary=conf, key="display_name", obj=prototype)
    dict_to_obj(dictionary=conf, key="description", obj=prototype)
    dict_to_obj(dictionary=conf, key="adcm_min_version", obj=prototype)
    dict_to_obj(dictionary=conf, key="venv", obj=prototype)
    dict_to_obj(dictionary=conf, key="edition", obj=prototype)

    process_config_group_customization(actual_config=conf, obj=prototype)

    dict_to_obj(dictionary=conf, key="config_group_customization", obj=prototype)
    dict_to_obj(dictionary=conf, key="allow_maintenance_mode", obj=prototype)
    dict_to_obj(dictionary=conf, key="allow_flags", obj=prototype)

    fix_display_name(conf=conf, obj=prototype)
    license_hash = get_license_hash(proto=prototype, conf=conf, bundle_hash=bundle_hash)
    if license_hash:
        if def_type not in {"cluster", "service", "provider"}:
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION",
                msg=(
                    f"Invalid license definition in {proto_ref(prototype=prototype)}. "
                    f"License can be placed in cluster, service or provider"
                ),
            )

        prototype.license_path = conf["license"]
        prototype.license_hash = license_hash

    prototype.save()

    save_actions(prototype=prototype, config=conf, bundle_hash=bundle_hash)
    upgrades = save_upgrade(prototype=prototype, config=conf, bundle_hash=bundle_hash)
    save_components(proto=prototype, conf=conf, bundle_hash=bundle_hash)
    save_prototype_config(prototype=prototype, proto_conf=conf, bundle_hash=bundle_hash)
    save_export(proto=prototype, conf=conf)
    save_import(proto=prototype, conf=conf)

    return prototype, upgrades


def check_component_constraint(proto, name, conf):
    if not conf:
        return

    if "constraint" not in conf:
        return

    if len(conf["constraint"]) > 2:
        raise_adcm_ex(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{name}" in {proto_ref(prototype=proto)} should have only 1 or 2 elements',
        )
    if not conf["constraint"]:
        raise_adcm_ex(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{name}" in {proto_ref(prototype=proto)} should not be empty',
        )


def save_components(proto: StagePrototype, conf: dict, bundle_hash: str) -> None:
    ref = proto_ref(prototype=proto)

    if not in_dict(dictionary=conf, key="components"):
        return

    for comp_name in conf["components"]:
        component_conf = conf["components"][comp_name]
        validate_name(name=comp_name, error_message=f'Component name "{comp_name}" of {ref}')
        component = StagePrototype(
            type="component",
            parent=proto,
            path=proto.path,
            name=comp_name,
            version=proto.version,
            adcm_min_version=proto.adcm_min_version,
        )

        dict_to_obj(dictionary=component_conf, key="description", obj=component)
        dict_to_obj(dictionary=component_conf, key="display_name", obj=component)
        dict_to_obj(dictionary=component_conf, key="monitoring", obj=component)

        fix_display_name(conf=component_conf, obj=component)
        check_display_name(obj=component)
        check_component_constraint(proto=proto, name=comp_name, conf=component_conf)

        dict_to_obj(dictionary=component_conf, key="params", obj=component)
        dict_to_obj(dictionary=component_conf, key="constraint", obj=component)
        dict_to_obj(dictionary=component_conf, key="requires", obj=component)
        dict_to_obj(dictionary=component_conf, key="venv", obj=component)
        dict_to_obj(dictionary=component_conf, key="bound_to", obj=component)

        process_config_group_customization(actual_config=component_conf, obj=component)

        dict_to_obj(dictionary=component_conf, key="config_group_customization", obj=component)
        dict_to_obj(dictionary=component_conf, key="allow_flags", obj=component)

        component.save()

        save_actions(prototype=component, config=component_conf, bundle_hash=bundle_hash)
        save_prototype_config(prototype=component, proto_conf=component_conf, bundle_hash=bundle_hash)


def check_upgrade(prototype: StagePrototype, config: dict) -> None:
    label = f'upgrade "{config["name"]}"'
    check_versions(prototype=prototype, config=config, label=label)
    check_upgrade_scripts(prototype=prototype, config=config, label=label)


def check_upgrade_scripts(prototype: StagePrototype, config: dict, label: str) -> None:
    ref = proto_ref(prototype=prototype)
    obj_ref = f"{label} of {ref}".capitalize()
    is_hc_acl_present = bool(config.get("hc_acl", False))
    count = 0

    if "scripts" in config:
        for action in config["scripts"]:
            if check_internal_script(
                config=action,
                allowed_scripts=("bundle_switch",),
                is_hc_acl_present=is_hc_acl_present,
                obj_ref=obj_ref,
                err_code="INVALID_UPGRADE_DEFINITION",
            ):
                count += 1

                if count > 1:
                    raise_adcm_ex(
                        code="INVALID_UPGRADE_DEFINITION",
                        msg=f'Script with script_type "internal" must be unique in {label} of {ref}',
                    )

        if count == 0:
            raise_adcm_ex(
                code="INVALID_UPGRADE_DEFINITION",
                msg=f'Scripts block in {label} of {ref} must contain exact one block with script "bundle_switch"',
            )
    else:
        if "masking" in config or "on_success" in config or "on_fail" in config:
            raise_adcm_ex(
                code="INVALID_UPGRADE_DEFINITION",
                msg=f"{label} of {ref} couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
            )


def check_versions(prototype: StagePrototype, config: dict, label: str) -> None:
    ref = proto_ref(prototype=prototype)

    if "min" in config["versions"] and "min_strict" in config["versions"]:
        raise_adcm_ex(
            code="INVALID_VERSION_DEFINITION",
            msg=f"min and min_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if all(("min" not in config["versions"], "min_strict" not in config["versions"], "import" not in label)):
        raise_adcm_ex(
            code="INVALID_VERSION_DEFINITION",
            msg=f"min or min_strict should be present in versions of {label} ({ref})",
        )

    if "max" in config["versions"] and "max_strict" in config["versions"]:
        raise_adcm_ex(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if all(("max" not in config["versions"], "max_strict" not in config["versions"], "import" not in label)):
        raise_adcm_ex(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict should be present in versions of {label} ({ref})",
        )

    for name in ("min", "min_strict", "max", "max_strict"):
        if name in config["versions"] and not config["versions"][name]:
            raise_adcm_ex(
                code="INVALID_VERSION_DEFINITION",
                msg=f"{name} versions of {label} should be not null ({ref})",
            )


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


def save_upgrade(prototype: StagePrototype, config: dict, bundle_hash: str) -> list[StageUpgrade]:
    if not in_dict(dictionary=config, key="upgrade"):
        return []

    upgrades = []

    for item in config["upgrade"]:
        check_upgrade(prototype=prototype, config=item)
        upgrade = StageUpgrade(name=item["name"])
        upgrade.display_name = item.get("display_name", item["name"])
        set_version(upgrade, item)
        dict_to_obj(item, "description", upgrade)
        if "states" in item:
            dict_to_obj(item["states"], "available", upgrade)

            if "available" in item["states"]:
                upgrade.state_available = item["states"]["available"]
            if "on_success" in item["states"]:
                upgrade.state_on_success = item["states"]["on_success"]
        if in_dict(dictionary=item, key="from_edition"):
            upgrade.from_edition = item["from_edition"]
        if "scripts" in item:
            upgrade.action = save_upgrade_action(
                prototype=prototype,
                config=copy(item),
                bundle_hash=bundle_hash,
                upgrade=upgrade,
            )

        upgrade.save()
        upgrades.append(upgrade)

    return upgrades


def save_export(proto: StagePrototype, conf: dict) -> None:
    ref = proto_ref(prototype=proto)
    if not in_dict(dictionary=conf, key="export"):
        return

    export = {}
    if isinstance(conf["export"], str):
        export = [conf["export"]]
    elif isinstance(conf["export"], list):
        export = conf["export"]

    for key in export:
        if not StagePrototypeConfig.objects.filter(prototype=proto, name=key):
            raise_adcm_ex(code="INVALID_OBJECT_DEFINITION", msg=f'{ref} does not has "{key}" config group')

        stage_prototype_export = StagePrototypeExport(prototype=proto, name=key)
        stage_prototype_export.save()


def get_config_groups(proto: StagePrototype, action: StageAction | None = None) -> dict:
    groups = {}
    for stage_prototype_config in StagePrototypeConfig.objects.filter(prototype=proto, action=action):
        if stage_prototype_config.subname != "":
            groups[stage_prototype_config.name] = stage_prototype_config.name

    return groups


def check_default_import(proto: StagePrototype, conf: dict) -> None:
    ref = proto_ref(prototype=proto)
    if "default" not in conf:
        return

    groups = get_config_groups(proto=proto)
    for key in conf["default"]:
        if key not in groups:
            raise_adcm_ex(code="INVALID_OBJECT_DEFINITION", msg=f'No import default group "{key}" in config ({ref})')


def save_import(proto: StagePrototype, conf: dict) -> None:
    ref = proto_ref(prototype=proto)
    if not in_dict(dictionary=conf, key="import"):
        return

    for key in conf["import"]:
        if "default" in conf["import"][key] and "required" in conf["import"][key]:
            raise_adcm_ex(
                code="INVALID_OBJECT_DEFINITION",
                msg=f"Import can't have default and be required in the same time ({ref})",
            )
        check_default_import(proto, conf["import"][key])
        stage_prototype_import = StagePrototypeImport(prototype=proto, name=key)
        if "versions" in conf["import"][key]:
            check_versions(proto, conf["import"][key], f'import "{key}"')
            set_version(stage_prototype_import, conf["import"][key])
            if stage_prototype_import.min_version and stage_prototype_import.max_version:  # noqa: SIM102
                if (
                    compare_prototype_versions(
                        str(stage_prototype_import.min_version),
                        str(stage_prototype_import.max_version),
                    )
                    > 0
                ):
                    raise_adcm_ex(
                        code="INVALID_VERSION_DEFINITION",
                        msg="Min version should be less or equal max version",
                    )

        dict_to_obj(conf["import"][key], "required", stage_prototype_import)
        dict_to_obj(conf["import"][key], "multibind", stage_prototype_import)
        dict_to_obj(conf["import"][key], "default", stage_prototype_import)

        stage_prototype_import.save()


def check_action_hc(proto: StagePrototype, conf: dict) -> None:
    if "hc_acl" not in conf:
        return

    for idx, item in enumerate(conf["hc_acl"]):
        if "service" not in item and proto.type == "service":
            item["service"] = proto.name
            conf["hc_acl"][idx]["service"] = proto.name


def save_sub_actions(conf, action):
    if action.type != settings.TASK_TYPE:
        return

    for sub in conf["scripts"]:
        sub_action = StageSubAction(
            action=action,
            script=sub["script"],
            script_type=sub["script_type"],
            name=sub["name"],
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
    prototype: StagePrototype,
    config: dict,
    bundle_hash: str,
    upgrade: StageUpgrade,
) -> None | StageAction:
    if not in_dict(dictionary=config, key="versions"):
        return None

    config["type"] = settings.TASK_TYPE
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

    return save_action(proto=prototype, config=config, bundle_hash=bundle_hash, action_name=name)


def check_internal_script(
    config: dict,
    allowed_scripts: tuple[str, ...],
    is_hc_acl_present: bool,
    obj_ref: str,
    err_code: str = "INVALID_OBJECT_DEFINITION",
) -> bool:
    if config["script_type"] != "internal":
        return False

    hc_apply = "hc_apply"

    allowed_scripts = {*allowed_scripts, hc_apply}

    if config["script"] not in allowed_scripts:
        raise_adcm_ex(
            code=err_code,
            msg=f"{obj_ref}: only `{allowed_scripts}` internal scripts allowed here, got `{config['script']}`",
        )

    if config["script"] == hc_apply and not is_hc_acl_present:
        raise_adcm_ex(
            code=err_code,
            msg=f"{obj_ref}: `{hc_apply}` requires `hc_acl` declaration",
        )

    if config["script"] == hc_apply:
        return False

    return True


def save_actions(prototype: StagePrototype, config: dict, bundle_hash: str) -> None:
    if not in_dict(dictionary=config, key="actions"):
        return

    prototype_ref = proto_ref(prototype=prototype)
    for name in sorted(config["actions"]):
        action_config = config["actions"][name]
        is_hc_acl_present = bool(action_config.get("hc_acl", False))
        obj_ref = f"Action {name} of {prototype_ref}"

        if action_config["type"] == settings.JOB_TYPE:
            check_internal_script(
                config=action_config,
                allowed_scripts=("bundle_revert",),
                is_hc_acl_present=is_hc_acl_present,
                obj_ref=obj_ref,
            )
        else:
            for subaction_config in action_config["scripts"]:
                check_internal_script(
                    config=subaction_config,
                    allowed_scripts=("bundle_revert",),
                    is_hc_acl_present=is_hc_acl_present,
                    obj_ref=obj_ref,
                )

        save_action(proto=prototype, config=action_config, bundle_hash=bundle_hash, action_name=name)


def save_action(proto: StagePrototype, config: dict, bundle_hash: str, action_name: str) -> StageAction:
    validate_name(
        name=action_name,
        error_message=f'Action name "{action_name}" of {proto.type} "{proto.name}" {proto.version}',
    )
    action = StageAction(prototype=proto, name=action_name)
    action.type = config["type"]

    if config["type"] == settings.JOB_TYPE:
        action.script = config["script"]
        action.script_type = config["script_type"]

    dict_to_obj(dictionary=config, key="description", obj=action)
    dict_to_obj(dictionary=config, key="allow_to_terminate", obj=action)
    dict_to_obj(dictionary=config, key="partial_execution", obj=action)
    dict_to_obj(dictionary=config, key="host_action", obj=action)
    dict_to_obj(dictionary=config, key="ui_options", obj=action)
    dict_to_obj(dictionary=config, key="params", obj=action)
    dict_to_obj(dictionary=config, key="log_files", obj=action)
    dict_to_obj(dictionary=config, key="venv", obj=action)
    dict_to_obj(dictionary=config, key="allow_in_maintenance_mode", obj=action)
    dict_to_obj(dictionary=config, key="config_jinja", obj=action)

    if "display_name" in config:
        dict_to_obj(dictionary=config, key="display_name", obj=action)
    else:
        action.display_name = action_name

    check_action_hc(proto=proto, conf=config)

    dict_to_obj(dictionary=config, key="hc_acl", obj=action, obj_key="hostcomponentmap")
    if MASKING in config:
        if STATES in config:
            raise_adcm_ex(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {action_name} uses both mutual excluding states "states" and "masking"',
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
            raise_adcm_ex(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {action_name} uses "on_success/on_fail" states without "masking"',
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
    save_sub_actions(conf=config, action=action)
    save_prototype_config(prototype=proto, proto_conf=config, bundle_hash=bundle_hash, action=action)

    return action


def get_yspec(prototype: StagePrototype | Prototype, bundle_hash: str, conf: dict, name: str, subname: str) -> Any:
    schema = None
    yspec_body = read_bundle_file(
        proto=prototype,
        fname=conf["yspec"],
        bundle_hash=bundle_hash,
        ref=f'yspec file of config key "{name}/{subname}":',
    )
    try:
        schema = yaml.safe_load(stream=yspec_body)
    except (YamlParserError, YamlScannerError) as e:
        raise_adcm_ex(
            code="CONFIG_TYPE_ERROR",
            msg=f'yspec file of config key "{name}/{subname}" yaml decode error: {e}',
        )

    success, error = check_rule(rules=schema)
    if not success:
        raise_adcm_ex(code="CONFIG_TYPE_ERROR", msg=f'yspec file of config key "{name}/{subname}" error: {error}')

    for _, value in schema.items():
        if value["match"] in {"one_of", "dict_key_selection", "set", "none", "any"}:
            raise AdcmEx(
                code="CONFIG_TYPE_ERROR",
                msg=f"yspec file of config key '{name}/{subname}': '{value['match']}' rule is not supported",
            )

    return schema


def check_variant(config: dict) -> dict:
    vtype = config["source"]["type"]
    source = {"type": vtype, "args": None}

    source["strict"] = config["source"].get("strict", True)

    if vtype == "inline":
        source["value"] = config["source"]["value"]
    elif vtype in ("config", "builtin"):
        source["name"] = config["source"]["name"]

    if vtype == "builtin" and "args" in config["source"]:
        source["args"] = config["source"]["args"]

    return source


def process_limits(config: dict, name: str, subname: str, prototype: StagePrototype, bundle_hash: str) -> dict:
    limits = {}

    if config["type"] == "option":
        limits = {"option": config["option"]}
    elif config["type"] == "variant":
        limits["source"] = check_variant(config=config)
    elif config["type"] in settings.STACK_NUMERIC_FIELD_TYPES:
        if "min" in config:
            limits["min"] = config["min"]

        if "max" in config:
            limits["max"] = config["max"]

    elif config["type"] == "structure":
        limits["yspec"] = get_yspec(
            prototype=prototype, bundle_hash=bundle_hash, conf=config, name=name, subname=subname
        )
    elif config["type"] == "group" and "activatable" in config:
        limits["activatable"] = config["activatable"]
        limits["active"] = False

        if "active" in config:
            limits["active"] = config["active"]

    if "read_only" in config and "writable" in config:
        key_ref = f'(config key "{name}/{subname}" of {proto_ref(prototype=prototype)})'
        msg = 'can not have "read_only" and "writable" simultaneously {}'
        raise_adcm_ex(code="INVALID_CONFIG_DEFINITION", msg=msg.format(key_ref))

    for label in ("read_only", "writable"):
        if label in config:
            limits[label] = config[label]

    return limits


def process_default(config: dict) -> None:
    if config["type"] == "map":
        config.setdefault("default", {})


def cook_conf(
    prototype: StagePrototype,
    config: dict,
    name: str,
    subname: str,
    bundle_hash: str,
    action: StageAction | None = None,
) -> None:
    stage_prototype_config = StagePrototypeConfig(prototype=prototype, action=action, name=name, type=config["type"])

    dict_to_obj(config, "description", stage_prototype_config)
    dict_to_obj(config, "display_name", stage_prototype_config)
    dict_to_obj(config, "required", stage_prototype_config)
    dict_to_obj(config, "ui_options", stage_prototype_config)
    dict_to_obj(config, "group_customization", stage_prototype_config)

    config["limits"] = process_limits(
        config=config, name=name, subname=subname, prototype=prototype, bundle_hash=bundle_hash
    )
    dict_to_obj(config, "limits", stage_prototype_config)

    if "display_name" not in config:
        if subname:
            stage_prototype_config.display_name = subname
        else:
            stage_prototype_config.display_name = name

    if "default" in config:
        check_config_type(
            prototype=prototype, key=name, subkey=subname, spec=config, value=config["default"], default=True
        )

    if config["type"] in settings.STACK_COMPLEX_FIELD_TYPES:
        dict_json_to_obj(config, "default", stage_prototype_config)
    else:
        dict_to_obj(config, "default", stage_prototype_config)

    if subname:
        stage_prototype_config.subname = subname

    try:
        stage_prototype_config.save()
    except IntegrityError:
        raise_adcm_ex(
            code="INVALID_CONFIG_DEFINITION",
            msg=f"Duplicate config on {prototype.type} {prototype}, action {action}, "
            f"with name {name} and subname {subname}",
        )


def save_prototype_config(
    prototype: StagePrototype,
    proto_conf: dict,
    bundle_hash: str,
    action: StageAction | None = None,
) -> None:
    if not in_dict(dictionary=proto_conf, key="config"):
        return

    conf_dict = proto_conf["config"]
    ref = proto_ref(prototype=prototype)

    if isinstance(conf_dict, dict):
        for name, conf in conf_dict.items():
            if "type" in conf:
                validate_name(name=name, error_message=f'Config key "{name}" of {ref}')
                cook_conf(
                    prototype=prototype, config=conf, name=name, subname="", bundle_hash=bundle_hash, action=action
                )
            else:
                validate_name(name=name, error_message=f'Config group "{name}" of {ref}')
                group_conf = {"type": "group", "required": False}
                cook_conf(
                    prototype=prototype,
                    config=group_conf,
                    name=name,
                    subname="",
                    bundle_hash=bundle_hash,
                    action=action,
                )

                for subname, subconf in conf.items():
                    err_msg = f'Config key "{name}/{subname}" of {ref}'
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(
                        prototype=prototype,
                        config=subconf,
                        name=name,
                        subname=subname,
                        bundle_hash=bundle_hash,
                        action=action,
                    )

    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            name = conf["name"]
            validate_name(name, f'Config key "{name}" of {ref}')
            cook_conf(prototype=prototype, config=conf, name=name, subname="", bundle_hash=bundle_hash, action=action)

            if conf["type"] == "group":
                for subconf in conf["subs"]:
                    subname = subconf["name"]
                    err_msg = f'Config key "{name}/{subname}" of {ref}'
                    validate_name(name, err_msg)
                    validate_name(subname, err_msg)
                    cook_conf(
                        prototype=prototype,
                        config=subconf,
                        name=name,
                        subname=subname,
                        bundle_hash=bundle_hash,
                        action=action,
                    )


def validate_name(name: str, error_message: str) -> None:
    if not isinstance(name, str):
        raise_adcm_ex(code="WRONG_NAME", msg=f"{error_message} should be string")

    regex = re.compile(pattern=NAME_REGEX)

    if regex.fullmatch(name) is None:
        raise_adcm_ex(
            code="WRONG_NAME",
            msg=f"{error_message} is incorrect. Only latin characters, digits, "
            f"dots (.), dashes (-), and underscores (_) are allowed.",
        )


def check_display_name(obj: StagePrototype) -> None:
    another_comps = (
        StagePrototype.objects.filter(type="component", display_name=obj.display_name, parent=obj.parent)
        .exclude(id=obj.id)
        .exists()
    )

    if another_comps:
        raise_adcm_ex(
            code="WRONG_NAME",
            msg=f"Display name for component within one service must be unique. "
            f"Incorrect definition of {proto_ref(prototype=obj)}",
        )


def fix_display_name(conf: dict, obj: StagePrototype) -> None:
    if isinstance(conf, dict) and "display_name" in conf:
        return

    obj.display_name = obj.name


def in_dict(dictionary: dict, key: str) -> bool:
    if not isinstance(dictionary, dict):
        return False

    if key in dictionary:
        if dictionary[key] is None:
            return False
        return True
    else:  # noqa: RET505
        return False


def dict_to_obj(dictionary, key, obj, obj_key=None):
    if not obj_key:
        obj_key = key

    if not isinstance(dictionary, dict):
        return

    if key in dictionary and dictionary[key] is not None:
        setattr(obj, obj_key, dictionary[key])


def dict_json_to_obj(dictionary: dict, key: str, obj: StagePrototypeConfig) -> None:
    if isinstance(dictionary, dict) and key in dictionary:
        setattr(obj, key, json.dumps(dictionary[key]))


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


def check_hostcomponents_objects_exist(hostcomponent_map: List[dict[Literal["host_id", "component_id"], int]]):
    host_ids = {hc["host_id"] for hc in hostcomponent_map}
    component_ids = {hc["component_id"] for hc in hostcomponent_map}

    host_queryset_ids = Host.objects.filter(id__in=host_ids).values_list("pk", flat=True)
    component_queryset_ids = ServiceComponent.objects.filter(id__in=component_ids).values_list("pk", flat=True)
    if len(diff := host_ids - set(host_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Hosts with ids {missing_ids} do not exist")
    if len(diff := component_ids - set(component_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Components with ids {missing_ids} do not exist")
