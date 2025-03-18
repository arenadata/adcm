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

from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable, Literal
import re

import yaml

from core.bundle_alt.predicates import is_component_key
from core.bundle_alt.representation import find_parent
from core.bundle_alt.schema import ADCMSchema, ClusterSchema, ComponentSchema, HostSchema, ProviderSchema, ServiceSchema
from core.bundle_alt.types import (
    ActionAvailability,
    ActionDefinition,
    BundleDefinitionKey,
    ConfigDefinition,
    ConfigParamPlainSpec,
    Definition,
    ImportDefinition,
    License,
    OnCompletion,
    ParameterKey,
    UpgradeDefinition,
    UpgradeRestrictions,
    VersionBound,
)
from core.job.types import JobSpec, ScriptType

# Public


# COPY Start (for ADCM-6370 copied from cm)
def detect_relative_path_to_bundle_root(source_file_dir: str | Path, raw_path: str) -> Path:
    """
    :param source_file_dir: Directory with file where given `path` is defined
    :param raw_path: Path to resolve

    >>> from pathlib import Path
    >>> this = detect_relative_path_to_bundle_root
    >>> this("", "./script.yaml") == Path("script.yaml")
    True
    >>> str(this(".", "./some/script.yaml")) == "some/script.yaml"
    True
    >>> str(this(Path(""), "script.yaml")) == "script.yaml"
    True
    >>> str(this(Path("inner"), "atroot/script.yaml")) == "atroot/script.yaml"
    True
    >>> str(this(Path("inner"), "./script.yaml")) == "inner/script.yaml"
    True
    >>> str(this(Path("inner"), "./alongside/script.yaml")) == "inner/alongside/script.yaml"
    True
    """
    if raw_path.startswith("./"):
        return Path(source_file_dir) / raw_path

    return Path(raw_path)


# this one's not copied, but adopted for simpliest case scenario
def load_yspec(path: Path):
    return yaml.safe_load(stream=path.read_text(encoding="utf-8"))


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


# COPY End


def schema_entry_to_definition(
    key: BundleDefinitionKey,
    entry: ClusterSchema | ServiceSchema | ComponentSchema | ProviderSchema | HostSchema | ADCMSchema,
    entries: dict[
        BundleDefinitionKey, ClusterSchema | ServiceSchema | ComponentSchema | ProviderSchema | HostSchema | ADCMSchema
    ],
    source_relative_path: str,
    bundle_root: Path,
) -> Definition:
    plain_entity = entry.model_dump(exclude_unset=True, exclude_none=True, exclude_defaults=True)
    context = {"bundle_root": bundle_root, "path": source_relative_path, "key": key, "object": plain_entity}

    if is_component_key(key):
        parent = find_parent(key, entries)
        inherited = {
            "name": key[-1],
            "version": parent.version,
            "type": "component",
            "adcm_min_version": parent.adcm_min_version,
        }
        plain_entity |= inherited

    definition: Definition = _convert(plain_entity, context)

    return definition


def extract_scripts(scripts: list[dict], path_resolution_root: Path) -> list[JobSpec] | None:
    return _extract_scripts(entity={"scripts": scripts}, context={"path": path_resolution_root})


def extract_config(config: list[dict], context: dict) -> ConfigDefinition | None:
    return _extract_config(entity={"config": config}, context=context)


def _convert(entity: dict, context: dict):
    result = {
        "name": entity["name"],
        "type": entity["type"],
        "version": str(entity["version"]),
        "path": context["path"],
        "upgrades": _extract_upgrades(entity, context),
        "actions": _extract_actions(entity, context),
        "config": _extract_config(entity, context),
        "imports": _extract_imports(entity),
        "exports": _extract_exports(entity),
        "license": _extract_license(entity, context),
    }

    _fill_value(result, entity, "adcm_min_version", cast=str)
    _fill_value(result, entity, "description")
    _fill_value(result, entity, "edition")
    _fill_value(result, entity, "flag_autogeneration")
    _fill_value(result, entity, "venv")
    _fill_value(result, entity, "shared")
    _fill_value(result, entity, "required")
    _fill_value(result, entity, "monitoring")
    _fill_value(result, entity, "config_group_customization")
    _fill_value(result, entity, "allow_maintenance_mode")
    _fill_value(result, entity, "constraint")
    _fill_value(result, entity, "bound_to")
    _fill_value(result, entity, "requires")

    _patch_display_name(result, entity)

    definition = Definition(**_drop_unset(result))
    _patch_upgrade_action_names(definition)

    return definition


