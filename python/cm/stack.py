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

from copy import copy
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Literal
import os
import re
import json
import hashlib
import warnings

from adcm_version import compare_prototype_versions
from core.job.types import ScriptType
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
from cm.adcm_config.config import reraise_file_errors_as_adcm_ex
from cm.adcm_config.utils import proto_ref
from cm.checker import FormatError, check, check_rule, round_trip_load
from cm.errors import AdcmEx
from cm.logger import logger
from cm.models import (
    Component,
    Host,
    Prototype,
    StageAction,
    StagePrototype,
    StagePrototypeConfig,
    StagePrototypeExport,
    StagePrototypeImport,
    StageSubAction,
    StageUpgrade,
)
from cm.services.bundle import PathResolver, detect_relative_path_to_bundle_root, is_path_correct
from cm.services.config.patterns import Pattern
from cm.utils import (
    ANY,
    AVAILABLE,
    MASKING,
    MULTI_STATE,
    NAME_REGEX,
    ON_FAIL,
    ON_SUCCESS,
    SET,
    STATE,
    STATES,
    UNAVAILABLE,
    UNSET,
    deep_get,
    get_on_fail_states,
)


def save_definition(
    path_resolver: PathResolver,
    source_file_subdir: Path,
    config_yaml_file: Path,
    config: dict | list,
    obj_list: dict,
) -> tuple[list[StagePrototype], list[StageUpgrade]]:
    prototypes = []
    stage_upgrades = []

    if isinstance(config, dict):
        config = [config]

    for obj_def in config:
        def_type = obj_def["type"]

        check_object_definition(
            path_resolver=path_resolver,
            fname=config_yaml_file,
            conf=obj_def,
            def_type=def_type,
            obj_list=obj_list,
            prototype_dir=source_file_subdir,
        )
        prototype, upgrades = save_prototype(
            path_resolver=path_resolver, path=source_file_subdir, conf=obj_def, def_type=def_type
        )
        logger.info('Save definition of %s "%s" %s to stage', def_type, obj_def["name"], obj_def["version"])
        obj_list[cook_obj_id(obj_def)] = config_yaml_file

        prototypes.append(prototype)
        stage_upgrades.extend(upgrades)

    return prototypes, stage_upgrades


def cook_obj_id(conf):
    return f"{conf['type']}.{conf['name']}.{conf['version']}"


def check_object_definition(
    path_resolver: PathResolver, fname: Path, conf: dict, def_type: str, obj_list, prototype_dir: str | Path
) -> None:
    ref = f'{def_type} "{conf["name"]}" {conf["version"]}'
    if cook_obj_id(conf) in obj_list:
        raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=f"Duplicate definition of {ref} (file {fname})")

    if not (actions := conf.get("actions")):
        return

    for action_name, action_data in actions.items():
        if action_name in {
            settings.ADCM_HOST_TURN_ON_MM_ACTION_NAME,
            settings.ADCM_HOST_TURN_OFF_MM_ACTION_NAME,
        }:
            if def_type != "cluster":
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'Action named "{action_name}" can be started only in cluster context',
                )

            if not action_data.get("host_action"):
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'Action named "{action_name}" should have "host_action: true" property',
                )

        if action_name in settings.ADCM_SERVICE_ACTION_NAMES_SET and set(action_data).intersection(
            settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET,
        ):
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION",
                msg=f"Maintenance mode actions shouldn't have "
                f'"{settings.ADCM_MM_ACTION_FORBIDDEN_PROPS_SET}" properties',
            )

        if config_jinja_path := action_data.get("config_jinja"):
            if "config" in action_data:
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg='"config" and "config_jinja" are mutually exclusive action options',
                )

            if not is_path_correct(config_jinja_path):
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'"config_jinja" has unsupported path format: {config_jinja_path}',
                )

            jinja_conf_file = path_resolver.resolve(
                detect_relative_path_to_bundle_root(source_file_dir=prototype_dir, raw_path=config_jinja_path)
            )
            try:
                Template(source=jinja_conf_file.read_text(encoding="utf-8"))
            except (FileNotFoundError, TemplateError) as e:
                raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=str(e)) from e

        if scripts_jinja_path := action_data.get("scripts_jinja"):
            # "scripts" and "scripts_jinja" mutual exclusivity is handled in adcm_schema.yaml

            if not is_path_correct(scripts_jinja_path):
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f'"scripts_jinja" has unsupported path format: {scripts_jinja_path}',
                )

            scripts_jinja_file = path_resolver.resolve(
                detect_relative_path_to_bundle_root(source_file_dir=prototype_dir, raw_path=scripts_jinja_path)
            )
            try:
                Template(source=scripts_jinja_file.read_text(encoding="utf-8"))
            except (FileNotFoundError, TemplateError) as e:
                raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=str(e)) from e


