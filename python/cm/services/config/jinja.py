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
from typing import Any

from core.bundle_alt.process import ConfigJinjaContext
from core.errors import localize_error
from django.conf import settings
from yaml import safe_load

from cm.models import (
    Action,
    Cluster,
    Component,
    Host,
    PrototypeConfig,
    Service,
)
from cm.services.bundle import BundlePathResolver, detect_relative_path_to_bundle_root
from cm.services.bundle_alt.load import parse_config_jinja
from cm.services.config.patterns import Pattern
from cm.services.jinja_env import get_env_for_jinja_config
from cm.services.template import TemplateBuilder


def get_jinja_config(
    action: Action, cluster_relative_object: Cluster | Service | Component | Host
) -> tuple[list[PrototypeConfig], dict[str, Any]]:
    resolver = BundlePathResolver(bundle_hash=action.prototype.bundle.hash)
    jinja_conf_file = resolver.resolve(action.config_jinja)

    template_builder = TemplateBuilder(
        template_path=jinja_conf_file,
        context=get_env_for_jinja_config(action=action, cluster_relative_object=cluster_relative_object),
        bundle_path=resolver.bundle_root,
    )

    # too difficult for now to pass headers from all usages
    # As part of the ADCM-6747 task, we are leaving the old mechanism
    # for preparing the configuration from the jinja file.
    # use_new_approach = use_new_bundle_parsing_approach(env=os.environ, headers={})
    use_new_approach = False

    if not use_new_approach:
        return _get_jinja_config_old(
            data=template_builder.data, action=action, config_file=jinja_conf_file, resolver=resolver
        )

    return _get_jinja_config_new(
        data=template_builder.data,
        action=action,
        config_file=jinja_conf_file,
        resolver=resolver,
        object_=cluster_relative_object,
    )


def _get_jinja_config_new(data: list[dict], action: Action, config_file: Path, resolver: BundlePathResolver, object_):
    context = ConfigJinjaContext(
        bundle_root=resolver.bundle_root,
        path=str(config_file.parent.relative_to(resolver.bundle_root)),
        object={"config_group_customization": False},
    )

    proto = object_.prototype
    with localize_error(f'Object of type {proto.type} named "{proto.name}", version {proto.version}'):
        configs = parse_config_jinja(data=data, context=context, prototype=action.prototype, action=action)

    return configs, {}


def _get_jinja_config_old(
    data: list[dict], action: Action, config_file: Path, resolver: BundlePathResolver
) -> tuple[list[PrototypeConfig], dict]:
    configs = []
    attr = {}

    for field in data:
        for normalized_field in _normalize_field(
            field=field, dir_with_config=config_file.parent.relative_to(resolver.bundle_root), resolver=resolver
        ):
            configs.append(PrototypeConfig(prototype=action.prototype, action=action, **normalized_field))

            if (
                normalized_field["type"] == "group"
                and "activatable" in normalized_field["limits"]
                and "active" in normalized_field["limits"]
                and normalized_field.get("name")
            ):
                attr[normalized_field["name"]] = normalized_field["limits"]

    return configs, attr


def _normalize_field(
    field: dict, dir_with_config: Path, resolver: BundlePathResolver, name: str = "", subname: str = ""
) -> list[dict]:
    """`dir_with_config` should be relative to bundle root"""
    normalized_field = {}
    normalized_fields = [normalized_field]

    name = name or field["name"]
    normalized_field["name"] = name

    if subname:
        normalized_field["subname"] = subname
    else:
        normalized_field["subname"] = ""

    if field.get("display_name") is None:
        normalized_field["display_name"] = subname or name
    else:
        normalized_field["display_name"] = field["display_name"]

    normalized_field["limits"] = _get_limits(field=field, dir_with_config=dir_with_config, resolver=resolver)

    if field["type"] in settings.STACK_FILE_FIELD_TYPES and field.get("default"):
        normalized_field["default"] = str(
            detect_relative_path_to_bundle_root(source_file_dir=dir_with_config, raw_path=field["default"])
        )
    else:
        normalized_field["default"] = field.get("default", "")

    normalized_field["type"] = field["type"]
    normalized_field["description"] = field.get("description", "")
    normalized_field["group_customization"] = field.get("group_customization", None)
    normalized_field["required"] = field.get("required", True)
    normalized_field["ui_options"] = field.get("ui_options", {})
    normalized_field["ansible_options"] = field.get("ansible_options", {})

    if "subs" in field:
        for sub in field["subs"]:
            normalized_fields.extend(
                _normalize_field(
                    field=sub,
                    dir_with_config=dir_with_config,
                    resolver=resolver,
                    name=name,
                    subname=sub["name"],
                ),
            )

    return normalized_fields


def _get_limits(field: dict, dir_with_config: Path, resolver: BundlePathResolver) -> dict:
    limits = {}

    if "pattern" in field:
        if field["type"] not in ("string", "text", "password", "secrettext"):
            message = f"Incorrectly rendered `config_jinja` file. `pattern` is not allowed in {field['type']}"
            raise RuntimeError(message)

        pattern = Pattern(regex_pattern=field.pop("pattern"))
        if not pattern.is_valid:
            display_name = field.get("display_name", field["name"])
            message = f"The pattern attribute value of {display_name} config parameter is not valid regular expression"
            raise RuntimeError(message)

        default = field.get("default")
        if default is not None and not pattern.matches(str(default)):
            display_name = field.get("display_name", field["name"])
            message = f"Default attribute value of {display_name} config parameter does not match pattern"
            raise RuntimeError(message)

        limits["pattern"] = pattern.raw

    if "yspec" in field and field["type"] in settings.STACK_COMPLEX_FIELD_TYPES:
        spec_path = detect_relative_path_to_bundle_root(source_file_dir=dir_with_config, raw_path=field["yspec"])
        limits["yspec"] = safe_load(stream=resolver.resolve(spec_path).read_text(encoding="utf-8"))

    if "option" in field and field["type"] == "option":
        limits["option"] = field["option"]

    if "source" in field and field["type"] == "variant":
        variant_type = field["source"]["type"]
        source = {"type": variant_type, "args": None}

        source["strict"] = field["source"].get("strict", True)

        if variant_type == "inline":
            source["value"] = field["source"]["value"]
        elif variant_type in ("config", "builtin"):
            source["name"] = field["source"]["name"]

        if variant_type == "builtin" and "args" in field["source"]:
            source["args"] = field["source"]["args"]

        limits["source"] = source

    if "activatable" in field and field["type"] == "group":
        limits.update(
            activatable=field["activatable"],
            active=False,
        )

        if "active" in field:
            limits.update(active=field["active"])

    if field["type"] in settings.STACK_NUMERIC_FIELD_TYPES:
        if "min" in field:
            limits["min"] = field["min"]

        if "max" in field:
            limits["max"] = field["max"]

    for label in ("read_only", "writable"):
        if label in field:
            limits[label] = field[label]

    return limits