def _extract_imports(entity: dict) -> list[dict] | None:
    imports = entity.get("imports")
    if imports is None:
        return None

    return list(map(_extract_import, _to_named_list(imports)))


def _extract_import(entity: dict) -> ImportDefinition:
    result = {
        "name": entity["name"],
        "min_version": _extract_version_bound(entity, "min"),
        "max_version": _extract_version_bound(entity, "max"),
        "is_required": entity.get("required"),
        "is_multibind_allowed": entity.get("multibind"),
        "default": entity.get("default"),
    }

    return ImportDefinition(**_drop_unset(result))


def _extract_exports(entity: dict) -> list | None:
    exports = entity.get("export")
    if exports is None:
        return None

    return _ensure_list(exports)


def _extract_actions(entity: dict, context: dict) -> list[ActionDefinition] | None:
    actions = entity.get("actions")
    if actions is None:
        return None

    return [_extract_action(action, context) for action in _to_named_list(actions)]


def _extract_action(entity, context):
    # thou we rely on default from definition classes,
    # specifics of availability states detection force to duplicate default in here
    defaults_for_available_at = {"states": [], "multi_states": "any"}
    defaults_for_unavailable_at = {"states": [], "multi_states": []}

    entity = _states_to_masking(_universalise_action_types(entity))

    result = {
        "config": _extract_config(entity, context),
        "scripts": _extract_scripts(entity, context),
        "available_at": _extract_action_availability(entity, "available", defaults_for_available_at),
        "unavailable_at": _extract_action_availability(entity, "unavailable", defaults_for_unavailable_at),
        "on_success": _extract_action_completion(entity, "on_success"),
        "on_fail": _extract_action_completion(entity, "on_fail"),
    }

    _fill_value(result, entity, "type")
    _fill_value(result, entity, "name")
    _fill_value(result, entity, "description")
    _fill_value(result, entity, "ui_options")
    _fill_value(result, entity, "allow_to_terminate")
    _fill_value(result, entity, "allow_for_action_host_group")
    _fill_value(result, entity, "allow_in_maintenance_mode")
    _fill_value(result, entity, "venv")
    _fill_value(result, entity, "partial_execution")
    _fill_value(result, entity, "is_host_action", source_keys=("host_action",))
    _fill_value(result, entity, "hostcomponentmap", source_keys=("hc_acl",))
    _fill_value(result, entity, "config_jinja", cast=partial(_normalize_path, context=context))
    _fill_value(result, entity, "scripts_jinja", cast=partial(_normalize_path, context=context))

    _patch_display_name(result, entity)

    return ActionDefinition(**_drop_unset(result))


def _extract_scripts(entity: dict, context: dict) -> list[JobSpec] | None:
    scripts = entity.get("scripts")
    if scripts is None:
        return None

    scripts_list = []

    for script in map(_flatten_on_fail, scripts):
        result = {}

        _fill_value(result, script, "name")
        _fill_value(result, script, "params")
        _fill_value(result, script, "state_on_fail")
        _fill_value(result, script, "multi_state_on_fail_set")
        _fill_value(result, script, "multi_state_on_fail_unset")
        _fill_value(result, script, "allow_to_terminate")
        _fill_value(result, script, "script", cast=partial(_normalize_path, context=context))
        _fill_value(result, script, "script_type", cast=ScriptType)

        _patch_display_name(result, script)

        # set defaults before cleanup
        scripts_list.append(JobSpec(**_drop_unset({"params": {}, "allow_to_terminate": False} | result)))

    return scripts_list


def _extract_config(entity: dict, context: dict) -> ConfigDefinition | None:
    config = entity.get("config")
    if config is None:
        return None

    flat_config = dict(__iterate_parameters(group=config, key=()))
    return _to_config_definition(flat_config, context)