def get_config_files(path: Path) -> list[tuple[Path, Path]]:
    conf_list = []
    if not path.is_dir():
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f"no directory: {path}", args=status.HTTP_404_NOT_FOUND)

    for item in path.rglob("*"):
        if item.is_file() and item.name in {"config.yaml", "config.yml"}:
            conf_list.append((item.relative_to(path).parent, item))

    if not conf_list:
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f'no config files in stack directory "{path}"')

    return conf_list


def read_definition(conf_file: Path) -> dict:
    warnings.simplefilter(action="error", category=ReusedAnchorWarning)
    schema_file = settings.CODE_DIR / "cm" / "adcm_schema.yaml"

    with Path(schema_file).open(encoding="utf-8") as f:
        rules = ruyaml.round_trip_load(f)
    try:
        with conf_file.open(encoding="utf-8") as f:
            data = round_trip_load(f, version="1.1", allow_duplicate_keys=True)
    except (RuYamlParserError, RuYamlScannerError, NotImplementedError) as e:
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f'YAML decode "{conf_file}" error: {e}') from e
    except ruyaml.error.ReusedAnchorWarning as e:
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f'YAML decode "{conf_file}" error: {e}') from e
    except DuplicateKeyError as e:
        msg = f"{e.context}\n{e.context_mark}\n{e.problem}\n{e.problem_mark}"
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f"Duplicate Keys error: {msg}") from e
    except ComposerError as e:
        raise AdcmEx(code="STACK_LOAD_ERROR", msg=f"YAML Composer error: {e}") from e

    try:
        check(data, rules)
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

    logger.info('Read config file: "%s"', conf_file)
    return data


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
    path_resolver: PathResolver, path: Path, conf: dict, def_type: str
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
    dict_to_obj(dictionary=conf, key="flag_autogeneration", obj=prototype)

    fix_display_name(conf=conf, obj=prototype)
    if "license" in conf:
        if def_type not in {"cluster", "service", "provider"}:
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION",
                msg=(
                    f"Invalid license definition in {proto_ref(prototype=prototype)}. "
                    f"License can be placed in cluster, service or provider"
                ),
            )

        if not is_path_correct(conf["license"]):
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION", msg=f"Unsupported path format for license: {prototype.license_path}"
            )

        prototype.license_path = detect_relative_path_to_bundle_root(
            source_file_dir=prototype.path, raw_path=conf["license"]
        )

        with reraise_file_errors_as_adcm_ex(filepath=prototype.license_path, reference="license file"):
            license_content: bytes = path_resolver.resolve(prototype.license_path).read_bytes()

        prototype.license_hash = hashlib.sha256(license_content).hexdigest()

    prototype.save()

    save_actions(prototype=prototype, config=conf, path_resolver=path_resolver)
    upgrades = save_upgrade(prototype=prototype, config=conf, path_resolver=path_resolver)
    save_components(proto=prototype, conf=conf, path_resolver=path_resolver)
    save_prototype_config(prototype=prototype, proto_conf=conf, path_resolver=path_resolver)
    save_export(proto=prototype, conf=conf)
    save_import(proto=prototype, conf=conf)

    return prototype, upgrades


