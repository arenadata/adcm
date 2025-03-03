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

from pathlib import Path
from typing import Any, Iterable, Literal
import re

import yaml

from core.bundle_alt._extract import (
    Step,
    any_true,
    cast,
    compose,
    const,
    each,
    either,
    extract,
    from_context,
    get,
    is_set,
    to,
    when,
    with_defaults,
)
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
    convert = _prepare_converter()

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

    definition: Definition = convert(plain_entity, context)

    return definition


# Converter

_patch_display_name = either(get("display_name"), get("name"))


def _prepare_converter() -> Step:
    extract_config = compose(get("config"), _to_flat_config_dict, _to_config_definition)

    extract_job_spec = compose(
        _flatten_on_fail,
        extract(
            {
                ".": (
                    "name",
                    "params",
                    "state_on_fail",
                    "multi_state_on_fail_set",
                    "multi_state_on_fail_unset",
                    "allow_to_terminate",
                ),
                "display_name": _patch_display_name,
                "script": (get("script"), _normalize_path),
                "script_type": (get("script_type"), cast(ScriptType)),
            }
        ),
        # thou most definitions has defaults, JobSpec doesn't,
        # so for a time being we'll provide it in here
        with_defaults({"params": {}, "allow_to_terminate": False}),
        to(JobSpec),
    )

    # thou we rely on default from definition classes,
    # specifics of availability states detection force to duplicate default in here
    defaults_for_available_at = {"states": [], "multi_states": "any"}
    defaults_for_unavailable_at = {"states": [], "multi_states": []}

    extract_action = compose(
        _universalise_action_types,
        _states_to_masking,
        extract(
            {
                ".": (
                    "type",
                    "name",
                    "description",
                    "ui_options",
                    "allow_to_terminate",
                    "allow_for_action_host_group",
                    "allow_in_maintenance_mode",
                    "venv",
                    "partial_execution",
                ),
                "display_name": _patch_display_name,
                "hostcomponentmap": get("hc_acl"),
                "config": extract_config,
                "config_jinja": (get("config_jinja"), _normalize_path),
                "scripts": (get("scripts"), each(extract_job_spec)),
                "scripts_jinja": (get("scripts_jinja"), _normalize_path),
                "available_at": _extract_action_availability("available", defaults_for_available_at),
                "unavailable_at": _extract_action_availability("unavailable", defaults_for_unavailable_at),
                "on_success": _extract_action_completion("on_success"),
                "on_fail": _extract_action_completion("on_fail"),
            }
        ),
        to(ActionDefinition),
    )

    extract_upgrade = compose(
        extract(
            {
                ".": ("name", "description"),
                "display_name": _patch_display_name,
                "state_available": (get("states"), get("available")),
                "state_on_success": (get("states"), get("on_success")),
                "restrictions": (
                    extract(
                        {
                            "min_version": _extract_version_bound("min"),
                            "max_version": _extract_version_bound("max"),
                            "from_editions": get("from_edition"),
                        }
                    ),
                    to(UpgradeRestrictions),
                ),
                "action": (when(is_set("scripts")), extract_action),
            }
        ),
        to(UpgradeDefinition),
    )

    return compose(
        extract(
            {
                ".": (
                    "name",
                    "type",
                    "description",
                    "edition",
                    "flag_autogeneration",
                    "venv",
                    "shared",
                    "requried",
                    "monitoring",
                    # propagate?
                    "config_group_customization",
                    "allow_maintenance_mode",
                    "constraint",
                    "bound_to",
                    "requires",
                ),
                "display_name": _patch_display_name,
                "path": from_context("path"),
                "adcm_min_version": (get("adcm_min_version"), cast(str)),
                "version": (get("version"), cast(str)),
                "config": extract_config,
                "upgrades": (get("upgrade"), each(extract_upgrade)),
                "license": _extract_license,
                "actions": (get("actions"), _to_named_list, each(extract_action)),
                "imports": (get("imports"), _to_named_list),
                "exports": (get("export"), _ensure_list),
            }
        ),
        to(Definition),
        # have to patch it afterwards due to lack of data before
        _patch_upgrade_action_names,
    )


# Generic Steps


def _to_named_list(result: dict[str, dict], _) -> list[dict]:
    return [{"name": key, **value} for key, value in result.items()]


def _ensure_list(result: list | Any, _) -> list:
    if not isinstance(result, list):
        return [result]

    return result


def _normalize_path(result: str, context: dict) -> str:
    # todo add check for "correct form" in parsing stage
    path_from_root = detect_relative_path_to_bundle_root(context["path"], result)
    return str(path_from_root)