def _extract_upgrades(entity: dict, context: dict) -> list[UpgradeDefinition] | None:
    upgrades = entity.get("upgrade")
    if upgrades is None:
        return None

    upgrades_list = []

    for upgrade in upgrades:
        result = {}

        _fill_value(result, upgrade, "name", cast=str)
        _fill_value(result, upgrade, "description")
        _fill_value(result, upgrade, "state_available", source_keys=("states", "available"))
        _fill_value(result, upgrade, "state_on_success", source_keys=("states", "on_success"))

        result["restrictions"] = UpgradeRestrictions(
            **_drop_unset(
                {
                    "min_version": _extract_version_bound(upgrade, "min"),
                    "max_version": _extract_version_bound(upgrade, "max"),
                    "from_editions": upgrade.get("from_edition"),
                }
            )
        )

        if "scripts" in upgrade:
            result["action"] = _extract_action(upgrade, context)

        _patch_display_name(result, upgrade)

        upgrades_list.append(UpgradeDefinition(**_drop_unset(result)))

    return upgrades_list


# Generic Steps


def _to_named_list(result: dict[str, dict]) -> list[dict]:
    return [{"name": key, **value} for key, value in result.items()]


def _ensure_list(result: list | Any) -> list:
    if not isinstance(result, list):
        return [result]

    return result


def _normalize_path(result: str, context: dict) -> str:
    path_from_root = detect_relative_path_to_bundle_root(context["path"], result)
    return str(path_from_root)


# Specific Steps


def _patch_upgrade_action_names(result: Definition) -> Definition:
    if not result.upgrades:
        return result

    owner = result

    for upgrade in result.upgrades:
        if not upgrade.action:
            continue

        min_ = upgrade.restrictions.min_version
        max_ = upgrade.restrictions.max_version

        # ! second strict is taken from min_ too,
        # ! because this error was in old code
        # ! => fixing it requires migrations
        versions = f"{min_.value}_strict_{min_.is_strict}-" f"{max_.value}_strict_{min_.is_strict}"
        editions = f"editions-{'_'.join(upgrade.restrictions.from_editions)}"
        available = f"state_available-{'_'.join(upgrade.state_available)}"
        on_success = f"state_on_success-{upgrade.state_on_success}"

        parts = (
            owner.name,
            owner.version,
            owner.edition,
            "upgrade",
            upgrade.name,
            versions,
            editions,
            available,
            on_success,
        )

        name = "_".join(map(str, parts))
        name = re.sub(r"\s+", "_", name).strip().lower()
        name = re.sub(r"[()]", "", name)

        upgrade.action.name = name
        upgrade.action.display_name = f"Upgrade: {upgrade.name}"

    return result


def _extract_license(result: dict, context: dict) -> License | None:
    license_path = result.get("license")
    if not license_path:
        return None

    return License(status="unaccepted", path=_normalize_path(license_path, context=context))


def _universalise_action_types(result: dict):
    if "type" not in result:
        # upgrade case
        return result | {"type": "task"}

    if result.get("type") == "job":
        return result | {"scripts": (result,)}

    if "scripts" not in result:
        result["scripts"] = ()

    return result


def _states_to_masking(result: dict):
    if "states" not in result or "masking" in result:
        return result

    states = result["states"]

    extra = {
        "masking": {
            "state": {
                # logic is different here for states:
                # if states isn't specified (no masking either),
                # action isn't available in any states
                "available": states.get("available", [])
            }
        },
    }

    if on_success := states.get("on_success"):
        extra["on_success"] = {"state": on_success}

    if on_fail := states.get("on_fail"):
        extra["on_fail"] = {"state": on_fail}

    return result | extra


def _flatten_on_fail(result: dict) -> dict:
    on_fail = result.get("on_fail", {})
    if isinstance(on_fail, str):
        on_fail: dict = {"state": on_fail}

    extra_fields = {}

    extra_fields["state_on_fail"] = on_fail.get("state", "")

    multi_state = on_fail.get("multi_state", {})
    extra_fields["multi_state_on_fail_set"] = multi_state.get("set", [])
    extra_fields["multi_state_on_fail_unset"] = multi_state.get("unset", [])

    return result | extra_fields