def check_component_constraint(proto, name, conf):
    if not conf:
        return

    if "constraint" not in conf:
        return

    if len(conf["constraint"]) > 2:
        raise AdcmEx(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{name}" in {proto_ref(prototype=proto)} should have only 1 or 2 elements',
        )
    if not conf["constraint"]:
        raise AdcmEx(
            code="INVALID_COMPONENT_DEFINITION",
            msg=f'constraint of component "{name}" in {proto_ref(prototype=proto)} should not be empty',
        )


def save_components(proto: StagePrototype, conf: dict, path_resolver: PathResolver) -> None:
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
        dict_to_obj(dictionary=component_conf, key="flag_autogeneration", obj=component)

        process_config_group_customization(actual_config=component_conf, obj=component)

        dict_to_obj(dictionary=component_conf, key="config_group_customization", obj=component)
        dict_to_obj(dictionary=component_conf, key="enable_outdated_config", obj=component)

        component.save()

        save_actions(prototype=component, config=component_conf, path_resolver=path_resolver)
        save_prototype_config(prototype=component, proto_conf=component_conf, path_resolver=path_resolver)


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
                    raise AdcmEx(
                        code="INVALID_UPGRADE_DEFINITION",
                        msg=f'Script with script_type "internal" must be unique in {label} of {ref}',
                    )

        if count == 0:
            raise AdcmEx(
                code="INVALID_UPGRADE_DEFINITION",
                msg=f'Scripts block in {label} of {ref} must contain exact one block with script "bundle_switch"',
            )
    elif "masking" in config or "on_success" in config or "on_fail" in config:
        raise AdcmEx(
            code="INVALID_UPGRADE_DEFINITION",
            msg=f"{label} of {ref} couldn't contain `masking`, `on_success` or `on_fail` without `scripts` block",
        )


def check_versions(prototype: StagePrototype, config: dict, label: str) -> None:
    ref = proto_ref(prototype=prototype)

    if "min" in config["versions"] and "min_strict" in config["versions"]:
        raise AdcmEx(
            code="INVALID_VERSION_DEFINITION",
            msg=f"min and min_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if all(("min" not in config["versions"], "min_strict" not in config["versions"], "import" not in label)):
        raise AdcmEx(
            code="INVALID_VERSION_DEFINITION",
            msg=f"min or min_strict should be present in versions of {label} ({ref})",
        )

    if "max" in config["versions"] and "max_strict" in config["versions"]:
        raise AdcmEx(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict can not be used simultaneously in versions of {label} ({ref})",
        )

    if all(("max" not in config["versions"], "max_strict" not in config["versions"], "import" not in label)):
        raise AdcmEx(
            code="INVALID_VERSION_DEFINITION",
            msg=f"max and max_strict should be present in versions of {label} ({ref})",
        )

    for name in ("min", "min_strict", "max", "max_strict"):
        if name in config["versions"] and not config["versions"][name]:
            raise AdcmEx(
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


def save_upgrade(prototype: StagePrototype, config: dict, path_resolver: PathResolver) -> list[StageUpgrade]:
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
                path_resolver=path_resolver,
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
            raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=f'{ref} does not has "{key}" config group')

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
            raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=f'No import default group "{key}" in config ({ref})')