def _from_object(key: str):
    return lambda _, c: c["object"].get(key)


# Specific Steps


def _patch_upgrade_action_names(result: Definition, _: dict) -> Definition:
    if not result.upgrades:
        return result

    owner = result

    for upgrade in result.upgrades:
        if not upgrade.action:
            continue

        min_ = upgrade.restrictions.min_version
        max_ = upgrade.restrictions.max_version

        versions = f"{min_.value}_strict_{min_.is_strict}-" f"{max_.value}_strict_{max_.is_strict}"
        editions = f"editions-{'_'.join(upgrade.restrictions.from_editions)}"
        available = f"state_available-{'_'.join(upgrade.state_available)}"
        on_success = f"state_on_success-{upgrade.state_on_success}"

        parts = (
            owner.name,
            owner.version,
            # todo add edition to def
            owner.edition,
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

    return License(status="unaccepted", path=_normalize_path(context["path"], license_path))


def _universalise_action_types(result: dict, _: dict):
    if "type" not in result:
        # upgrade case
        return result | {"type": "task"}

    if result.get("type") == "job":
        return result | {"scripts": (result,)}

    if "scripts" not in result:
        result["scripts"] = ()

    return result


def _states_to_masking(result: dict, _):
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
        }
    }

    if on_success := states.get("on_success"):
        extra["on_success"] = on_success

    if on_fail := states.get("on_fail"):
        extra["on_fail"] = on_fail

    return result | extra


def _flatten_on_fail(result: dict, _) -> dict:
    on_fail = result.get("on_fail", {})
    if isinstance(on_fail, str):
        on_fail: dict = {"state": on_fail}

    extra_fields = {}

    extra_fields["state_on_fail"] = on_fail.get("state", "")

    multi_state = on_fail.get("multi_state", {})
    extra_fields["multi_state_on_fail_set"] = multi_state.get("set", [])
    extra_fields["multi_state_on_fail_unset"] = multi_state.get("unset", [])

    return result | extra_fields


def _extract_version_bound(x: Literal["min", "max"]) -> tuple:
    strict_key = f"{x}_strict"
    return (
        get("versions"),
        when(any_true(is_set(x), is_set(strict_key))),
        extract({"value": compose(either(get(x), get(strict_key)), cast(str)), "is_strict": is_set(strict_key)}),
        to(VersionBound),
    )


def _extract_action_availability(x: Literal["available", "unavailable"], defaults: dict):
    return (
        either(
            compose(
                get("masking"),
                extract(
                    {
                        "states": (get("state"), get(x)),
                        "multi_states": (get("multi_state"), get(x)),
                    }
                ),
                with_defaults(defaults),
            ),
            const(defaults),
        ),
        to(ActionAvailability),
    )


def _extract_action_completion(outcome: Literal["on_success", "on_fail"]):
    return (
        get("masking"),
        extract(
            {
                "set_state": (get(outcome), get("state")),
                "set_multi_state": (get(outcome), get("multi_state"), get("set")),
                "unset_multi_state": (get(outcome), get("multi_state"), get("unset")),
            }
        ),
        to(OnCompletion),
    )


def _to_flat_config_dict(result: list[dict], _) -> dict[ParameterKey, dict]:
    return dict(__iterate_parameters(group=result, key=()))


def _to_config_definition(result: dict[ParameterKey, dict], context: dict) -> ConfigDefinition:
    extract_spec = compose(
        extract(
            {
                ".": (
                    "type",
                    "description",
                    "required",
                    "ui_options",
                    "default",
                    "read_only",
                    "writable",
                ),
                "key": from_context("_param_key"),
                "display_name": _patch_display_name,
                "group_customization": either(get("group_customization"), _from_object("config_group_customization")),
                "limits": extract({".": ("min", "max", "pattern", "option", "activatable")}),
            }
        ),
        to(ConfigParamPlainSpec),
    )

    parameters = {}
    values = {}
    attrs = {}

    bundle_root = Path(context["bundle_root"])

    for key, param in result.items():
        param_context = {"_param_key": key}
        spec = extract_spec(param, context | param_context)

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


def __iterate_parameters(group: list[dict], key: ParameterKey) -> Iterable[tuple[ParameterKey, dict]]:
    for param in group:
        param_key = (*key, str(param["name"]))

        yield param_key, param

        if param["type"] == "group":
            yield from __iterate_parameters(group=param["subs"], key=param_key)