def _extract_version_bound(entry: dict, x: Literal["min", "max"]) -> VersionBound | None:
    strict_key = f"{x}_strict"

    versions = entry.get("versions")
    if versions is None:
        return None

    if x in versions:
        return VersionBound(value=str(versions[x]), is_strict=False)

    if strict_key in versions:
        return VersionBound(value=str(versions[strict_key]), is_strict=True)

    return None


def _extract_action_availability(entity: dict, x: Literal["available", "unavailable"], defaults: dict):
    masking = entity.get("masking")
    if masking is None:
        return None

    result = {}

    _fill_value(result, masking, "states", source_keys=("state", x))
    _fill_value(result, masking, "multi_states", source_keys=("multi_state", x))

    return ActionAvailability(**_drop_unset(defaults | result))


def _extract_action_completion(entity: dict, outcome: Literal["on_success", "on_fail"]):
    on_outcome = entity.get(outcome)
    if on_outcome is None:
        return None

    result = {}

    _fill_value(result, on_outcome, "set_state", source_keys=("state",))
    _fill_value(result, on_outcome, "set_multi_state", source_keys=("multi_state", "set"))
    _fill_value(result, on_outcome, "unset_multi_state", source_keys=("multi_state", "unset"))

    return OnCompletion(**_drop_unset(result))


def _to_config_definition(result: dict[ParameterKey, dict], context: dict) -> ConfigDefinition:
    parameters = {}
    values = {}
    attrs = {}

    bundle_root = Path(context["bundle_root"])

    for key, param in result.items():
        param_context = {"_param_key": key}
        spec = _extract_spec(param, context | param_context)

        # > Fine-tuning (patching spec) section

        if "file" in spec.type and spec.default:
            normalized_default = _normalize_path(spec.default, context)
            param["default"] = normalized_default
            spec.default = normalized_default
        elif spec.type == "structure":
            # simply load file, checks will be performed later
            yspec_path = _normalize_path(param["yspec"], context)
            schema = load_yspec(bundle_root / yspec_path)
            spec.limits["yspec"] = schema
        elif spec.type == "variant":
            spec.limits["source"] = check_variant(param)

        if param.get("activatable"):
            active = param.get("active", False)
            attrs[key] = {"active": active}
            spec.limits["active"] = active

        # < Fine-tuning finished

        parameters[key] = spec

        default_value = param.get("default")
        if default_value is not None:
            values[key] = default_value

    return ConfigDefinition(parameters=parameters, default_values=values, default_attrs=attrs)


def _extract_spec(entity: dict, context: dict) -> ConfigParamPlainSpec:
    result = {"key": context["_param_key"]}

    limits = _drop_unset(
        {
            "min": entity.get("min"),
            "max": entity.get("max"),
            "pattern": entity.get("pattern"),
            "option": entity.get("option"),
            "activatable": entity.get("activatable"),
        }
    )
    _fill_value(limits, entity, "read_only")
    _fill_value(limits, entity, "writable")
    if limits:
        result["limits"] = limits

    _fill_value(result, entity, "type")
    _fill_value(result, entity, "description")
    _fill_value(result, entity, "required")
    _fill_value(result, entity, "ui_options")
    _fill_value(result, entity, "default")

    result["group_customization"] = entity.get(
        "group_customization", context["object"].get("config_group_customization")
    )

    _patch_display_name(result, entity)

    return ConfigParamPlainSpec(**_drop_unset(result))


def __iterate_parameters(group: list[dict], key: ParameterKey) -> Iterable[tuple[ParameterKey, dict]]:
    for param in group:
        param_key = (*key, str(param["name"]))

        yield param_key, param

        if param["type"] == "group":
            yield from __iterate_parameters(group=param["subs"], key=param_key)


# Utils


def _patch_display_name(target: dict, source: dict) -> None:
    target["display_name"] = source.get("display_name") or source["name"]


def _drop_unset(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _fill_value(
    target: dict, source: dict, key: str, source_keys: tuple[str, ...] | None = None, cast: Callable | None = None
) -> None:
    source_keys = source_keys or (key,)

    value = source
    for k in source_keys:
        value = value.get(k)
        if value is None:
            break

    if value is None:
        return

    if cast:
        value = cast(value)

    target[key] = value