def save_import(proto: StagePrototype, conf: dict) -> None:
    ref = proto_ref(prototype=proto)
    if not in_dict(dictionary=conf, key="import"):
        return

    for key in conf["import"]:
        if "default" in conf["import"][key] and "required" in conf["import"][key]:
            raise AdcmEx(
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
                    raise AdcmEx(
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


def save_sub_actions(conf, action, prototype_dir: Path | str):
    if action.type != settings.TASK_TYPE:
        sub_action = StageSubAction(
            action=action,
            script=conf["script"],
            script_type=conf["script_type"],
            name=action.name,
            allow_to_terminate=action.allow_to_terminate,
        )
        if sub_action.script_type != ScriptType.INTERNAL:
            if not is_path_correct(sub_action.script):
                raise AdcmEx(
                    code="INVALID_OBJECT_DEFINITION",
                    msg=f"Script {sub_action.name} of {action.name} has unsupported path format: {sub_action.script}",
                )

            sub_action.script = str(
                detect_relative_path_to_bundle_root(source_file_dir=prototype_dir, raw_path=str(sub_action.script))
            )
        sub_action.display_name = action.display_name

        dict_to_obj(conf, "params", sub_action)
        on_fail = conf.get(ON_FAIL, "")
        if isinstance(on_fail, str):
            sub_action.state_on_fail = on_fail
            sub_action.multi_state_on_fail_set = []
            sub_action.multi_state_on_fail_unset = []
        elif isinstance(on_fail, dict):
            sub_action.state_on_fail = deep_get(on_fail, STATE, default="")
            sub_action.multi_state_on_fail_set = deep_get(on_fail, MULTI_STATE, SET, default=[])
            sub_action.multi_state_on_fail_unset = deep_get(on_fail, MULTI_STATE, UNSET, default=[])

        sub_action.save()
        return

    action_wide_params = conf.get("params", {})
    for sub in conf.get("scripts", []):
        sub_action = StageSubAction(
            action=action,
            script=sub["script"],
            script_type=sub["script_type"],
            name=sub["name"],
            allow_to_terminate=sub.get("allow_to_terminate", action.allow_to_terminate),
        )
        if sub_action.script_type != ScriptType.INTERNAL:
            sub_action.script = str(
                detect_relative_path_to_bundle_root(source_file_dir=prototype_dir, raw_path=str(sub_action.script))
            )
        sub_action.display_name = sub["name"]

        if "display_name" in sub:
            sub_action.display_name = sub["display_name"]

        dict_to_obj(sub, "params", sub_action)
        if not sub_action.params and action_wide_params:
            sub_action.params = action_wide_params

        state_on_fail, multi_state_on_fail_set, multi_state_on_fail_unset = get_on_fail_states(config=sub)
        sub_action.state_on_fail = state_on_fail
        sub_action.multi_state_on_fail_set = multi_state_on_fail_set
        sub_action.multi_state_on_fail_unset = multi_state_on_fail_unset

        sub_action.save()


def save_upgrade_action(
    prototype: StagePrototype,
    config: dict,
    path_resolver: PathResolver,
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

    return save_action(proto=prototype, config=config, path_resolver=path_resolver, action_name=name)


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
        raise AdcmEx(
            code=err_code,
            msg=f"{obj_ref}: only `{allowed_scripts}` internal scripts allowed here, got `{config['script']}`",
        )

    if config["script"] == hc_apply and not is_hc_acl_present:
        raise AdcmEx(
            code=err_code,
            msg=f"{obj_ref}: `{hc_apply}` requires `hc_acl` declaration",
        )

    if config["script"] == hc_apply:
        return False

    return True


def save_actions(prototype: StagePrototype, config: dict, path_resolver: PathResolver) -> None:
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
        elif "scripts" in action_config:
            for subaction_config in action_config["scripts"]:
                check_internal_script(
                    config=subaction_config,
                    allowed_scripts=("bundle_revert",),
                    is_hc_acl_present=is_hc_acl_present,
                    obj_ref=obj_ref,
                )

        save_action(proto=prototype, config=action_config, path_resolver=path_resolver, action_name=name)


def save_action(proto: StagePrototype, config: dict, path_resolver: PathResolver, action_name: str) -> StageAction:
    validate_name(
        name=action_name,
        error_message=f'Action name "{action_name}" of {proto.type} "{proto.name}" {proto.version}',
    )
    action = StageAction(prototype=proto, name=action_name)
    action.type = config["type"]

    if config.get("host_action", False) and config.get("allow_for_action_host_group", False):
        message = (
            "The allow_for_action_host_group and host_action attributes are mutually exclusive. "
            f"Check {action_name} action definition"
        )
        raise AdcmEx(code="INVALID_ACTION_DEFINITION", msg=message)

    dict_to_obj(dictionary=config, key="description", obj=action)
    dict_to_obj(dictionary=config, key="allow_to_terminate", obj=action)
    dict_to_obj(dictionary=config, key="partial_execution", obj=action)
    dict_to_obj(dictionary=config, key="host_action", obj=action)
    dict_to_obj(dictionary=config, key="allow_for_action_host_group", obj=action)
    dict_to_obj(dictionary=config, key="ui_options", obj=action)
    dict_to_obj(dictionary=config, key="venv", obj=action)
    dict_to_obj(dictionary=config, key="allow_in_maintenance_mode", obj=action)
    dict_to_obj(dictionary=config, key="config_jinja", obj=action)
    dict_to_obj(dictionary=config, key="scripts_jinja", obj=action)

    if action.config_jinja:
        action.config_jinja = detect_relative_path_to_bundle_root(
            source_file_dir=proto.path, raw_path=action.config_jinja
        )

    if action.scripts_jinja:
        action.scripts_jinja = detect_relative_path_to_bundle_root(
            source_file_dir=proto.path, raw_path=action.scripts_jinja
        )

    if "display_name" in config:
        dict_to_obj(dictionary=config, key="display_name", obj=action)
    else:
        action.display_name = action_name

    check_action_hc(proto=proto, conf=config)

    dict_to_obj(dictionary=config, key="hc_acl", obj=action, obj_key="hostcomponentmap")
    if MASKING in config:
        if STATES in config:
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {action_name} uses both mutual excluding states "states" and "masking"',
            )

        action.state_available = deep_get(config, MASKING, STATE, AVAILABLE, default=ANY)
        action.state_unavailable = deep_get(config, MASKING, STATE, UNAVAILABLE, default=[])
        action.state_on_success = deep_get(config, ON_SUCCESS, STATE, default="")
        action.state_on_fail = deep_get(config, ON_FAIL, STATE, default="")

        action.multi_state_available = deep_get(config, MASKING, MULTI_STATE, AVAILABLE, default=ANY)
        action.multi_state_unavailable = deep_get(config, MASKING, MULTI_STATE, UNAVAILABLE, default=[])
        action.multi_state_on_success_set = deep_get(config, ON_SUCCESS, MULTI_STATE, SET, default=[])
        action.multi_state_on_success_unset = deep_get(config, ON_SUCCESS, MULTI_STATE, UNSET, default=[])
        action.multi_state_on_fail_set = deep_get(config, ON_FAIL, MULTI_STATE, SET, default=[])
        action.multi_state_on_fail_unset = deep_get(config, ON_FAIL, MULTI_STATE, UNSET, default=[])
    else:
        if ON_SUCCESS in config or ON_FAIL in config:
            raise AdcmEx(
                code="INVALID_OBJECT_DEFINITION",
                msg=f'Action {action_name} uses "on_success/on_fail" states without "masking"',
            )

        action.state_available = deep_get(config, STATES, AVAILABLE, default=[])
        action.state_unavailable = []
        action.state_on_success = deep_get(config, STATES, ON_SUCCESS, default="")
        action.state_on_fail = deep_get(config, STATES, ON_FAIL, default="")

        action.multi_state_available = ANY
        action.multi_state_unavailable = []
        action.multi_state_on_success_set = []
        action.multi_state_on_success_unset = []
        action.multi_state_on_fail_set = []
        action.multi_state_on_fail_unset = []

    action.save()

    save_sub_actions(conf=config, action=action, prototype_dir=proto.path)

    save_prototype_config(prototype=proto, proto_conf=config, path_resolver=path_resolver, action=action)

    return action


@lru_cache
def get_rules_for_yspec_schema():
    with (settings.CODE_DIR / "cm" / "yspec_schema.yaml").open(encoding="utf-8") as f:
        return ruyaml.round_trip_load(stream=f)


def check_yspec_schema(conf_file: Path) -> None:
    with Path(conf_file).open(encoding="utf-8") as f:
        data = ruyaml.round_trip_load(stream=f)

    check(data=data, rules=get_rules_for_yspec_schema())


def get_yspec(
    path_resolver: PathResolver, prototype: StagePrototype | Prototype, conf: dict, name: str, subname: str
) -> Any:
    yspec_file = path_resolver.resolve(
        detect_relative_path_to_bundle_root(source_file_dir=prototype.path, raw_path=conf["yspec"])
    )
    try:
        check_yspec_schema(conf_file=yspec_file)
    except FormatError as error:
        msg = (
            f"Line {error.line} error in '{conf['yspec']}' file of config key '{name}/{subname}' from"
            f" '{prototype.display_name}' {prototype.type}: {error}"
        )
        raise AdcmEx(code="INVALID_OBJECT_DEFINITION", msg=msg) from error

    try:
        schema = yaml.safe_load(stream=yspec_file.read_text(encoding="utf-8"))
    except (YamlParserError, YamlScannerError) as e:
        raise AdcmEx(
            code="CONFIG_TYPE_ERROR",
            msg=f'yspec file of config key "{name}/{subname}" yaml decode error: {e}',
        ) from e

    success, error = check_rule(rules=schema)
    if not success:
        raise AdcmEx(code="CONFIG_TYPE_ERROR", msg=f'yspec file of config key "{name}/{subname}" error: {error}')

    for _, value in schema.items():
        if value["match"] in {"one_of", "dict_key_selection", "set", "none", "any"}:
            raise AdcmEx(
                code="CONFIG_TYPE_ERROR",
                msg=f"yspec file of config key '{name}/{subname}': '{value['match']}' rule is not supported",
            )

    return schema


def check_variant(config: dict) -> dict:
    vtype = config["source"]["type"]
    source = {"type": vtype, "args": None, "strict": config["source"].get("strict", True)}

    if vtype == "inline":
        source["value"] = config["source"]["value"]
    elif vtype in ("config", "builtin"):
        source["name"] = config["source"]["name"]

    if vtype == "builtin" and "args" in config["source"]:
        source["args"] = config["source"]["args"]

    return source


def process_limits(
    config: dict, name: str, subname: str, prototype: StagePrototype, path_resolver: PathResolver
) -> dict:
    limits = {}
    param_type = config["type"]

    param_pattern = config.get("pattern")
    if isinstance(param_pattern, str):
        pattern = Pattern(regex_pattern=param_pattern)
        if not pattern.is_valid:
            display_name = config.get("display_name", config["name"])
            message = f"The pattern attribute value of {display_name} config parameter is not valid regular expression"
            raise AdcmEx(code="INVALID_CONFIG_DEFINITION", msg=message)

        default = config.get("default")
        if default is not None and not pattern.matches(str(default)):
            display_name = config.get("display_name", config["name"])
            message = f"The default attribute value of {display_name} config parameter does not match pattern"
            raise AdcmEx(code="INVALID_CONFIG_DEFINITION", msg=message)

        limits["pattern"] = pattern.raw

    if param_type == "option":
        limits = {"option": config["option"]}
    elif param_type == "variant":
        limits["source"] = check_variant(config=config)
    elif param_type in settings.STACK_NUMERIC_FIELD_TYPES:
        if "min" in config:
            limits["min"] = config["min"]

        if "max" in config:
            limits["max"] = config["max"]

    elif param_type == "structure":
        limits["yspec"] = get_yspec(
            path_resolver=path_resolver, prototype=prototype, conf=config, name=name, subname=subname
        )
    elif param_type == "group" and "activatable" in config:
        limits["activatable"] = config["activatable"]
        limits["active"] = False

        if "active" in config:
            limits["active"] = config["active"]

    if "read_only" in config and "writable" in config:
        key_ref = f'(config key "{name}/{subname}" of {proto_ref(prototype=prototype)})'
        msg = 'can not have "read_only" and "writable" simultaneously {}'
        raise AdcmEx(code="INVALID_CONFIG_DEFINITION", msg=msg.format(key_ref))

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
    path_resolver: PathResolver,
    action: StageAction | None = None,
) -> None:
    stage_prototype_config = StagePrototypeConfig(prototype=prototype, action=action, name=name, type=config["type"])

    dict_to_obj(config, "description", stage_prototype_config)
    dict_to_obj(config, "display_name", stage_prototype_config)
    dict_to_obj(config, "required", stage_prototype_config)
    dict_to_obj(config, "ui_options", stage_prototype_config)
    dict_to_obj(config, "group_customization", stage_prototype_config)
    dict_to_obj(config, "ansible_options", stage_prototype_config)

    config["limits"] = process_limits(
        config=config, name=name, subname=subname, prototype=prototype, path_resolver=path_resolver
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
    elif config["type"] in settings.STACK_FILE_FIELD_TYPES and isinstance(config.get("default"), str):
        stage_prototype_config.default = detect_relative_path_to_bundle_root(
            source_file_dir=prototype.path, raw_path=config["default"]
        )
    else:
        dict_to_obj(config, "default", stage_prototype_config)

    if subname:
        stage_prototype_config.subname = subname

    try:
        stage_prototype_config.save()
    except IntegrityError as err:
        raise AdcmEx(
            code="INVALID_CONFIG_DEFINITION",
            msg=f"Duplicate config on {prototype.type} {prototype}, action {action}, "
            f"with name {name} and subname {subname}",
        ) from err


def save_prototype_config(
    prototype: StagePrototype,
    proto_conf: dict,
    path_resolver: PathResolver,
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
                    prototype=prototype, config=conf, name=name, subname="", path_resolver=path_resolver, action=action
                )
            else:
                validate_name(name=name, error_message=f'Config group "{name}" of {ref}')
                group_conf = {"type": "group", "required": False}
                cook_conf(
                    prototype=prototype,
                    config=group_conf,
                    name=name,
                    subname="",
                    path_resolver=path_resolver,
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
                        path_resolver=path_resolver,
                        action=action,
                    )

    elif isinstance(conf_dict, list):
        for conf in conf_dict:
            name = conf["name"]
            validate_name(name, f'Config key "{name}" of {ref}')
            cook_conf(
                prototype=prototype, config=conf, name=name, subname="", path_resolver=path_resolver, action=action
            )

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
                        path_resolver=path_resolver,
                        action=action,
                    )


def validate_name(name: str, error_message: str) -> None:
    if not isinstance(name, str):
        raise AdcmEx(code="WRONG_NAME", msg=f"{error_message} should be string")

    regex = re.compile(pattern=NAME_REGEX)

    if regex.fullmatch(name) is None:
        raise AdcmEx(
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
        raise AdcmEx(
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


def check_hostcomponents_objects_exist(hostcomponent_map: List[dict[Literal["host_id", "component_id"], int]]):
    host_ids = {hc["host_id"] for hc in hostcomponent_map}
    component_ids = {hc["component_id"] for hc in hostcomponent_map}

    host_queryset_ids = Host.objects.filter(id__in=host_ids).values_list("pk", flat=True)
    component_queryset_ids = Component.objects.filter(id__in=component_ids).values_list("pk", flat=True)
    if len(diff := host_ids - set(host_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Hosts with ids {missing_ids} do not exist")
    if len(diff := component_ids - set(component_queryset_ids)) != 0:
        missing_ids = ", ".join(str(h_id) for h_id in diff)
        raise NotFound(f"Components with ids {missing_ids} do not exist")
